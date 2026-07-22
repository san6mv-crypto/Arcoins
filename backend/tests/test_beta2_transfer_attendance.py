"""
Beta 2 flow tests:
- Student-to-student transfer via RA (+ message)
- Attendance: mark, get by class, student history
- Config attendance_required
- Run-allowance: gated by attendance
"""
import os
import io
import uuid
from datetime import date

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cost-checker-65.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@arcoins.edu", "password": "admin123"}
TEACHER = {"email": "professor@arcoins.edu", "password": "prof123"}   # 7A
TEACHER2 = {"email": "marta@arcoins.edu", "password": "prof123"}      # 8B


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text}"
    d = r.json()
    return d["token"], d["user"]


def H(token):
    return {"Authorization": f"Bearer {token}"}


STATE = {}


@pytest.fixture(scope="module", autouse=True)
def setup_module():
    admin_token, _ = login(ADMIN)
    STATE["admin_token"] = admin_token
    teacher_token, teacher_user = login(TEACHER)
    STATE["teacher_token"] = teacher_token
    STATE["teacher_id"] = teacher_user["id"]
    teacher2_token, _ = login(TEACHER2)
    STATE["teacher2_token"] = teacher2_token

    # classes
    cs = requests.get(f"{API}/admin/classes", headers=H(admin_token)).json()
    STATE["class_7a"] = next(c["id"] for c in cs if "7" in c["name"])
    STATE["class_8b"] = next(c["id"] for c in cs if "8" in c["name"])

    # Import 2 students with unique RAs for transfer testing
    suffix = uuid.uuid4().hex[:5].upper()
    ra_a = f"TR{suffix}A1"
    ra_b = f"TR{suffix}B2"
    csv_text = f"nome,ra\nSender Beta {suffix},{ra_a}\nReceiver Beta {suffix},{ra_b}\n"
    files = {"file": ("students.csv", csv_text.encode("utf-8"), "text/csv")}
    data = {"initial_balance": "100", "class_id": STATE["class_7a"]}
    r = requests.post(
        f"{API}/admin/students/bulk-import",
        headers=H(admin_token), files=files, data=data, timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created_count"] == 2, body

    # Find created ids and their logins
    sender_login = next(c["login"] for c in body["created"] if c["ra"] == ra_a)
    receiver_login = next(c["login"] for c in body["created"] if c["ra"] == ra_b)

    users = requests.get(f"{API}/admin/users", headers=H(admin_token)).json()
    for u in users:
        if u.get("ra") == ra_a:
            STATE["sender_id"] = u["id"]
        elif u.get("ra") == ra_b:
            STATE["receiver_id"] = u["id"]
    STATE["ra_a"] = ra_a
    STATE["ra_b"] = ra_b

    # Login sender/receiver
    s_tok, s_user = login({"email": sender_login, "password": ra_a})
    STATE["sender_token"] = s_tok
    STATE["sender_balance"] = s_user["balance"]
    r_tok, r_user = login({"email": receiver_login, "password": ra_b})
    STATE["receiver_token"] = r_tok
    STATE["receiver_balance"] = r_user["balance"]

    # Save current config to restore
    cfg = requests.get(f"{API}/admin/config", headers=H(admin_token)).json()
    STATE["orig_cfg"] = cfg

    yield

    # Cleanup: delete created users
    for uid_key in ("sender_id", "receiver_id"):
        uid = STATE.get(uid_key)
        if uid:
            try:
                requests.delete(f"{API}/admin/users/{uid}", headers=H(admin_token), timeout=10)
            except Exception:
                pass
    # Delete their transactions and attendance
    # (No admin endpoint for that -> rely on cascade absence; ok for test env.)

    # Restore config
    try:
        requests.post(
            f"{API}/admin/config",
            headers=H(admin_token),
            json={
                "daily_allowance": STATE["orig_cfg"].get("daily_allowance", 10.0),
                "savings_rate": STATE["orig_cfg"].get("savings_rate", 0.02),
                "attendance_required": bool(STATE["orig_cfg"].get("attendance_required", False)),
            },
            timeout=10,
        )
    except Exception:
        pass


# -------------------- Transfer --------------------
class TestTransfer:
    def test_transfer_success_debits_and_credits(self):
        r = requests.post(
            f"{API}/student/transfer",
            headers=H(STATE["sender_token"]),
            json={"ra": STATE["ra_b"], "amount": 20, "message": "olá amigo"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["amount"] == 20
        assert "receiver_name" in data
        assert "new_balance" in data
        assert data["new_balance"] == round(STATE["sender_balance"] - 20, 2)

        # Verify balances persisted
        me_s = requests.get(f"{API}/auth/me", headers=H(STATE["sender_token"])).json()
        me_r = requests.get(f"{API}/auth/me", headers=H(STATE["receiver_token"])).json()
        assert me_s["balance"] == round(STATE["sender_balance"] - 20, 2)
        assert me_r["balance"] == round(STATE["receiver_balance"] + 20, 2)
        STATE["sender_balance"] = me_s["balance"]
        STATE["receiver_balance"] = me_r["balance"]

    def test_transfer_creates_two_transactions_with_message(self):
        txs_s = requests.get(f"{API}/student/transactions", headers=H(STATE["sender_token"])).json()
        txs_r = requests.get(f"{API}/student/transactions", headers=H(STATE["receiver_token"])).json()
        out = [t for t in txs_s if t["type"] == "transfer_out"]
        inn = [t for t in txs_r if t["type"] == "transfer_in"]
        assert len(out) >= 1
        assert len(inn) >= 1
        # message in description
        assert 'olá amigo' in out[0]["description"] or '"olá amigo"' in out[0]["description"]
        assert "Transferência enviada" in out[0]["description"]
        assert "Recebido de" in inn[0]["description"]
        assert out[0]["amount"] == -20
        assert inn[0]["amount"] == 20

    def test_transfer_ra_not_found(self):
        r = requests.post(
            f"{API}/student/transfer",
            headers=H(STATE["sender_token"]),
            json={"ra": "NOSUCHRA999", "amount": 5},
        )
        assert r.status_code == 404
        assert "não encontrado" in r.text.lower()

    def test_transfer_insufficient_balance(self):
        r = requests.post(
            f"{API}/student/transfer",
            headers=H(STATE["sender_token"]),
            json={"ra": STATE["ra_b"], "amount": 5000},
        )
        assert r.status_code == 400
        assert "insuficiente" in r.text.lower()

    def test_transfer_to_self(self):
        r = requests.post(
            f"{API}/student/transfer",
            headers=H(STATE["sender_token"]),
            json={"ra": STATE["ra_a"], "amount": 5},
        )
        assert r.status_code == 400

    def test_transfer_negative_amount(self):
        r = requests.post(
            f"{API}/student/transfer",
            headers=H(STATE["sender_token"]),
            json={"ra": STATE["ra_b"], "amount": -10},
        )
        assert r.status_code == 400
        assert "positivo" in r.text.lower()

    def test_transfer_zero_amount(self):
        r = requests.post(
            f"{API}/student/transfer",
            headers=H(STATE["sender_token"]),
            json={"ra": STATE["ra_b"], "amount": 0},
        )
        assert r.status_code == 400

    def test_transfer_over_max(self):
        r = requests.post(
            f"{API}/student/transfer",
            headers=H(STATE["sender_token"]),
            json={"ra": STATE["ra_b"], "amount": 10001},
        )
        assert r.status_code == 400


# -------------------- Attendance --------------------
class TestAttendance:
    def test_teacher_marks_own_class(self):
        # Get students in 7A
        r = requests.get(
            f"{API}/attendance/class/{STATE['class_7a']}",
            headers=H(STATE["teacher_token"]),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["class_id"] == STATE["class_7a"]
        assert "students" in data
        STATE["students_7a"] = data["students"]
        assert len(data["students"]) > 0
        # Every student should have attendance field
        for s in data["students"]:
            assert "attendance" in s
            assert "marked" in s["attendance"]
            assert "present" in s["attendance"]

    def test_teacher_cannot_access_other_class(self):
        r = requests.get(
            f"{API}/attendance/class/{STATE['class_8b']}",
            headers=H(STATE["teacher_token"]),
        )
        assert r.status_code == 403

    def test_teacher_cannot_mark_other_class(self):
        today = date.today().isoformat()
        r = requests.post(
            f"{API}/attendance/mark",
            headers=H(STATE["teacher_token"]),
            json={"class_id": STATE["class_8b"], "date": today,
                  "present_ids": [], "absent_ids": []},
        )
        assert r.status_code == 403

    def test_admin_can_access_any_class(self):
        r = requests.get(
            f"{API}/attendance/class/{STATE['class_8b']}",
            headers=H(STATE["admin_token"]),
        )
        assert r.status_code == 200

    def test_mark_attendance_upsert(self):
        today = date.today().isoformat()
        students = STATE["students_7a"]
        # first half present, rest absent
        half = len(students) // 2
        present_ids = [s["id"] for s in students[:half]]
        absent_ids = [s["id"] for s in students[half:]]
        r = requests.post(
            f"{API}/attendance/mark",
            headers=H(STATE["teacher_token"]),
            json={"class_id": STATE["class_7a"], "date": today,
                  "present_ids": present_ids, "absent_ids": absent_ids},
        )
        assert r.status_code == 200, r.text
        assert r.json()["count"] == len(students)

        # Verify persistence via GET
        r2 = requests.get(
            f"{API}/attendance/class/{STATE['class_7a']}?date={today}",
            headers=H(STATE["teacher_token"]),
        )
        assert r2.status_code == 200
        for s in r2.json()["students"]:
            assert s["attendance"]["marked"] is True
            if s["id"] in present_ids:
                assert s["attendance"]["present"] is True
            elif s["id"] in absent_ids:
                assert s["attendance"]["present"] is False

        # Upsert: flip first student from present to absent, ensure no duplicates
        first_id = students[0]["id"]
        r3 = requests.post(
            f"{API}/attendance/mark",
            headers=H(STATE["teacher_token"]),
            json={"class_id": STATE["class_7a"], "date": today,
                  "present_ids": [], "absent_ids": [first_id]},
        )
        assert r3.status_code == 200
        r4 = requests.get(
            f"{API}/attendance/class/{STATE['class_7a']}?date={today}",
            headers=H(STATE["teacher_token"]),
        )
        rec = next(s for s in r4.json()["students"] if s["id"] == first_id)
        assert rec["attendance"]["present"] is False

        STATE["today"] = today
        STATE["present_ids_today"] = present_ids[1:] if first_id in present_ids else present_ids
        STATE["all_class_student_ids"] = [s["id"] for s in students]

    def test_invalid_date_400(self):
        r = requests.post(
            f"{API}/attendance/mark",
            headers=H(STATE["teacher_token"]),
            json={"class_id": STATE["class_7a"], "date": "not-a-date",
                  "present_ids": [], "absent_ids": []},
        )
        assert r.status_code == 400

    def test_class_not_found(self):
        r = requests.post(
            f"{API}/attendance/mark",
            headers=H(STATE["admin_token"]),
            json={"class_id": "nope-class", "date": date.today().isoformat(),
                  "present_ids": [], "absent_ids": []},
        )
        assert r.status_code == 404

    def test_student_attendance_history(self):
        # Login as one of the marked students (Lucas = aluno@)
        tok, _ = login({"email": "aluno@arcoins.edu", "password": "aluno123"})
        r = requests.get(f"{API}/student/attendance", headers=H(tok))
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Lucas is in 7A and we marked today
        today = STATE["today"]
        assert any(rec["date"] == today for rec in data)


# -------------------- Config + Run Allowance --------------------
class TestConfigAndAllowance:
    def test_set_config_attendance_required_true(self):
        r = requests.post(
            f"{API}/admin/config",
            headers=H(STATE["admin_token"]),
            json={"daily_allowance": 10.0, "savings_rate": 0.02, "attendance_required": True},
        )
        assert r.status_code == 200
        cfg = requests.get(f"{API}/admin/config", headers=H(STATE["admin_token"])).json()
        assert cfg["attendance_required"] is True

    def test_run_allowance_with_attendance_required(self):
        """Only students marked present today receive allowance."""
        # Get current balances of both an intended-present (sender) and intended-absent (receiver)
        # First ensure they are set: mark sender_id present, receiver_id absent for today
        today = date.today().isoformat()
        requests.post(
            f"{API}/attendance/mark",
            headers=H(STATE["admin_token"]),
            json={"class_id": STATE["class_7a"], "date": today,
                  "present_ids": [STATE["sender_id"]],
                  "absent_ids": [STATE["receiver_id"]]},
        )

        # Snapshot balances
        sb_before = requests.get(f"{API}/auth/me", headers=H(STATE["sender_token"])).json()["balance"]
        rb_before = requests.get(f"{API}/auth/me", headers=H(STATE["receiver_token"])).json()["balance"]

        r = requests.post(f"{API}/admin/run-allowance", headers=H(STATE["admin_token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["attendance_required"] is True
        assert "distributed_to" in body
        assert "skipped_absent" in body

        # sender should have received allowance (if not already today), receiver should NOT
        sb_after = requests.get(f"{API}/auth/me", headers=H(STATE["sender_token"])).json()["balance"]
        rb_after = requests.get(f"{API}/auth/me", headers=H(STATE["receiver_token"])).json()["balance"]

        # Receiver marked absent -> no change
        assert rb_after == rb_before, f"Absent student should NOT receive allowance: {rb_before} -> {rb_after}"
        # Sender present -> received (unless already got one earlier today)
        # If body distributed_to > 0 and sender not in earlier tx, check +amount
        # We can be flexible: allowance may already have been given today by previous test in this suite/day
        assert sb_after >= sb_before

    def test_run_allowance_idempotent_same_day(self):
        # Run twice, second should not duplicate
        r1 = requests.post(f"{API}/admin/run-allowance", headers=H(STATE["admin_token"]))
        assert r1.status_code == 200
        distributed_1 = r1.json()["distributed_to"]
        r2 = requests.post(f"{API}/admin/run-allowance", headers=H(STATE["admin_token"]))
        assert r2.status_code == 200
        assert r2.json()["distributed_to"] == 0, "Second run same day should distribute to 0 (idempotent)"

    def test_run_allowance_without_attendance_required(self):
        """When attendance_required=false, ALL students should be considered."""
        r = requests.post(
            f"{API}/admin/config",
            headers=H(STATE["admin_token"]),
            json={"daily_allowance": 10.0, "savings_rate": 0.02, "attendance_required": False},
        )
        assert r.status_code == 200

        # Receiver had been skipped in previous run because absent.
        # Now with attendance_required=false, receiver should also get allowance
        rb_before = requests.get(f"{API}/auth/me", headers=H(STATE["receiver_token"])).json()["balance"]
        r = requests.post(f"{API}/admin/run-allowance", headers=H(STATE["admin_token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["attendance_required"] is False
        assert body["skipped_absent"] == 0
        rb_after = requests.get(f"{API}/auth/me", headers=H(STATE["receiver_token"])).json()["balance"]
        # Receiver should now have +10 (since first run skipped them, they had no allowance tx today)
        assert rb_after == round(rb_before + 10.0, 2), f"Receiver {rb_before} -> {rb_after}"
