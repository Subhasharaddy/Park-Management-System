"""Accounts for all three roles (citizen -> users, admin -> admins, staff -> staff)."""
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db
from utils import now

TABLES = {"citizen": "users", "admin": "admins", "staff": "staff"}


def _t(role):
    return TABLES[role]  # whitelisted table name, never user input


def get(role, uid):
    if role not in TABLES:
        return None
    return get_db().one(f"SELECT * FROM {_t(role)} WHERE id=%s", (uid,))


def find_by_email(role, email):
    return get_db().one(f"SELECT * FROM {_t(role)} WHERE email=%s", (email.strip().lower(),))


def authenticate(role, email, password):
    u = find_by_email(role, email)
    # Always run a hash check so timing doesn't reveal whether the email exists.
    ok = check_password_hash(u["password_hash"] if u else _DUMMY, password)
    if u and ok and (role == "admin" or u["is_active"]):
        return u
    return None


_DUMMY = generate_password_hash("not-a-real-password")


def create_citizen(name, email, phone, password):
    return get_db().execute(
        "INSERT INTO users (full_name,email,phone,password_hash,is_active,created_at) VALUES (%s,%s,%s,%s,1,%s)",
        (name, email.lower(), phone or None, generate_password_hash(password), now()))


def create_admin(name, email, password):
    return get_db().execute(
        "INSERT INTO admins (full_name,email,password_hash,created_at) VALUES (%s,%s,%s,%s)",
        (name, email.lower(), generate_password_hash(password), now()))


def update_citizen(uid, name, phone):
    get_db().execute("UPDATE users SET full_name=%s, phone=%s WHERE id=%s", (name, phone or None, uid))


def set_password(role, uid, password):
    get_db().execute(f"UPDATE {_t(role)} SET password_hash=%s WHERE id=%s",
                     (generate_password_hash(password), uid))


def list_citizens(q="", page=1, per_page=15):
    where, params = "", []
    if q:
        where = "WHERE u.full_name LIKE %s OR u.email LIKE %s"
        params = [f"%{q}%", f"%{q}%"]
    db = get_db()
    total = db.scalar(f"SELECT COUNT(*) FROM users u {where}", params)
    rows = db.query(
        f"""SELECT u.*, (SELECT COUNT(*) FROM complaints c WHERE c.user_id=u.id) AS complaint_count
            FROM users u {where} ORDER BY u.created_at DESC, u.id DESC LIMIT %s OFFSET %s""",
        params + [per_page, (page - 1) * per_page])
    return rows, total


def set_active(role, uid, active):
    get_db().execute(f"UPDATE {_t(role)} SET is_active=%s WHERE id=%s", (1 if active else 0, uid))
