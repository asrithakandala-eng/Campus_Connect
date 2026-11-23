"""SQLite storage layer: schema, ID generation, queries, demo data."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import pandas as pd

import auth
import config
import fraud_detection
import nlp_matching

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin')),
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (            -- claimants, identified by contact
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lost_reports (
    report_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    date_lost TEXT NOT NULL,
    reporter_name TEXT NOT NULL,
    contact TEXT NOT NULL,
    private_clue TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open',
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS found_reports (
    report_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    date_found TEXT NOT NULL,
    finder_name TEXT NOT NULL,
    contact TEXT NOT NULL,
    private_clue TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open',
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    found_id TEXT NOT NULL REFERENCES found_reports(report_id),
    lost_id TEXT REFERENCES lost_reports(report_id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    claimant_name TEXT NOT NULL,
    contact TEXT NOT NULL,
    ownership_description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending Review',
    risk_level TEXT NOT NULL DEFAULT 'LOW' CHECK (risk_level IN ('LOW','MEDIUM','HIGH')),
    risk_points INTEGER NOT NULL DEFAULT 0,
    is_demo INTEGER NOT NULL DEFAULT 0,
    submitted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fraud_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
    indicator TEXT NOT NULL,
    severity INTEGER NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
    admin_username TEXT NOT NULL,
    action TEXT NOT NULL,
    new_status TEXT NOT NULL,
    note TEXT,
    decided_at TEXT NOT NULL
);
"""

_KIND = {
    "lost": ("lost_reports", "L", "date_lost", "reporter_name"),
    "found": ("found_reports", "F", "date_found", "finder_name"),
}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction():
    """BEGIN IMMEDIATE locks writers, so two users can never get the same report ID."""
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()


def query_df(sql: str, params=()) -> pd.DataFrame:
    conn = get_conn()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def next_id(conn, table: str, column: str, prefix: str) -> str:
    row = conn.execute(f"SELECT MAX(CAST(SUBSTR({column}, 3) AS INTEGER)) FROM {table}").fetchone()[0]
    return f"{prefix}-{(row or 1000) + 1}"


# ------------------------------------------------------------------ setup
def init_db(admin_password: str | None = None) -> None:
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()
    with transaction() as conn:
        if conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0] == 0:
            pw = admin_password or os.environ.get("CAMPUSCONNECT_ADMIN_PASSWORD") or config.DEFAULT_ADMIN_PASSWORD
            h, salt = auth.hash_password(pw)
            conn.execute(
                "INSERT INTO admins(username, full_name, role, password_hash, salt, created_at) VALUES (?,?,?,?,?,?)",
                (config.DEFAULT_ADMIN_USERNAME, "Campus Administrator", "admin", h, salt, now_str()),
            )
    seed_demo_data()


def authenticate(username: str, password: str):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM admins WHERE username=?", ((username or "").strip(),)).fetchone()
    finally:
        conn.close()
    if row and auth.verify_password(password or "", row["password_hash"], row["salt"]):
        return {"username": row["username"], "full_name": row["full_name"], "role": row["role"]}
    return None


# ------------------------------------------------------------------ reports
def add_report(kind: str, data: dict, is_demo: bool = False) -> str:
    table, prefix, date_col, person_col = _KIND[kind]
    with transaction() as conn:
        rid = next_id(conn, table, "report_id", prefix)
        conn.execute(
            f"INSERT INTO {table}(report_id, item_name, category, description, location, {date_col}, "
            f"{person_col}, contact, private_clue, status, is_demo, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, data["item_name"].strip(), data["category"], data["description"].strip(), data["location"],
             data["date"].isoformat(), data["person_name"].strip(), data["contact"].strip(),
             data["private_clue"].strip(), "Open", int(is_demo), now_str()),
        )
    return rid


def list_reports(kind: str | None = None) -> pd.DataFrame:
    """PUBLIC view of reports: no contact details, no private clues."""
    parts = []
    if kind in (None, "lost"):
        parts.append("SELECT report_id, item_name, category, 'Lost' AS report_type, description, location, "
                     "date_lost AS date, status, is_demo FROM lost_reports")
    if kind in (None, "found"):
        parts.append("SELECT report_id, item_name, category, 'Found' AS report_type, description, location, "
                     "date_found AS date, status, is_demo FROM found_reports")
    return query_df(" UNION ALL ".join(parts) + " ORDER BY date DESC, report_id DESC")


def get_report(report_id: str, admin: bool = False) -> dict | None:
    if report_id is None or pd.isna(report_id):
        return None

    normalized_id = str(report_id).strip().upper()

    if not normalized_id:
        return None

    kind = "lost" if normalized_id.startswith("L-") else "found"
    table = _KIND[kind][0]
    conn = get_conn()

    try:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE report_id=?",
            (normalized_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    d = dict(row)

    if not admin:
        d.pop("private_clue", None)
        d.pop("contact", None)
        d.pop("reporter_name", None)
        d.pop("finder_name", None)

    return d

def admin_reports(kind: str) -> pd.DataFrame:
    """Full report data including private clues. Call only for authenticated admins."""
    return query_df(f"SELECT * FROM {_KIND[kind][0]} ORDER BY report_id DESC")


def set_report_status(kind: str, report_id: str, status: str) -> None:
    if status not in config.REPORT_STATUSES:
        raise ValueError("Invalid status")
    with transaction() as conn:
        conn.execute(f"UPDATE {_KIND[kind][0]} SET status=? WHERE report_id=?", (status, report_id))


# ------------------------------------------------------------------ claims
def add_claim(data: dict, is_demo: bool = False) -> str:
    contact = data["contact"].strip()
    with transaction() as conn:
        if not conn.execute("SELECT 1 FROM found_reports WHERE report_id=?", (data["found_id"],)).fetchone():
            raise ValueError("Found report does not exist")
        user = conn.execute("SELECT id FROM users WHERE contact=?", (contact.lower(),)).fetchone()
        if user:
            uid = user["id"]
        else:
            uid = conn.execute("INSERT INTO users(contact, name, created_at) VALUES (?,?,?)",
                               (contact.lower(), data["claimant_name"].strip(), now_str())).lastrowid
        cid = next_id(conn, "claims", "claim_id", "C")
        conn.execute(
            "INSERT INTO claims(claim_id, found_id, lost_id, user_id, claimant_name, contact, "
            "ownership_description, status, is_demo, submitted_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, data["found_id"], data.get("lost_id") or None, uid, data["claimant_name"].strip(), contact,
             data["ownership_description"].strip(), "Pending Review", int(is_demo), now_str()),
        )
        conn.execute("UPDATE found_reports SET status='Claim in Progress' WHERE report_id=? AND status='Open'",
                     (data["found_id"],))
        fraud_detection.evaluate_claim(conn, cid)       # checked before any admin decision
        fraud_detection.evaluate_related(conn, cid)
    return cid


def claim_status_lookup(claim_id: str, contact: str):
    """Claimants may see only the status of their own claim (never risk level or clues)."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT status, submitted_at FROM claims WHERE claim_id=? AND LOWER(contact)=?",
                           ((claim_id or "").strip().upper(), (contact or "").strip().lower())).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def list_claims() -> pd.DataFrame:
    return query_df(
        "SELECT c.claim_id, c.found_id, f.item_name, c.claimant_name, c.contact, c.lost_id, c.risk_level, "
        "c.risk_points, c.status, c.submitted_at, c.is_demo, c.ownership_description "
        "FROM claims c JOIN found_reports f ON f.report_id=c.found_id ORDER BY c.claim_id DESC")


def list_flags(claim_id: str | None = None) -> pd.DataFrame:
    sql = ("SELECT fl.claim_id, fl.indicator, fl.severity, fl.detail, fl.created_at, c.risk_level "
           "FROM fraud_flags fl JOIN claims c ON c.claim_id=fl.claim_id")
    if claim_id:
        return query_df(sql + " WHERE fl.claim_id=? ORDER BY fl.severity DESC", (claim_id,))
    return query_df(sql + " ORDER BY fl.created_at DESC, fl.severity DESC")


def list_review_history() -> pd.DataFrame:
    return query_df("SELECT claim_id, admin_username, action, new_status, note, decided_at "
                    "FROM review_history ORDER BY id DESC")


def record_review(claim_id: str, admin_username: str, action: str, note: str) -> str:
    """Apply an administrator decision and log it. Only humans call this - never the risk engine."""
    new_status = config.REVIEW_ACTIONS[action]
    with transaction() as conn:
        claim = conn.execute("SELECT found_id FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
        conn.execute("UPDATE claims SET status=? WHERE claim_id=?", (new_status, claim_id))
        conn.execute(
            "INSERT INTO review_history(claim_id, admin_username, action, new_status, note, decided_at) "
            "VALUES (?,?,?,?,?,?)", (claim_id, admin_username, action, new_status, note.strip(), now_str()))
        if new_status == "Rejected":                    # reopen item if nobody else is claiming it
            active = conn.execute(
                "SELECT COUNT(*) FROM claims WHERE found_id=? AND status IN (?,?,?,?)",
                (claim["found_id"], *config.ACTIVE_CLAIM_STATUSES, "Approved")).fetchone()[0]
            if active == 0:
                conn.execute("UPDATE found_reports SET status='Open' WHERE report_id=? AND status='Claim in Progress'",
                             (claim["found_id"],))
    return new_status


# ------------------------------------------------------------------ stats
def count_possible_matches() -> int:
    lost = list_reports("lost")
    found = list_reports("found")
    lost = lost[lost["status"] == "Open"]
    found = found[found["status"].isin(["Open", "Claim in Progress"])]
    if lost.empty or found.empty:
        return 0
    return int((nlp_matching.score_matrix(lost, found)["S"] >= config.MATCH_THRESHOLD).sum())


def get_stats() -> dict:
    conn = get_conn()
    try:
        one = lambda sql: conn.execute(sql).fetchone()[0]
        s = {
            "lost": one("SELECT COUNT(*) FROM lost_reports"),
            "found": one("SELECT COUNT(*) FROM found_reports"),
            "claims": one("SELECT COUNT(*) FROM claims"),
            "low": one("SELECT COUNT(*) FROM claims WHERE risk_level='LOW'"),
            "medium": one("SELECT COUNT(*) FROM claims WHERE risk_level='MEDIUM'"),
            "high": one("SELECT COUNT(*) FROM claims WHERE risk_level='HIGH'"),
            "manual": one("SELECT COUNT(*) FROM claims WHERE risk_level IN ('MEDIUM','HIGH') "
                          "AND status IN ('Pending Review','Under Verification','More Information Required')"),
            "demo": one("SELECT (SELECT COUNT(*) FROM lost_reports WHERE is_demo=1) + "
                        "(SELECT COUNT(*) FROM found_reports WHERE is_demo=1) + "
                        "(SELECT COUNT(*) FROM claims WHERE is_demo=1)"),
        }
    finally:
        conn.close()
    s["reports"] = s["lost"] + s["found"]
    s["flagged"] = s["medium"] + s["high"]
    s["matches"] = count_possible_matches()
    return s


# ------------------------------------------------------------------ demo data
def seed_demo_data() -> None:
    conn = get_conn()
    try:
        empty = conn.execute("SELECT (SELECT COUNT(*) FROM lost_reports)+(SELECT COUNT(*) FROM found_reports)").fetchone()[0] == 0
    finally:
        conn.close()
    if not empty:
        return
    day = lambda n: date.today() - timedelta(days=n)
    # (item, category, description, location, days_ago, clue)
    lost = [
        ("Black water bottle", "Personal Items", "Black stainless steel insulated water bottle, 750 ml, with a flip-top lid.", "FOOD COURT", 3, "Small dent near the bottom and a red mountain sticker on the side"),
        ("Blue notebook", "Books and Stationery", "Blue spiral notebook, A4 size, used for Signals and Systems class notes.", "ACADEMIC BLOCK", 5, "Pressed flower tucked inside the back cover and my name on the first page"),
        ("Wireless earbuds case", "Electronics", "White wireless earbuds charging case with a transparent protective cover.", "CV BLOCK", 4, "Initials AK scratched on the lid of the case"),
        ("Student ID card", "Personal Items", "SRM-AP student ID card with a blue lanyard.", "TREE COURT AREA", 6, "Registration number ends with 47"),
        ("Grey hoodie", "Clothing", "Grey pullover hoodie, size M, with a front pocket.", "NAB", 7, "Small ink stain on the left sleeve cuff"),
        ("Scientific calculator", "Electronics", "Black scientific calculator, Casio fx-991EX, with slide-on cover.", "X LAB", 2, "Letter R written in white marker on the back"),
    ]
    found = [
        ("Black steel water bottle", "Personal Items", "Black insulated steel bottle with a flip lid, found on a table.", "FOOD COURT", 2, "Red mountain sticker and a dent at the base"),
        ("Blue spiral notebook", "Books and Stationery", "Blue spiral-bound notebook with handwritten class notes, found on a bench.", "V BLOCK", 4, "Pressed flower inside the back cover"),
        ("Earbuds charging case", "Electronics", "White charging case for wireless earbuds with a clear protective cover.", "SR BLOCK", 4, "Scratched initials AK on the lid"),
        ("University identity card", "Personal Items", "Student identity card on a blue lanyard, found near the tree court.", "TREE COURT AREA", 5, "Registration number ends with 47"),
        ("Grey hooded sweatshirt", "Clothing", "Grey hooded sweatshirt, medium size, front kangaroo pocket.", "NAB", 6, "Ink stain on the left cuff"),
        ("Scientific calculator", "Electronics", "Black scientific calculator, Casio, with slide-on cover.", "X LAB", 1, "Letter R written in white marker on the back"),
    ]
    for i, (n, c, d, loc, ago, clue) in enumerate(lost):
        add_report("lost", dict(item_name=n, category=c, description=d, location=loc, date=day(ago),
                                person_name=["Ananya Rao", "Rahul Verma", "Arjun Kumar", "Vikram Singh", "Priya Nair", "Sneha Reddy"][i],
                                contact=["ananya.r@srmap.edu.in", "rahul.v@srmap.edu.in", "arjun.k@srmap.edu.in",
                                         "vikram.s@srmap.edu.in", "priya.n@srmap.edu.in", "sneha.r@srmap.edu.in"][i],
                                private_clue=clue), is_demo=True)
    for i, (n, c, d, loc, ago, clue) in enumerate(found):
        add_report("found", dict(item_name=n, category=c, description=d, location=loc, date=day(ago),
                                 person_name=["Security Desk", "Library Staff", "Housekeeping", "Security Desk", "Student Volunteer", "Lab Assistant"][i],
                                 contact=f"finder{i + 1}@srmap.edu.in", private_clue=clue), is_demo=True)
    claims = [
        dict(found_id="F-1001", lost_id="L-1001", claimant_name="Ananya Rao", contact="ananya.r@srmap.edu.in",
             ownership_description="My black steel bottle with a flip lid. It has a red mountain sticker on the side and a small dent at the bottom."),
        dict(found_id="F-1002", lost_id="L-1002", claimant_name="Rahul Verma", contact="rahul.v@srmap.edu.in",
             ownership_description="Blue notebook with my class notes, it has some stickers on the cover."),
        dict(found_id="F-1003", lost_id=None, claimant_name="Karthik Menon", contact="karthik.m@srmap.edu.in",
             ownership_description="White earbuds case, I think it has some scratches on it."),
        dict(found_id="F-1003", lost_id=None, claimant_name="Divya Iyer", contact="divya.i@srmap.edu.in",
             ownership_description="White earbuds case, I think it has some scratches on it too."),
        dict(found_id="F-1006", lost_id="L-1006", claimant_name="Sneha Reddy", contact="sneha.r@srmap.edu.in",
             ownership_description="Black Casio scientific calculator with a slide cover. The letter R is written in white marker on the back."),
        dict(found_id="F-1004", lost_id=None, claimant_name="Vikram Singh", contact="vikram.s@srmap.edu.in",
             ownership_description="I lost my student ID card with a blue lanyard near the tree court area yesterday."),
    ]
    ids = [add_claim(c, is_demo=True) for c in claims]
    record_review(ids[4], "admin", "Mark as under investigation", "Demo: asked the lab assistant to confirm the marking on the back.")
