import os
import tempfile
import unittest

from app import app, get_db, init_db


class ParticipantDetailTest(unittest.TestCase):
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
        name="Ada Lovelace",
        in_process_at=None,
        out_process_at=None,
    ):
        with app.app_context():
            db = get_db()
            participant_id = db.execute(
                """
                INSERT INTO participants (
                    name,
                    rank,
                    nat,
                    visit_request_status,
                    badge_number,
                    organization,
                    thread_initiative,
                    in_process_at,
                    out_process_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    "CPT",
                    "US",
                    "Approved",
                    "1001",
                    "Example Unit",
                    "Alpha",
                    in_process_at,
                    out_process_at,
                ),
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

    def test_detail_page_shows_core_fields_and_empty_visit_history(self):
        participant_id = self.add_participant()

        response = self.client.get(f"/participants/{participant_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for expected_text in [
            "Ada Lovelace",
            "CPT",
            "US",
            "Approved",
            "1001",
            "Example Unit",
            "Alpha",
            "Mission Area / Initiative",
            "Current status: Not Checked In",
            "No visit history has been recorded for this participant yet.",
            "No badge replacement history has been recorded for this participant yet.",
            "← Back to Participants",
        ]:
            self.assertIn(expected_text, body)

    def test_detail_page_shows_each_current_status(self):
        participant_ids = {
            "On Ground": self.add_participant(
                "On Ground Person",
                in_process_at="2026-07-08 09:00:00",
            ),
            "Off Ground": self.add_participant(
                "Off Ground Person",
                in_process_at="2026-07-08 09:00:00",
                out_process_at="2026-07-08 17:00:00",
            ),
            "Not Checked In": self.add_participant("Not Checked In Person"),
        }

        for status, participant_id in participant_ids.items():
            with self.subTest(status=status):
                response = self.client.get(f"/participants/{participant_id}")
                self.assertIn(
                    f"Current status: {status}",
                    response.get_data(as_text=True),
                )

    def test_visit_history_is_newest_first_with_open_and_closed_statuses(self):
        participant_id = self.add_participant(
            in_process_at="2026-08-12 09:30:00",
        )
        self.add_visit(
            participant_id,
            "2026-07-01 08:00:00",
            "2026-07-11 17:00:00",
        )
        self.add_visit(participant_id, "2026-08-12 09:30:00")

        response = self.client.get(f"/participants/{participant_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertLess(
            body.index("2026-08-12 09:30:00"),
            body.index("2026-07-01 08:00:00"),
        )
        self.assertIn("<td>Open</td>", body)
        self.assertIn("<td>Closed</td>", body)
        self.assertIn("2026-07-11 17:00:00", body)

    def test_current_attendance_shows_on_ground_open_visit_timestamp(self):
        participant_id = self.add_participant(
            in_process_at="2026-08-12 09:30:00",
        )
        self.add_visit(
            participant_id,
            "2026-07-01 08:00:00",
            "2026-07-11 17:00:00",
        )
        self.add_visit(participant_id, "2026-08-12 09:45:00")

        response = self.client.get(f"/participants/{participant_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Current Attendance", body)
        self.assertIn("<dt>Current Status</dt>", body)
        self.assertIn("<dd>On Ground</dd>", body)
        self.assertIn("<dt>Current In-Process Date/Time</dt>", body)
        self.assertIn("<dd>2026-08-12 09:45:00</dd>", body)
        self.assertIn("<dt>Current Out-Process Date/Time</dt>", body)
        self.assertIn("<dd>—</dd>", body)

    def test_current_attendance_shows_off_ground_latest_visit_timestamps(self):
        participant_id = self.add_participant(
            in_process_at="2026-08-12 09:30:00",
            out_process_at="2026-08-12 17:00:00",
        )
        self.add_visit(
            participant_id,
            "2026-07-01 08:00:00",
            "2026-07-11 17:00:00",
        )
        self.add_visit(
            participant_id,
            "2026-08-12 09:45:00",
            "2026-08-12 17:10:00",
        )

        response = self.client.get(f"/participants/{participant_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("<dd>Off Ground</dd>", body)
        self.assertIn("<dd>2026-08-12 09:45:00</dd>", body)
        self.assertIn("<dd>2026-08-12 17:10:00</dd>", body)

    def test_current_attendance_shows_not_checked_in_without_timestamps(self):
        participant_id = self.add_participant()

        response = self.client.get(f"/participants/{participant_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("<dd>Not Checked In</dd>", body)
        self.assertIn("<dt>Current In-Process Date/Time</dt>", body)
        self.assertIn("<dt>Current Out-Process Date/Time</dt>", body)
        self.assertGreaterEqual(body.count("<dd>—</dd>"), 2)

    def test_current_attendance_uses_legacy_participant_timestamp_fallback(self):
        participant_id = self.add_participant(
            in_process_at="2026-08-12 09:30:00",
            out_process_at="2026-08-12 17:00:00",
        )

        response = self.client.get(f"/participants/{participant_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("<dd>Off Ground</dd>", body)
        self.assertIn("<dd>2026-08-12 09:30:00</dd>", body)
        self.assertIn("<dd>2026-08-12 17:00:00</dd>", body)

    def test_missing_participant_returns_not_found(self):
        response = self.client.get("/participants/9999")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Traceback", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
