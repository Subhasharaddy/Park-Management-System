"""Helpers: validation, image handling, formatting."""
import re
import secrets
from datetime import datetime
from pathlib import Path

from flask import current_app
from PIL import Image, ImageOps

from constants import ALLOWED_IMAGE_EXT

Image.MAX_IMAGE_PIXELS = 40_000_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+()\-\s]{7,20}$")


def now():
    return datetime.now().replace(microsecond=0)


def valid_email(v):
    return bool(v) and len(v) <= 150 and EMAIL_RE.match(v) is not None


def valid_phone(v):
    return (not v) or PHONE_RE.match(v) is not None


def password_problem(pw):
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain both letters and digits."
    return None


def parse_coord(lat, lng):
    try:
        la, lo = float(lat), float(lng)
    except (TypeError, ValueError):
        return None
    if not (-90 <= la <= 90 and -180 <= lo <= 180):
        return None
    return round(la, 7), round(lo, 7)


def safe_next(path):
    if path and path.startswith("/") and not path.startswith("//") and "\\" not in path:
        return path
    return None


def save_image(storage):
    """Validate, strip metadata (incl. EXIF GPS), re-encode as JPEG. Returns 'uploads/xxx.jpg' or None."""
    if not storage or not storage.filename:
        return None
    ext = storage.filename.rsplit(".", 1)[-1].lower() if "." in storage.filename else ""
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValueError("Only JPG, PNG or WEBP images are allowed.")
    try:
        img = Image.open(storage.stream)
        img.verify()
        storage.stream.seek(0)
        img = ImageOps.exif_transpose(Image.open(storage.stream)).convert("RGB")
    except Exception:
        raise ValueError("The uploaded file is not a valid image.")
    img.thumbnail((1600, 1600))
    name = f"{secrets.token_hex(12)}.jpg"
    img.save(Path(current_app.config["UPLOAD_FOLDER"]) / name, "JPEG", quality=85)
    return f"uploads/{name}"


def delete_upload(rel_path):
    if rel_path and rel_path.startswith("uploads/"):
        p = Path(current_app.config["UPLOAD_FOLDER"]) / rel_path.split("/", 1)[1]
        try:
            p.unlink()
        except OSError:
            pass


def fmt_dt(v, fmt="%d %b %Y, %I:%M %p"):
    if not v:
        return "—"
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v)
        except ValueError:
            return v
    return v.strftime(fmt)


def slug(v):
    return re.sub(r"[^a-z]+", "-", (v or "").lower()).strip("-")
