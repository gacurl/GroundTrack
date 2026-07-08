import os
import tempfile
import unittest

from app import app, get_db, init_db


class ParticipantsPageTest(unittest.TestCase):
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
        badge_number=None,
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
                    out_process_at,
                    is_walkup
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    "CPT",
                    "US",
                    "Approved",
                    badge_number,
                    "Example Unit",
                    "Alpha",
                    in_process_at,
                    out_process_at,
                    0,
                ),
            ).lastrowid
            db.commit()
        return participant_id

    def test_participants_route_empty_state(self):
        response = self.client.get("/participants")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Participants", body)
        self.assertIn(
            "No participants have been added yet. "
            "Import a spreadsheet or add a walk-up participant.",
            body,
        )
        self.assertIn("← Back to Dashboard", body)

    def test_dashboard_links_to_participants(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('href="/participants"', body)
        self.assertIn("Participants", body)

    def test_participants_route_shows_seeded_participants(self):
        participant_id = self.add_participant("Ada Lovelace", badge_number="1001")

        response = self.client.get("/participants")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Ada Lovelace", body)
        self.assertIn("CPT", body)
        self.assertIn("US", body)
        self.assertIn("Approved", body)
        self.assertIn("1001", body)
        self.assertIn("Example Unit", body)
        self.assertIn("Alpha", body)
        self.assertIn("Mission Area / Initiative", body)
        self.assertIn(f'href="/participants/{participant_id}"', body)

    def test_participants_route_shows_status_text(self):
        self.add_participant(
            "On Ground Person",
            badge_number="1001",
            in_process_at="2026-07-07 09:00:00",
            out_process_at=None,
        )
        self.add_participant(
            "Off Ground Person",
            badge_number="1002",
            in_process_at="2026-07-07 09:00:00",
            out_process_at="2026-07-07 10:00:00",
        )
        self.add_participant("Not Checked In Person", badge_number="1003")

        response = self.client.get("/participants")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("On Ground", body)
        self.assertIn("Off Ground", body)
        self.assertIn("Not Checked In", body)
        self.assertIn("Mission Area / Initiative", body)


if __name__ == "__main__":
    unittest.main()
