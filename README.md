# Assignment Submission Portal

A small web application where students submit the link to a completed assignment and
see every saved submission in one place. Built with Python, Flask, SQLite, and Bootstrap 5.

## Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installing Dependencies](#installing-dependencies)
- [Running the Application](#running-the-application)
- [Using the Portal](#using-the-portal)
- [Configuration](#configuration)
- [Executing Automated Tests](#executing-automated-tests)
- [Starting the Local Report Receiver](#starting-the-local-report-receiver)
- [Bonus: Conditional Deployment to GitHub Pages](#bonus-conditional-deployment-to-github-pages)
- [Bonus: Email Report](#bonus-email-report)
- [Troubleshooting](#troubleshooting)

## Features

- Submission form with Student Name, Registration Number, Assignment Title, and Submission URL
- Server-side validation: every field is required, values are trimmed and length-limited,
  and the URL must start with `http://` or `https://` and include a host
- Browser-side `required` checks as a first line of defense
- Flash messages for validation errors and success confirmations
- Submissions saved to a local SQLite database (`submissions.db`) so they persist between runs
- Responsive Bootstrap 5 interface (loaded from a CDN) with submission URLs shown as clickable links

## Project Structure

```
assignment-portal/
├── app.py              # Flask app: database setup, validation, routes
├── requirements.txt    # Python dependencies (Flask, pytest)
├── test_app.py         # Automated tests (pytest)
├── receiver.py         # Local report receiver (POST /report, port 5001)
├── run_tests_and_report.py  # Runs pytest, builds and sends the JSON report
├── send_email_report.py     # Bonus: emails the report
├── demo/
│   └── index.html      # Bonus: static demo published to GitHub Pages
├── DEMO.md             # Demonstration and submission checklist
├── .github/workflows/
│   └── ci.yml          # GitHub Actions pipeline
├── templates/
│   └── index.html      # Single page: header, form, submissions table
├── README.md
├── .gitignore
├── submissions.db      # Created automatically on first run (not committed)
├── test-report.json    # Written by receiver.py when a report arrives (not committed)
└── report-history/     # Timestamped copy of every received report (not committed)
```

## Prerequisites

- **Python 3.8 or newer.** Check with `python --version` (or `python3 --version`).
- **pip**, which is included with current Python installs.
- An internet connection when viewing the page, because Bootstrap is loaded from a CDN.

## Installing Dependencies

Using a virtual environment keeps this project's packages separate from the rest of your system.

1. **Open a terminal in the project folder** (the folder containing `app.py`).

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   ```

   On some systems the command is `python3 -m venv venv`.

3. **Activate it:**

   | Platform | Command |
   |---|---|
   | macOS / Linux | `source venv/bin/activate` |
   | Windows (Command Prompt) | `venv\Scripts\activate.bat` |
   | Windows (PowerShell) | `venv\Scripts\Activate.ps1` |

   Your prompt should now start with `(venv)`.

   > PowerShell may block the activation script. If so, run
   > `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

4. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

5. **Confirm Flask is installed:**

   ```bash
   python -c "import flask; print(flask.__version__)"
   ```

## Running the Application

With the virtual environment active, start the app from the project folder:

```bash
python app.py
```

The first run creates `submissions.db` automatically. You should see output similar to:

```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

Open **http://127.0.0.1:5000** in your browser. Press `Ctrl+C` in the terminal to stop the server.

### Alternative: the Flask command

```bash
flask --app app run --debug
```

To use a different port (for example, if 5000 is already taken):

```bash
flask --app app run --debug --port 5001
```

> `app.py` runs in debug mode when started with `python app.py`. Debug mode is for local
> development only. Do not expose it on a public network.

## Using the Portal

1. Fill in all four fields on the left: Student Name, Registration Number,
   Assignment Title, and Submission URL.
2. Select **Submit assignment**.
3. On success, a green message appears and the new entry shows at the top of the
   Submissions table. On failure, a red message explains what to fix and your
   entries stay in the form.

Submission URLs open in a new tab when clicked.

### Resetting the data

Stop the app and delete `submissions.db`. A fresh, empty database is created the next time you start it.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Signs the session cookie used by flash messages | `dev-only-change-me` |

Set a strong, private value before deploying anywhere beyond your own machine:

```bash
# macOS / Linux
export SECRET_KEY="replace-with-a-long-random-string"

# Windows PowerShell
$env:SECRET_KEY = "replace-with-a-long-random-string"
```

## Executing Automated Tests

The tests live in `test_app.py` and use [pytest](https://docs.pytest.org/). They run against a
private in-memory SQLite database, so your real `submissions.db` is never changed.

1. Activate your virtual environment and install dependencies (this includes pytest):

   ```bash
   pip install -r requirements.txt
   ```

2. Run the tests from the project folder:

   ```bash
   pytest test_app.py
   ```

   Add `-v` for one line per test. A passing run ends with `3 passed`.

### What the tests cover

| Test | Checks |
|---|---|
| `test_valid_submission_is_saved` | A complete form with a valid URL redirects, is stored in the database, and appears on the page as a clickable link with a success message |
| `test_missing_registration_number_is_rejected` | A blank registration number returns a validation message (HTTP 400) and nothing is saved |
| `test_invalid_url_is_rejected` | A URL such as `not-a-url` returns a validation message (HTTP 400) and nothing is saved |

### Continuous integration

`.github/workflows/ci.yml` runs `pytest test_app.py` on GitHub Actions for every push to any
branch, then forwards a JSON report to the receiver (see below). Results appear in the
repository's **Actions** tab.

## Starting the Local Report Receiver

`receiver.py` is a small HTTP server that collects test reports sent by the CI pipeline
(or by you, locally) and saves the most recent one, pretty-printed, to `test-report.json`
in the folder you start it from. It uses only the Python standard library, so there is
nothing extra to install.

### 1. Start the receiver

In a **second terminal** (the Flask app keeps running in the first), from the project folder:

```bash
python receiver.py
```

```
Report receiver listening on http://127.0.0.1:5001/report
Saving the latest report to /path/to/assignment-portal/test-report.json
Press Ctrl+C to stop.
```

It listens on port **5001**, because `app.py` already uses 5000. Confirm it is running:

```bash
curl http://127.0.0.1:5001/health     # {"status": "ok"}
```

Optional settings (environment variables): `RECEIVER_PORT`, `RECEIVER_HOST`, and
`REPORT_TOKEN` (if set, senders must include a matching `X-Report-Token` header).

### 2. Send a report from your own machine

`run_tests_and_report.py` runs pytest, builds the JSON report, and POSTs it to the receiver:

```bash
# macOS / Linux
export REPORT_RECEIVER_URL=http://127.0.0.1:5001/report
python run_tests_and_report.py

# Windows PowerShell
$env:REPORT_RECEIVER_URL = "http://127.0.0.1:5001/report"
python run_tests_and_report.py
```

The receiver prints a confirmation and writes the file:

```
[+] Report saved to test-report.json
    owner/assignment-portal @ main (0123456) run local-1767000000: PASSED (3/3 passed, 0 failed)
```

The script exits with pytest's exit code, so a failing test still fails the command. If the
receiver cannot be reached, it prints a warning but does not change that exit code.

### 3. Send reports from GitHub Actions

GitHub's servers cannot reach `127.0.0.1` on your computer, so the receiver must be exposed
through a public tunnel while the pipeline runs. Any tunnel tool works, for example:

```bash
ngrok http 5001
# or
cloudflared tunnel --url http://127.0.0.1:5001
```

Copy the public `https://...` address the tool prints, then in your GitHub repository go to
**Settings > Secrets and variables > Actions > New repository secret** and add:

| Secret | Value |
|---|---|
| `REPORT_RECEIVER_URL` | The tunnel address plus `/report`, e.g. `https://abc123.ngrok-free.app/report` |
| `REPORT_TOKEN` *(recommended)* | Any long random string. Start the receiver with the same value in `REPORT_TOKEN` |

Because the tunnel address is public, setting `REPORT_TOKEN` stops other people from posting
reports to your receiver. Free tunnel addresses usually change each time you restart the tool,
so update the secret when that happens.

Then push a commit. The **Send test report** step in `.github/workflows/ci.yml` runs after the
tests, always, whether they passed or failed, and the job still fails if any test failed.

### Report format

```json
{
  "repository": "owner/assignment-portal",
  "branch": "main",
  "commit_sha": "0123456789abcdef0123456789abcdef01234567",
  "run_id": "424242",
  "timestamp": "2026-10-29T15:01:06Z",
  "total": 3,
  "passed": 2,
  "failed": 1,
  "skipped": 0,
  "status": "failed",
  "tests": [
    { "name": "test_app.test_valid_submission_is_saved", "status": "passed", "message": null },
    { "name": "test_app.test_invalid_url_is_rejected", "status": "failed", "message": "AssertionError: ..." }
  ]
}
```

- `status` is `passed`, `failed`, or `error` (no test results were produced at all, for
  example when dependencies failed to install).
- Each test's `status` is `passed`, `failed`, or `skipped`; `message` holds the failure
  message for failed tests and is `null` otherwise.
- The receiver answers `400` with a list of problems if a required field is missing or
  has the wrong type, and `401` if a token is required and wrong.

## Bonus: Conditional Deployment to GitHub Pages

The `deploy` job in `.github/workflows/ci.yml` publishes the static demo in `demo/` to
GitHub Pages. `demo/index.html` is a browser-only version of the portal that uses the same
validation rules; its submissions are stored in the visitor's browser (localStorage), because
GitHub Pages cannot run the Flask backend.

How the conditions work:

- `needs: test` means the deploy job runs only if the test job finished successfully. If any
  test fails, deployment is **skipped** and the previously published site stays unchanged.
- `if: github.ref == 'refs/heads/main'` limits deployment to pushes to `main`.

One-time setup: in the repository go to **Settings > Pages** and set **Source** to
**GitHub Actions**. After the first successful push to `main`, the site is available at
`https://<your-username>.github.io/<repository-name>/` (the exact URL is also shown in the
deploy job's summary).

## Bonus: Email Report

After every run, passing or failing, the **Email test report** step runs
`send_email_report.py`. The email subject shows the result, and the body lists the commit,
branch, run ID, overall result, total/passed/failed counts, and each test's result with failure
messages. The full report is attached as `test-report.json`.

Add these as repository secrets (**Settings > Secrets and variables > Actions**):

| Secret | Required | Example / note |
|---|---|---|
| `SMTP_USERNAME` | yes | `yourname@gmail.com` |
| `SMTP_PASSWORD` | yes | For Gmail, a 16-character **app password** (requires 2-step verification), not your normal password |
| `EMAIL_TO` | yes | Recipient address; separate several with commas |
| `SMTP_HOST` | no | Default `smtp.gmail.com` |
| `SMTP_PORT` | no | Default `587` (STARTTLS); `465` uses SSL |
| `EMAIL_FROM` | no | Default: `SMTP_USERNAME` |

Credentials live only in repository secrets, never in the code. If the secrets are missing, the
step prints a notice and is skipped. If sending fails, it prints a warning and the job result is
still decided only by the tests.

To try it from your own machine, with a report file such as `report.json` made by
`python run_tests_and_report.py --output report.json`:

```bash
export SMTP_USERNAME=... SMTP_PASSWORD=... EMAIL_TO=...
python send_email_report.py --report report.json
```

See `DEMO.md` for the full demonstration and submission checklist.

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `python: command not found` | Use `python3`, or install Python from https://www.python.org/downloads/ |
| `ModuleNotFoundError: No module named 'flask'` | The virtual environment is not active, or dependencies are not installed. Activate it and run `pip install -r requirements.txt`. |
| `Address already in use` | Another program is using port 5000. Stop it, or run on another port with `flask --app app run --port 5001`. |
| Receiver says `Address already in use` | Something else is on port 5001. Set `RECEIVER_PORT` to another port and update your URL to match. |
| CI runs but no report arrives | The `REPORT_RECEIVER_URL` secret must be a public tunnel URL ending in `/report`, and the receiver and tunnel must be running. Check the **Send test report** step log for a warning. |
| Deploy job did not run | It runs only on pushes to `main` and only when tests pass. Also check Settings > Pages > Source is set to GitHub Actions. |
| No email arrived | Check the **Email test report** step log. For Gmail use an app password, and look in spam. |
| Page looks unstyled | Bootstrap loads from a CDN. Check your internet connection. |
| Flash messages do not appear | Cookies may be blocked in your browser. Allow cookies for `127.0.0.1`. |
| Submission rejected as an invalid URL | The link must begin with `http://` or `https://` and contain no spaces. |
