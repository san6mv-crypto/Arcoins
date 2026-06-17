from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta, date
from typing import List, Optional, Literal

import bcrypt
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
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
    email: EmailStr
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


class PurchaseInput(BaseModel):
    item_id: str


class SavingsInput(BaseModel):
    amount: float


class ConfigModel(BaseModel):
    daily_allowance: float = 10.0
    savings_rate: float = 0.02


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
    }


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
        {"$set": {"daily_allowance": payload.daily_allowance, "savings_rate": payload.savings_rate}},
        upsert=True,
    )
    return {"ok": True}


@api.post("/admin/run-allowance")
async def run_allowance(user: dict = Depends(require_roles("admin"))):
    cfg = await db.config.find_one({"id": "main"})
    amount = cfg["daily_allowance"] if cfg else 10.0
    students = await db.users.find({"role": "student"}).to_list(1000)
    today = date.today().isoformat()
    count = 0
    for s in students:
        existing = await db.transactions.find_one({
            "user_id": s["id"], "type": "allowance", "meta.date": today,
        })
        if existing:
            continue
        await add_transaction(s["id"], "allowance", amount, "Mesada diária", {"date": today})
        count += 1
    return {"ok": True, "distributed_to": count, "amount": amount}


async def seed_data():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)

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
