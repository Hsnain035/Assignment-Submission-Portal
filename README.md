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
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Single page: header, form, submissions table
├── README.md
├── .gitignore
└── submissions.db      # Created automatically on first run (not committed)
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

> **PLACEHOLDER: to be completed in a later step.**
>
> This section will explain how to install any test dependencies, run the automated
> test suite, and read the results.
>
> - [ ] Test dependencies
> - [ ] Command to run the tests
> - [ ] What the tests cover
> - [ ] How to interpret the output

## Starting the Local Report Receiver

> **PLACEHOLDER: to be completed in a later step.**
>
> This section will explain what the local report receiver is, how to start it, and how
> it works together with the test run.
>
> - [ ] What the report receiver does
> - [ ] Command to start it
> - [ ] Port and address it listens on
> - [ ] How to confirm it is receiving reports

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `python: command not found` | Use `python3`, or install Python from https://www.python.org/downloads/ |
| `ModuleNotFoundError: No module named 'flask'` | The virtual environment is not active, or dependencies are not installed. Activate it and run `pip install -r requirements.txt`. |
| `Address already in use` | Another program is using port 5000. Stop it, or run on another port with `flask --app app run --port 5001`. |
| Page looks unstyled | Bootstrap loads from a CDN. Check your internet connection. |
| Flash messages do not appear | Cookies may be blocked in your browser. Allow cookies for `127.0.0.1`. |
| Submission rejected as an invalid URL | The link must begin with `http://` or `https://` and contain no spaces. |
