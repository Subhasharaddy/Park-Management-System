"""Admin dashboard: complaints, citizens, staff, reports."""
import csv
import io

from flask import (Blueprint, Response, flash, g, redirect, render_template, request, url_for)

from constants import CATEGORY_NAMES, STATUSES
from models import complaint
from models import staff as staff_model
from models import user as users
from security import role_required
from utils import delete_upload, password_problem, save_image, valid_email, valid_phone

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _filters():
    a = request.args
    return dict(q=a.get("q", "").strip(), status=a.get("status", ""), category=a.get("category", ""),
                date_from=a.get("date_from", ""), date_to=a.get("date_to", ""))


@bp.route("/")
@role_required("admin")
def dashboard():
    counts = complaint.status_counts()
    recent, _ = complaint.search(per_page=6)
    charts = dict(
        status={"labels": STATUSES, "data": [counts[s] for s in STATUSES]},
        category=complaint.category_counts(),
        parks=complaint.park_counts(),
        monthly=complaint.monthly_counts(),
    )
    return render_template("admin_dashboard.html", counts=counts, recent=recent, charts=charts,
                           points=complaint.map_points())


@bp.route("/complaints")
@role_required("admin")
def complaints():
    page = max(request.args.get("page", 1, type=int), 1)
    f = _filters()
    rows, total = complaint.search(page=page, per_page=12, **f)
    return render_template("admin_complaints.html", complaints=rows, total=total, page=page,
                           pages=(total + 11) // 12, f=f)


@bp.route("/complaints/<int:cid>")
@role_required("admin")
def complaint_detail(cid):
    c = complaint.get_by_id(cid)
    if not c:
        return render_template("404.html"), 404
    return render_template("admin_complaint.html", c=c, updates=complaint.updates_for(cid),
                           staff_list=staff_model.list_active())


@bp.route("/complaints/<int:cid>/status", methods=["POST"])
@role_required("admin")
def update_status(cid):
    c = complaint.get_by_id(cid)
    if not c:
        return render_template("404.html"), 404
    f = request.form
    new_status = f.get("status", "")
    photo = None
    try:
        photo = save_image(request.files.get("resolution_photo"))
        staff_id = None
        if new_status == "Assigned" and f.get("staff_id", "").isdigit():
            staff_id = int(f["staff_id"])
            if not any(m["id"] == staff_id for m in staff_model.list_active()):
                raise ValueError("Please choose an active staff member.")
        complaint.apply_update(c, new_status=new_status, role="admin", actor_name=g.user["full_name"],
                               remark=f.get("remark", ""), reason=f.get("rejection_reason", ""),
                               photo=photo, staff_id=staff_id)
        flash("Complaint updated and the citizen has been notified.", "success")
    except (ValueError, complaint.StatusError) as e:
        delete_upload(photo)
        flash(str(e), "danger")
    return redirect(url_for("admin.complaint_detail", cid=cid))


@bp.route("/complaints/<int:cid>/assign", methods=["POST"])
@role_required("admin")
def assign(cid):
    c = complaint.get_by_id(cid)
    if not c:
        return render_template("404.html"), 404
    sid = request.form.get("staff_id", type=int)
    member = next((s for s in staff_model.list_active() if s["id"] == sid), None)
    if not member:
        flash("Please choose an active staff member.", "danger")
    elif c["status"] in ("Resolved", "Rejected"):
        flash("Re-open the complaint (change its status) before assigning staff.", "warning")
    else:
        new_status = "Assigned" if c["status"] in ("Submitted", "Under Review") else c["status"]
        complaint.apply_update(c, new_status=new_status, role="admin", actor_name=g.user["full_name"],
                               remark=f"Assigned to {member['full_name']}. " + request.form.get("remark", "").strip(),
                               staff_id=sid)
        flash(f"Assigned to {member['full_name']}.", "success")
    return redirect(url_for("admin.complaint_detail", cid=cid))


@bp.route("/complaints/<int:cid>/delete", methods=["POST"])
@role_required("admin")
def delete_complaint(cid):
    c = complaint.get_by_id(cid)
    if not c:
        return render_template("404.html"), 404
    if request.form.get("confirm_code", "").strip().upper() != c["complaint_code"]:
        flash("Deletion cancelled: the confirmation ID did not match.", "warning")
        return redirect(url_for("admin.complaint_detail", cid=cid))
    complaint.delete(cid)
    for p in (c["photo_path"], c["resolution_photo_path"]):
        delete_upload(p)
    flash(f"Complaint {c['complaint_code']} permanently deleted.", "success")
    return redirect(url_for("admin.complaints"))


@bp.route("/citizens")
@role_required("admin")
def citizens():
    page = max(request.args.get("page", 1, type=int), 1)
    q = request.args.get("q", "").strip()
    rows, total = users.list_citizens(q, page)
    return render_template("admin_citizens.html", citizens=rows, total=total, page=page,
                           pages=(total + 14) // 15, q=q)


@bp.route("/citizens/<int:uid>/toggle", methods=["POST"])
@role_required("admin")
def toggle_citizen(uid):
    u = users.get("citizen", uid)
    if u:
        users.set_active("citizen", uid, not u["is_active"])
        flash(f"{u['full_name']} {'deactivated' if u['is_active'] else 'activated'}.", "success")
    return redirect(request.referrer or url_for("admin.citizens"))


@bp.route("/staff", methods=["GET", "POST"])
@role_required("admin")
def staff():
    if request.method == "POST":
        f = request.form
        name, email = f.get("full_name", "").strip(), f.get("email", "").strip().lower()
        phone, dept, pw = f.get("phone", "").strip(), f.get("department", "").strip(), f.get("password", "")
        errors = []
        if len(name) < 2:
            errors.append("Staff name is required.")
        if not valid_email(email):
            errors.append("Valid email required.")
        elif users.find_by_email("staff", email):
            errors.append("A staff account with this email exists.")
        if not valid_phone(phone):
            errors.append("Phone number looks invalid.")
        if password_problem(pw):
            errors.append(password_problem(pw))
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            staff_model.create(name, email, phone, dept[:100], pw)
            flash(f"Staff account created for {name}.", "success")
            return redirect(url_for("admin.staff"))
    return render_template("admin_staff.html", staff_list=staff_model.list_all())


@bp.route("/staff/<int:sid>/edit", methods=["POST"])
@role_required("admin")
def edit_staff(sid):
    s = users.get("staff", sid)
    if not s:
        return render_template("404.html"), 404
    f = request.form
    name, phone = f.get("full_name", "").strip(), f.get("phone", "").strip()
    if len(name) < 2 or not valid_phone(phone):
        flash("Please provide a valid name and phone number.", "danger")
        return redirect(url_for("admin.staff"))
    staff_model.update(sid, name, phone, f.get("department", "").strip()[:100])
    new_pw = f.get("new_password", "")
    if new_pw:
        if password_problem(new_pw):
            flash(password_problem(new_pw), "danger")
            return redirect(url_for("admin.staff"))
        users.set_password("staff", sid, new_pw)
    flash("Staff details updated.", "success")
    return redirect(url_for("admin.staff"))


@bp.route("/staff/<int:sid>/toggle", methods=["POST"])
@role_required("admin")
def toggle_staff(sid):
    s = users.get("staff", sid)
    if s:
        users.set_active("staff", sid, not s["is_active"])
        flash(f"{s['full_name']} {'deactivated' if s['is_active'] else 'activated'}.", "success")
    return redirect(url_for("admin.staff"))


@bp.route("/reports")
@role_required("admin")
def reports():
    f = _filters()
    rows, total = complaint.search(per_page=500, **f)
    by_status = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    return render_template("admin_reports.html", rows=rows, total=total, f=f, by_status=by_status)


def _csv_safe(v):
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # block spreadsheet formula injection


@bp.route("/reports/export.csv")
@role_required("admin")
def export_csv():
    rows, _ = complaint.search(per_page=100000, **_filters())
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Complaint ID", "Title", "Category", "Park", "Status", "Citizen", "Assigned staff",
                "Latitude", "Longitude", "Submitted", "Resolved"])
    for r in rows:
        w.writerow([_csv_safe(x) for x in (r["complaint_code"], r["title"], r["category"], r["park_name"],
                                           r["status"], r["citizen_name"], r["staff_name"], r["latitude"],
                                           r["longitude"], r["created_at"], r["resolved_at"])])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=parkcare_report.csv"})
