import os
import sqlite3
from datetime import date, datetime
from zipfile import BadZipFile

import click
from flask import Flask, g, render_template, request
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


app = Flask(__name__)
app.config["DATABASE"] = os.path.join(app.instance_path, "groundtrack.sqlite")


NAV_ITEMS = [
    ("dashboard", "Dashboard"),
    ("import_page", "Import"),
    ("scan", "Scan"),
    ("participants", "Participants"),
    ("walk_up", "Walk-Up"),
    ("on_ground_report", "On-Ground Report"),
]

EXPECTED_IMPORT_COLUMNS = [
    "No.",
    "Name",
    "Rank",
    "NAT",
    "Visit Request Status",
    "Badge #",
    "In-Process Date/Time",
    "Out-Process Date/Time",
    "Your Unit, Organization, or Company",
    "Thread / Initiative",
]


@app.context_processor
def inject_navigation():
    return {"nav_items": NAV_ITEMS}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(app.instance_path, exist_ok=True)
    db = get_db()

    with app.open_resource("schema.sql") as schema_file:
        db.executescript(schema_file.read().decode("utf-8"))


@app.cli.command("init-db")
def init_db_command():
    init_db()
    click.echo("Initialized the local GroundTrack database.")


def database_exists():
    return os.path.exists(app.config["DATABASE"])


def get_dashboard_counts():
    counts = {
        "total_participants": 0,
        "currently_on_ground": 0,
        "checked_out": 0,
        "walkup_participants": 0,
    }

    if not database_exists():
        return counts, False

    try:
        row = get_db().execute(
            """
            SELECT
                COUNT(*) AS total_participants,
                SUM(
                    CASE
                        WHEN in_process_at IS NOT NULL
                            AND in_process_at != ''
                            AND (
                                out_process_at IS NULL
                                OR out_process_at = ''
                                OR out_process_at < in_process_at
                            )
                        THEN 1 ELSE 0
                    END
                ) AS currently_on_ground,
                SUM(
                    CASE
                        WHEN out_process_at IS NOT NULL
                            AND out_process_at != ''
                            AND (
                                in_process_at IS NULL
                                OR in_process_at = ''
                                OR out_process_at >= in_process_at
                            )
                        THEN 1 ELSE 0
                    END
                ) AS checked_out,
                SUM(CASE WHEN is_walkup = 1 THEN 1 ELSE 0 END) AS walkup_participants
            FROM participants
            """
        ).fetchone()
    except sqlite3.OperationalError:
        return counts, False

    for key in counts:
        counts[key] = row[key] or 0

    return counts, True


def is_xlsx_file(filename):
    return filename.lower().endswith(".xlsx")


def cell_value_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def get_header_map(sheet):
    header_row = next(
        sheet.iter_rows(min_row=1, max_row=1, values_only=True),
        (),
    )
    return {
        cell_value_text(value): index
        for index, value in enumerate(header_row)
        if cell_value_text(value)
    }


def count_data_rows(sheet, header_map):
    row_count = 0
    for row_values in sheet.iter_rows(min_row=2, values_only=True):
        if any(
            import_cell(row_values, header_map, column)
            for column in EXPECTED_IMPORT_COLUMNS
        ):
            row_count += 1
    return row_count


def import_cell(row_values, header_map, column):
    column_index = header_map[column]
    if column_index >= len(row_values):
        return None

    value = cell_value_text(row_values[column_index])
    return value or None


def open_import_workbook(file_storage):
    try:
        workbook = load_workbook(file_storage, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, OSError):
        return None, None, None, "The uploaded file could not be read as an .xlsx workbook."

    if "Data" not in workbook.sheetnames:
        workbook.close()
        return None, None, None, "The workbook is missing the Data sheet."

    data_sheet = workbook["Data"]
    header_map = get_header_map(data_sheet)
    missing_columns = [
        column for column in EXPECTED_IMPORT_COLUMNS if column not in header_map
    ]

    if missing_columns:
        workbook.close()
        return (
            None,
            None,
            None,
            "Missing expected columns: " + ", ".join(missing_columns),
        )

    return workbook, data_sheet, header_map, None


def validate_import_workbook(file_storage):
    workbook, data_sheet, header_map, error = open_import_workbook(file_storage)
    if error:
        return False, error

    try:
        data_row_count = count_data_rows(data_sheet, header_map)
        return True, f"Spreadsheet validated. Found {data_row_count} data rows."
    finally:
        workbook.close()


def existing_badge_numbers():
    rows = get_db().execute(
        """
        SELECT badge_number
        FROM participants
        WHERE badge_number IS NOT NULL
            AND badge_number != ''
        """
    ).fetchall()
    return {row["badge_number"] for row in rows}


def row_to_participant(row_values, header_map):
    return {
        "source_row_no": import_cell(row_values, header_map, "No."),
        "name": import_cell(row_values, header_map, "Name"),
        "rank": import_cell(row_values, header_map, "Rank"),
        "nat": import_cell(row_values, header_map, "NAT"),
        "visit_request_status": import_cell(
            row_values,
            header_map,
            "Visit Request Status",
        ),
        "badge_number": import_cell(row_values, header_map, "Badge #"),
        "in_process_at": import_cell(row_values, header_map, "In-Process Date/Time"),
        "out_process_at": import_cell(row_values, header_map, "Out-Process Date/Time"),
        "organization": import_cell(
            row_values,
            header_map,
            "Your Unit, Organization, or Company",
        ),
        "thread_initiative": import_cell(row_values, header_map, "Thread / Initiative"),
        "is_walkup": 0,
    }


def insert_participant(participant):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO participants (
            source_row_no,
            name,
            rank,
            nat,
            visit_request_status,
            badge_number,
            in_process_at,
            out_process_at,
            organization,
            thread_initiative,
            is_walkup
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            participant["source_row_no"],
            participant["name"],
            participant["rank"],
            participant["nat"],
            participant["visit_request_status"],
            participant["badge_number"],
            participant["in_process_at"],
            participant["out_process_at"],
            participant["organization"],
            participant["thread_initiative"],
            participant["is_walkup"],
        ),
    )
    db.execute(
        """
        INSERT INTO activity_log (participant_id, action, badge_number, note)
        VALUES (?, ?, ?, ?)
        """,
        (
            cursor.lastrowid,
            "IMPORT",
            participant["badge_number"],
            "Imported from spreadsheet",
        ),
    )


def import_participants_from_workbook(file_storage):
    workbook, data_sheet, header_map, error = open_import_workbook(file_storage)
    if error:
        return False, error

    imported_count = 0
    skipped_count = 0

    try:
        seen_badges = existing_badge_numbers()

        for row_values in data_sheet.iter_rows(min_row=2, values_only=True):
            participant = row_to_participant(row_values, header_map)
            badge_number = participant["badge_number"]

            if not participant["name"]:
                skipped_count += 1
                continue

            if badge_number:
                if badge_number in seen_badges:
                    skipped_count += 1
                    continue
                seen_badges.add(badge_number)

            insert_participant(participant)
            imported_count += 1

        get_db().commit()
    except sqlite3.OperationalError:
        db = g.get("db")
        if db is not None:
            db.rollback()
        return False, "Local database is not initialized. Run flask init-db first."
    finally:
        workbook.close()

    return (
        True,
        f"Imported {imported_count} rows. Skipped {skipped_count} rows.",
    )


@app.route("/")
def dashboard():
    counts, database_ready = get_dashboard_counts()
    return render_template(
        "dashboard.html",
        counts=counts,
        database_ready=database_ready,
    )


@app.route("/import", methods=["GET", "POST"])
def import_page():
    message = None
    message_type = None

    if request.method == "POST":
        upload = request.files.get("spreadsheet")

        if upload is None or upload.filename == "":
            message = "No file selected. Choose an .xlsx spreadsheet to upload."
            message_type = "error"
        elif not is_xlsx_file(upload.filename):
            message = "File must be an .xlsx spreadsheet."
            message_type = "error"
        else:
            is_imported, message = import_participants_from_workbook(upload)
            message_type = "success" if is_imported else "error"

    return render_template(
        "import.html",
        message=message,
        message_type=message_type,
        expected_columns=EXPECTED_IMPORT_COLUMNS,
    )


@app.route("/scan")
def scan():
    return render_template(
        "placeholder.html",
        title="Scan",
        message="Badge scan and check-in/check-out actions will be added later.",
    )


@app.route("/participants")
def participants():
    return render_template(
        "placeholder.html",
        title="Participants",
        message="Participant records will appear here after import support is added.",
    )


@app.route("/walk-up")
def walk_up():
    return render_template(
        "placeholder.html",
        title="Walk-Up",
        message="Walk-up participant entry will be added in a later milestone.",
    )


@app.route("/on-ground")
def on_ground_report():
    return render_template(
        "placeholder.html",
        title="On-Ground Report",
        message="Current on-ground reporting will be added after check-in support exists.",
    )


if __name__ == "__main__":
    app.run(debug=True)
