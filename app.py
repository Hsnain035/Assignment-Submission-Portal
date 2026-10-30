"""Assignment Submission Portal

A small Flask application that lets students submit assignment links and
shows every saved submission. Data is stored in a local SQLite database.
"""

import os
import sqlite3
from urllib.parse import urlparse

from flask import Flask, flash, g, redirect, render_template, request, url_for

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DATABASE = os.path.join(BASE_DIR, "submissions.db")

# Field limits keep the database tidy and match the HTML maxlength attributes.
LIMITS = {"name": 100, "reg_number": 30, "title": 150, "url": 500}

app = Flask(__name__)
# Needed for flash messages. Set SECRET_KEY in the environment for production.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
# Path (or SQLite URI, e.g. "file:name?mode=memory&cache=shared") of the database.
# Tests override this so they never touch the real submissions.db.
app.config["DATABASE"] = DEFAULT_DATABASE


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------
def get_db():
    """Return a per-request SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"], uri=True)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the submissions table if it does not already exist."""
    with sqlite3.connect(app.config["DATABASE"], uri=True) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                reg_number TEXT NOT NULL,
                title      TEXT NOT NULL,
                url        TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def is_valid_url(value):
    """True only for well-formed http:// or https:// links."""
    if any(ch.isspace() for ch in value):
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname)
    except ValueError:
        return False


def validate_submission(form):
    """Return (cleaned_data, errors) for a submitted form."""
    labels = {
        "name": "Student name",
        "reg_number": "Registration number",
        "title": "Assignment title",
        "url": "Submission URL",
    }
    data = {key: (form.get(key) or "").strip() for key in labels}
    errors = []

    for key, label in labels.items():
        if not data[key]:
            errors.append(f"{label} is required.")
        elif len(data[key]) > LIMITS[key]:
            errors.append(f"{label} must be {LIMITS[key]} characters or fewer.")

    if data["url"] and len(data["url"]) <= LIMITS["url"] and not is_valid_url(data["url"]):
        errors.append(
            "Submission URL must be a valid link starting with http:// or https://."
        )

    return data, errors


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
def fetch_submissions():
    return get_db().execute(
        "SELECT id, name, reg_number, title, url, created_at "
        "FROM submissions ORDER BY id DESC"
    ).fetchall()


@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html", submissions=fetch_submissions(), form={}, limits=LIMITS
    )


@app.route("/submit", methods=["POST"])
def submit():
    data, errors = validate_submission(request.form)

    if errors:
        for message in errors:
            flash(message, "danger")
        # Re-render with what the student typed so nothing has to be retyped.
        return (
            render_template(
                "index.html",
                submissions=fetch_submissions(),
                form=data,
                limits=LIMITS,
            ),
            400,
        )

    db = get_db()
    db.execute(
        "INSERT INTO submissions (name, reg_number, title, url) VALUES (?, ?, ?, ?)",
        (data["name"], data["reg_number"], data["title"], data["url"]),
    )
    db.commit()

    flash("Assignment submitted successfully.", "success")
    return redirect(url_for("index"))


# Create the database on import so it works under `flask run` and `python app.py`.
init_db()

if __name__ == "__main__":
    app.run(debug=True)