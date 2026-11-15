"""Public pages, complaint submission and tracking."""
from flask import (Blueprint, current_app, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)

from constants import CATEGORY_NAMES, TRACK_STEPS
from db import get_db
from models import complaint
from security import role_required
from utils import parse_coord, save_image, delete_upload

bp = Blueprint("complaints", __name__)


@bp.route("/")
def index():
    return render_template("index.html", stats=complaint.public_stats())


@bp.route("/api/stats")
def api_stats():
    return jsonify(complaint.public_stats())


@bp.route("/report", methods=["GET", "POST"])
@role_required("citizen")
def report():
    db = get_db()
    parks = db.query("SELECT id, name, latitude, longitude FROM parks ORDER BY name")
    cfg = current_app.config
    ctx = dict(parks=parks, default_lat=cfg["MAP_DEFAULT_LAT"], default_lng=cfg["MAP_DEFAULT_LNG"])
    if request.method == "POST":
        f = request.form
        title, desc, cat = f.get("title", "").strip(), f.get("description", "").strip(), f.get("category", "")
        park_sel, park_other = f.get("park_id", ""), f.get("park_other", "").strip()
        errors, park_id = [], None
        if not 5 <= len(title) <= 150:
            errors.append("Title must be 5-150 characters.")
        if not 10 <= len(desc) <= 2000:
            errors.append("Description must be 10-2000 characters.")
        if cat not in CATEGORY_NAMES:
            errors.append("Please choose an issue category.")
        if park_sel == "other":
            if len(park_other) < 3:
                errors.append("Please enter the park name.")
            park_other = park_other[:150]
        elif park_sel.isdigit() and any(p["id"] == int(park_sel) for p in parks):
            park_id, park_other = int(park_sel), None
        else:
            errors.append("Please select a park.")
        coords = parse_coord(f.get("latitude"), f.get("longitude"))
        if not coords:
            errors.append("Please set the issue location (use GPS or click on the map).")
        photo = None
        if not errors:
            try:
                photo = save_image(request.files.get("photo"))
            except ValueError as e:
                errors.append(str(e))
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("complaint.html", form=f, **ctx), 400
        try:
            _cid, code = complaint.create(g.user, park_id, park_other, title, desc, cat, *coords, photo)
        except Exception:
            delete_upload(photo)
            current_app.logger.exception("Could not save complaint")
            flash("Could not save your complaint. Please try again.", "danger")
            return render_template("complaint.html", form=f, **ctx), 500
        flash(f"Complaint submitted! Your complaint ID is {code}.", "success")
        return redirect(url_for("complaints.track", code=code))
    return render_template("complaint.html", form={}, **ctx)


def _tracking_context(c):
    status = c["status"]
    if status == "Rejected":
        step = -1
    else:
        step = TRACK_STEPS.index(status)
    return dict(c=c, updates=complaint.updates_for(c["id"]), steps=TRACK_STEPS, step=step)


@bp.route("/track", methods=["GET"])
def track_form():
    code = request.args.get("code", "").strip()
    if code:
        return redirect(url_for("complaints.track", code=code))
    mine = []
    if g.user and g.role == "citizen":
        mine, _ = complaint.search(user_id=g.user["id"], per_page=50)
    return render_template("tracking.html", c=None, mine=mine)


@bp.route("/track/<code>")
def track(code):
    c = complaint.get_by_code(code)
    mine = []
    if g.user and g.role == "citizen":
        mine, _ = complaint.search(user_id=g.user["id"], per_page=50)
    if not c:
        flash(f"No complaint found with ID '{code[:30]}'. Check the ID and try again.", "warning")
        return render_template("tracking.html", c=None, mine=mine), 404
    return render_template("tracking.html", mine=mine, **_tracking_context(c))


@bp.route("/api/track/<code>")
def api_track(code):
    c = complaint.get_by_code(code)
    if not c:
        return jsonify(error="Not found"), 404
    return jsonify(code=c["complaint_code"], status=c["status"], updated_at=str(c["updated_at"]))
