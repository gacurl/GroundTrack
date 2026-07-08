import os
import sqlite3
import tempfile
import unittest

from app import app, get_db, init_db


class ParticipantVisitModelTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        app.config["DATABASE"] = os.path.join(
            self.tempdir.name,
            "groundtrack.sqlite",
        )

        with app.app_context():
            init_db()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_database_initialization_creates_participant_visits_table(self):
        with app.app_context():
            columns = get_db().execute(
                "PRAGMA table_info(participant_visits)"
            ).fetchall()

        self.assertEqual(
            [column["name"] for column in columns],
            [
                "id",
                "participant_id",
                "in_process_at",
                "out_process_at",
                "created_at",
            ],
        )
        self.assertEqual(columns[1]["notnull"], 1)
        self.assertEqual(columns[4]["notnull"], 1)

    def test_visit_is_tied_to_participant_without_changing_participant_timestamps(
        self,
    ):
        participant_in = "2026-07-08 09:00:00"
        participant_out = "2026-07-08 17:00:00"
        visit_in = "2026-08-12 09:30:00"

        with app.app_context():
            db = get_db()
            participant_id = db.execute(
                """
                INSERT INTO participants (
                    name,
                    in_process_at,
                    out_process_at
                ) VALUES (?, ?, ?)
                """,
                ("Sally Example", participant_in, participant_out),
            ).lastrowid
            visit_id = db.execute(
                """
                INSERT INTO participant_visits (
                    participant_id,
                    in_process_at,
                    out_process_at
                ) VALUES (?, ?, ?)
                """,
                (participant_id, visit_in, None),
            ).lastrowid
            db.commit()

            row = db.execute(
                """
                SELECT
                    participant_visits.id,
                    participant_visits.participant_id,
                    participant_visits.in_process_at AS visit_in,
                    participant_visits.out_process_at AS visit_out,
                    participant_visits.created_at,
                    participants.name,
                    participants.in_process_at AS participant_in,
                    participants.out_process_at AS participant_out
                FROM participant_visits
                JOIN participants
                    ON participants.id = participant_visits.participant_id
                WHERE participant_visits.id = ?
                """,
                (visit_id,),
            ).fetchone()

        self.assertEqual(row["participant_id"], participant_id)
        self.assertEqual(row["name"], "Sally Example")
        self.assertEqual(row["visit_in"], visit_in)
        self.assertIsNone(row["visit_out"])
        self.assertIsNotNone(row["created_at"])
        self.assertEqual(row["participant_in"], participant_in)
        self.assertEqual(row["participant_out"], participant_out)

    def test_visit_requires_an_existing_participant(self):
        with app.app_context():
            with self.assertRaises(sqlite3.IntegrityError):
                get_db().execute(
                    """
                    INSERT INTO participant_visits (
                        participant_id,
                        in_process_at
                    ) VALUES (?, ?)
                    """,
                    (9999, "2026-07-08 09:00:00"),
                )


if __name__ == "__main__":
    unittest.main()
