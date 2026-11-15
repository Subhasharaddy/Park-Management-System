"""Citizen dashboard, profile and notifications."""
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

from models import complaint, notification
from models import user as users
from security import role_required
from utils import password_problem, valid_phone

bp = Blueprint("citizen", __name__)


@bp.route("/dashboard")
@role_required("citizen")
def dashboard():
    page = max(request.args.get("page", 1, type=int), 1)
    status = request.args.get("status", "")
    rows, total = complaint.search(user_id=g.user["id"], status=status, page=page, per_page=8)
    return render_template("citizen_dashboard.html", complaints=rows, total=total, page=page, pages=(total + 7) // 8,
                           counts=complaint.status_counts(user_id=g.user["id"]), status=status,
                           notes=notification.list_for(g.user["id"], 5))


@bp.route("/profile", methods=["GET", "POST"])
@role_required("citizen")
def profile():
    if request.method == "POST":
        f = request.form
        name, phone = f.get("full_name", "").strip(), f.get("phone", "").strip()
        errors = []
        if len(name) < 2 or len(name) > 100:
            errors.append("Please enter your full name.")
        if not valid_phone(phone):
            errors.append("Phone number looks invalid.")
        new_pw = f.get("new_password", "")
        if new_pw:
            if not users.authenticate("citizen", g.user["email"], f.get("current_password", "")):
                errors.append("Current password is incorrect.")
            elif password_problem(new_pw):
                errors.append(password_problem(new_pw))
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("profile.html"), 400
        users.update_citizen(g.user["id"], name, phone)
        if new_pw:
            users.set_password("citizen", g.user["id"], new_pw)
        flash("Profile updated.", "success")
        return redirect(url_for("citizen.profile"))
    return render_template("profile.html")


@bp.route("/notifications")
@role_required("citizen")
def notifications():
    return render_template("notifications.html", notes=notification.list_for(g.user["id"], 100))


@bp.route("/notifications/read", methods=["POST"])
@role_required("citizen")
def mark_read():
    nid = request.form.get("id", type=int)
    notification.mark_read(g.user["id"], nid)
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True, unread=notification.unread_count(g.user["id"]))
    return redirect(url_for("citizen.notifications"))


@bp.route("/api/notifications/unread")
@role_required("citizen")
def api_unread():
    return jsonify(unread=notification.unread_count(g.user["id"]))
