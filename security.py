"""CSRF protection, login throttling, role guards and security headers."""
import secrets
import time
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for

_FAILS = {}  # (ip, email) -> [count, first_ts]
MAX_FAILS, WINDOW = 5, 600


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def throttled(email):
    key = (request.remote_addr, email.lower())
    rec = _FAILS.get(key)
    if rec and time.time() - rec[1] > WINDOW:
        _FAILS.pop(key, None)
        return False
    return bool(rec and rec[0] >= MAX_FAILS)


def record_fail(email):
    key = (request.remote_addr, email.lower())
    rec = _FAILS.setdefault(key, [0, time.time()])
    rec[0] += 1


def clear_fails(email):
    _FAILS.pop((request.remote_addr, email.lower()), None)


def role_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if g.get("user") is None or g.role != role:
                flash("Please log in to continue.", "warning")
                session["next"] = request.full_path.rstrip("?") if request.method == "GET" else None
                return redirect(url_for("auth.login", role=role))
            return fn(*a, **kw)
        return wrapper
    return deco


def init_app(app):
    from models import notification, user as users

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def _csrf_and_user():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
            expected = session.get("_csrf", "")
            if not sent or not expected or not secrets.compare_digest(sent, expected):
                abort(400, "Invalid or missing CSRF token. Please reload the page and try again.")
        g.user, g.role = None, session.get("role")
        if g.role and session.get("uid"):
            u = users.get(g.role, session["uid"])
            if u and (g.role == "admin" or u.get("is_active")):
                g.user = u
            else:
                session.clear()
                g.role = None

    @app.context_processor
    def _ctx():
        unread = 0
        if g.get("user") and g.role == "citizen":
            unread = notification.unread_count(g.user["id"])
        return {"current_user": g.get("user"), "role": g.get("role"), "unread_count": unread}

    @app.after_request
    def _headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.endpoint != "static":
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp
