"""Maintenance staff management."""
from werkzeug.security import generate_password_hash

from db import get_db
from utils import now


def create(name, email, phone, department, password):
    return get_db().execute(
        "INSERT INTO staff (full_name,email,phone,department,password_hash,is_active,created_at) "
        "VALUES (%s,%s,%s,%s,%s,1,%s)",
        (name, email.lower(), phone or None, department or None, generate_password_hash(password), now()))


def update(sid, name, phone, department):
    get_db().execute("UPDATE staff SET full_name=%s, phone=%s, department=%s WHERE id=%s",
                     (name, phone or None, department or None, sid))


def list_all():
    return get_db().query(
        """SELECT s.*,
             (SELECT COUNT(*) FROM complaints c WHERE c.assigned_staff_id=s.id
                AND c.status IN ('Assigned','In Progress')) AS open_count,
             (SELECT COUNT(*) FROM complaints c WHERE c.assigned_staff_id=s.id
                AND c.status='Resolved') AS done_count
           FROM staff s ORDER BY s.is_active DESC, s.full_name""")


def list_active():
    return get_db().query("SELECT id, full_name, department FROM staff WHERE is_active=1 ORDER BY full_name")
