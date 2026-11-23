"""Rule-based suspicious-claim detection.

The module flags *patterns* for a human administrator to review. It never
rejects a claim, never declares anyone guilty, and its risk level is kept
completely separate from the item-matching score.

Severity: 1 = minor indicator, 2 = stronger indicator.
Risk level: no indicators -> LOW | any indicator -> MEDIUM |
            3+ points AND 2+ indicators -> HIGH
"""
from datetime import datetime, timedelta

import config
from nlp_matching import keyword_overlap, text_similarity_pair

SIMILAR_CLAIM_THRESHOLD = 0.75
RAPID_WINDOW_HOURS = 24


def classify(flags: list[dict]) -> tuple[str, int]:
    points = sum(f["severity"] for f in flags)
    if not flags:
        return "LOW", 0
    if points >= 3 and len(flags) >= 2:
        return "HIGH", points
    return "MEDIUM", points


def _collect_flags(conn, claim) -> list[dict]:
    flags: list[dict] = []

    def flag(indicator: str, severity: int, detail: str):
        flags.append({"indicator": indicator, "severity": severity, "detail": detail})

    found = conn.execute("SELECT * FROM found_reports WHERE report_id=?", (claim["found_id"],)).fetchone()
    lost = None
    if claim["lost_id"]:
        lost = conn.execute("SELECT * FROM lost_reports WHERE report_id=?", (claim["lost_id"],)).fetchone()
    desc = claim["ownership_description"]

    # 1. Private clue verification against the found report
    ov = keyword_overlap(found["private_clue"], desc)
    if ov is not None:
        if ov == 0:
            flag("Private clue not matched", 2,
                 "None of the key details in the finder's private clue appear in the ownership description.")
        elif ov < 0.5:
            flag("Private clue only partly matched", 1,
                 f"Only {ov:.0%} of the finder's private clue details appear in the ownership description.")

    # 2. Consistency with the claimant's own lost report
    if lost is not None:
        if lost["contact"].strip().lower() != claim["contact"].strip().lower():
            flag("Contact differs from linked lost report", 1,
                 "The claimant's contact does not match the contact on the lost report they linked.")
        ov_lost = keyword_overlap(lost["private_clue"], desc)
        if ov_lost is not None and ov_lost < 0.34:
            flag("Claim inconsistent with linked lost report", 1,
                 "The ownership description shares few details with the private clue in the linked lost report.")
        ov_clues = keyword_overlap(found["private_clue"], lost["private_clue"])
        if ov_clues is not None and ov_clues == 0:
            flag("Lost and found private clues conflict", 2,
                 "The private clues recorded in the lost and found reports share no details.")
        if text_similarity_pair(f"{lost['item_name']} {lost['description']}",
                                f"{found['item_name']} {found['description']}") < 0.05:
            flag("Lost and found descriptions contradict", 1,
                 "The public descriptions of the linked lost and found reports have almost nothing in common.")

    # 3. Incomplete ownership information
    if len(desc.split()) < 6:
        flag("Incomplete ownership information", 1,
             "The ownership description is very short, so it cannot be verified properly.")

    # 4/5. Other claims on the same found item
    others = conn.execute(
        "SELECT * FROM claims WHERE found_id=? AND claim_id<>?", (claim["found_id"], claim["claim_id"])
    ).fetchall()
    other_people = {o["user_id"] for o in others if o["user_id"] != claim["user_id"]}
    if other_people:
        n = len(other_people)
        flag("Multiple claimants for one item", 1 if n == 1 else 2,
             f"{n} other person(s) have also claimed this found item.")
    for o in others:
        sim = text_similarity_pair(desc, o["ownership_description"])
        if sim >= SIMILAR_CLAIM_THRESHOLD:
            same = o["user_id"] == claim["user_id"]
            flag("Repeated or near-identical claim description", 1 if same else 2,
                 f"Description is {sim:.0%} similar to claim {o['claim_id']}"
                 f"{' by the same account' if same else ' from a different account'}.")
            break

    # 6. Repeated unsuccessful claims by the same account
    rejected = conn.execute(
        "SELECT COUNT(*) FROM claims WHERE user_id=? AND status='Rejected' AND claim_id<>?",
        (claim["user_id"], claim["claim_id"]),
    ).fetchone()[0]
    if rejected >= 2:
        flag("Repeated unsuccessful claims", 2, f"This account has {rejected} previously rejected claims.")
    elif rejected == 1:
        flag("Previous unsuccessful claim", 1, "This account has 1 previously rejected claim.")

    # 7. Unusual burst of submissions
    try:
        t = datetime.strptime(claim["submitted_at"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        t = datetime.now()
    start = (t - timedelta(hours=RAPID_WINDOW_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    burst = conn.execute(
        "SELECT COUNT(*) FROM claims WHERE user_id=? AND submitted_at>=? AND submitted_at<=?",
        (claim["user_id"], start, claim["submitted_at"]),
    ).fetchone()[0]
    if burst >= 3:
        flag("Unusual number of claim submissions", 2 if burst >= 5 else 1,
             f"{burst} claims were submitted from this account within {RAPID_WINDOW_HOURS} hours.")
    return flags


def evaluate_claim(conn, claim_id: str) -> dict:
    """Run all checks, store the flags and risk level, and return them. Status is never changed."""
    claim = conn.execute("SELECT * FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
    flags = _collect_flags(conn, claim)
    level, points = classify(flags)
    conn.execute("DELETE FROM fraud_flags WHERE claim_id=?", (claim_id,))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for f in flags:
        conn.execute(
            "INSERT INTO fraud_flags(claim_id, indicator, severity, detail, created_at) VALUES (?,?,?,?,?)",
            (claim_id, f["indicator"], f["severity"], f["detail"], now),
        )
    conn.execute("UPDATE claims SET risk_level=?, risk_points=? WHERE claim_id=?", (level, points, claim_id))
    return {"risk_level": level, "risk_points": points, "flags": flags}


def evaluate_related(conn, claim_id: str) -> None:
    """Re-check other open claims on the same found item (a new rival claim changes their picture)."""
    claim = conn.execute("SELECT found_id FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
    rows = conn.execute(
        "SELECT claim_id FROM claims WHERE found_id=? AND claim_id<>? AND status IN (?,?,?)",
        (claim["found_id"], claim_id, *config.ACTIVE_CLAIM_STATUSES),
    ).fetchall()
    for r in rows:
        evaluate_claim(conn, r["claim_id"])
