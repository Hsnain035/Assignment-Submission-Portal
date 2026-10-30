# Demonstration and Submission Guide

A checklist for the Step 5 demonstration, the bonus tasks, and what to submit.
Commands assume a terminal opened in the project folder.

## A. One-time setup

1. **Create the GitHub repository** and push this project to it (branch `main`).
2. **Start the receiver** (terminal 1) and leave it running:
   ```bash
   export REPORT_TOKEN="pick-a-long-random-string"     # Windows PowerShell: $env:REPORT_TOKEN = "..."
   python receiver.py
   ```
3. **Start a tunnel** (terminal 2) and leave it running:
   ```bash
   ngrok http 5001          # or: cloudflared tunnel --url http://127.0.0.1:5001
   ```
   Copy the public `https://...` address it prints.
4. **Add repository secrets** (Settings > Secrets and variables > Actions):

   | Secret | Value |
   |---|---|
   | `REPORT_RECEIVER_URL` | tunnel address + `/report` |
   | `REPORT_TOKEN` | the same string you used in step 2 |
   | `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_TO` | for the email bonus (see README) |
   | `SMTP_HOST`, `SMTP_PORT`, `EMAIL_FROM` | optional; defaults are `smtp.gmail.com`, `587`, and your username |

5. **Enable GitHub Pages** (Settings > Pages > Source: **GitHub Actions**).

## B. The three demonstration runs

For each run, capture the evidence listed. The receiver also keeps a copy of every report in
`report-history/`, so the passing and failing files are both preserved even though
`test-report.json` is overwritten each time.

### Run 1: passing

```bash
git add . && git commit -m "Initial portal with tests and CI" && git push origin main
```

Show: Actions run with green tests; receiver console `[+] Report saved to test-report.json`;
`test-report.json` with `"status": "passed"`; the deployed Pages site; the email.

### Run 2: introduce a defect, failing

In `app.py`, inside `is_valid_url`, replace the line

```python
        return parsed.scheme in ("http", "https") and bool(parsed.hostname)
```

with

```python
        return True
```

Then:

```bash
git commit -am "Break URL validation (intentional defect)" && git push origin main
```

Show: the **Run tests** step failing (red) and the job failing; `test_invalid_url_is_rejected`
reported as failed; `test-report.json` now with `"status": "failed"`, `"failed": 1` and the
failure message; the **Deploy** job *skipped*, with the Pages site still showing the earlier
version; the failure email.

### Run 3: fix the defect, passing again

Restore the original line, then:

```bash
git commit -am "Fix URL validation" && git push origin main
```

Show: green run, `test-report.json` back to `"status": "passed"`, Deploy job runs again, email received.

## C. Evidence checklist

- [ ] Screenshot of the Actions run list showing pass, fail, pass
- [ ] Screenshot of the failing **Run tests** step and the skipped **Deploy** job
- [ ] `test-report.json` after each run (or the files in `report-history/`)
- [ ] Receiver console output showing each `[+] Report saved` line
- [ ] Deployed Pages URL (shown in the Deploy job and in Settings > Pages)
- [ ] Screenshot of a passing-run email and a failing-run email (including the attachment)

## D. Submission checklist

- [ ] GitHub repository URL
- [ ] Setup instructions (the README)
- [ ] Evidence for the passing, failing, and corrected runs
- [ ] Pages URL and email evidence (bonus tasks)

## E. Tips for the viva

- Know why `needs: test` stops deployment when a test fails.
- Know why the report step uses `if: always()` and why the test step still fails the job.
- Know why a tunnel is needed: the GitHub runner's `localhost` is the runner, not your computer.
- Keep the receiver and tunnel running for the whole demonstration. Free tunnel addresses change when
  restarted, so update the `REPORT_RECEIVER_URL` secret if you restart the tunnel.
