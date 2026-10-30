"""Email the JSON test report produced by run_tests_and_report.py.

Usage
    python send_email_report.py [--report report.json]

Configuration (environment variables; in GitHub Actions use repository secrets)
    SMTP_USERNAME   login for the SMTP server (required)
    SMTP_PASSWORD   password or app password  (required)
    EMAIL_TO        recipient address(es), comma-separated (required)
    SMTP_HOST       default smtp.gmail.com
    SMTP_PORT       default 587 (STARTTLS); 465 uses implicit SSL
    EMAIL_FROM      default: SMTP_USERNAME

If the required settings are missing the script prints a notice and exits 0.
A delivery failure prints a warning and exits 0, so email problems never change
whether the pipeline passes or fails.
"""

import argparse
import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage

MAX_DETAIL_CHARS = 400


def _annotate(level, message):
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{level}::{message}")
    else:
        print(f"[{level}] {message}")


def run_url(report):
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo and str(report.get("run_id", "")).isdigit():
        return f"{server}/{repo}/actions/runs/{report['run_id']}"
    return None


def format_body(report):
    lines = [
        f"Overall result: {str(report.get('status', 'unknown')).upper()}",
        f"Repository:     {report.get('repository')}",
        f"Branch:         {report.get('branch')}",
        f"Commit:         {report.get('commit_sha')}",
        f"Run ID:         {report.get('run_id')}",
        f"Timestamp:      {report.get('timestamp')}",
    ]
    url = run_url(report)
    if url:
        lines.append(f"Run URL:        {url}")
    lines += [
        "",
        f"Total: {report.get('total')}   Passed: {report.get('passed')}   "
        f"Failed: {report.get('failed')}   Skipped: {report.get('skipped', 0)}",
        "",
        "Test results:",
    ]
    for test in report.get("tests", []):
        label = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}.get(
            test.get("status"), "????"
        )
        lines.append(f"  [{label}] {test.get('name')}")
        if test.get("status") == "failed" and test.get("message"):
            detail = test["message"][:MAX_DETAIL_CHARS]
            lines += [f"         {line}" for line in detail.splitlines()]
    if not report.get("tests"):
        lines.append("  (no test results were produced)")
    lines += ["", "The full report is attached as test-report.json."]
    return "\n".join(lines)


def build_message(report, sender, recipient):
    message = EmailMessage()
    sha = str(report.get("commit_sha", ""))[:7]
    message["Subject"] = (
        f"[{str(report.get('status', 'unknown')).upper()}] "
        f"{report.get('repository')} @ {report.get('branch')} ({sha}) - "
        f"{report.get('passed')}/{report.get('total')} tests passed"
    )
    message["From"] = sender
    message["To"] = recipient
    message.set_content(format_body(report))
    message.add_attachment(
        (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
        maintype="application",
        subtype="json",
        filename="test-report.json",
    )
    return message


def send(message, host, port, username, password):
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=context)
            smtp.login(username, password)
            smtp.send_message(message)


def main():
    parser = argparse.ArgumentParser(description="Email the JSON test report.")
    parser.add_argument("--report", default="report.json", help="JSON report to send")
    args = parser.parse_args()

    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    recipient = os.environ.get("EMAIL_TO", "").strip()
    if not (username and password and recipient):
        _annotate("notice", "Email not configured (SMTP_USERNAME, SMTP_PASSWORD, EMAIL_TO); skipping.")
        return 0

    try:
        with open(args.report, encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        _annotate("warning", f"Cannot read {args.report}: {exc}")
        return 0

    host = os.environ.get("SMTP_HOST", "").strip() or "smtp.gmail.com"
    try:
        port = int(os.environ.get("SMTP_PORT", "").strip() or 587)
    except ValueError:
        _annotate("warning", "SMTP_PORT must be a number; skipping email.")
        return 0
    sender = os.environ.get("EMAIL_FROM", "").strip() or username

    try:
        send(build_message(report, sender, recipient), host, port, username, password)
    except (smtplib.SMTPException, OSError) as exc:
        _annotate("warning", f"Could not send email report: {exc}")
        return 0

    print(f"[+] Email report sent to {recipient}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
