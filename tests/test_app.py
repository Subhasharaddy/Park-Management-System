"""End-to-end tests against a temporary SQLite database (run: python -m unittest discover -s tests -v)."""
import io
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

import db  # noqa: E402
import security  # noqa: E402
from app import create_app  # noqa: E402
from models import complaint, staff as staff_model, user as users  # noqa: E402

PW = "Passw0rd123"


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (30, 160, 80)).save(buf, "PNG")
    buf.seek(0)
    return buf


class Base(unittest.TestCase):
    def setUp(self):
        security._FAILS.clear()
        self.tmp = tempfile.mkdtemp()
        self.app = create_app({"TESTING": True, "DB_BACKEND": "sqlite", "SECRET_KEY": "test",
                               "SQLITE_PATH": os.path.join(self.tmp, "t.sqlite3"),
                               "UPLOAD_FOLDER": os.path.join(self.tmp, "uploads")})
        os.makedirs(self.app.config["UPLOAD_FOLDER"], exist_ok=True)
        with self.app.app_context():
            d = db.connect(self.app.config)
            db.init_schema(d)
            d.close()
            users.create_admin("Admin", "admin@t.local", PW)
            users.create_citizen("Cathy Citizen", "cathy@t.local", "", PW)
            staff_model.create("Sam Staff", "sam@t.local", "", "Civil", PW)
            staff_model.create("Other Staff", "other@t.local", "", "Civil", PW)
        self.c = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def token(self, client=None, path="/login"):
        client = client or self.c
        html = client.get(path).get_data(as_text=True)
        return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)

    def post(self, path, data=None, client=None, **kw):
        client = client or self.c
        data = dict(data or {})
        data["csrf_token"] = self.token(client)
        return client.post(path, data=data, **kw)

    def login(self, role, email, client=None):
        r = self.post("/login", {"role": role, "email": email, "password": PW}, client=client)
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True)[:300])

    def new_complaint(self, title="Bench is broken"):
        self.login("citizen", "cathy@t.local")
        r = self.post("/report", {"title": title, "description": "Two slats are missing near the gate.",
                                  "category": "Broken Bench", "park_id": "1", "latitude": "12.97", "longitude": "77.59",
                                  "photo": (png_bytes(), "x.png")}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        return re.search(r"/track/(PC-\d{4}-\d{4})", r.headers["Location"]).group(1)


class TestPublicAndAuth(Base):
    def test_pages_render(self):
        for path in ("/", "/login", "/register", "/track", "/api/stats"):
            self.assertEqual(self.c.get(path).status_code, 200, path)
        self.assertEqual(self.c.get("/nope").status_code, 404)
        self.assertIn("404", self.c.get("/nope").get_data(as_text=True))

    def test_stats_come_from_db(self):
        self.new_complaint()
        s = self.c.get("/api/stats").get_json()
        self.assertEqual((s["total"], s["resolved"], s["pending"], s["parks"]), (1, 0, 1, 6))

    def test_csrf_enforced(self):
        self.assertEqual(self.c.post("/login", data={"email": "a", "password": "b"}).status_code, 400)

    def test_register_validation_and_login(self):
        r = self.post("/register", {"full_name": "A", "email": "bad", "password": "short", "confirm_password": "x"})
        self.assertEqual(r.status_code, 400)
        r = self.post("/register", {"full_name": "New User", "email": "new@t.local", "password": PW, "confirm_password": PW})
        self.assertEqual(r.status_code, 302)
        r = self.post("/register", {"full_name": "New User", "email": "new@t.local", "password": PW, "confirm_password": PW})
        self.assertEqual(r.status_code, 400)  # duplicate
        self.login("citizen", "new@t.local")
        self.assertEqual(self.c.get("/dashboard").status_code, 200)

    def test_wrong_password_and_throttle(self):
        for _ in range(5):
            r = self.post("/login", {"role": "citizen", "email": "cathy@t.local", "password": "wrong"})
            self.assertEqual(r.status_code, 401)
        r = self.post("/login", {"role": "citizen", "email": "cathy@t.local", "password": PW})
        self.assertEqual(r.status_code, 429)

    def test_role_isolation(self):
        self.login("citizen", "cathy@t.local")
        self.assertEqual(self.c.get("/admin/").status_code, 302)
        self.assertEqual(self.c.get("/staff/").status_code, 302)
        self.assertEqual(self.post("/admin/staff", {}).status_code, 302)
        # a citizen's credentials never work on the admin tab
        c2 = self.app.test_client()
        r = self.post("/login", {"role": "admin", "email": "cathy@t.local", "password": PW}, client=c2)
        self.assertEqual(r.status_code, 401)

    def test_profile_update(self):
        self.login("citizen", "cathy@t.local")
        r = self.post("/profile", {"full_name": "Cathy Renamed", "phone": "9876543210",
                                   "current_password": PW, "new_password": "NewPass123"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("Cathy Renamed", self.c.get("/profile").get_data(as_text=True))
        c2 = self.app.test_client()
        self.login("citizen", "cathy@t.local", client=c2) if False else None
        r = self.post("/login", {"role": "citizen", "email": "cathy@t.local", "password": "NewPass123"}, client=c2)
        self.assertEqual(r.status_code, 302)


class TestComplaintLifecycle(Base):
    def test_submit_validation(self):
        self.login("citizen", "cathy@t.local")
        r = self.post("/report", {"title": "x", "description": "short", "category": "Nope", "park_id": ""},
                      content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)
        r = self.post("/report", {"title": "Valid title", "description": "A valid description here", "category": "Other",
                                  "park_id": "1", "latitude": "999", "longitude": "1"}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)
        r = self.post("/report", {"title": "Valid title", "description": "A valid description here", "category": "Other",
                                  "park_id": "1", "latitude": "12.9", "longitude": "77.5",
                                  "photo": (io.BytesIO(b"not an image"), "evil.png")}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)

    def test_report_requires_login(self):
        self.assertEqual(self.c.get("/report").status_code, 302)

    def test_submit_upload_and_track(self):
        code = self.new_complaint()
        self.assertRegex(code, r"^PC-\d{4}-0001$")
        files = os.listdir(self.app.config["UPLOAD_FOLDER"])
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith(".jpg"))
        page = self.c.get(f"/track/{code}").get_data(as_text=True)
        self.assertIn(code, page)
        self.assertIn("Submitted", page)
        self.assertEqual(self.c.get("/track/PC-1999-9999").status_code, 404)
        self.assertEqual(self.c.get("/api/track/" + code).get_json()["status"], "Submitted")

    def test_full_workflow_with_notifications(self):
        code = self.new_complaint()
        with self.app.app_context():
            cid = complaint.get_by_code(code)["id"]
            sam = users.find_by_email("staff", "sam@t.local")["id"]
        admin, staff = self.app.test_client(), self.app.test_client()
        self.login("admin", "admin@t.local", client=admin)
        self.login("staff", "sam@t.local", client=staff)
        # admin: review, then assign
        r = self.post(f"/admin/complaints/{cid}/status", {"status": "Under Review", "remark": "Looking into it"}, client=admin)
        self.assertEqual(r.status_code, 302)
        r = self.post(f"/admin/complaints/{cid}/assign", {"staff_id": sam}, client=admin)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            c = complaint.get_by_id(cid)
            self.assertEqual((c["status"], c["assigned_staff_id"]), ("Assigned", sam))
        # staff sees it, other staff does not
        self.assertIn(code, staff.get("/staff/").get_data(as_text=True))
        other = self.app.test_client()
        self.login("staff", "other@t.local", client=other)
        self.assertEqual(other.get(f"/staff/complaints/{cid}").status_code, 404)
        self.assertEqual(self.post(f"/staff/complaints/{cid}/update", {"status": "In Progress"}, client=other).status_code, 404)
        # staff: progress, cannot complete without photo/remark
        self.post(f"/staff/complaints/{cid}/update", {"status": "In Progress", "remark": "On site"}, client=staff)
        self.post(f"/staff/complaints/{cid}/update", {"status": "Resolved", "remark": "Done"}, client=staff,
                  content_type="multipart/form-data")
        with self.app.app_context():
            self.assertEqual(complaint.get_by_id(cid)["status"], "In Progress")
        r = self.post(f"/staff/complaints/{cid}/update", {"status": "Resolved", "remark": "Replaced slats",
                                                           "repair_photo": (png_bytes(), "fix.png")},
                      client=staff, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            c = complaint.get_by_id(cid)
            self.assertEqual(c["status"], "Resolved")
            self.assertTrue(c["resolution_photo_path"])
            self.assertTrue(c["resolved_at"])
        # citizen got notifications + history
        notes = self.c.get("/notifications").get_data(as_text=True)
        self.assertIn("Resolved", notes)
        self.assertIn("Assigned", notes)
        self.assertEqual(self.c.get("/api/notifications/unread").get_json()["unread"] > 0, True)
        self.post("/notifications/read", {}, )
        self.assertEqual(self.c.get("/api/notifications/unread").get_json()["unread"], 0)
        self.assertIn("Replaced slats", self.c.get(f"/track/{code}").get_data(as_text=True))

    def test_reject_needs_reason_and_assigned_needs_staff(self):
        code = self.new_complaint()
        with self.app.app_context():
            cid = complaint.get_by_code(code)["id"]
        admin = self.app.test_client()
        self.login("admin", "admin@t.local", client=admin)
        self.post(f"/admin/complaints/{cid}/status", {"status": "Rejected"}, client=admin)
        self.post(f"/admin/complaints/{cid}/status", {"status": "Assigned"}, client=admin)
        with self.app.app_context():
            self.assertEqual(complaint.get_by_id(cid)["status"], "Submitted")
        self.post(f"/admin/complaints/{cid}/status", {"status": "Rejected", "rejection_reason": "Duplicate"}, client=admin)
        page = self.c.get(f"/track/{code}").get_data(as_text=True)
        self.assertIn("rejected", page.lower())
        self.assertIn("Duplicate", page)

    def test_delete_safeguard(self):
        code = self.new_complaint()
        with self.app.app_context():
            cid = complaint.get_by_code(code)["id"]
        admin = self.app.test_client()
        self.login("admin", "admin@t.local", client=admin)
        self.post(f"/admin/complaints/{cid}/delete", {"confirm_code": "wrong"}, client=admin)
        with self.app.app_context():
            self.assertIsNotNone(complaint.get_by_id(cid))
        self.post(f"/admin/complaints/{cid}/delete", {"confirm_code": code.lower()}, client=admin)
        with self.app.app_context():
            self.assertIsNone(complaint.get_by_id(cid))
        self.assertEqual(os.listdir(self.app.config["UPLOAD_FOLDER"]), [])


class TestAdminTools(Base):
    def setUp(self):
        super().setUp()
        self.admin = self.app.test_client()
        self.login("admin", "admin@t.local", client=self.admin)

    def test_dashboard_lists_search_reports(self):
        self.new_complaint("Water pipe leaking badly")
        for path in ("/admin/", "/admin/complaints", "/admin/citizens", "/admin/staff", "/admin/reports",
                     "/admin/complaints?q=pipe&status=Submitted&category=Broken+Bench"):
            self.assertEqual(self.admin.get(path).status_code, 200, path)
        self.assertIn("Water pipe", self.admin.get("/admin/complaints?q=pipe").get_data(as_text=True))
        self.assertNotIn("Water pipe", self.admin.get("/admin/complaints?q=zzzz").get_data(as_text=True))
        csv = self.admin.get("/admin/reports/export.csv")
        self.assertEqual(csv.mimetype, "text/csv")
        self.assertIn("Water pipe", csv.get_data(as_text=True))

    def test_csv_formula_injection_blocked(self):
        self.new_complaint("=HYPERLINK(\"http://evil\")")
        body = self.admin.get("/admin/reports/export.csv").get_data(as_text=True)
        self.assertIn("'=HYPERLINK", body)

    def test_staff_management(self):
        r = self.post("/admin/staff", {"full_name": "New Staff", "email": "ns@t.local", "password": PW, "department": "Water"}, client=self.admin)
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            sid = users.find_by_email("staff", "ns@t.local")["id"]
        self.post(f"/admin/staff/{sid}/edit", {"full_name": "Renamed Staff", "phone": "123456789", "department": "Roads"}, client=self.admin)
        self.assertIn("Renamed Staff", self.admin.get("/admin/staff").get_data(as_text=True))
        sc = self.app.test_client()
        self.login("staff", "ns@t.local", client=sc)
        self.post(f"/admin/staff/{sid}/toggle", {}, client=self.admin)
        r = self.post("/login", {"role": "staff", "email": "ns@t.local", "password": PW}, client=self.app.test_client())
        self.assertEqual(r.status_code, 401)           # deactivated staff cannot log in
        self.assertEqual(sc.get("/staff/").status_code, 302)  # ...and existing sessions are dropped

    def test_citizen_deactivation(self):
        with self.app.app_context():
            uid = users.find_by_email("citizen", "cathy@t.local")["id"]
        self.post(f"/admin/citizens/{uid}/toggle", {}, client=self.admin)
        r = self.post("/login", {"role": "citizen", "email": "cathy@t.local", "password": PW}, client=self.app.test_client())
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
