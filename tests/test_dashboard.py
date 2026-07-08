import os
import re
import tempfile
import unittest

from app import app, get_db, init_db


class DashboardTest(unittest.TestCase):
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
        in_process_at=None,
        out_process_at=None,
        is_walkup=0,
    ):
        with app.app_context():
            db = get_db()
            db.execute(
                """
                INSERT INTO participants (
                    name,
                    in_process_at,
                    out_process_at,
                    is_walkup
                ) VALUES (?, ?, ?, ?)
                """,
                (name, in_process_at, out_process_at, is_walkup),
            )
            db.commit()

    def test_dashboard_displays_expected_counts(self):
        self.add_participant("Not Checked In")
        self.add_participant(
            "Currently On Ground 1",
            in_process_at="2026-07-08 09:00:00",
            is_walkup=1,
        )
        self.add_participant(
            "Currently On Ground 2",
            in_process_at="2026-07-08 09:30:00",
            is_walkup=1,
        )
        self.add_participant(
            "Checked Out 1",
            in_process_at="2026-07-08 08:00:00",
            out_process_at="2026-07-08 10:00:00",
        )
        self.add_participant(
            "Checked Out 2",
            in_process_at="2026-07-08 08:15:00",
            out_process_at="2026-07-08 10:15:00",
        )
        self.add_participant(
            "Checked Out 3",
            in_process_at="2026-07-08 08:30:00",
            out_process_at="2026-07-08 10:30:00",
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        expected_counts = [
            ("Total Participants", "6"),
            ("Currently On Ground", "2"),
            ("Not Checked In", "1"),
            ("Checked Out", "3"),
            ("Walk-Up Participants", "2"),
        ]
        for label, count in expected_counts:
            self.assertRegex(
                body,
                rf"<span>{re.escape(label)}</span>\s*<strong>{count}</strong>",
            )

    def test_dashboard_displays_quick_links(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        expected_links = [
            ("/scan", "Scan Check In / Check Out"),
            ("/participants", "Participants"),
            ("/walk-up", "Add Walk-Up Participant"),
            ("/on-ground", "On-Ground Report"),
            ("/import", "Import Spreadsheet"),
            ("/on-ground/export.csv", "Export CSV"),
        ]
        for href, label in expected_links:
            self.assertIn(f'href="{href}"', body)
            self.assertIn(f"<strong>{label}</strong>", body)


if __name__ == "__main__":
    unittest.main()
