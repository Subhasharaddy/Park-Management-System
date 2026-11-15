"""Complaint data access and the single place where status changes happen."""
import secrets
from collections import Counter, OrderedDict

from constants import ACTIVE_STATUSES, PENDING_STATUSES, STATUSES
from db import get_db
from models import notification
from utils import now

BASE = """SELECT c.*, COALESCE(p.name, c.park_other) AS park_name,
                 u.full_name AS citizen_name, u.email AS citizen_email,
                 s.full_name AS staff_name
          FROM complaints c
          LEFT JOIN parks p ON p.id = c.park_id
          JOIN users u ON u.id = c.user_id
          LEFT JOIN staff s ON s.id = c.assigned_staff_id"""


def get_by_id(cid):
    return get_db().one(BASE + " WHERE c.id=%s", (cid,))


def get_by_code(code):
    return get_db().one(BASE + " WHERE c.complaint_code=%s", (code.strip().upper(),))


def updates_for(cid):
    return get_db().query("SELECT * FROM complaint_updates WHERE complaint_id=%s ORDER BY created_at, id", (cid,))


def create(user, park_id, park_other, title, description, category, lat, lng, photo):
    db = get_db()
    ts = now()
    with db.transaction():
        cid = db.execute(
            """INSERT INTO complaints (complaint_code,user_id,park_id,park_other,title,description,category,
               latitude,longitude,photo_path,status,created_at,updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Submitted',%s,%s)""",
            ("TMP" + secrets.token_hex(8), user["id"], park_id, park_other, title, description, category,
             lat, lng, photo, ts, ts))
        code = f"PC-{ts.year}-{cid:04d}"
        db.execute("UPDATE complaints SET complaint_code=%s WHERE id=%s", (code, cid))
        db.execute(
            """INSERT INTO complaint_updates (complaint_id,actor_role,actor_name,old_status,new_status,remark,created_at)
               VALUES (%s,'citizen',%s,NULL,'Submitted','Complaint submitted by citizen.',%s)""",
            (cid, user["full_name"], ts))
        notification.add(user["id"], cid, f"Your complaint {code} was submitted successfully.")
    return cid, code


def search(q="", status="", category="", user_id=None, staff_id=None, date_from="", date_to="",
           page=1, per_page=12):
    where, params = [], []
    if q:
        where.append("(c.complaint_code LIKE %s OR c.title LIKE %s OR c.description LIKE %s "
                     "OR COALESCE(p.name, c.park_other) LIKE %s)")
        params += [f"%{q}%"] * 4
    if status in STATUSES:
        where.append("c.status=%s"); params.append(status)
    if category:
        where.append("c.category=%s"); params.append(category)
    if user_id:
        where.append("c.user_id=%s"); params.append(user_id)
    if staff_id:
        where.append("c.assigned_staff_id=%s"); params.append(staff_id)
    if date_from:
        where.append("c.created_at >= %s"); params.append(date_from + " 00:00:00")
    if date_to:
        where.append("c.created_at <= %s"); params.append(date_to + " 23:59:59")
    w = (" WHERE " + " AND ".join(where)) if where else ""
    db = get_db()
    total = db.scalar(
        "SELECT COUNT(*) FROM complaints c LEFT JOIN parks p ON p.id=c.park_id" + w, params)
    rows = db.query(BASE + w + " ORDER BY c.created_at DESC, c.id DESC LIMIT %s OFFSET %s",
                    params + [per_page, (page - 1) * per_page])
    return rows, total


def status_counts(user_id=None, staff_id=None):
    where, params = "", []
    if user_id:
        where, params = "WHERE user_id=%s", [user_id]
    elif staff_id:
        where, params = "WHERE assigned_staff_id=%s", [staff_id]
    rows = get_db().query(f"SELECT status, COUNT(*) AS n FROM complaints {where} GROUP BY status", params)
    out = {s: 0 for s in STATUSES}
    out.update({r["status"]: r["n"] for r in rows})
    out["Total"] = sum(out[s] for s in STATUSES)
    out["Pending"] = sum(out[s] for s in PENDING_STATUSES)
    return out


def public_stats():
    c = status_counts()
    return {"total": c["Total"], "resolved": c["Resolved"],
            "pending": sum(c[s] for s in ACTIVE_STATUSES),
            "parks": get_db().scalar("SELECT COUNT(*) FROM parks")}


def category_counts():
    return get_db().query("SELECT category AS label, COUNT(*) AS n FROM complaints GROUP BY category ORDER BY n DESC")


def park_counts(limit=6):
    return get_db().query(
        """SELECT COALESCE(p.name, c.park_other) AS label, COUNT(*) AS n FROM complaints c
           LEFT JOIN parks p ON p.id=c.park_id GROUP BY COALESCE(p.name, c.park_other)
           ORDER BY n DESC LIMIT %s""", (limit,))


def monthly_counts(months=6):
    rows = get_db().query("SELECT created_at, status FROM complaints")
    cnt, res = Counter(), Counter()
    for r in rows:
        key = str(r["created_at"])[:7]
        cnt[key] += 1
        if r["status"] == "Resolved":
            res[key] += 1
    today = now()
    keys = []
    y, m = today.year, today.month
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys.reverse()
    return {"labels": keys, "reported": [cnt[k] for k in keys], "resolved": [res[k] for k in keys]}


def map_points(staff_id=None):
    w, p = ("WHERE assigned_staff_id=%s", [staff_id]) if staff_id else ("", [])
    return get_db().query(
        f"SELECT id, complaint_code, title, category, status, latitude, longitude FROM complaints {w}", p)


class StatusError(ValueError):
    pass


def apply_update(c, *, new_status, role, actor_name, remark="", reason=None, photo=None, staff_id=None):
    """Change status / assignment, write the audit trail and notify the citizen - atomically."""
    if new_status not in STATUSES:
        raise StatusError("Unknown status.")
    old = c["status"]
    if new_status == "Rejected" and not (reason or "").strip():
        raise StatusError("A rejection reason is required.")
    if new_status == "Assigned" and not (staff_id or c["assigned_staff_id"]):
        raise StatusError("Assign a staff member before setting the status to Assigned.")
    ts = now()
    f = OrderedDict(status=new_status, updated_at=ts)
    if staff_id:
        f["assigned_staff_id"] = staff_id
    if new_status == "Rejected":
        f["rejection_reason"] = reason.strip()[:500]
    elif old == "Rejected":
        f["rejection_reason"] = None
    if new_status == "Resolved":
        f["resolved_at"] = ts
        if photo:
            f["resolution_photo_path"] = photo
    elif old == "Resolved":
        f["resolved_at"] = None
    sets = ", ".join(f"{k}=%s" for k in f)  # keys are fixed literals above
    log_remark = (remark or "").strip()[:1000]
    if new_status == "Rejected":
        log_remark = (log_remark + " " if log_remark else "") + f"Reason: {reason.strip()[:500]}"
    db = get_db()
    with db.transaction():
        db.execute(f"UPDATE complaints SET {sets} WHERE id=%s", list(f.values()) + [c["id"]])
        db.execute(
            """INSERT INTO complaint_updates (complaint_id,actor_role,actor_name,old_status,new_status,remark,photo_path,created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (c["id"], role, actor_name, old, new_status, log_remark or None, photo, ts))
        if new_status != old:
            msg = f"Complaint {c['complaint_code']} is now '{new_status}'."
        elif log_remark:
            msg = f"New update on complaint {c['complaint_code']}."
        else:
            msg = None
        if msg:
            notification.add(c["user_id"], c["id"], msg)


def delete(cid):
    db = get_db()
    with db.transaction():
        db.execute("DELETE FROM complaints WHERE id=%s", (cid,))
