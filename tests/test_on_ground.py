import csv
import io
import os
import tempfile
import unittest

from app import app, get_db, init_db


class OnGroundReportTest(unittest.TestCase):
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
            db.execute(
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
            )
            db.commit()

    def test_on_ground_route_empty_state(self):
        response = self.client.get("/on-ground")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("On-Ground Report", body)
        self.assertIn("Nobody is currently on ground.", body)
        self.assertIn("← Back to Dashboard", body)
        self.assertIn('href="/on-ground/export.csv"', body)
        self.assertIn("Export CSV", body)
        self.assertNotIn("Thread / Initiative", body)

    def test_on_ground_route_only_shows_currently_on_ground(self):
        self.add_participant(
            "On Ground Person",
            "1001",
            in_process_at="2026-07-07 09:00:00",
            out_process_at=None,
        )
        self.add_participant(
            "Checked Out Person",
            "1002",
            in_process_at="2026-07-07 09:00:00",
            out_process_at="2026-07-07 10:00:00",
        )
        self.add_participant("Not Checked In Person", "1003")

        response = self.client.get("/on-ground")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("On Ground Person", body)
        self.assertIn("1001", body)
        self.assertIn("2026-07-07 09:00:00", body)
        self.assertIn("Example Unit", body)
        self.assertIn("Alpha", body)
        self.assertIn("Mission Area / Initiative", body)
        self.assertNotIn("Checked Out Person", body)
        self.assertNotIn("Not Checked In Person", body)

    def test_on_ground_route_excludes_blank_out_process_only_when_checked_in(self):
        self.add_participant(
            "Blank Out Process Person",
            "1004",
            in_process_at="2026-07-07 11:00:00",
            out_process_at="",
        )

        response = self.client.get("/on-ground")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Blank Out Process Person", body)

    def test_export_returns_only_currently_on_ground_participants(self):
        self.add_participant(
            "On Ground Person",
            "1001",
            in_process_at="2026-07-07 09:00:00",
            out_process_at=None,
        )
        self.add_participant(
            "Checked Out Person",
            "1002",
            in_process_at="2026-07-07 09:00:00",
            out_process_at="2026-07-07 10:00:00",
        )
        self.add_participant("Not Checked In Person", "1003")

        response = self.client.get("/on-ground/export.csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn(
            "attachment; filename=on_ground_report.csv",
            response.headers["Content-Disposition"],
        )
        rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
        self.assertEqual(
            rows[0],
            [
                "Name",
                "Rank",
                "NAT",
                "Visit Request Status",
                "Badge #",
                "In-Process Date/Time",
                "Unit / Organization / Company",
                "Mission Area / Initiative",
            ],
        )
        self.assertEqual(
            rows[1],
            [
                "On Ground Person",
                "CPT",
                "US",
                "Approved",
                "1001",
                "2026-07-07 09:00:00",
                "Example Unit",
                "Alpha",
            ],
        )
        self.assertEqual(len(rows), 2)

    def test_empty_export_returns_headers_only(self):
        response = self.client.get("/on-ground/export.csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0],
            [
                "Name",
                "Rank",
                "NAT",
                "Visit Request Status",
                "Badge #",
                "In-Process Date/Time",
                "Unit / Organization / Company",
                "Mission Area / Initiative",
            ],
        )


if __name__ == "__main__":
    unittest.main()
