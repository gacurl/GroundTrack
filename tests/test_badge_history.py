import os
import tempfile
import unittest

from app import app, get_db, init_db


class BadgeHistoryTest(unittest.TestCase):
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

    def add_participant(self):
        with app.app_context():
            db = get_db()
            participant_id = db.execute(
                """
                INSERT INTO participants (name, badge_number)
                VALUES (?, ?)
                """,
                ("Ada Lovelace", "3003"),
            ).lastrowid
            db.commit()
        return participant_id

    def add_badge_change(
        self,
        participant_id,
        old_badge,
        new_badge,
        changed_at,
    ):
        with app.app_context():
            db = get_db()
            db.execute(
                """
                INSERT INTO badge_history (
                    participant_id,
                    old_badge,
                    new_badge,
                    changed_at
                ) VALUES (?, ?, ?, ?)
                """,
                (participant_id, old_badge, new_badge, changed_at),
            )
            db.commit()

    def test_database_initialization_creates_badge_history_table(self):
        with app.app_context():
            columns = get_db().execute(
                "PRAGMA table_info(badge_history)"
            ).fetchall()

        self.assertEqual(
            [column["name"] for column in columns],
            [
                "id",
                "participant_id",
                "old_badge",
                "new_badge",
                "changed_at",
            ],
        )
        self.assertEqual(columns[1]["notnull"], 1)
        self.assertEqual(columns[2]["notnull"], 0)
        self.assertEqual(columns[3]["notnull"], 1)
        self.assertEqual(columns[4]["notnull"], 1)

    def test_detail_page_shows_badge_history_newest_first(self):
        participant_id = self.add_participant()
        self.add_badge_change(
            participant_id,
            "1001",
            "2002",
            "2026-07-09 10:30:00",
        )
        self.add_badge_change(
            participant_id,
            "2002",
            "3003",
            "2026-08-12 09:15:00",
        )

        response = self.client.get(f"/participants/{participant_id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Badge History", body)
        self.assertIn("Changed Date/Time", body)
        self.assertIn("Old Badge #", body)
        self.assertIn("New Badge #", body)
        self.assertLess(
            body.index("2026-08-12 09:15:00"),
            body.index("2026-07-09 10:30:00"),
        )
        self.assertIn("1001", body)
        self.assertIn("2002", body)
        self.assertIn("3003", body)


if __name__ == "__main__":
    unittest.main()
