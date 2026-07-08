# GroundTrack MVP Smoke Test

## Purpose

Use this checklist before a customer demo or local event to confirm the core
GroundTrack operator workflows work together. Run it with fake or approved
sample data only.

## Pre-test setup

1. Use a fresh checkout or other disposable copy of GroundTrack.
2. Create and activate a Python virtual environment.
3. Install the local dependencies:

   ```sh
   python3 -m pip install -r requirements.txt
   ```

4. Protect any existing event data. If `instance/groundtrack.sqlite` exists,
   move it to a safe backup location before continuing. Do not use a live event
   database for this smoke test.
5. Initialize a fresh local database:

   ```sh
   flask --app app init-db
   ```

6. Prepare a small `.xlsx` workbook containing fake participants and the
   columns listed on the Import page. Include at least one participant with a
   known, unique badge number.
7. Start GroundTrack:

   ```sh
   flask --app app run
   ```

8. Open the local address shown by Flask, normally
   `http://127.0.0.1:5000`.

Record the fake names and badge numbers used during the test so scan and report
results can be checked accurately.

## Smoke test checklist

| # | Scenario | Steps | Expected result | Pass |
|---:|---|---|---|:---:|
| 1 | App starts locally | Start GroundTrack with `flask --app app run` and open the local address. | The app starts without an error and the Dashboard loads. | ☐ |
| 2 | Dashboard counts and quick links | Review the Dashboard before and after adding participants. Open each quick link. | Counts match the current fake records. Links open Scan, Participants, Walk-Up, On-Ground Report, Import, and CSV export. | ☐ |
| 3 | Import Spreadsheet page | Open **Import Spreadsheet**, select the fake `.xlsx` workbook, and import it. | The page loads, the import finishes, and a clear summary reports imported and skipped entries. | ☐ |
| 4 | Participants empty and populated states | View Participants before adding data, then view it after the import or a walk-up creation. | The empty state explains how to add participants. The populated table shows the expected fake participant details and status. | ☐ |
| 5 | Walk-up required-field validation | Submit the Walk-Up form with required fields missing. | The participant is not created and the message names the required fields. | ☐ |
| 6 | Walk-up without immediate check-in | Add a fake walk-up with a unique badge and leave **Check in now** clear. | The success message says the participant was added and is not checked in. The participant status is **Not Checked In**. | ☐ |
| 7 | Walk-up with immediate check-in | Add another fake walk-up with a unique badge and select **Check in now**. | The success message says the participant was added and checked in. The participant appears on the On-Ground Report. | ☐ |
| 8 | Scan check-in for known badge | On Scan, enter a known badge belonging to a participant who is not checked in and choose **Check In**. | A clear checked-in message appears. Dashboard and report counts update. | ☐ |
| 9 | Scan check-out for on-ground badge | Enter the badge of an on-ground participant and choose **Check Out**. | A clear checked-out message appears. The participant no longer appears on the On-Ground Report. | ☐ |
| 10 | Unknown badge scan | Enter a fake badge that does not exist and choose either scan action. | The message says the badge was not found and asks the operator to check it and try again. | ☐ |
| 11 | Duplicate walk-up badge | Try to add a walk-up using a badge already assigned to another participant. | The participant is not created. The message says the badge is already in use and asks for a different badge. | ☐ |
| 12 | On-Ground Report empty and populated states | Check the report when nobody is checked in. Then check in a known participant and reload it. | The empty state says nobody is currently on ground. The populated state shows only currently checked-in participants. | ☐ |
| 13 | Export current on-ground CSV | From the Dashboard or On-Ground Report, select **Export CSV**. Open `on_ground_report.csv`. Repeat when the report is empty if practical. | The file downloads with the expected headers and only current on-ground participants. An empty export contains headers only. | ☐ |
| 14 | Demo data safety | Review the imported workbook, walk-ups, displayed pages, and exported CSV. | All names, organizations, badges, and other details are fake or approved sample data. | ☐ |
| 15 | Offline/local-first operation | Disconnect from the internet or disable network access, keep the local Flask server running, and repeat page navigation plus a scan action. | Core workflows and local styling continue to work. No CDN, cloud service, remote API, internet font, or hosted asset is required. | ☐ |

## Pass/fail notes

| Date | Tester | Environment | Result | Notes or follow-up issue |
|---|---|---|---|---|
|  |  |  | Pass / Fail |  |

For a failed scenario, record the exact step, operator-visible message, and
whether retrying changed the result. Do not include real participant data,
credentials, or other sensitive information in notes or screenshots.

## Known demo limitations

- A temporary hosted demo is not a production deployment.
- The MVP has no login or authentication.
- Public demos must use fake or approved sample data only.
- The current production direction is local-first unless the customer requests
  a hosted version.
- Multi-visit and lost badge workflows are tracked separately in Milestone 7.
