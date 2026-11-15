"""In-app notifications for citizens."""
from db import get_db
from utils import now


def add(user_id, complaint_id, message):
    get_db().execute(
        "INSERT INTO notifications (user_id,complaint_id,message,is_read,created_at) VALUES (%s,%s,%s,0,%s)",
        (user_id, complaint_id, message[:500], now()))


def unread_count(user_id):
    return get_db().scalar("SELECT COUNT(*) FROM notifications WHERE user_id=%s AND is_read=0", (user_id,))


def list_for(user_id, limit=50):
    return get_db().query(
        """SELECT n.*, c.complaint_code FROM notifications n
           LEFT JOIN complaints c ON c.id=n.complaint_id
           WHERE n.user_id=%s ORDER BY n.created_at DESC, n.id DESC LIMIT %s""", (user_id, limit))


def mark_read(user_id, nid=None):
    if nid:
        get_db().execute("UPDATE notifications SET is_read=1 WHERE user_id=%s AND id=%s", (user_id, nid))
    else:
        get_db().execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (user_id,))
