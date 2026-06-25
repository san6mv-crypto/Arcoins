"""
Beta flow tests: CSV bulk-import of students + Vouchers (single-use).
"""
import os
import io
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cost-checker-65.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@arcoins.edu", "password": "admin123"}
TEACHER = {"email": "professor@arcoins.edu", "password": "prof123"}
TEACHER2 = {"email": "marta@arcoins.edu", "password": "prof123"}
ALUNO_LUCAS = {"email": "aluno@arcoins.edu", "password": "aluno123"}     # 7A
ALUNO_JULIA = {"email": "julia@arcoins.edu", "password": "aluno123"}     # 8B


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    return data["token"], data["user"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- shared state ----------
STATE = {}


@pytest.fixture(scope="module", autouse=True)
def setup_module():
    admin_token, _ = login(ADMIN)
    STATE["admin_token"] = admin_token
    teacher_token, teacher_user = login(TEACHER)
    STATE["teacher_token"] = teacher_token
    STATE["teacher_id"] = teacher_user["id"]
    teacher2_token, teacher2_user = login(TEACHER2)
    STATE["teacher2_token"] = teacher2_token
    # classes
    cs = requests.get(f"{API}/admin/classes", headers=auth_headers(admin_token)).json()
    STATE["class_7a"] = next(c["id"] for c in cs if "7" in c["name"])
    STATE["class_8b"] = next(c["id"] for c in cs if "8" in c["name"])
    STATE["created_users"] = []
    STATE["created_vouchers"] = []
    yield
    # cleanup
    for uid in STATE["created_users"]:
        try:
            requests.delete(f"{API}/admin/users/{uid}", headers=auth_headers(admin_token), timeout=10)
        except Exception:
            pass
    for vid in STATE["created_vouchers"]:
        try:
            requests.delete(f"{API}/vouchers/{vid}", headers=auth_headers(admin_token), timeout=10)
        except Exception:
            pass


# ---------- CSV bulk import ----------
class TestBulkImport:
    def _post_csv(self, csv_text, class_id=None, initial_balance=0, token=None):
        token = token or STATE["admin_token"]
        files = {"file": ("students.csv", csv_text.encode("utf-8"), "text/csv")}
        data = {"initial_balance": str(initial_balance)}
        if class_id:
            data["class_id"] = class_id
        return requests.post(
            f"{API}/admin/students/bulk-import",
            headers=auth_headers(token), files=files, data=data, timeout=30,
        )

    def test_bulk_import_creates_logins_with_accents_and_duplicates(self):
        # unique RAs per run to avoid collisions
        suffix = uuid.uuid4().hex[:6].upper()
        csv = (
            "nome,ra\n"
            f"Júlia Teste {suffix},RA{suffix}A1\n"
            f"Joao Outro {suffix},RA{suffix}B2\n"
            f"Maria Teste {suffix},RA{suffix}C3\n"
            f"Maria Outra {suffix},RA{suffix}D4\n"   # duplicate first name -> @maria.<ra>
            ",RA{suffix}E5\n"                         # empty name -> skipped
            f"Sem RA {suffix},\n"                     # empty ra -> skipped
            f"Curto {suffix},X\n"                     # ra <3 -> skipped
        )
        r = self._post_csv(csv, class_id=STATE["class_7a"], initial_balance=5)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["created_count"] == 4
        assert body["skipped_count"] == 3
        logins = {c["login"] for c in body["created"]}
        # accent-stripped first names
        assert any(l.startswith("@julia") for l in logins)
        assert any(l.startswith("@joao") for l in logins)
        # duplicates: first @maria, second @maria.<ra>
        maria_logins = sorted([l for l in logins if l.startswith("@maria")])
        assert maria_logins[0] == "@maria"
        assert maria_logins[1].startswith("@maria.RA")

        # remember to cleanup + remember a created student for downstream tests
        STATE["maria_login"] = "@maria"
        STATE["maria_ra"] = next(c["ra"] for c in body["created"] if c["login"] == "@maria")
        STATE["julia_login"] = next(l for l in logins if l.startswith("@julia"))
        STATE["julia_ra"] = next(c["ra"] for c in body["created"] if c["login"] == STATE["julia_login"])

        # Track created users by fetching all users and matching email
        users = requests.get(f"{API}/admin/users", headers=auth_headers(STATE["admin_token"])).json()
        for c in body["created"]:
            for u in users:
                if u["email"] == c["login"]:
                    STATE["created_users"].append(u["id"])

        # skipped reasons
        reasons = [s["reason"] for s in body["skipped"]]
        assert any("vazio" in r for r in reasons)
        assert any("RA muito curto" in r or "muito curto" in r for r in reasons)

    def test_imported_student_login_with_ra(self):
        r = requests.post(f"{API}/auth/login", json={
            "email": STATE["maria_login"], "password": STATE["maria_ra"]
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["ra"] == STATE["maria_ra"]
        assert data["user"]["password_locked"] is True
        assert data["user"]["balance"] == 5.0
        STATE["maria_token"] = data["token"]

    def test_auth_me_returns_ra_and_lock(self):
        r = requests.get(f"{API}/auth/me", headers=auth_headers(STATE["maria_token"]))
        assert r.status_code == 200
        u = r.json()
        assert u["ra"] == STATE["maria_ra"]
        assert u["password_locked"] is True

    def test_duplicate_ra_rejected(self):
        suffix = uuid.uuid4().hex[:6].upper()
        # First time should create
        csv1 = f"nome,ra\nAluno Novo {suffix},DUP{suffix}\n"
        r1 = self._post_csv(csv1)
        assert r1.json()["created_count"] == 1
        # Second time with same RA must be rejected
        csv2 = f"nome,ra\nOutro Aluno {suffix},DUP{suffix}\n"
        r2 = self._post_csv(csv2)
        body = r2.json()
        assert body["created_count"] == 0
        assert body["skipped_count"] == 1
        assert "já cadastrado" in body["skipped"][0]["reason"].lower()
        # track for cleanup
        users = requests.get(f"{API}/admin/users", headers=auth_headers(STATE["admin_token"])).json()
        for u in users:
            if u.get("ra") == f"DUP{suffix}":
                STATE["created_users"].append(u["id"])

    def test_invalid_class_id_returns_400(self):
        csv = "nome,ra\nQualquer,12345\n"
        r = self._post_csv(csv, class_id="not-a-class-id")
        assert r.status_code == 400

    def test_missing_columns_returns_400(self):
        csv = "foo,bar\nX,Y\n"
        r = self._post_csv(csv)
        assert r.status_code == 400
        assert "nome" in r.text.lower() and "ra" in r.text.lower()

    def test_import_without_class_id_ok(self):
        suffix = uuid.uuid4().hex[:6].upper()
        csv = f"nome,ra\nSem Turma {suffix},NOCLS{suffix}\n"
        r = self._post_csv(csv, class_id=None)
        assert r.status_code == 200
        users = requests.get(f"{API}/admin/users", headers=auth_headers(STATE["admin_token"])).json()
        for u in users:
            if u.get("ra") == f"NOCLS{suffix}":
                assert u.get("class_id") is None
                STATE["created_users"].append(u["id"])


# ---------- Vouchers ----------
class TestVouchers:
    def test_teacher_creates_voucher_autocode(self):
        r = requests.post(
            f"{API}/vouchers",
            headers=auth_headers(STATE["teacher_token"]),
            json={"value": 10, "description": "Test auto"},
        )
        assert r.status_code == 200, r.text
        v = r.json()
        assert len(v["code"]) == 6
        assert v["value"] == 10
        STATE["created_vouchers"].append(v["id"])
        STATE["v_auto_id"] = v["id"]

    def test_teacher_creates_voucher_with_custom_code(self):
        code = f"BETA{uuid.uuid4().hex[:4].upper()}"
        r = requests.post(
            f"{API}/vouchers",
            headers=auth_headers(STATE["teacher_token"]),
            json={"value": 20, "code": code, "description": "Custom"},
        )
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["code"] == code
        STATE["created_vouchers"].append(v["id"])
        STATE["v_custom_id"] = v["id"]
        STATE["v_custom_code"] = code

    def test_duplicate_code_400(self):
        r = requests.post(
            f"{API}/vouchers",
            headers=auth_headers(STATE["teacher_token"]),
            json={"value": 5, "code": STATE["v_custom_code"]},
        )
        assert r.status_code == 400

    def test_admin_creates_voucher(self):
        r = requests.post(
            f"{API}/vouchers",
            headers=auth_headers(STATE["admin_token"]),
            json={"value": 7, "description": "Admin"},
        )
        assert r.status_code == 200
        STATE["created_vouchers"].append(r.json()["id"])
        STATE["v_admin_id"] = r.json()["id"]

    def test_teacher_lists_only_own_vouchers(self):
        r = requests.get(f"{API}/vouchers", headers=auth_headers(STATE["teacher_token"]))
        assert r.status_code == 200
        ids = [v["id"] for v in r.json()]
        assert STATE["v_auto_id"] in ids
        assert STATE["v_custom_id"] in ids
        assert STATE["v_admin_id"] not in ids

    def test_admin_lists_all_vouchers(self):
        r = requests.get(f"{API}/vouchers", headers=auth_headers(STATE["admin_token"]))
        assert r.status_code == 200
        ids = [v["id"] for v in r.json()]
        assert STATE["v_auto_id"] in ids
        assert STATE["v_admin_id"] in ids

    def test_student_redeems_voucher(self):
        student_token, student = login(ALUNO_LUCAS)
        STATE["lucas_token"] = student_token
        STATE["lucas_balance_before"] = student["balance"]
        r = requests.post(
            f"{API}/student/vouchers/redeem",
            headers=auth_headers(student_token),
            json={"code": STATE["v_custom_code"]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["value"] == 20
        # balance changed
        me = requests.get(f"{API}/auth/me", headers=auth_headers(student_token)).json()
        assert me["balance"] == round(STATE["lucas_balance_before"] + 20, 2)
        # transaction recorded as 'voucher'
        tx = requests.get(f"{API}/student/transactions", headers=auth_headers(student_token)).json()
        assert any(t["type"] == "voucher" and t["amount"] == 20 for t in tx)

    def test_second_student_cannot_redeem_same_code(self):
        token, _ = login(ALUNO_JULIA)
        STATE["julia_real_token"] = token
        r = requests.post(
            f"{API}/student/vouchers/redeem",
            headers=auth_headers(token),
            json={"code": STATE["v_custom_code"]},
        )
        assert r.status_code == 400
        assert "resgatado" in r.text.lower()

    def test_same_student_cannot_redeem_twice(self):
        r = requests.post(
            f"{API}/student/vouchers/redeem",
            headers=auth_headers(STATE["lucas_token"]),
            json={"code": STATE["v_custom_code"]},
        )
        assert r.status_code in (400,)

    def test_invalid_code_404(self):
        r = requests.post(
            f"{API}/student/vouchers/redeem",
            headers=auth_headers(STATE["lucas_token"]),
            json={"code": "NOPE99"},
        )
        assert r.status_code == 404

    def test_class_restricted_voucher(self):
        code = f"CLS{uuid.uuid4().hex[:4].upper()}"
        r = requests.post(
            f"{API}/vouchers",
            headers=auth_headers(STATE["teacher_token"]),
            json={"value": 8, "code": code, "class_id": STATE["class_8b"]},
        )
        assert r.status_code == 200
        STATE["created_vouchers"].append(r.json()["id"])
        # Lucas is in 7A -> 403
        r2 = requests.post(
            f"{API}/student/vouchers/redeem",
            headers=auth_headers(STATE["lucas_token"]),
            json={"code": code},
        )
        assert r2.status_code == 403

    def test_delete_voucher_permissions(self):
        # Create one as teacher
        r = requests.post(
            f"{API}/vouchers",
            headers=auth_headers(STATE["teacher_token"]),
            json={"value": 3},
        )
        vid = r.json()["id"]
        # Other teacher cannot delete
        r2 = requests.delete(f"{API}/vouchers/{vid}", headers=auth_headers(STATE["teacher2_token"]))
        assert r2.status_code == 403
        # Creator can delete
        r3 = requests.delete(f"{API}/vouchers/{vid}", headers=auth_headers(STATE["teacher_token"]))
        assert r3.status_code == 200

    def test_redeemed_voucher_cannot_be_deleted(self):
        # v_custom was redeemed by Lucas
        r = requests.delete(f"{API}/vouchers/{STATE['v_custom_id']}", headers=auth_headers(STATE["teacher_token"]))
        assert r.status_code == 400
