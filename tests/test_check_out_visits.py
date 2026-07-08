import os
import tempfile
import unittest
from unittest.mock import patch

from app import app, get_db, init_db


class CheckOutVisitTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        app.config["DATABASE"] = os.path.join(
            self.tempdir.name,
            "groundtrack.sqlite",
        )

        with app.app_context():
            init_db()

        self.client = app.test_client()

    def tearDown(self):
        self.tempdir.cleanup()

    def add_participant(
        self,
        name,
        badge_number,
        in_process_at=None,
        out_process_at=None,
    ):
        with app.app_context():
            db = get_db()
            participant_id = db.execute(
                """
                INSERT INTO participants (
                    name,
                    badge_number,
                    in_process_at,
                    out_process_at
                ) VALUES (?, ?, ?, ?)
                """,
                (name, badge_number, in_process_at, out_process_at),
            ).lastrowid
            db.commit()
        return participant_id

    def add_visit(self, participant_id, in_process_at, out_process_at=None):
        with app.app_context():
            db = get_db()
            visit_id = db.execute(
                """
                INSERT INTO participant_visits (
                    participant_id,
                    in_process_at,
                    out_process_at
                ) VALUES (?, ?, ?)
                """,
                (participant_id, in_process_at, out_process_at),
            ).lastrowid
            db.commit()
        return visit_id

    def check_out(self, badge_number):
        return self.client.post(
            "/scan",
            data={"badge_number": badge_number, "action": "check_out"},
        )

    @patch("app.local_timestamp", return_value="2026-08-22 17:00:00")
    def test_check_out_closes_current_visit_with_same_timestamp(self, _timestamp):
        participant_id = self.add_participant(
            "Return Visitor",
            "V200",
            in_process_at="2026-08-12 09:30:00",
        )
        prior_visit_id = self.add_visit(
            participant_id,
            "2026-07-01 08:00:00",
            "2026-07-11 17:00:00",
        )
        current_visit_id = self.add_visit(
            participant_id,
            "2026-08-12 09:30:00",
        )

        response = self.check_out("V200")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Checked out Return Visitor.", response.get_data(as_text=True))
        with app.app_context():
            participant = get_db().execute(
                """
                SELECT out_process_at
                FROM participants
                WHERE id = ?
                """,
                (participant_id,),
            ).fetchone()
            visits = get_db().execute(
                """
                SELECT id, out_process_at
                FROM participant_visits
                WHERE participant_id = ?
                ORDER BY id
                """,
                (participant_id,),
            ).fetchall()

        self.assertEqual(participant["out_process_at"], "2026-08-22 17:00:00")
        self.assertEqual(visits[0]["id"], prior_visit_id)
        self.assertEqual(visits[0]["out_process_at"], "2026-07-11 17:00:00")
        self.assertEqual(visits[1]["id"], current_visit_id)
        self.assertEqual(visits[1]["out_process_at"], "2026-08-22 17:00:00")

    @patch("app.local_timestamp", return_value="2026-08-22 17:00:00")
    def test_check_out_closes_only_most_recent_open_visit(self, _timestamp):
        participant_id = self.add_participant(
            "Duplicate Open Visits",
            "V201",
            in_process_at="2026-08-12 09:30:00",
        )
        older_open_visit_id = self.add_visit(
            participant_id,
            "2026-07-01 08:00:00",
        )
        current_visit_id = self.add_visit(
            participant_id,
            "2026-08-12 09:30:00",
        )
        other_participant_id = self.add_participant(
            "Other Visitor",
            "V202",
            in_process_at="2026-08-15 09:00:00",
        )
        other_visit_id = self.add_visit(
            other_participant_id,
            "2026-08-15 09:00:00",
        )

        self.check_out("V201")

        with app.app_context():
            visits = get_db().execute(
                """
                SELECT id, out_process_at
                FROM participant_visits
                WHERE id IN (?, ?, ?)
                ORDER BY id
                """,
                (older_open_visit_id, current_visit_id, other_visit_id),
            ).fetchall()

        self.assertIsNone(visits[0]["out_process_at"])
        self.assertEqual(visits[1]["out_process_at"], "2026-08-22 17:00:00")
        self.assertIsNone(visits[2]["out_process_at"])

    @patch("app.local_timestamp", return_value="2026-08-22 17:00:00")
    def test_not_on_ground_does_not_change_visits(self, _timestamp):
        participant_id = self.add_participant(
            "Already Checked Out",
            "V203",
            in_process_at="2026-08-12 09:30:00",
            out_process_at="2026-08-20 16:00:00",
        )
        visit_id = self.add_visit(
            participant_id,
            "2026-08-12 09:30:00",
            "2026-08-20 16:00:00",
        )

        response = self.check_out("V203")

        self.assertIn(
            "Already Checked Out is not on ground. No changes were made.",
            response.get_data(as_text=True),
        )
        with app.app_context():
            visit = get_db().execute(
                """
                SELECT out_process_at
                FROM participant_visits
                WHERE id = ?
                """,
                (visit_id,),
            ).fetchone()
            visit_count = get_db().execute(
                """
                SELECT COUNT(*) AS count
                FROM participant_visits
                WHERE participant_id = ?
                """,
                (participant_id,),
            ).fetchone()["count"]

        self.assertEqual(visit["out_process_at"], "2026-08-20 16:00:00")
        self.assertEqual(visit_count, 1)

    @patch("app.local_timestamp", return_value="2026-08-22 17:00:00")
    def test_on_ground_participant_without_open_visit_can_check_out(
        self,
        _timestamp,
    ):
        participant_id = self.add_participant(
            "Legacy On Ground",
            "V204",
            in_process_at="2026-08-12 09:30:00",
        )

        response = self.check_out("V204")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Checked out Legacy On Ground.", response.get_data(as_text=True))
        with app.app_context():
            participant = get_db().execute(
                """
                SELECT out_process_at
                FROM participants
                WHERE id = ?
                """,
                (participant_id,),
            ).fetchone()
            visit_count = get_db().execute(
                """
                SELECT COUNT(*) AS count
                FROM participant_visits
                WHERE participant_id = ?
                """,
                (participant_id,),
            ).fetchone()["count"]

        self.assertEqual(participant["out_process_at"], "2026-08-22 17:00:00")
        self.assertEqual(visit_count, 0)


if __name__ == "__main__":
    unittest.main()
