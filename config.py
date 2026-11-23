"""Central configuration for CampusConnect."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("CAMPUSCONNECT_DB", BASE_DIR / "data" / "campusconnect.db"))

UNIVERSITY = "SRM University\u2013AP"
APP_NAME = "CampusConnect"
APP_SUBTITLE = "Smart Campus Lost and Found Matcher"

LOCATIONS = [
    "SR BLOCK", "CV BLOCK", "V BLOCK", "JC BOSE BLOCK", "ACADEMIC BLOCK",
    "FOOD COURT", "NAB", "X LAB", "TREE COURT AREA",
]
CATEGORIES = [
    "Electronics", "Accessories", "Books and Stationery",
    "Clothing", "Personal Items", "Others",
]

CLAIM_STATUSES = [
    "Pending Review", "Under Verification", "Approved",
    "Rejected", "More Information Required",
]
ACTIVE_CLAIM_STATUSES = ("Pending Review", "Under Verification", "More Information Required")
REPORT_STATUSES = ["Open", "Claim in Progress", "Returned", "Closed"]

# Admin review actions -> resulting claim status
REVIEW_ACTIONS = {
    "Approve claim": "Approved",
    "Reject claim": "Rejected",
    "Request additional information": "More Information Required",
    "Mark as under investigation": "Under Verification",
}

# ---- Matching formula: S = 0.70*T + 0.20*L + 0.10*D ----
W_TEXT, W_LOC, W_DATE = 0.70, 0.20, 0.10
DATE_WINDOW_DAYS = 14          # D falls linearly to 0 after this many days apart
MATCH_THRESHOLD = 0.40         # pairs at/above this count as "possible matches"
TOP_N = 3

# Location similarity: same place = 1.0, same zone of campus = 0.5, otherwise 0
LOCATION_ZONES = {
    "SR BLOCK": "academic", "CV BLOCK": "academic", "V BLOCK": "academic",
    "JC BOSE BLOCK": "academic", "ACADEMIC BLOCK": "academic",
    "NAB": "academic", "X LAB": "academic",
    "FOOD COURT": "common", "TREE COURT AREA": "common",
}
SAME_ZONE_SCORE = 0.5

MATCH_DISCLAIMER = (
    "A higher score means the two reports are more similar, but it does not "
    "guarantee that they describe the same physical item. Ownership must still "
    "be verified by an administrator."
)

# ---- Admin account (change the password before deploying!) ----
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@12345"
MAX_LOGIN_ATTEMPTS = 5
