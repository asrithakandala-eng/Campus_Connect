"""Run with:  python -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["CAMPUSCONNECT_DB"] = str(Path(_tmp) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auth, config, database as db, nlp_matching as nlp  # noqa: E402


def setUpModule():
    db.init_db(admin_password="Test@12345")


def _report(**kw):
    base = dict(item_name="Red umbrella", category="Others", description="Large red umbrella with wooden handle",
                location="NAB", date=date.today(), person_name="Test User", contact="test@example.com",
                private_clue="Name tag tied to the handle")
    base.update(kw)
    return base


class TestCore(unittest.TestCase):
    def test_demo_data_counts(self):
        self.assertEqual(len(db.list_reports("lost")), 6)
        self.assertEqual(len(db.list_reports("found")), 6)
        self.assertGreaterEqual(db.get_stats()["claims"], 6)

    def test_unique_sequential_ids(self):
        a = db.add_report("lost", _report())
        b = db.add_report("lost", _report())
        f = db.add_report("found", _report())
        self.assertTrue(a.startswith("L-") and f.startswith("F-"))
        self.assertEqual(int(b[2:]), int(a[2:]) + 1)

    def test_public_view_hides_private_data(self):
        cols = set(db.list_reports().columns)
        self.assertFalse({"private_clue", "contact"} & cols)
        pub = db.get_report("F-1001")
        self.assertNotIn("private_clue", pub)
        self.assertNotIn("contact", pub)
        self.assertIn("private_clue", db.get_report("F-1001", admin=True))

    def test_preprocess(self):
        self.assertEqual(nlp.preprocess("The Black, water-bottle!"), "black water bottle")

    def test_top_three_and_formula(self):
        lost = db.get_report("L-1001")
        q = dict(item_name=lost["item_name"], description=lost["description"],
                 location=lost["location"], date=lost["date_lost"])
        top = nlp.rank_matches(q, db.list_reports("found"))
        self.assertEqual(len(top), 3)
        self.assertEqual(top.iloc[0]["report_id"], "F-1001")
        r = top.iloc[0]
        self.assertAlmostEqual(r["score"], 0.7 * r["text_sim"] + 0.2 * r["loc_sim"] + 0.1 * r["date_sim"])
        self.assertTrue((top["score"].diff().dropna() <= 0).all())

    def test_every_demo_lost_item_matches_its_pair(self):
        lost, found = db.list_reports("lost"), db.list_reports("found")
        lost = lost[lost["report_id"].isin([f"L-100{i}" for i in range(1, 7)])]
        found = found[found["report_id"].isin([f"F-100{i}" for i in range(1, 7)])]
        S = nlp.score_matrix(lost.sort_values("report_id"), found.sort_values("report_id"))["S"]
        self.assertEqual(list(S.argmax(axis=1)), list(range(6)))

    def test_risk_levels_of_demo_claims(self):
        risk = db.list_claims().set_index("claim_id")["risk_level"]
        self.assertEqual(risk["C-1001"], "LOW")
        self.assertEqual(risk["C-1002"], "MEDIUM")
        self.assertEqual(risk["C-1003"], "HIGH")
        self.assertEqual(risk["C-1004"], "HIGH")
        self.assertEqual(risk["C-1005"], "LOW")
        self.assertEqual(risk["C-1006"], "MEDIUM")
        self.assertFalse(db.list_flags("C-1003").empty)

    def test_risk_never_auto_rejects(self):
        statuses = db.list_claims().set_index("claim_id")["status"]
        self.assertNotEqual(statuses["C-1003"], "Rejected")
        self.assertNotEqual(statuses["C-1004"], "Rejected")

    def test_admin_login_and_hashing(self):
        self.assertIsNotNone(db.authenticate("admin", "Test@12345"))
        self.assertIsNone(db.authenticate("admin", "wrong"))
        conn = db.get_conn()
        h = conn.execute("SELECT password_hash FROM admins").fetchone()[0]
        conn.close()
        self.assertNotIn("Test@12345", h)

    def test_review_is_recorded(self):
        before = len(db.list_review_history())
        status = db.record_review("C-1002", "admin", "Request additional information", "Please describe the cover.")
        self.assertEqual(status, "More Information Required")
        self.assertEqual(len(db.list_review_history()), before + 1)
        self.assertEqual(db.list_claims().set_index("claim_id").loc["C-1002", "status"], status)

    def test_new_claim_flags_and_claimant_status_lookup(self):
        cid = db.add_claim(dict(found_id="F-1005", lost_id=None, claimant_name="Test Person",
                                contact="tp@example.com", ownership_description="grey hoodie"))
        row = db.list_claims().set_index("claim_id").loc[cid]
        self.assertIn(row["risk_level"], ("MEDIUM", "HIGH"))
        self.assertEqual(db.claim_status_lookup(cid, "tp@example.com")["status"], "Pending Review")
        self.assertIsNone(db.claim_status_lookup(cid, "someone@else.com"))

    def test_data_persists_across_connections(self):
        n = db.get_stats()["reports"]
        self.assertEqual(db.get_stats()["reports"], n)
        self.assertTrue(config.DB_PATH.exists())


if __name__ == "__main__":
    unittest.main()
