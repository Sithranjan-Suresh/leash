import json
import sqlite3
import threading
import time
from . import config

_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS rule(id INTEGER PRIMARY KEY, text TEXT, tool TEXT, condition TEXT,
  verdict TEXT, source TEXT, enabled INTEGER DEFAULT 1, created_at REAL);
CREATE TABLE IF NOT EXISTS run(id INTEGER PRIMARY KEY, kind TEXT, score REAL, started_at REAL);
CREATE TABLE IF NOT EXISTS action(id INTEGER PRIMARY KEY, run_id INTEGER, tool TEXT, args TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS decision(id INTEGER PRIMARY KEY, action_id INTEGER, verdict TEXT, reason TEXT,
  decided_by TEXT, rule_id INTEGER, latency_ms REAL);
CREATE TABLE IF NOT EXISTS attack(id INTEGER PRIMARY KEY, run_id INTEGER, scenario_id TEXT, payload TEXT,
  blocked INTEGER, reason TEXT, suggested_rule TEXT, accepted INTEGER DEFAULT 0);
"""


def conn():
    global _conn
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.executescript(SCHEMA)
        return _conn


def reset(path=None):
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None
        if path:
            config.DB_PATH = path


def execute(sql, params=()):
    with _lock:
        c = conn().execute(sql, params)
        conn().commit()
        return c


def query(sql, params=()):
    with _lock:
        return [dict(r) for r in conn().execute(sql, params).fetchall()]


def _rule_row(r):
    r["condition"] = json.loads(r["condition"] or "{}")
    r["enabled"] = bool(r["enabled"])
    return r


def list_rules(only_enabled=False):
    sql = "SELECT * FROM rule" + (" WHERE enabled=1" if only_enabled else "") + " ORDER BY id"
    return [_rule_row(r) for r in query(sql)]


def add_rule(text, tool, condition, verdict, source="user"):
    c = execute("INSERT INTO rule(text,tool,condition,verdict,source,created_at) VALUES(?,?,?,?,?,?)",
                (text, tool, json.dumps(condition or {}), verdict, source, time.time()))
    return _rule_row(query("SELECT * FROM rule WHERE id=?", (c.lastrowid,))[0])
