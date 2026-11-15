"""Tiny DB layer: PyMySQL for MySQL, sqlite3 as an offline/test fallback.

All SQL in the project uses %s placeholders; for SQLite they are translated to ?.
"""
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"


class Database:
    def __init__(self, conn, backend):
        self.conn, self.backend = conn, backend

    def _params(self, params):
        if self.backend == "sqlite":  # store datetimes as ISO text (same shape MySQL gives back via fmt_dt)
            return tuple(v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else v for v in params)
        return tuple(params)

    def _prep(self, sql):
        return sql.replace("%s", "?") if self.backend == "sqlite" else sql

    def query(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(self._prep(sql), self._params(params))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    def one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql, params=()):
        row = self.one(sql, params)
        return next(iter(row.values())) if row else None

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(self._prep(sql), self._params(params))
        last = cur.lastrowid
        self.rowcount = cur.rowcount
        cur.close()
        return last

    @contextmanager
    def transaction(self):
        if self.backend == "mysql":
            self.conn.begin()
        else:
            self.conn.execute("BEGIN")
        try:
            yield self
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


def connect(cfg, create_database=False):
    if cfg["DB_BACKEND"] == "sqlite":
        conn = sqlite3.connect(cfg["SQLITE_PATH"], isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return Database(conn, "sqlite")
    import pymysql
    from pymysql.cursors import DictCursor
    kwargs = dict(host=cfg["MYSQL_HOST"], port=cfg["MYSQL_PORT"], user=cfg["MYSQL_USER"],
                  password=cfg["MYSQL_PASSWORD"], charset="utf8mb4", cursorclass=DictCursor,
                  autocommit=True)
    if create_database:
        conn = pymysql.connect(**kwargs)
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['MYSQL_DATABASE']}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.select_db(cfg["MYSQL_DATABASE"])
    else:
        conn = pymysql.connect(database=cfg["MYSQL_DATABASE"], **kwargs)
    return Database(conn, "mysql")


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config)
    return g.db


def init_app(app):
    @app.teardown_appcontext
    def _close(_exc):
        d = g.pop("db", None)
        if d is not None:
            d.close()


def _statements(backend):
    text = SCHEMA_FILE.read_text(encoding="utf-8")
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))
    out = []
    for stmt in text.split(";"):
        stmt = stmt.strip()
        if not stmt or re.match(r"(?i)^(CREATE DATABASE|USE)\b", stmt):
            continue
        if backend == "sqlite":
            stmt = stmt.replace("INT AUTO_INCREMENT PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
            stmt = re.sub(r"\)\s*ENGINE=[^;]*", ")", stmt)
            stmt = stmt.replace("INSERT IGNORE", "INSERT OR IGNORE")
        out.append(stmt)
    return out


def init_schema(database):
    """Create all tables (idempotent) and seed the parks list."""
    for stmt in _statements(database.backend):
        database.execute(stmt.replace("%", "%%") if database.backend == "mysql" and "%" in stmt else stmt)
