# GroundTrack MVP Security and Demo Verification

## Purpose

Use this checklist before a public demo, temporary hosted demo, or local event
use. It verifies GroundTrack's limited MVP posture without claiming production
security features that the app does not provide.

GroundTrack is a local-first, offline-capable MVP. A temporary hosted demo is
for demonstration only and is not a production deployment.

## Before verification

- Use a fresh checkout or disposable working copy.
- Use fake or explicitly approved sample participant data.
- Do not copy a live event database, registration spreadsheet, or export into
  the verification copy.
- Stop and remove public access to a temporary demo when the demonstration is
  complete.

## Verification checklist

| Check | How to verify | Expected result | Pass |
|---|---|---|:---:|
| Demo data is safe | Review every imported participant, walk-up, screenshot, database, and export prepared for the demo. | All participant details are fake or explicitly approved sample data. No real participant data is used in a public demo. | ☐ |
| Hosting posture is stated accurately | Review demo notes and what presenters tell viewers. | The temporary hosted demo is described as a non-production demonstration. No production-readiness claim is made. | ☐ |
| MVP remains local-first | Start the app and perform the core smoke test from `docs/mvp_smoke_test.md` on the local machine. | Core workflows run locally. Temporary demo hosting has not become an MVP runtime requirement. | ☐ |
| No SQLite data is tracked | Run `git ls-files '*.db' '*.sqlite' '*.sqlite3'`. | The command returns no files. | ☐ |
| No uploaded data is tracked | Run `git ls-files uploads` and inspect any result. | Only `uploads/.gitkeep` may be listed. No uploaded spreadsheet or participant data is tracked. | ☐ |
| No spreadsheet or export is tracked | Run `git ls-files '*.csv' '*.xlsx'`. | The command returns no files. Generated CSV exports and spreadsheet data remain untracked. | ☐ |
| Ignore rules protect local artifacts | Run `git check-ignore -v instance/test.sqlite uploads/test.xlsx test_export.csv test_data.xlsx .venv/bin/python __pycache__/app.cpython-312.pyc`. | Every test path is matched by an ignore rule. Do not create these files just to run the check. | ☐ |
| No CDN or remote asset is required | Inspect `templates/`, `static/`, and `app.py` for remote script, stylesheet, font, image, or API URLs. Then repeat the MVP smoke test without internet access. | Pages use local assets and core workflows work without a CDN, remote API, internet font, or other hosted asset. | ☐ |
| Dependencies remain local and small | Review `requirements.txt` and installed runtime configuration. | The MVP requires no cloud SDK, remote database, external authentication provider, or hosted service. | ☐ |
| Authentication claims stay in scope | Review demo notes, page copy, and presenter language. | The MVP is described as having no login, authentication, roles, or production access control. Nobody implies otherwise. | ☐ |
| Scanner behavior stays simple | Scan a fake badge with the supported scanner or type the same value into the Scan field. | The scanner behaves as keyboard input only. No badge hardware integration or hardware-security claim is made. | ☐ |
| No cloud dependency is required | Disconnect internet access while keeping the local Flask server running, then repeat a scan, walk-up creation, report view, and CSV export. | The workflows continue locally with SQLite and local assets. | ☐ |

## Repository check

Before sharing or committing changes, run:

```sh
git status --short
git diff --check
git ls-files '*.db' '*.sqlite' '*.sqlite3' '*.csv' '*.xlsx'
git ls-files uploads
```

Review `git status --short` manually. Do not stage or commit:

- `AGENTS.md`
- `.venv/`, Python cache files, or test caches
- SQLite database files
- uploaded or imported spreadsheets
- generated CSV or XLSX exports
- environment files, logs, or other local event data

The expected `git ls-files uploads` result is only `uploads/.gitkeep`. The
other `git ls-files` command should return no output.

## Verification notes

| Date | Reviewer | Local or temporary demo | Result | Notes or follow-up issue |
|---|---|---|---|---|
|  |  |  | Pass / Fail |  |

Record failures without including participant data, credentials, private URLs,
or screenshots containing sensitive information.

## Scope boundaries

- This checklist does not add or certify authentication, authorization,
  encryption, audit controls, internet exposure controls, or production
  hosting security.
- Temporary hosting for a controlled demo does not make the MVP production
  ready.
- Production hosting or use with real participant data requires a separate
  security, privacy, access-control, retention, backup, and deployment review.
- GroundTrack's current MVP direction remains local-first unless a customer
  requests and approves a separately scoped hosted version.
