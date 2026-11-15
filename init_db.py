"""Create the database, tables, sample parks and the first admin.

    python init_db.py            # schema + parks + admin
    python init_db.py --demo     # also add demo citizen/staff accounts and sample complaints

No passwords are hard-coded: values come from .env (ADMIN_PASSWORD) or a random one is generated and
printed once. Demo credentials are also written to instance/demo_credentials.txt (git-ignored).
"""
import argparse
import random
import secrets
from datetime import timedelta
from pathlib import Path

import db
from app import create_app
from models import complaint, staff as staff_model, user as users
from utils import now


def _pw():
    return "Pc" + secrets.token_urlsafe(8).replace("-", "x").replace("_", "y") + "7"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="add demo accounts + sample complaints")
    args = ap.parse_args()
    app = create_app()
    lines = []
    with app.app_context():
        cfg = app.config
        database = db.connect(cfg, create_database=True)
        db.init_schema(database)
        database.close()
        print("Tables created, parks seeded.")
        if not users.find_by_email("admin", cfg["ADMIN_EMAIL"]):
            pw = cfg["ADMIN_PASSWORD"] or _pw()
            users.create_admin(cfg["ADMIN_NAME"], cfg["ADMIN_EMAIL"], pw)
            lines.append(f"ADMIN   {cfg['ADMIN_EMAIL']}  /  {pw}")
        else:
            print("Admin already exists - left unchanged.")
        if args.demo:
            _demo(lines)
    if lines:
        print("\n=== Credentials (shown once) ===")
        print("\n".join(lines))
        out = Path(app.instance_path) / "demo_credentials.txt"
        out.write_text("\n".join(lines) + "\n")
        print(f"(also saved to {out})")


def _demo(lines):
    if not users.find_by_email("citizen", "citizen@parkcare.local"):
        pw = _pw()
        users.create_citizen("Demo Citizen", "citizen@parkcare.local", "9876543210", pw)
        lines.append(f"CITIZEN citizen@parkcare.local  /  {pw}")
    for name, email, dept in (("Ravi Maintenance", "ravi@parkcare.local", "Horticulture"),
                              ("Meena Repairs", "meena@parkcare.local", "Civil Works")):
        if not users.find_by_email("staff", email):
            pw = _pw()
            staff_model.create(name, email, "9000000000", dept, pw)
            lines.append(f"STAFF   {email}  /  {pw}")
    citizen = users.find_by_email("citizen", "citizen@parkcare.local")
    d = db.get_db()
    if d.scalar("SELECT COUNT(*) FROM complaints") > 0:
        return
    parks = d.query("SELECT * FROM parks")
    staff = staff_model.list_active()
    samples = [("Bench slats broken near fountain", "Broken Bench", "Three slats are cracked and one is missing."),
               ("Pipe leaking by the walkway", "Water Leakage", "Continuous leak forming a puddle on the path."),
               ("Dustbins overflowing", "Garbage Overflow", "Bins have not been emptied for days."),
               ("Cracked tiles on jogging track", "Damaged Pathway", "Several tiles lifted - trip hazard."),
               ("Street light not working", "Broken Street Light", "Dark stretch near the east gate."),
               ("Swing chain rusted", "Damaged Playground", "Chain looks unsafe for children.")]
    rnd = random.Random(7)
    flow = ["Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Rejected"]
    for i, (t, cat, desc) in enumerate(samples):
        p = parks[i % len(parks)]
        cid, _ = complaint.create(citizen, p["id"], None, t, desc, cat,
                                  float(p["latitude"]) + rnd.uniform(-.002, .002),
                                  float(p["longitude"]) + rnd.uniform(-.002, .002), None)
        c = complaint.get_by_id(cid)
        st = flow[i]
        if st in ("Assigned", "In Progress", "Resolved"):
            complaint.apply_update(c, new_status="Assigned", role="admin", actor_name="Demo Admin",
                                   remark="Assigned for repair.", staff_id=staff[i % len(staff)]["id"])
            c = complaint.get_by_id(cid)
        if st == "Under Review":
            complaint.apply_update(c, new_status="Under Review", role="admin", actor_name="Demo Admin", remark="Reviewing.")
        elif st in ("In Progress", "Resolved"):
            complaint.apply_update(c, new_status="In Progress", role="staff", actor_name="Demo Staff", remark="Work started.")
            if st == "Resolved":
                complaint.apply_update(complaint.get_by_id(cid), new_status="Resolved", role="staff",
                                       actor_name="Demo Staff", remark="Repair completed.")
        elif st == "Rejected":
            complaint.apply_update(c, new_status="Rejected", role="admin", actor_name="Demo Admin",
                                   reason="Duplicate of an existing complaint.")
        d.execute("UPDATE complaints SET created_at=%s WHERE id=%s", (now() - timedelta(days=(6 - i) * 9), cid))
    lines.append("(6 sample complaints added for the demo citizen)")


if __name__ == "__main__":
    main()
