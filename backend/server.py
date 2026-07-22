from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import re
import csv
import uuid
import logging
import secrets
import unicodedata
from datetime import datetime, timezone, timedelta, date
from io import StringIO
from typing import List, Optional, Literal

import bcrypt
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"

app = FastAPI(title="Arcoins API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arcoins")


def now_utc():
    return datetime.now(timezone.utc)


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def create_token(user_id: str, role: str) -> str:
    payload = {"sub": user_id, "role": role, "exp": now_utc() + timedelta(days=7), "iat": now_utc()}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(401, "Não autenticado")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token inválido")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "Usuário não encontrado")
    return user


def require_roles(*roles: str):
    async def checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(403, "Acesso negado para este perfil")
        return user
    return checker


Role = Literal["student", "teacher", "admin"]


class LoginInput(BaseModel):
    email: str
    password: str


class ChallengeCreate(BaseModel):
    title: str
    description: str
    reward: float
    class_id: Optional[str] = None


class StoreItemInput(BaseModel):
    name: str
    description: str
    price: float
    image: Optional[str] = None
    stock: int = 100


class CreateUserInput(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["student", "teacher", "admin"]
    class_id: Optional[str] = None
    initial_balance: Optional[float] = 0
    initial_savings: Optional[float] = 0


class CreateClassInput(BaseModel):
    name: str
    teacher_id: Optional[str] = None


class VoucherCreate(BaseModel):
    value: float
    description: Optional[str] = ""
    code: Optional[str] = None
    class_id: Optional[str] = None
    max_uses: Optional[int] = 1
    expires_at: Optional[str] = None  # ISO date string YYYY-MM-DD or full ISO


class VoucherUpdate(BaseModel):
    value: Optional[float] = None
    description: Optional[str] = None
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None
    active: Optional[bool] = None


class VoucherRedeem(BaseModel):
    code: str


class TransferInput(BaseModel):
    ra: str
    amount: float
    message: Optional[str] = ""


class AttendanceMark(BaseModel):
    class_id: str
    date: str  # YYYY-MM-DD
    present_ids: List[str] = []
    absent_ids: List[str] = []


class PurchaseInput(BaseModel):
    item_id: str


class SavingsInput(BaseModel):
    amount: float


class ConfigModel(BaseModel):
    daily_allowance: float = 10.0
    savings_rate: float = 0.02
    attendance_required: Optional[bool] = False


async def add_transaction(user_id: str, ttype: str, amount: float, description: str, meta: dict = None):
    txn = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": ttype,
        "amount": amount,
        "description": description,
        "created_at": now_utc().isoformat(),
        "meta": meta or {},
    }
    await db.transactions.insert_one(txn)
    await db.users.update_one({"id": user_id}, {"$inc": {"balance": amount}})
    return txn


async def user_to_public(u: dict) -> dict:
    return {
        "id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"],
        "avatar": u.get("avatar"), "class_id": u.get("class_id"),
        "balance": round(u.get("balance", 0), 2),
        "savings": round(u.get("savings", 0), 2),
        "ra": u.get("ra"),
        "password_locked": bool(u.get("password_locked", False)),
    }


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_first_name(full_name: str) -> str:
    base = strip_accents(full_name.strip()).lower()
    parts = re.findall(r"[a-z0-9]+", base)
    return parts[0] if parts else "aluno"


def gen_voucher_code(length: int = 6) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@api.post("/auth/login")
async def login(payload: LoginInput, response: Response):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "E-mail ou senha inválidos")
    token = create_token(user["id"], user["role"])
    response.set_cookie("access_token", token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    return {"token": token, "user": await user_to_public(user)}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    full = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return await user_to_public(full)


@api.get("/student/transactions")
async def my_transactions(user: dict = Depends(require_roles("student"))):
    txns = await db.transactions.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return txns


@api.get("/student/challenges")
async def available_challenges(user: dict = Depends(require_roles("student"))):
    q = {"active": True, "$or": [{"class_id": user.get("class_id")}, {"class_id": None}]}
    challs = await db.challenges.find(q, {"_id": 0}).sort("created_at", -1).to_list(100)
    subs = await db.submissions.find({"student_id": user["id"]}, {"_id": 0}).to_list(500)
    sub_map = {s["challenge_id"]: s for s in subs}
    for c in challs:
        s = sub_map.get(c["id"])
        c["submission_status"] = s["status"] if s else None
    return challs


@api.post("/student/challenges/{challenge_id}/submit")
async def submit_challenge(challenge_id: str, user: dict = Depends(require_roles("student"))):
    ch = await db.challenges.find_one({"id": challenge_id, "active": True})
    if not ch:
        raise HTTPException(404, "Desafio não encontrado")
    existing = await db.submissions.find_one({"challenge_id": challenge_id, "student_id": user["id"]})
    if existing and existing["status"] in ("pending", "approved"):
        raise HTTPException(400, "Você já enviou este desafio")
    sub = {
        "id": str(uuid.uuid4()),
        "challenge_id": challenge_id, "student_id": user["id"],
        "status": "pending", "created_at": now_utc().isoformat(), "reviewed_at": None,
    }
    await db.submissions.insert_one(sub)
    sub.pop("_id", None)
    return sub


@api.get("/student/store")
async def list_store(user: dict = Depends(get_current_user)):
    items = await db.store_items.find({"active": True}, {"_id": 0}).to_list(200)
    return items


@api.post("/student/store/buy")
async def buy_item(payload: PurchaseInput, user: dict = Depends(require_roles("student"))):
    item = await db.store_items.find_one({"id": payload.item_id, "active": True})
    if not item:
        raise HTTPException(404, "Item não encontrado")
    if item["stock"] <= 0:
        raise HTTPException(400, "Item esgotado")
    fresh = await db.users.find_one({"id": user["id"]})
    if fresh["balance"] < item["price"]:
        raise HTTPException(400, "Saldo insuficiente")
    await db.store_items.update_one({"id": item["id"]}, {"$inc": {"stock": -1}})
    txn = await add_transaction(user["id"], "purchase", -item["price"], f"Compra: {item['name']}", {"item_id": item["id"]})
    await db.purchases.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "item_id": item["id"],
        "item_name": item["name"], "price": item["price"], "created_at": now_utc().isoformat(),
    })
    return {"ok": True, "transaction": {k: v for k, v in txn.items() if k != "_id"}}


@api.post("/student/savings/deposit")
async def savings_deposit(payload: SavingsInput, user: dict = Depends(require_roles("student"))):
    if payload.amount <= 0:
        raise HTTPException(400, "Valor inválido")
    fresh = await db.users.find_one({"id": user["id"]})
    if fresh["balance"] < payload.amount:
        raise HTTPException(400, "Saldo insuficiente")
    await add_transaction(user["id"], "savings_deposit", -payload.amount, "Depósito na poupança")
    await db.users.update_one({"id": user["id"]}, {"$inc": {"savings": payload.amount}})
    return {"ok": True}


@api.post("/student/savings/withdraw")
async def savings_withdraw(payload: SavingsInput, user: dict = Depends(require_roles("student"))):
    if payload.amount <= 0:
        raise HTTPException(400, "Valor inválido")
    fresh = await db.users.find_one({"id": user["id"]})
    if fresh.get("savings", 0) < payload.amount:
        raise HTTPException(400, "Poupança insuficiente")
    await db.users.update_one({"id": user["id"]}, {"$inc": {"savings": -payload.amount}})
    await add_transaction(user["id"], "savings_withdraw", payload.amount, "Resgate da poupança")
    return {"ok": True}


@api.get("/teacher/classes")
async def my_classes(user: dict = Depends(require_roles("teacher", "admin"))):
    q = {} if user["role"] == "admin" else {"teacher_id": user["id"]}
    classes = await db.classes.find(q, {"_id": 0}).to_list(100)
    for c in classes:
        c["student_count"] = await db.users.count_documents({"class_id": c["id"], "role": "student"})
    return classes


@api.get("/teacher/students")
async def list_my_students(user: dict = Depends(require_roles("teacher", "admin"))):
    if user["role"] == "admin":
        class_ids = [c["id"] for c in await db.classes.find({}, {"_id": 0, "id": 1}).to_list(100)]
    else:
        class_ids = [c["id"] for c in await db.classes.find({"teacher_id": user["id"]}, {"_id": 0, "id": 1}).to_list(100)]
    students = await db.users.find(
        {"role": "student", "class_id": {"$in": class_ids}},
        {"_id": 0, "password_hash": 0},
    ).to_list(500)
    return students


@api.post("/teacher/challenges")
async def create_challenge(payload: ChallengeCreate, user: dict = Depends(require_roles("teacher", "admin"))):
    ch = {
        "id": str(uuid.uuid4()), "title": payload.title, "description": payload.description,
        "reward": payload.reward, "created_by": user["id"], "class_id": payload.class_id,
        "active": True, "created_at": now_utc().isoformat(),
    }
    await db.challenges.insert_one(ch)
    ch.pop("_id", None)
    return ch


@api.get("/teacher/submissions")
async def pending_submissions(user: dict = Depends(require_roles("teacher", "admin"))):
    q = {} if user["role"] == "admin" else {"created_by": user["id"]}
    challenges = await db.challenges.find(q, {"_id": 0}).to_list(500)
    ch_map = {c["id"]: c for c in challenges}
    subs = await db.submissions.find(
        {"challenge_id": {"$in": list(ch_map.keys())}, "status": "pending"}, {"_id": 0}
    ).to_list(500)
    student_ids = list({s["student_id"] for s in subs})
    students = await db.users.find({"id": {"$in": student_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(500)
    st_map = {s["id"]: s["name"] for s in students}
    for s in subs:
        s["challenge_title"] = ch_map.get(s["challenge_id"], {}).get("title", "")
        s["reward"] = ch_map.get(s["challenge_id"], {}).get("reward", 0)
        s["student_name"] = st_map.get(s["student_id"], "")
    return subs


@api.post("/teacher/submissions/{submission_id}/review")
async def review_submission(submission_id: str, approve: bool, user: dict = Depends(require_roles("teacher", "admin"))):
    sub = await db.submissions.find_one({"id": submission_id})
    if not sub:
        raise HTTPException(404, "Submissão não encontrada")
    if sub["status"] != "pending":
        raise HTTPException(400, "Submissão já revisada")
    ch = await db.challenges.find_one({"id": sub["challenge_id"]})
    if not ch:
        raise HTTPException(404, "Desafio não encontrado")
    status = "approved" if approve else "rejected"
    await db.submissions.update_one(
        {"id": submission_id},
        {"$set": {"status": status, "reviewed_at": now_utc().isoformat()}},
    )
    if approve:
        await add_transaction(
            sub["student_id"], "challenge", ch["reward"], f"Desafio concluído: {ch['title']}",
            {"challenge_id": ch["id"]},
        )
    return {"ok": True, "status": status}


@api.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_roles("admin"))):
    total_students = await db.users.count_documents({"role": "student"})
    total_teachers = await db.users.count_documents({"role": "teacher"})
    total_challenges = await db.challenges.count_documents({"active": True})
    total_items = await db.store_items.count_documents({"active": True})
    agg = db.users.aggregate([
        {"$match": {"role": "student"}},
        {"$group": {"_id": None, "total": {"$sum": "$balance"}, "savings": {"$sum": "$savings"}}}
    ])
    circ = 0
    sav = 0
    async for row in agg:
        circ = row.get("total", 0)
        sav = row.get("savings", 0)
    purchases_count = await db.purchases.count_documents({})
    return {
        "students": total_students, "teachers": total_teachers,
        "active_challenges": total_challenges, "store_items": total_items,
        "arc_in_circulation": round(circ, 2), "arc_in_savings": round(sav, 2),
        "total_purchases": purchases_count,
    }


@api.get("/admin/users")
async def all_users(user: dict = Depends(require_roles("admin"))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return users


@api.post("/admin/users")
async def create_user(payload: CreateUserInput, user: dict = Depends(require_roles("admin"))):
    email = payload.email.lower().strip()
    if len(payload.password) < 4:
        raise HTTPException(400, "Senha muito curta (mínimo 4 caracteres)")
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(400, "E-mail já cadastrado")
    if payload.role == "student" and payload.class_id:
        klass = await db.classes.find_one({"id": payload.class_id})
        if not klass:
            raise HTTPException(400, "Turma inválida")
    avatar_seed = payload.name.replace(" ", "") or email
    avatar_style = "adventurer" if payload.role == "student" else "avataaars"
    uid = str(uuid.uuid4())
    initial_balance = float(payload.initial_balance or 0)
    initial_savings = float(payload.initial_savings or 0)
    doc = {
        "id": uid,
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name.strip(),
        "role": payload.role,
        "class_id": payload.class_id if payload.role == "student" else None,
        "avatar": f"https://api.dicebear.com/7.x/{avatar_style}/svg?seed={avatar_seed}",
        "balance": initial_balance,
        "savings": initial_savings,
        "created_at": now_utc().isoformat(),
    }
    await db.users.insert_one(doc)
    if payload.role == "student" and initial_balance > 0:
        await db.transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "type": "adjustment",
            "amount": initial_balance,
            "description": "Saldo inicial de boas-vindas",
            "created_at": now_utc().isoformat(),
            "meta": {},
        })
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    return doc


@api.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_roles("admin"))):
    if user_id == user["id"]:
        raise HTTPException(400, "Você não pode remover a si mesmo")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "Usuário não encontrado")
    await db.users.delete_one({"id": user_id})
    return {"ok": True}


@api.get("/admin/classes")
async def list_classes_admin(user: dict = Depends(require_roles("admin"))):
    classes = await db.classes.find({}, {"_id": 0}).to_list(200)
    for c in classes:
        c["student_count"] = await db.users.count_documents({"class_id": c["id"], "role": "student"})
    return classes


@api.post("/admin/classes")
async def create_class(payload: CreateClassInput, user: dict = Depends(require_roles("admin"))):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "Nome obrigatório")
    existing = await db.classes.find_one({"name": name})
    if existing:
        raise HTTPException(400, "Turma já existe")
    teacher_id = payload.teacher_id
    if teacher_id:
        t = await db.users.find_one({"id": teacher_id, "role": "teacher"})
        if not t:
            raise HTTPException(400, "Professor inválido")
    klass = {
        "id": str(uuid.uuid4()),
        "name": name,
        "teacher_id": teacher_id,
        "created_at": now_utc().isoformat(),
    }
    await db.classes.insert_one(klass)
    klass.pop("_id", None)
    return klass


# ---------- Bulk Import Students via CSV ----------
@api.post("/admin/students/bulk-import")
async def bulk_import_students(
    file: UploadFile = File(...),
    class_id: Optional[str] = Form(None),
    initial_balance: Optional[float] = Form(0),
    user: dict = Depends(require_roles("admin")),
):
    """
    Importa alunos via CSV. Cabeçalhos esperados (em qualquer ordem, case-insensitive):
    - nome (ou name)
    - ra (ou registration)
    Login do aluno = '@<primeiroNome>' (ou '@<primeiroNome>.<RA>' em caso de duplicidade).
    Senha do aluno = RA (sem possibilidade de troca).
    """
    if class_id:
        klass = await db.classes.find_one({"id": class_id})
        if not klass:
            raise HTTPException(400, "Turma inválida")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except Exception:
            raise HTTPException(400, "Não foi possível ler o CSV. Use codificação UTF-8.")

    sniffer = csv.Sniffer()
    sample = text[:2048]
    try:
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(400, "CSV vazio ou sem cabeçalho")

    # normalize headers
    headers = {h.strip().lower(): h for h in reader.fieldnames}
    name_key = headers.get("nome") or headers.get("name") or headers.get("aluno")
    ra_key = headers.get("ra") or headers.get("registration") or headers.get("matrícula") or headers.get("matricula")
    if not name_key or not ra_key:
        raise HTTPException(400, f"CSV precisa ter colunas 'nome' e 'ra'. Encontradas: {list(reader.fieldnames)}")

    created = []
    skipped = []
    initial_balance = float(initial_balance or 0)

    for idx, row in enumerate(reader, start=2):
        name = (row.get(name_key) or "").strip()
        ra = (row.get(ra_key) or "").strip()
        if not name or not ra:
            skipped.append({"line": idx, "reason": "nome ou RA vazio", "name": name, "ra": ra})
            continue
        if len(ra) < 3:
            skipped.append({"line": idx, "reason": "RA muito curto (mínimo 3 caracteres)", "name": name, "ra": ra})
            continue

        # Skip if RA already exists
        ra_exists = await db.users.find_one({"ra": ra})
        if ra_exists:
            skipped.append({"line": idx, "reason": "RA já cadastrado", "name": name, "ra": ra})
            continue

        # Generate login: @firstname, with RA suffix if duplicate
        first = normalize_first_name(name)
        candidate = f"@{first}"
        if await db.users.find_one({"email": candidate}):
            candidate = f"@{first}.{ra}"
            if await db.users.find_one({"email": candidate}):
                skipped.append({"line": idx, "reason": "login não pôde ser gerado (duplicado)", "name": name, "ra": ra})
                continue

        uid = str(uuid.uuid4())
        doc = {
            "id": uid,
            "email": candidate,                 # used as login key
            "password_hash": hash_password(ra),
            "name": name,
            "role": "student",
            "class_id": class_id,
            "ra": ra,
            "password_locked": True,            # student cannot change own password
            "avatar": f"https://api.dicebear.com/7.x/adventurer/svg?seed={first}{ra}",
            "balance": initial_balance,
            "savings": 0.0,
            "created_at": now_utc().isoformat(),
        }
        await db.users.insert_one(doc)
        if initial_balance > 0:
            await db.transactions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "type": "adjustment",
                "amount": initial_balance,
                "description": "Saldo inicial de boas-vindas",
                "created_at": now_utc().isoformat(),
                "meta": {},
            })
        created.append({"name": name, "ra": ra, "login": candidate})

    return {
        "ok": True,
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created": created,
        "skipped": skipped,
    }


# ---------- Vouchers ----------
def parse_expiry(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        if len(s) == 10:
            d = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(hours=23, minutes=59, seconds=59)
        else:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d.isoformat()
    except Exception:
        raise HTTPException(400, "Data de validade inválida (use YYYY-MM-DD)")


def voucher_status(v: dict) -> str:
    if not v.get("active", True):
        return "inactive"
    if v.get("expires_at"):
        try:
            exp = datetime.fromisoformat(v["expires_at"].replace("Z", "+00:00"))
            if exp < now_utc():
                return "expired"
        except Exception:
            pass
    if v.get("uses", 0) >= int(v.get("max_uses", 1)):
        return "exhausted"
    return "active"


@api.post("/vouchers")
async def voucher_create(payload: VoucherCreate, user: dict = Depends(require_roles("teacher", "admin"))):
    if payload.value <= 0:
        raise HTTPException(400, "Valor deve ser positivo")
    code = (payload.code or gen_voucher_code()).upper().strip()
    if not re.match(r"^[A-Z0-9_-]{3,20}$", code):
        raise HTTPException(400, "Código inválido. Use 3-20 caracteres alfanuméricos.")
    if await db.vouchers.find_one({"code": code}):
        raise HTTPException(400, "Código já existe. Escolha outro.")
    if payload.class_id:
        klass = await db.classes.find_one({"id": payload.class_id})
        if not klass:
            raise HTTPException(400, "Turma inválida")
    max_uses = int(payload.max_uses or 1)
    if max_uses < 1 or max_uses > 1000:
        raise HTTPException(400, "Máximo de usos deve estar entre 1 e 1000")
    v = {
        "id": str(uuid.uuid4()),
        "code": code,
        "value": float(payload.value),
        "description": (payload.description or "").strip(),
        "class_id": payload.class_id,
        "created_by": user["id"],
        "created_by_name": user["name"],
        "max_uses": max_uses,
        "uses": 0,
        "expires_at": parse_expiry(payload.expires_at),
        "redemptions": [],
        "active": True,
        "created_at": now_utc().isoformat(),
    }
    await db.vouchers.insert_one(v)
    v.pop("_id", None)
    v["status"] = voucher_status(v)
    return v


@api.get("/vouchers")
async def voucher_list(user: dict = Depends(require_roles("teacher", "admin"))):
    q = {} if user["role"] == "admin" else {"created_by": user["id"]}
    vouchers = await db.vouchers.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    for v in vouchers:
        # backward compat for old single-use docs
        if "max_uses" not in v:
            v["max_uses"] = 1
            v["uses"] = 1 if v.get("redeemed_by") else 0
            v["redemptions"] = (
                [{"user_id": v["redeemed_by"], "name": "", "redeemed_at": v.get("redeemed_at")}]
                if v.get("redeemed_by") else []
            )
        v["status"] = voucher_status(v)
    return vouchers


@api.patch("/vouchers/{voucher_id}")
async def voucher_update(voucher_id: str, payload: VoucherUpdate, user: dict = Depends(require_roles("teacher", "admin"))):
    v = await db.vouchers.find_one({"id": voucher_id})
    if not v:
        raise HTTPException(404, "Voucher não encontrado")
    if user["role"] != "admin" and v.get("created_by") != user["id"]:
        raise HTTPException(403, "Você só pode editar seus próprios vouchers")
    updates = {}
    if payload.value is not None:
        if payload.value <= 0:
            raise HTTPException(400, "Valor deve ser positivo")
        updates["value"] = float(payload.value)
    if payload.description is not None:
        updates["description"] = payload.description.strip()
    if payload.max_uses is not None:
        mu = int(payload.max_uses)
        if mu < 1 or mu > 1000:
            raise HTTPException(400, "Máximo de usos entre 1 e 1000")
        if mu < v.get("uses", 0):
            raise HTTPException(400, f"max_uses ({mu}) não pode ser menor que usos atuais ({v.get('uses', 0)})")
        updates["max_uses"] = mu
    if payload.expires_at is not None:
        updates["expires_at"] = parse_expiry(payload.expires_at)
    if payload.active is not None:
        updates["active"] = bool(payload.active)
    if not updates:
        raise HTTPException(400, "Nada para atualizar")
    await db.vouchers.update_one({"id": voucher_id}, {"$set": updates})
    fresh = await db.vouchers.find_one({"id": voucher_id}, {"_id": 0})
    fresh["status"] = voucher_status(fresh)
    return fresh


@api.delete("/vouchers/{voucher_id}")
async def voucher_delete(voucher_id: str, user: dict = Depends(require_roles("teacher", "admin"))):
    v = await db.vouchers.find_one({"id": voucher_id})
    if not v:
        raise HTTPException(404, "Voucher não encontrado")
    if user["role"] != "admin" and v.get("created_by") != user["id"]:
        raise HTTPException(403, "Você só pode remover seus próprios vouchers")
    if v.get("uses", 0) > 0 or v.get("redeemed_by"):
        raise HTTPException(400, "Voucher já resgatado não pode ser removido. Desative-o se preferir.")
    await db.vouchers.delete_one({"id": voucher_id})
    return {"ok": True}


@api.post("/student/vouchers/redeem")
async def voucher_redeem(payload: VoucherRedeem, user: dict = Depends(require_roles("student"))):
    code = payload.code.upper().strip()
    v = await db.vouchers.find_one({"code": code})
    if not v or not v.get("active", True):
        raise HTTPException(404, "Código inválido ou desativado")
    # backward compat
    max_uses = int(v.get("max_uses", 1))
    uses = int(v.get("uses", 1 if v.get("redeemed_by") else 0))
    redemptions = v.get("redemptions") or ([{"user_id": v["redeemed_by"]}] if v.get("redeemed_by") else [])
    if v.get("class_id") and v["class_id"] != user.get("class_id"):
        raise HTTPException(403, "Este voucher não é da sua turma")
    if v.get("expires_at"):
        try:
            exp = datetime.fromisoformat(v["expires_at"].replace("Z", "+00:00"))
            if exp < now_utc():
                raise HTTPException(400, "Voucher expirado")
        except HTTPException:
            raise
        except Exception:
            pass
    if uses >= max_uses:
        raise HTTPException(400, "Voucher esgotado")
    if any(r.get("user_id") == user["id"] for r in redemptions):
        raise HTTPException(400, "Você já resgatou este voucher")
    # Atomic update with guard against race
    new_redemption = {"user_id": user["id"], "name": user["name"], "redeemed_at": now_utc().isoformat()}
    res = await db.vouchers.update_one(
        {"id": v["id"], "uses": uses, "redemptions.user_id": {"$ne": user["id"]}},
        {"$inc": {"uses": 1}, "$push": {"redemptions": new_redemption}},
    )
    if res.modified_count == 0:
        raise HTTPException(400, "Voucher acaba de ser resgatado por outro aluno. Tente outro código.")
    await add_transaction(
        user["id"], "voucher", float(v["value"]),
        f"Voucher resgatado: {v.get('description') or v['code']}",
        {"voucher_id": v["id"], "code": v["code"]},
    )
    return {"ok": True, "value": v["value"], "description": v.get("description") or "", "code": v["code"]}


@api.get("/student/vouchers/history")
async def voucher_my_history(user: dict = Depends(require_roles("student"))):
    vs = await db.vouchers.find(
        {"redemptions.user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return vs


# ---------- Transferências entre alunos ----------
@api.post("/student/transfer")
async def student_transfer(payload: TransferInput, user: dict = Depends(require_roles("student"))):
    ra = payload.ra.strip()
    amount = float(payload.amount)
    if amount <= 0:
        raise HTTPException(400, "Valor deve ser positivo")
    if amount > 10000:
        raise HTTPException(400, "Valor máximo por transferência é ₡ 10.000")
    if ra == user.get("ra"):
        raise HTTPException(400, "Você não pode enviar para si mesmo")
    receiver = await db.users.find_one({"ra": ra, "role": "student"})
    if not receiver:
        raise HTTPException(404, "Aluno com esse RA não encontrado")
    if receiver["id"] == user["id"]:
        raise HTTPException(400, "Você não pode enviar para si mesmo")
    fresh = await db.users.find_one({"id": user["id"]})
    if fresh["balance"] < amount:
        raise HTTPException(400, "Saldo insuficiente")
    msg = (payload.message or "").strip()[:120]
    desc_send = f"Transferência enviada para {receiver['name']}" + (f' · "{msg}"' if msg else "")
    desc_recv = f"Recebido de {user['name']}" + (f' · "{msg}"' if msg else "")
    meta = {"peer_id": receiver["id"], "peer_name": receiver["name"], "message": msg}
    meta_recv = {"peer_id": user["id"], "peer_name": user["name"], "message": msg}
    await add_transaction(user["id"], "transfer_out", -amount, desc_send, meta)
    await add_transaction(receiver["id"], "transfer_in", amount, desc_recv, meta_recv)
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0, "balance": 1, "name": 1})
    return {
        "ok": True,
        "receiver_name": receiver["name"],
        "amount": amount,
        "new_balance": round(updated.get("balance", 0), 2),
    }


# ---------- Presença (Attendance) ----------
@api.post("/attendance/mark")
async def attendance_mark(payload: AttendanceMark, user: dict = Depends(require_roles("teacher", "admin"))):
    # Validate class access
    klass = await db.classes.find_one({"id": payload.class_id})
    if not klass:
        raise HTTPException(404, "Turma não encontrada")
    if user["role"] == "teacher" and klass.get("teacher_id") != user["id"]:
        raise HTTPException(403, "Você não é responsável por esta turma")
    # normalize date
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d").date().isoformat()
    except Exception:
        raise HTTPException(400, "Data inválida (YYYY-MM-DD)")
    updates = []
    all_ids = set(payload.present_ids) | set(payload.absent_ids)
    for sid in all_ids:
        present = sid in payload.present_ids
        await db.attendance.update_one(
            {"user_id": sid, "date": d},
            {"$set": {
                "id": str(uuid.uuid4()),
                "user_id": sid,
                "class_id": payload.class_id,
                "date": d,
                "present": present,
                "marked_by": user["id"],
                "marked_at": now_utc().isoformat(),
            }},
            upsert=True,
        )
        updates.append({"user_id": sid, "present": present})
    return {"ok": True, "date": d, "class_id": payload.class_id, "count": len(updates)}


@api.get("/attendance/class/{class_id}")
async def attendance_get_class(class_id: str, date: Optional[str] = None,
                                user: dict = Depends(require_roles("teacher", "admin"))):
    klass = await db.classes.find_one({"id": class_id})
    if not klass:
        raise HTTPException(404, "Turma não encontrada")
    if user["role"] == "teacher" and klass.get("teacher_id") != user["id"]:
        raise HTTPException(403, "Você não é responsável por esta turma")
    d = date or datetime.now(timezone.utc).date().isoformat()
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except Exception:
        raise HTTPException(400, "Data inválida")
    students = await db.users.find(
        {"role": "student", "class_id": class_id},
        {"_id": 0, "password_hash": 0},
    ).to_list(500)
    recs = await db.attendance.find({"class_id": class_id, "date": d}, {"_id": 0}).to_list(500)
    rmap = {r["user_id"]: r for r in recs}
    for s in students:
        r = rmap.get(s["id"])
        s["attendance"] = {
            "marked": bool(r),
            "present": r["present"] if r else None,
        }
    return {"class_id": class_id, "date": d, "students": students}


@api.get("/student/attendance")
async def student_attendance_my(user: dict = Depends(require_roles("student"))):
    recs = await db.attendance.find({"user_id": user["id"]}, {"_id": 0}).sort("date", -1).to_list(100)
    return recs


@api.get("/admin/store")
async def admin_store(user: dict = Depends(require_roles("admin"))):
    return await db.store_items.find({}, {"_id": 0}).to_list(200)


@api.post("/admin/store")
async def admin_store_create(payload: StoreItemInput, user: dict = Depends(require_roles("admin"))):
    item = {
        "id": str(uuid.uuid4()), "name": payload.name, "description": payload.description,
        "price": payload.price,
        "image": payload.image or "https://images.unsplash.com/photo-1566869112473-77c4fb94359c?w=400",
        "stock": payload.stock, "active": True,
    }
    await db.store_items.insert_one(item)
    item.pop("_id", None)
    return item


@api.delete("/admin/store/{item_id}")
async def admin_store_delete(item_id: str, user: dict = Depends(require_roles("admin"))):
    await db.store_items.update_one({"id": item_id}, {"$set": {"active": False}})
    return {"ok": True}


@api.get("/admin/config")
async def get_config(user: dict = Depends(require_roles("admin"))):
    cfg = await db.config.find_one({"id": "main"}, {"_id": 0})
    if not cfg:
        cfg = {"id": "main", "daily_allowance": 10.0, "savings_rate": 0.02}
        await db.config.insert_one(cfg)
        cfg.pop("_id", None)
    return cfg


@api.post("/admin/config")
async def set_config(payload: ConfigModel, user: dict = Depends(require_roles("admin"))):
    await db.config.update_one(
        {"id": "main"},
        {"$set": {
            "daily_allowance": payload.daily_allowance,
            "savings_rate": payload.savings_rate,
            "attendance_required": bool(payload.attendance_required),
        }},
        upsert=True,
    )
    return {"ok": True}


@api.post("/admin/run-allowance")
async def run_allowance(user: dict = Depends(require_roles("admin"))):
    cfg = await db.config.find_one({"id": "main"}) or {}
    amount = cfg.get("daily_allowance", 10.0)
    attendance_required = bool(cfg.get("attendance_required", False))
    today = date.today().isoformat()
    students = await db.users.find({"role": "student"}).to_list(1000)

    present_ids = set()
    if attendance_required:
        recs = await db.attendance.find({"date": today, "present": True}, {"_id": 0, "user_id": 1}).to_list(2000)
        present_ids = {r["user_id"] for r in recs}

    count = 0
    skipped_absent = 0
    for s in students:
        if attendance_required and s["id"] not in present_ids:
            skipped_absent += 1
            continue
        existing = await db.transactions.find_one({
            "user_id": s["id"], "type": "allowance", "meta.date": today,
        })
        if existing:
            continue
        await add_transaction(s["id"], "allowance", amount, "Mesada diária", {"date": today})
        count += 1
    return {
        "ok": True,
        "distributed_to": count,
        "amount": amount,
        "skipped_absent": skipped_absent,
        "attendance_required": attendance_required,
        "date": today,
    }


async def seed_data():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.users.create_index("ra", sparse=True)
    await db.vouchers.create_index("code", unique=True)

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@arcoins.edu").lower()
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
    admin = await db.users.find_one({"email": admin_email})
    if not admin:
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": admin_email,
            "password_hash": hash_password(admin_pass),
            "name": "Dir. Ana Moreira", "role": "admin",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Ana",
            "balance": 0, "savings": 0, "created_at": now_utc().isoformat(),
        })
        logger.info("Admin seeded")

    cfg = await db.config.find_one({"id": "main"})
    if not cfg:
        await db.config.insert_one({"id": "main", "daily_allowance": 10.0, "savings_rate": 0.02})

    teachers_seed = [
        ("professor@arcoins.edu", "prof123", "Prof. Carlos Lima", "Teacher"),
        ("marta@arcoins.edu", "prof123", "Prof. Marta Silva", "Teacher2"),
    ]
    teacher_ids = []
    for email, pw, name, seed in teachers_seed:
        existing = await db.users.find_one({"email": email})
        if existing:
            teacher_ids.append(existing["id"])
            continue
        tid = str(uuid.uuid4())
        teacher_ids.append(tid)
        await db.users.insert_one({
            "id": tid, "email": email, "password_hash": hash_password(pw),
            "name": name, "role": "teacher",
            "avatar": f"https://api.dicebear.com/7.x/avataaars/svg?seed={seed}",
            "balance": 0, "savings": 0, "created_at": now_utc().isoformat(),
        })

    classes_seed = [("7º Ano A", teacher_ids[0]), ("8º Ano B", teacher_ids[1])]
    class_ids = []
    for name, tid in classes_seed:
        existing = await db.classes.find_one({"name": name})
        if existing:
            class_ids.append(existing["id"])
            continue
        cid = str(uuid.uuid4())
        class_ids.append(cid)
        await db.classes.insert_one({"id": cid, "name": name, "teacher_id": tid, "created_at": now_utc().isoformat()})

    students_seed = [
        ("aluno@arcoins.edu", "aluno123", "Lucas Pereira", class_ids[0]),
        ("maria@arcoins.edu", "aluno123", "Maria Santos", class_ids[0]),
        ("joao@arcoins.edu", "aluno123", "João Almeida", class_ids[0]),
        ("sofia@arcoins.edu", "aluno123", "Sofia Costa", class_ids[0]),
        ("pedro@arcoins.edu", "aluno123", "Pedro Mendes", class_ids[1]),
        ("julia@arcoins.edu", "aluno123", "Júlia Rocha", class_ids[1]),
        ("rafa@arcoins.edu", "aluno123", "Rafael Dias", class_ids[1]),
        ("bia@arcoins.edu", "aluno123", "Beatriz Nunes", class_ids[1]),
    ]
    for i, (email, pw, name, cid) in enumerate(students_seed):
        existing = await db.users.find_one({"email": email})
        if existing:
            continue
        sid = str(uuid.uuid4())
        initial = 45 + (i * 7) % 40
        await db.users.insert_one({
            "id": sid, "email": email, "password_hash": hash_password(pw),
            "name": name, "role": "student", "class_id": cid,
            "avatar": f"https://api.dicebear.com/7.x/adventurer/svg?seed={name}",
            "balance": float(initial), "savings": float(10 + i * 2),
            "created_at": now_utc().isoformat(),
        })
        await db.transactions.insert_one({
            "id": str(uuid.uuid4()), "user_id": sid, "type": "adjustment",
            "amount": float(initial), "description": "Saldo inicial de boas-vindas",
            "created_at": now_utc().isoformat(), "meta": {},
        })
        for d in range(1, 4):
            await db.transactions.insert_one({
                "id": str(uuid.uuid4()), "user_id": sid, "type": "allowance",
                "amount": 10.0, "description": "Mesada diária",
                "created_at": (now_utc() - timedelta(days=d)).isoformat(),
                "meta": {"date": (date.today() - timedelta(days=d)).isoformat()},
            })

    if await db.challenges.count_documents({}) == 0:
        challs = [
            ("Leitura da Semana", "Leia um livro e escreva um resumo de meia página.", 15, teacher_ids[0], class_ids[0]),
            ("Desafio de Matemática", "Resolva a lista extra de frações da página 42.", 12, teacher_ids[0], class_ids[0]),
            ("Feira de Ciências", "Participe apresentando um experimento.", 25, teacher_ids[1], class_ids[1]),
            ("Redação ENEM Kids", "Escreva uma redação sobre educação financeira.", 20, teacher_ids[1], class_ids[1]),
            ("Missão Escola Limpa", "Ajude a manter sua sala organizada por uma semana.", 8, teacher_ids[0], None),
        ]
        for title, desc, reward, tid, cid in challs:
            await db.challenges.insert_one({
                "id": str(uuid.uuid4()), "title": title, "description": desc,
                "reward": float(reward), "created_by": tid, "class_id": cid,
                "active": True, "created_at": now_utc().isoformat(),
            })

    if await db.store_items.count_documents({}) == 0:
        items = [
            ("Lápis Personalizado", "Lápis colorido exclusivo Arcoins.", 8, "https://images.unsplash.com/photo-1568871391867-0fc99ff97f47?w=400", 50),
            ("15 min de Leitura Livre", "Escolha um livro e leia por 15 min durante a aula.", 5, "https://images.unsplash.com/photo-1535905557558-afc4877a26fc?w=400", 999),
            ("Vale Lanche Especial", "Lanche extra na cantina em dia especial.", 25, "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400", 20),
            ("Escolher Música da Aula", "Você escolhe a música que tocará no intervalo.", 12, "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400", 30),
            ("Caderno Temático", "Caderno colorido com capa temática.", 35, "https://images.unsplash.com/photo-1497515114629-f71d768fd07c?w=400", 15),
            ("Adesivos Arcoins", "Pacote com 10 adesivos exclusivos.", 6, "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=400", 100),
        ]
        for name, desc, price, img, stock in items:
            await db.store_items.insert_one({
                "id": str(uuid.uuid4()), "name": name, "description": desc,
                "price": float(price), "image": img, "stock": stock, "active": True,
            })

    logger.info("Seed complete")


@app.on_event("startup")
async def on_startup():
    await seed_data()


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


@api.get("/")
async def root():
    return {"ok": True, "service": "Arcoins API"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
