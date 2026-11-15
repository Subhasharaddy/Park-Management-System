"""Configuration. Everything sensitive comes from environment variables / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")  # auto-generated into instance/.secret_key if empty
    DB_BACKEND = os.getenv("DB_BACKEND", "mysql").lower()  # "mysql" (default) or "sqlite" (tests/offline demo)
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "parkcare")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "parkcare_db")
    SQLITE_PATH = os.getenv("SQLITE_PATH", str(BASE_DIR / "instance" / "parkcare.sqlite3"))

    UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per request

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)  # set true behind HTTPS
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8

    MAP_DEFAULT_LAT = float(os.getenv("MAP_DEFAULT_LAT", "12.9716"))
    MAP_DEFAULT_LNG = float(os.getenv("MAP_DEFAULT_LNG", "77.5946"))

    # Used by `python init_db.py`
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Park Administrator")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@parkcare.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")  # empty => random password is generated and printed once
