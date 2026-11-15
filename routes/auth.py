"""Registration, login (citizen / staff / admin) and logout."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import security
from models import user as users
from utils import password_problem, safe_next, valid_email, valid_phone

bp = Blueprint("auth", __name__)
HOME = {"citizen": "citizen.dashboard", "staff": "staff.dashboard", "admin": "admin.dashboard"}


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        name, email = f.get("full_name", "").strip(), f.get("email", "").strip().lower()
        phone, pw = f.get("phone", "").strip(), f.get("password", "")
        errors = []
        if len(name) < 2 or len(name) > 100:
            errors.append("Please enter your full name.")
        if not valid_email(email):
            errors.append("Please enter a valid email address.")
        if not valid_phone(phone):
            errors.append("Phone number looks invalid.")
        if password_problem(pw):
            errors.append(password_problem(pw))
        if pw != f.get("confirm_password", ""):
            errors.append("Passwords do not match.")
        if not errors and users.find_by_email("citizen", email):
            errors.append("An account with this email already exists.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html", form=f), 400
        users.create_citizen(name, email, phone, pw)
        flash("Account created. You can log in now.", "success")
        return redirect(url_for("auth.login", role="citizen"))
    return render_template("register.html", form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    role = request.values.get("role", "citizen")
    if role not in users.TABLES:
        role = "citizen"
    if request.method == "POST":
        email, pw = request.form.get("email", "").strip().lower(), request.form.get("password", "")
        if security.throttled(email):
            flash("Too many failed attempts. Please wait 10 minutes and try again.", "danger")
            return render_template("login.html", role=role), 429
        u = users.authenticate(role, email, pw)
        if not u:
            security.record_fail(email)
            flash("Invalid email or password (or the account is deactivated).", "danger")
            return render_template("login.html", role=role, email=email), 401
        security.clear_fails(email)
        nxt = safe_next(session.get("next"))
        session.clear()  # prevent session fixation
        session.update(role=role, uid=u["id"])
        session.permanent = True
        flash(f"Welcome back, {u['full_name']}!", "success")
        if nxt and role == "citizen":
            return redirect(nxt)
        return redirect(url_for(HOME[role]))
    return render_template("login.html", role=role)


@bp.route("/admin/login")
def admin_login():
    return redirect(url_for("auth.login", role="admin"))


@bp.route("/staff/login")
def staff_login():
    return redirect(url_for("auth.login", role="staff"))


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("complaints.index"))
