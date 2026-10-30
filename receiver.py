"""Local report receiver.

A lightweight HTTP server that accepts CI test reports and saves the latest
one, pretty-printed, to test-report.json in the working directory.

    python receiver.py

Endpoints
    POST /report   accept a JSON test report (see REQUIRED FIELDS below)
    GET  /health   simple liveness check

Environment variables (all optional)
    RECEIVER_HOST   interface to bind to (default 127.0.0.1)
    RECEIVER_PORT   port to listen on     (default 5001, because app.py uses 5000)
    REPORT_TOKEN    if set, requests must send a matching X-Report-Token header
"""

import hmac
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("RECEIVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("RECEIVER_PORT", "5001"))
TOKEN = os.environ.get("REPORT_TOKEN")
REPORT_FILE = "test-report.json"
HISTORY_DIR = "report-history"
MAX_BODY_BYTES = 1_000_000

STRING_FIELDS = ("repository", "branch", "commit_sha", "timestamp")
COUNT_FIELDS = ("total", "passed", "failed")
OVERALL_STATUSES = {"passed", "failed", "error"}
TEST_STATUSES = {"passed", "failed", "skipped"}


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_report(payload):
    """Return a list of problems with the payload (empty list means valid)."""
    if not isinstance(payload, dict):
        return ["Payload must be a JSON object."]

    errors = []
    for key in STRING_FIELDS:
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            errors.append(f"'{key}' must be a non-empty string.")

    run_id = payload.get("run_id")
    if isinstance(run_id, bool) or not isinstance(run_id, (str, int)) or run_id == "":
        errors.append("'run_id' must be a non-empty string or integer.")

    for key in COUNT_FIELDS:
        if not _is_count(payload.get(key)):
            errors.append(f"'{key}' must be a non-negative integer.")

    if payload.get("status") not in OVERALL_STATUSES:
        errors.append(f"'status' must be one of {sorted(OVERALL_STATUSES)}.")

    tests = payload.get("tests")
    if not isinstance(tests, list):
        errors.append("'tests' must be an array.")
    else:
        for i, test in enumerate(tests):
            if not isinstance(test, dict):
                errors.append(f"tests[{i}] must be an object.")
                continue
            if not isinstance(test.get("name"), str) or not test["name"]:
                errors.append(f"tests[{i}].name must be a non-empty string.")
            if test.get("status") not in TEST_STATUSES:
                errors.append(f"tests[{i}].status must be one of {sorted(TEST_STATUSES)}.")
            message = test.get("message")
            if message is not None and not isinstance(message, str):
                errors.append(f"tests[{i}].message must be a string or null.")
    return errors


def save_report(payload):
    """Write the payload to test-report.json atomically, pretty-printed."""
    directory = os.getcwd()
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_path, os.path.join(directory, REPORT_FILE))
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def archive_report(payload):
    """Keep a timestamped copy of every report so earlier runs are not lost."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = re.sub(r"[^A-Za-z0-9._-]", "_", str(payload["run_id"]))[:40]
    name = f"{stamp}_{payload['status']}_run{run_id}.json"
    os.makedirs(HISTORY_DIR, exist_ok=True)
    shutil.copyfile(REPORT_FILE, os.path.join(HISTORY_DIR, name))
    return name


class ReportHandler(BaseHTTPRequestHandler):
    server_version = "ReportReceiver/1.0"

    def _send_json(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "Not found. Use POST /report."})

    def do_POST(self):
        if self.path != "/report":
            self._send_json(404, {"error": "Not found. Use POST /report."})
            return

        if TOKEN:
            supplied = self.headers.get("X-Report-Token", "")
            if not hmac.compare_digest(supplied, TOKEN):
                print("[!] Rejected report: missing or wrong X-Report-Token")
                self._send_json(401, {"error": "Invalid or missing X-Report-Token."})
                return

        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send_json(411, {"error": "Content-Length header is required."})
            return
        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "Payload too large."})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"[!] Rejected report: invalid JSON ({exc})")
            self._send_json(400, {"error": f"Invalid JSON: {exc}"})
            return

        errors = validate_report(payload)
        if errors:
            print(f"[!] Rejected report: {len(errors)} validation error(s)")
            self._send_json(400, {"error": "Invalid report.", "details": errors})
            return

        save_report(payload)
        print(f"[+] Report saved to {REPORT_FILE}")
        try:
            print(f"    Copy kept in {HISTORY_DIR}/{archive_report(payload)}")
        except OSError as exc:
            print(f"    (could not keep a history copy: {exc})")
        print(
            f"    {payload['repository']} @ {payload['branch']} "
            f"({payload['commit_sha'][:7]}) run {payload['run_id']}: "
            f"{payload['status'].upper()} "
            f"({payload['passed']}/{payload['total']} passed, {payload['failed']} failed)"
        )
        self._send_json(200, {"status": "received", "file": REPORT_FILE})

    def log_message(self, fmt, *args):
        # Keep the console readable: only our own [+] / [!] messages.
        pass


def main():
    server = ThreadingHTTPServer((HOST, PORT), ReportHandler)
    print(f"Report receiver listening on http://{HOST}:{PORT}/report")
    print(f"Saving the latest report to {os.path.join(os.getcwd(), REPORT_FILE)}")
    print(f"Keeping a copy of every report in {HISTORY_DIR}/")
    if TOKEN:
        print("X-Report-Token authentication is enabled.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
