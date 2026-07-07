from flask import Flask, render_template


app = Flask(__name__)


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


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


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
