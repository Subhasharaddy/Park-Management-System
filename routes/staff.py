"""Staff dashboard - staff only ever see complaints assigned to them."""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from models import complaint
from security import role_required
from utils import delete_upload, save_image

bp = Blueprint("staff", __name__, url_prefix="/staff")
STAFF_STATUSES = ("In Progress", "Resolved")


def _mine(cid):
    c = complaint.get_by_id(cid)
    return c if c and c["assigned_staff_id"] == g.user["id"] else None


@bp.route("/")
@role_required("staff")
def dashboard():
    status = request.args.get("status", "")
    rows, total = complaint.search(staff_id=g.user["id"], status=status, per_page=100)
    return render_template("staff_dashboard.html", complaints=rows, total=total, status=status,
                           counts=complaint.status_counts(staff_id=g.user["id"]),
                           points=complaint.map_points(staff_id=g.user["id"]))


@bp.route("/complaints/<int:cid>")
@role_required("staff")
def detail(cid):
    c = _mine(cid)
    if not c:
        return render_template("404.html"), 404  # same answer whether it exists or not
    return render_template("staff_complaint.html", c=c, updates=complaint.updates_for(cid))


@bp.route("/complaints/<int:cid>/update", methods=["POST"])
@role_required("staff")
def update(cid):
    c = _mine(cid)
    if not c:
        return render_template("404.html"), 404
    f = request.form
    new_status, remark = f.get("status", ""), f.get("remark", "").strip()
    photo = None
    try:
        if c["status"] not in ("Assigned", "In Progress"):
            raise ValueError("This complaint is closed. Contact the admin to re-open it.")
        if new_status not in STAFF_STATUSES:
            raise ValueError("Choose 'In Progress' or 'Resolved'.")
        photo = save_image(request.files.get("repair_photo"))
        if new_status == "Resolved" and not photo:
            raise ValueError("Upload a photo of the completed repair to mark the work as completed.")
        if new_status == "Resolved" and not remark:
            raise ValueError("Add a short work remark describing what was done.")
        complaint.apply_update(c, new_status=new_status, role="staff", actor_name=g.user["full_name"],
                               remark=remark, photo=photo)
        flash("Progress updated. The citizen has been notified.", "success")
    except (ValueError, complaint.StatusError) as e:
        delete_upload(photo)
        flash(str(e), "danger")
    return redirect(url_for("staff.detail", cid=cid))
