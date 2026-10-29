"""Automated tests for the Assignment Submission Portal.

Tests run against an in-memory SQLite database, so the real
submissions.db is never read or modified.
"""

import sqlite3
import uuid

import pytest

import app as portal

VALID = {
    "name": "Ayesha Khan",
    "reg_number": "FA23-BSE-014",
    "title": "Software Project Management - Assignment 1",
    "url": "https://github.com/ayesha/spm-assignment-1",
}


@pytest.fixture
def client():
    """Flask test client wired to a private in-memory SQLite database.

    Plain ":memory:" gives every new connection its own empty database, and the
    app opens one connection per request. A named shared-cache in-memory
    database lets all connections see the same data. The `keeper` connection
    keeps it alive for the duration of the test and is also used for assertions.
    """
    uri = f"file:test_{uuid.uuid4().hex}?mode=memory&cache=shared"
    portal.app.config.update(TESTING=True, DATABASE=uri)

    keeper = sqlite3.connect(uri, uri=True)
    keeper.row_factory = sqlite3.Row
    portal.init_db()

    with portal.app.test_client() as test_client:
        test_client.db = keeper
        yield test_client

    keeper.close()
    portal.app.config["DATABASE"] = portal.DEFAULT_DATABASE


def count_rows(client):
    return client.db.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]


def test_valid_submission_is_saved(client):
    """Test Case 1: complete details and a valid URL are accepted and saved."""
    response = client.post("/submit", data=VALID)

    # Success redirects back to the main page.
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    # The record is stored in the database...
    assert count_rows(client) == 1
    row = client.db.execute("SELECT * FROM submissions").fetchone()
    assert row["name"] == VALID["name"]
    assert row["reg_number"] == VALID["reg_number"]
    assert row["title"] == VALID["title"]
    assert row["url"] == VALID["url"]

    # ...and shown on the page with a success message and a clickable link.
    page = client.get("/")
    assert b"Assignment submitted successfully." in page.data
    assert VALID["name"].encode() in page.data
    assert f'href="{VALID["url"]}"'.encode() in page.data


def test_missing_registration_number_is_rejected(client):
    """Test Case 2: a missing registration number is rejected and not saved."""
    data = {**VALID, "reg_number": ""}
    response = client.post("/submit", data=data)

    assert response.status_code == 400
    assert b"Registration number is required." in response.data
    assert count_rows(client) == 0


def test_invalid_url_is_rejected(client):
    """Test Case 3: a malformed submission URL is rejected and not saved."""
    data = {**VALID, "url": "not-a-url"}
    response = client.post("/submit", data=data)

    assert response.status_code == 400
    assert b"Submission URL must be a valid link" in response.data
    assert count_rows(client) == 0
