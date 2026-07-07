import os
import sqlite3

import click
from flask import Flask, g, render_template


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


@app.route("/")
def dashboard():
    counts, database_ready = get_dashboard_counts()
    return render_template(
        "dashboard.html",
        counts=counts,
        database_ready=database_ready,
    )


@app.route("/import")
def import_page():
    return render_template(
        "placeholder.html",
        title="Import",
        message="Spreadsheet import will be added in a later milestone.",
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
