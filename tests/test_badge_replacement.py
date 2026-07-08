import os
import tempfile
import unittest
from unittest.mock import patch

from app import app, get_db, init_db


class BadgeReplacementTest(unittest.TestCase):
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

    def add_participant(self, name, badge_number):
        with app.app_context():
            db = get_db()
            participant_id = db.execute(
                """
                INSERT INTO participants (name, badge_number)
                VALUES (?, ?)
                """,
                (name, badge_number),
            ).lastrowid
            db.commit()
        return participant_id

    def add_visit(self, participant_id):
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
                (
                    participant_id,
                    "2026-07-08 09:00:00",
                    "2026-07-08 17:00:00",
                ),
            ).lastrowid
            db.commit()
        return visit_id

    def post_scan(self, badge_number, action):
        return self.client.post(
            "/scan",
            data={"badge_number": badge_number, "action": action},
        )

    def replace_badge(self, participant_id, new_badge_number):
        return self.client.post(
            f"/participants/{participant_id}/replace-badge",
            data={"new_badge_number": new_badge_number},
        )

    def test_detail_page_links_to_replacement_form(self):
        participant_id = self.add_participant("Ada Lovelace", "1001")

        response = self.client.get(f"/participants/{participant_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Replace Lost Badge", body)
        self.assertIn(
            f'href="/participants/{participant_id}/replace-badge"',
            body,
        )

    def test_replacement_form_shows_participant_and_current_badge(self):
        participant_id = self.add_participant("Ada Lovelace", "1001")

        response = self.client.get(
            f"/participants/{participant_id}/replace-badge"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Ada Lovelace", body)
        self.assertIn("Current badge:", body)
        self.assertIn("1001", body)
        self.assertIn('name="new_badge_number"', body)

    @patch("app.local_timestamp", return_value="2026-07-09 10:30:00")
    def test_valid_replacement_updates_existing_participant_and_preserves_visits(
        self,
        _timestamp,
    ):
        participant_id = self.add_participant("Ada Lovelace", "1001")
        visit_id = self.add_visit(participant_id)

        response = self.client.post(
            f"/participants/{participant_id}/replace-badge",
            data={"new_badge_number": " 2002 "},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"/participants/{participant_id}?badge_replaced=1",
            response.headers["Location"],
        )

        detail_response = self.client.get(response.headers["Location"])
        self.assertIn(
            "Badge replaced for Ada Lovelace. New badge: 2002",
            detail_response.get_data(as_text=True),
        )

        with app.app_context():
            db = get_db()
            participants = db.execute(
                """
                SELECT id, badge_number
                FROM participants
                """
            ).fetchall()
            visits = db.execute(
                """
                SELECT id, participant_id, in_process_at, out_process_at
                FROM participant_visits
                """
            ).fetchall()
            badge_history = db.execute(
                """
                SELECT participant_id, old_badge, new_badge, changed_at
                FROM badge_history
                """
            ).fetchall()

        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0]["id"], participant_id)
        self.assertEqual(participants[0]["badge_number"], "2002")
        self.assertEqual(len(visits), 1)
        self.assertEqual(visits[0]["id"], visit_id)
        self.assertEqual(visits[0]["participant_id"], participant_id)
        self.assertEqual(visits[0]["in_process_at"], "2026-07-08 09:00:00")
        self.assertEqual(visits[0]["out_process_at"], "2026-07-08 17:00:00")
        self.assertEqual(len(badge_history), 1)
        self.assertEqual(badge_history[0]["participant_id"], participant_id)
        self.assertEqual(badge_history[0]["old_badge"], "1001")
        self.assertEqual(badge_history[0]["new_badge"], "2002")
        self.assertEqual(badge_history[0]["changed_at"], "2026-07-09 10:30:00")

    def test_old_badge_check_in_warns_and_does_not_create_open_visit(self):
        participant_id = self.add_participant("Ada Lovelace", "1001")
        self.replace_badge(participant_id, "2002")

        response = self.post_scan("1001", "check_in")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Badge 1001 was replaced/lost and is no longer active. "
            "Current badge for Ada Lovelace is 2002.",
            response.get_data(as_text=True),
        )
        with app.app_context():
            participant = get_db().execute(
                """
                SELECT in_process_at, out_process_at
                FROM participants
                WHERE id = ?
                """,
                (participant_id,),
            ).fetchone()
            open_visit_count = get_db().execute(
                """
                SELECT COUNT(*) AS count
                FROM participant_visits
                WHERE participant_id = ?
                    AND out_process_at IS NULL
                """,
                (participant_id,),
            ).fetchone()["count"]

        self.assertIsNone(participant["in_process_at"])
        self.assertIsNone(participant["out_process_at"])
        self.assertEqual(open_visit_count, 0)

    @patch("app.local_timestamp", return_value="2026-07-09 11:00:00")
    def test_old_badge_check_out_warns_and_does_not_close_open_visit(
        self,
        _timestamp,
    ):
        participant_id = self.add_participant("Ada Lovelace", "1001")
        self.replace_badge(participant_id, "2002")
        self.post_scan("2002", "check_in")

        response = self.post_scan("1001", "check_out")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Badge 1001 was replaced/lost and is no longer active. "
            "Current badge for Ada Lovelace is 2002.",
            response.get_data(as_text=True),
        )
        with app.app_context():
            participant = get_db().execute(
                """
                SELECT in_process_at, out_process_at
                FROM participants
                WHERE id = ?
                """,
                (participant_id,),
            ).fetchone()
            open_visit_count = get_db().execute(
                """
                SELECT COUNT(*) AS count
                FROM participant_visits
                WHERE participant_id = ?
                    AND out_process_at IS NULL
                """,
                (participant_id,),
            ).fetchone()["count"]

        self.assertEqual(participant["in_process_at"], "2026-07-09 11:00:00")
        self.assertIsNone(participant["out_process_at"])
        self.assertEqual(open_visit_count, 1)

    @patch("app.local_timestamp", return_value="2026-07-09 11:00:00")
    def test_current_replacement_badge_still_checks_in_normally(self, _timestamp):
        participant_id = self.add_participant("Ada Lovelace", "1001")
        self.replace_badge(participant_id, "2002")

        response = self.post_scan("2002", "check_in")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Checked in Ada Lovelace.", response.get_data(as_text=True))
        with app.app_context():
            participant = get_db().execute(
                """
                SELECT in_process_at, out_process_at
                FROM participants
                WHERE id = ?
                """,
                (participant_id,),
            ).fetchone()

        self.assertEqual(participant["in_process_at"], "2026-07-09 11:00:00")
        self.assertIsNone(participant["out_process_at"])

    def test_unknown_badge_scan_keeps_existing_unknown_message(self):
        response = self.post_scan("UNKNOWN", "check_in")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Badge UNKNOWN was not found. Check the badge number and try again.",
            response.get_data(as_text=True),
        )

    def test_blank_badge_is_rejected(self):
        participant_id = self.add_participant("Ada Lovelace", "1001")

        response = self.client.post(
            f"/participants/{participant_id}/replace-badge",
            data={"new_badge_number": "   "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Enter a new badge number.",
            response.get_data(as_text=True),
        )
        self.assertEqual(self.current_badge(participant_id), "1001")
        self.assertEqual(self.badge_history_count(participant_id), 0)

    def test_same_badge_is_rejected(self):
        participant_id = self.add_participant("Ada Lovelace", "1001")

        response = self.client.post(
            f"/participants/{participant_id}/replace-badge",
            data={"new_badge_number": " 1001 "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "The new badge number matches the current badge. "
            "No changes were made.",
            response.get_data(as_text=True),
        )
        self.assertEqual(self.current_badge(participant_id), "1001")
        self.assertEqual(self.badge_history_count(participant_id), 0)

    def test_badge_assigned_to_another_participant_is_rejected(self):
        participant_id = self.add_participant("Ada Lovelace", "1001")
        self.add_participant("Grace Hopper", "2002")

        response = self.client.post(
            f"/participants/{participant_id}/replace-badge",
            data={"new_badge_number": "2002"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Badge 2002 is already in use. Enter a different badge number.",
            response.get_data(as_text=True),
        )
        self.assertEqual(self.current_badge(participant_id), "1001")
        self.assertEqual(self.badge_history_count(participant_id), 0)

    def test_missing_participant_returns_not_found(self):
        get_response = self.client.get("/participants/9999/replace-badge")
        post_response = self.client.post(
            "/participants/9999/replace-badge",
            data={"new_badge_number": "2002"},
        )

        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(post_response.status_code, 404)
        self.assertNotIn("Traceback", get_response.get_data(as_text=True))
        self.assertNotIn("Traceback", post_response.get_data(as_text=True))

    def current_badge(self, participant_id):
        with app.app_context():
            return get_db().execute(
                """
                SELECT badge_number
                FROM participants
                WHERE id = ?
                """,
                (participant_id,),
            ).fetchone()["badge_number"]

    def badge_history_count(self, participant_id):
        with app.app_context():
            return get_db().execute(
                """
                SELECT COUNT(*) AS count
                FROM badge_history
                WHERE participant_id = ?
                """,
                (participant_id,),
            ).fetchone()["count"]


if __name__ == "__main__":
    unittest.main()
