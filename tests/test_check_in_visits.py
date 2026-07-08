import os
import tempfile
import unittest
from unittest.mock import patch

from app import app, get_db, init_db


class CheckInVisitTest(unittest.TestCase):
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
            db.execute(
                """
                INSERT INTO participant_visits (
                    participant_id,
                    in_process_at,
                    out_process_at
                ) VALUES (?, ?, ?)
                """,
                (participant_id, in_process_at, out_process_at),
            )
            db.commit()

    def check_in(self, badge_number):
        return self.client.post(
            "/scan",
            data={"badge_number": badge_number, "action": "check_in"},
        )

    @patch("app.local_timestamp", return_value="2026-07-08 09:00:00")
    def test_first_check_in_creates_one_open_visit(self, _timestamp):
        participant_id = self.add_participant("First Visit", "V100")

        response = self.check_in("V100")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Checked in First Visit.", response.get_data(as_text=True))
        with app.app_context():
            participant = get_db().execute(
                """
                SELECT in_process_at, out_process_at
                FROM participants
                WHERE id = ?
                """,
                (participant_id,),
            ).fetchone()
            visits = get_db().execute(
                """
                SELECT participant_id, in_process_at, out_process_at
                FROM participant_visits
                WHERE participant_id = ?
                """,
                (participant_id,),
            ).fetchall()

        self.assertEqual(participant["in_process_at"], "2026-07-08 09:00:00")
        self.assertIsNone(participant["out_process_at"])
        self.assertEqual(len(visits), 1)
        self.assertEqual(visits[0]["participant_id"], participant_id)
        self.assertEqual(visits[0]["in_process_at"], "2026-07-08 09:00:00")
        self.assertIsNone(visits[0]["out_process_at"])

    @patch("app.local_timestamp", return_value="2026-07-08 10:00:00")
    def test_repeat_check_in_while_on_ground_does_not_create_visit(self, _timestamp):
        participant_id = self.add_participant(
            "Already On Ground",
            "V101",
            in_process_at="2026-07-08 09:00:00",
        )
        self.add_visit(participant_id, "2026-07-08 09:00:00")

        response = self.check_in("V101")

        self.assertIn(
            "Already On Ground is already checked in. No changes were made.",
            response.get_data(as_text=True),
        )
        with app.app_context():
            visits = get_db().execute(
                """
                SELECT in_process_at, out_process_at
                FROM participant_visits
                WHERE participant_id = ?
                """,
                (participant_id,),
            ).fetchall()

        self.assertEqual(len(visits), 1)
        self.assertEqual(visits[0]["in_process_at"], "2026-07-08 09:00:00")

    @patch("app.local_timestamp", return_value="2026-08-12 09:30:00")
    def test_return_check_in_updates_participant_and_creates_new_visit(
        self,
        _timestamp,
    ):
        participant_id = self.add_participant(
            "Return Visitor",
            "V102",
            in_process_at="2026-07-01 08:00:00",
            out_process_at="2026-07-11 17:00:00",
        )
        self.add_visit(
            participant_id,
            "2026-07-01 08:00:00",
            "2026-07-11 17:00:00",
        )

        response = self.check_in("V102")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Checked in Return Visitor.", response.get_data(as_text=True))
        with app.app_context():
            participant = get_db().execute(
                """
                SELECT in_process_at, out_process_at
                FROM participants
                WHERE id = ?
                """,
                (participant_id,),
            ).fetchone()
            visits = get_db().execute(
                """
                SELECT in_process_at, out_process_at
                FROM participant_visits
                WHERE participant_id = ?
                ORDER BY id
                """,
                (participant_id,),
            ).fetchall()

        self.assertEqual(participant["in_process_at"], "2026-08-12 09:30:00")
        self.assertIsNone(participant["out_process_at"])
        self.assertEqual(len(visits), 2)
        self.assertEqual(visits[0]["out_process_at"], "2026-07-11 17:00:00")
        self.assertEqual(visits[1]["in_process_at"], "2026-08-12 09:30:00")
        self.assertIsNone(visits[1]["out_process_at"])


if __name__ == "__main__":
    unittest.main()
