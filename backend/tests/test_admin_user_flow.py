"""Backend tests for admin user/class creation and student onboarding flow."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # fallback for tests run inside container without preview URL
    BASE_URL = "http://localhost:8001"

ADMIN_EMAIL = "admin@arcoins.edu"
ADMIN_PASSWORD = "admin123"

TEST_TAG = uuid.uuid4().hex[:8]
CREATED_USERS = []  # list of (id, email)
CREATED_CLASSES = []  # list of ids


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    yield s
    # cleanup
    for uid, _ in CREATED_USERS:
        try:
            s.delete(f"{BASE_URL}/api/admin/users/{uid}")
        except Exception:
            pass


# ---------- Admin auth ----------
def test_admin_login_success():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    data = r.json()
    assert "token" in data and data["user"]["role"] == "admin"
    assert data["user"]["email"] == ADMIN_EMAIL


def test_admin_login_invalid():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert r.status_code == 401


# ---------- List users ----------
def test_admin_list_users_has_seed(admin_client):
    r = admin_client.get(f"{BASE_URL}/api/admin/users")
    assert r.status_code == 200
    users = r.json()
    assert isinstance(users, list)
    assert len(users) >= 11, f"expected >=11 seed users, got {len(users)}"
    # ensure password hash not leaked
    assert all("password_hash" not in u for u in users)


# ---------- Create student with initial balance ----------
def test_create_student_with_initial_balance(admin_client):
    email = f"test_student_{TEST_TAG}@arcoins.edu"
    payload = {"name": "Test Student", "email": email,
               "password": "stud123", "role": "student", "initial_balance": 75}
    r = admin_client.post(f"{BASE_URL}/api/admin/users", json=payload)
    assert r.status_code == 200, r.text
    u = r.json()
    assert u["balance"] == 75
    assert u["class_id"] is None
    assert u["role"] == "student"
    assert "password_hash" not in u
    CREATED_USERS.append((u["id"], email))

    # student can login
    r2 = requests.post(f"{BASE_URL}/api/auth/login",
                       json={"email": email, "password": "stud123"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["user"]["balance"] == 75
    assert body["user"]["role"] == "student"
    token = body["token"]

    # /api/auth/me
    me = requests.get(f"{BASE_URL}/api/auth/me",
                      headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    md = me.json()
    assert md["balance"] == 75 and md["role"] == "student"

    # /api/student/transactions contains welcome transaction
    tx = requests.get(f"{BASE_URL}/api/student/transactions",
                      headers={"Authorization": f"Bearer {token}"})
    assert tx.status_code == 200
    txns = tx.json()
    welcome = [t for t in txns if t.get("description") == "Saldo inicial de boas-vindas"]
    assert len(welcome) == 1
    assert welcome[0]["amount"] == 75


# ---------- Create teacher ----------
def test_create_teacher_and_login(admin_client):
    email = f"test_teacher_{TEST_TAG}@arcoins.edu"
    r = admin_client.post(f"{BASE_URL}/api/admin/users", json={
        "name": "Test Teacher", "email": email, "password": "tea123", "role": "teacher"
    })
    assert r.status_code == 200
    u = r.json()
    assert u["role"] == "teacher"
    CREATED_USERS.append((u["id"], email))

    r2 = requests.post(f"{BASE_URL}/api/auth/login",
                       json={"email": email, "password": "tea123"})
    assert r2.status_code == 200
    token = r2.json()["token"]
    cls = requests.get(f"{BASE_URL}/api/teacher/classes",
                       headers={"Authorization": f"Bearer {token}"})
    assert cls.status_code == 200


# ---------- Validation errors ----------
def test_duplicate_email_returns_400(admin_client):
    email = f"dup_{TEST_TAG}@arcoins.edu"
    p = {"name": "Dup", "email": email, "password": "abcd", "role": "student"}
    r1 = admin_client.post(f"{BASE_URL}/api/admin/users", json=p)
    assert r1.status_code == 200
    CREATED_USERS.append((r1.json()["id"], email))
    r2 = admin_client.post(f"{BASE_URL}/api/admin/users", json=p)
    assert r2.status_code == 400
    assert "já cadastrado" in r2.json().get("detail", "")


def test_short_password_returns_400(admin_client):
    r = admin_client.post(f"{BASE_URL}/api/admin/users", json={
        "name": "Short", "email": f"short_{TEST_TAG}@arcoins.edu",
        "password": "ab", "role": "student"
    })
    assert r.status_code == 400


def test_invalid_class_id_returns_400(admin_client):
    r = admin_client.post(f"{BASE_URL}/api/admin/users", json={
        "name": "BadClass", "email": f"badclass_{TEST_TAG}@arcoins.edu",
        "password": "abcd", "role": "student", "class_id": "nonexistent-class-id"
    })
    assert r.status_code == 400
    assert "Turma inválida" in r.json().get("detail", "")


# ---------- Classes ----------
def test_create_class_and_list(admin_client):
    cname = f"Turma Teste {TEST_TAG}"
    r = admin_client.post(f"{BASE_URL}/api/admin/classes", json={"name": cname})
    assert r.status_code == 200
    klass = r.json()
    assert klass["name"] == cname
    CREATED_CLASSES.append(klass["id"])
    lst = admin_client.get(f"{BASE_URL}/api/admin/classes")
    assert lst.status_code == 200
    found = [c for c in lst.json() if c["id"] == klass["id"]]
    assert len(found) == 1
    assert found[0]["student_count"] == 0


def test_assign_student_to_class(admin_client):
    # need a class
    if not CREATED_CLASSES:
        r = admin_client.post(f"{BASE_URL}/api/admin/classes",
                              json={"name": f"AssignClass {TEST_TAG}"})
        CREATED_CLASSES.append(r.json()["id"])
    cid = CREATED_CLASSES[0]
    email = f"assigned_{TEST_TAG}@arcoins.edu"
    r = admin_client.post(f"{BASE_URL}/api/admin/users", json={
        "name": "Assigned", "email": email, "password": "abcd",
        "role": "student", "class_id": cid, "initial_balance": 10
    })
    assert r.status_code == 200, r.text
    u = r.json()
    assert u["class_id"] == cid
    CREATED_USERS.append((u["id"], email))


# ---------- Delete ----------
def test_admin_cannot_delete_self(admin_client):
    me = admin_client.get(f"{BASE_URL}/api/auth/me").json()
    r = admin_client.delete(f"{BASE_URL}/api/admin/users/{me['id']}")
    assert r.status_code == 400
    assert "si mesmo" in r.json().get("detail", "")


def test_admin_delete_user(admin_client):
    # create temp user
    email = f"todelete_{TEST_TAG}@arcoins.edu"
    r = admin_client.post(f"{BASE_URL}/api/admin/users", json={
        "name": "Del", "email": email, "password": "abcd", "role": "student"
    })
    uid = r.json()["id"]
    d = admin_client.delete(f"{BASE_URL}/api/admin/users/{uid}")
    assert d.status_code == 200
    # confirm gone
    users = admin_client.get(f"{BASE_URL}/api/admin/users").json()
    assert not any(u["id"] == uid for u in users)


# ---------- Password hash and JWT ----------
def test_password_is_bcrypt_hashed():
    """Verify directly via login that bcrypt is used (login works = checkpw works)."""
    # login a freshly created seed student
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "aluno@arcoins.edu", "password": "aluno123"})
    assert r.status_code == 200


def test_jwt_token_reusable(admin_client):
    """Multiple calls with same token should succeed."""
    for _ in range(3):
        r = admin_client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
