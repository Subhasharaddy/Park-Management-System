# ParkCare 3D – Smart Park Maintenance & Complaint Tracking System

College mini project: *an application for citizens to report maintenance issues in public parks and gardens and track resolution.*

**Stack:** Flask · MySQL (PyMySQL) · HTML/CSS/JS · Three.js · GSAP · Leaflet + OpenStreetMap · Chart.js · Font Awesome

## Features
- **3D homepage** – procedural park (trees, fountain with particle water, benches, path, flowers, butterflies, birds, fireflies), six animated issue scenes, animated DB-backed counters, GSAP scroll animations, loading screen, static fallback when WebGL is unavailable.
- **Citizens** – register/login, profile, report issues (category stickers, photo upload, GPS + Leaflet map picker), unique IDs like `PC-2026-0001`, history, in-app notifications.
- **Tracking** – by complaint ID or from "my complaints": progress tracker, photos, map, staff, admin/staff remarks, rejection reason, auto-refresh on status change.
- **Admin** – stats, 4 Chart.js charts, map, search/filter, assign staff, status + remarks + resolution photo, citizen & staff management, guarded delete (type the ID), HTML report + CSV export.
- **Staff** – own login, only their assigned complaints, progress updates, repair photo to mark completed.

## Run on Windows (PowerShell)
```powershell
# 1. MySQL: install MySQL 8, or use Docker:  $env:MYSQL_ROOT_PASSWORD="rootpw"; $env:MYSQL_PASSWORD="parkpw"; docker compose up -d
# 2. Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
# 3. Configuration
Copy-Item .env.example .env          # then edit MYSQL_* values (user needs CREATE DATABASE rights)
# 4. Create database, tables, parks, admin (+ demo accounts and sample complaints)
python init_db.py --demo
# 5. Start
python app.py                        # open http://127.0.0.1:5000
```
`init_db.py` prints the generated passwords **once** and saves them to `instance/demo_credentials.txt` (git-ignored). Set `ADMIN_PASSWORD` in `.env` to choose your own. Alternatively import `schema.sql` in MySQL Workbench / `mysql < schema.sql`.

Logins: `/login?role=citizen|staff|admin` (tabs on the login page). Demo emails: `admin@parkcare.local`, `citizen@parkcare.local`, `ravi@parkcare.local`, `meena@parkcare.local`.

## Tests
```powershell
python -m unittest discover -s tests -v
```
17 end-to-end tests (auth, CSRF, throttling, role isolation, upload validation, full complaint workflow, notifications, delete safeguard, CSV, staff/citizen deactivation) run against a temporary **SQLite** file via `DB_BACKEND=sqlite`.

## Structure
`app.py` factory · `config.py` · `db.py` (MySQL/SQLite layer) · `security.py` (CSRF, throttle, roles) · `routes/` · `models/` · `templates/` · `static/{css,js}` · `schema.sql` · `init_db.py` · `tests/`

## Security notes
Hashed passwords (Werkzeug), session fixation reset on login, CSRF tokens on every POST, login throttling (5 tries / 10 min, in-memory), parameterised SQL only, uploads re-encoded with Pillow (EXIF/GPS stripped, random names), role checks on every admin/staff route, CSV formula-injection guard, security headers. For production use HTTPS (`SESSION_COOKIE_SECURE=true`) and a real WSGI server (e.g. waitress on Windows).

## Honest limitations
- **MySQL path not run in the build environment** (no MySQL server there). All logic was tested on SQLite through the same SQL layer; the MySQL schema/driver code is standard but please run `init_db.py` and report any error.
- **Browser features** (WebGL scenes, Leaflet, GPS, Chart.js) load libraries from CDNs and need internet; I could not view them in a real browser while building, so check visuals in Chrome and tweak.
- **3D models are generated in code** (no GLB/GLTF files bundled). To use your own, add them to `static/models/` and load with `GLTFLoader`.
- The reference video and the uploaded ZIP (empty) were not accessible, so the design follows your colour/style description.
- Sample park names/coordinates are placeholders – edit the `parks` table. Notifications are in-app only (no email/SMS). Throttling resets on restart. Admin accounts are created by `init_db.py` only.
