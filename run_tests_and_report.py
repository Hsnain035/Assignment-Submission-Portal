"""Run pytest (or read an existing JUnit XML file), build a structured JSON test
report, and POST it to the report receiver.

Usage
    python run_tests_and_report.py                    # run test_app.py, then report
    python run_tests_and_report.py -q -k submit       # extra options go to pytest
    python run_tests_and_report.py --skip-run --junit-file report.xml
                                                      # report on a finished run (used by CI)

Environment variables
    REPORT_RECEIVER_URL   full URL to POST to, e.g. http://127.0.0.1:5001/report
                          (if unset, the report is built but not sent)
    REPORT_TOKEN          optional; sent as the X-Report-Token header

Git/GitHub metadata comes from the standard GitHub Actions variables
(GITHUB_REPOSITORY, GITHUB_REF_NAME, GITHUB_SHA, GITHUB_RUN_ID) and falls back
to the local git repository when run on your own machine.

Exit code: pytest's exit code when this script ran pytest, otherwise 0. A failure
to deliver the report prints a warning but never changes the exit code.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

MAX_MESSAGE_CHARS = 2000


# --------------------------------------------------------------------------
# Metadata
# --------------------------------------------------------------------------
def _git(*args):
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10, check=True
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def collect_metadata():
    """Repository, branch, commit, run id and timestamp for this execution."""
    repository = (
        os.environ.get("GITHUB_REPOSITORY")
        or _git("config", "--get", "remote.origin.url")
        or os.path.basename(os.getcwd())
    )
    branch = (
        os.environ.get("GITHUB_REF_NAME")
        or _git("rev-parse", "--abbrev-ref", "HEAD")
        or "unknown"
    )
    commit_sha = os.environ.get("GITHUB_SHA") or _git("rev-parse", "HEAD") or "unknown"
    run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{int(time.time())}"
    timestamp = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    return {
        "repository": repository,
        "branch": branch,
        "commit_sha": commit_sha,
        "run_id": run_id,
        "timestamp": timestamp,
    }


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------
def parse_junit(path):
    """Return a list of per-test dicts, or [] if the file is missing/unreadable."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return []

    tests = []
    for case in root.iter("testcase"):
        classname = case.get("classname") or ""
        name = f"{classname}.{case.get('name')}" if classname else case.get("name", "")

        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        skipped = case.find("skipped")

        if problem is not None:
            status = "failed"
            detail = (problem.get("message") or "").strip()
            body = (problem.text or "").strip()
            message = "\n".join(part for part in (detail, body) if part)
            message = message[:MAX_MESSAGE_CHARS] or "Test failed."
        elif skipped is not None:
            status = "skipped"
            message = (skipped.get("message") or "").strip() or None
        else:
            status = "passed"
            message = None

        tests.append({"name": name, "status": status, "message": message})
    return tests


def build_report(tests):
    passed = sum(t["status"] == "passed" for t in tests)
    failed = sum(t["status"] == "failed" for t in tests)
    skipped = sum(t["status"] == "skipped" for t in tests)

    if not tests:
        status = "error"  # no results at all: pytest crashed or never ran
    elif failed:
        status = "failed"
    else:
        status = "passed"

    return {
        **collect_metadata(),
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "status": status,
        "tests": tests,
    }


# --------------------------------------------------------------------------
# Delivery
# --------------------------------------------------------------------------
def _annotate(level, message):
    """Print a GitHub Actions annotation in CI, a plain line elsewhere."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{level}::{message}")
    else:
        print(f"[{level}] {message}")


def send_report(report, url, attempts=3):
    body = json.dumps(report).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("REPORT_TOKEN")
    if token:
        headers["X-Report-Token"] = token

    last_error = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                print(f"[+] Report delivered (HTTP {response.status}).")
                return True
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code} {exc.reason}"
            if exc.code < 500:  # client errors will not fix themselves on retry
                break
        except (urllib.error.URLError, OSError) as exc:
            last_error = str(getattr(exc, "reason", exc))
        if attempt < attempts:
            time.sleep(2 * attempt)

    _annotate("warning", f"Could not deliver test report to receiver: {last_error}")
    return False


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "pytest_args", nargs="*",
        help="targets passed to pytest (default: test_app.py); "
             "unrecognised options such as -q or -k are passed through too",
    )
    parser.add_argument("--junit-file", default="report.xml",
                        help="JUnit XML file to write (or read with --skip-run)")
    parser.add_argument("--output", metavar="FILE",
                        help="also write the JSON report to this file (e.g. for emailing)")
    parser.add_argument("--skip-run", action="store_true",
                        help="do not run pytest; report on an existing JUnit XML file")
    args, extra = parser.parse_known_args()
    pytest_args = args.pytest_args + extra or ["test_app.py"]

    exit_code = 0
    if not args.skip_run:
        if os.path.exists(args.junit_file):
            os.remove(args.junit_file)  # never report on a stale file
        command = [sys.executable, "-m", "pytest", *pytest_args,
                   f"--junitxml={args.junit_file}"]
        exit_code = subprocess.run(command).returncode

    report = build_report(parse_junit(args.junit_file))
    print(
        f"Report: {report['status'].upper()} - {report['passed']} passed, "
        f"{report['failed']} failed, {report['skipped']} skipped "
        f"of {report['total']} total"
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    url = os.environ.get("REPORT_RECEIVER_URL", "").strip()
    if url:
        send_report(report, url)
    else:
        _annotate("notice", "REPORT_RECEIVER_URL is not set; report was not sent.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
