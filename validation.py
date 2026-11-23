"""Input validation for all forms. Each function returns a list of error messages."""
import re
from datetime import date

import config

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?\d[\d\s\-]{8,14}\d$")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,59}$")


def _name(value: str, label: str) -> list[str]:
    return [] if NAME_RE.match((value or "").strip()) else [f"{label} must be 2\u201360 letters (no digits or symbols)."]


def _contact(value: str) -> list[str]:
    v = (value or "").strip()
    if EMAIL_RE.match(v) or PHONE_RE.match(v):
        return []
    return ["Contact must be a valid email address or phone number."]


def validate_report(data: dict) -> list[str]:
    errors = []
    if len((data.get("item_name") or "").strip()) < 3:
        errors.append("Item name must be at least 3 characters.")
    if data.get("category") not in config.CATEGORIES:
        errors.append("Please choose a valid category.")
    if len((data.get("description") or "").strip()) < 15:
        errors.append("Description must be at least 15 characters so matching can work well.")
    if data.get("location") not in config.LOCATIONS:
        errors.append("Please choose a valid campus location.")
    d = data.get("date")
    if not isinstance(d, date) or d > date.today():
        errors.append("Date cannot be empty or in the future.")
    errors += _name(data.get("person_name"), "Name")
    errors += _contact(data.get("contact"))
    if len((data.get("private_clue") or "").strip()) < 5:
        errors.append("Private identifying clue must be at least 5 characters.")
    return errors


def validate_claim(data: dict, found_exists: bool, lost_exists: bool) -> list[str]:
    errors = []
    if not found_exists:
        errors.append("Please select a valid found-item report.")
    errors += _name(data.get("claimant_name"), "Name")
    errors += _contact(data.get("contact"))
    if len((data.get("ownership_description") or "").strip()) < 10:
        errors.append("Ownership description must be at least 10 characters.")
    if data.get("lost_id") and not lost_exists:
        errors.append("The lost report ID you entered does not exist (leave it blank if you have none).")
    return errors
