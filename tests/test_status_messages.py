import io
import os
import tempfile
import unittest

from openpyxl import Workbook

from app import EXPECTED_IMPORT_COLUMNS, app, get_db, init_db


class StatusMessageTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        app.config["DATABASE"] = os.path.join(
            self.tempdir.name,
            "groundtrack.sqlite",
        )

        with app.app_context():
            init_db()
            db = get_db()
            db.execute(
                """
                INSERT INTO participants (name, badge_number, is_walkup)
                VALUES (?, ?, ?)
                """,
                ("Scan Person", "S100", 0),
            )
            db.commit()

        self.client = app.test_client()

    def tearDown(self):
        self.tempdir.cleanup()

    def post_scan(self, badge_number, action):
        return self.client.post(
            "/scan",
            data={"badge_number": badge_number, "action": action},
        )

    def test_scan_messages_cover_common_check_in_and_check_out_states(self):
        response = self.post_scan("S100", "check_in")
        self.assertIn("Checked in Scan Person.", response.get_data(as_text=True))

        response = self.post_scan("S100", "check_in")
        self.assertIn(
            "Scan Person is already checked in. No changes were made.",
            response.get_data(as_text=True),
        )

        response = self.post_scan("S100", "check_out")
        self.assertIn("Checked out Scan Person.", response.get_data(as_text=True))

        response = self.post_scan("S100", "check_out")
        self.assertIn(
            "Scan Person is not on ground. No changes were made.",
            response.get_data(as_text=True),
        )

    def test_scan_messages_explain_missing_and_unknown_badges(self):
        response = self.post_scan("", "check_in")
        self.assertIn(
            "Enter or scan a badge number.",
            response.get_data(as_text=True),
        )

        response = self.post_scan("UNKNOWN", "check_in")
        self.assertIn(
            "Badge UNKNOWN was not found. Check the badge number and try again.",
            response.get_data(as_text=True),
        )

    def test_import_messages_summarize_success_and_failure(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet.append(EXPECTED_IMPORT_COLUMNS)
        participant = [
            "1",
            "Imported Person",
            "CPT",
            "US",
            "Approved",
            "I100",
            "",
            "",
            "Example Unit",
            "Alpha",
        ]
        sheet.append(participant)
        sheet.append(participant)
        upload = io.BytesIO()
        workbook.save(upload)
        workbook.close()
        upload.seek(0)

        response = self.client.post(
            "/import",
            data={"spreadsheet": (upload, "participants.xlsx")},
            content_type="multipart/form-data",
        )
        self.assertIn(
            "Imported 1 participant. Skipped 1 entry, including 1 duplicate.",
            response.get_data(as_text=True),
        )

        response = self.client.post("/import", data={})
        self.assertIn(
            "No file selected. Choose an .xlsx spreadsheet to upload.",
            response.get_data(as_text=True),
        )


if __name__ == "__main__":
    unittest.main()
