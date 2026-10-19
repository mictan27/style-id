# Runbook: calibration study (gates: LiDAR ≤ 1.5 cm, photo ≤ 2.5 cm MAE on chest and waist)

Goal: 60 to 100 adults, each measured once by tape and scanned on both paths, so a per-measurement correction can be trained and the body-fit gates checked.

## Before
- Legal review of body-data handling in the launch market; consent form; adults only.
- One trained measurer for the whole study, so tape error is consistent.
- Recruit a spread of heights and builds; log sex, age band and build notes, not names.

## Session (about 15 minutes per person)
1. Tape: height, neck, shoulder, chest, waist, hip, arm length, bicep, back length. Follow the illustrated guide. Enter into `tape.csv` (`subject_id, measurer, date, <nine fields>`).
2. LiDAR scan with the app on a Pro iPhone: phone propped at waist height 2 m away, fitted clothing, A-pose, slow 360° turn. Note anything unusual.
3. Photo scan on the same or a non-Pro iPhone: front and side with the timer, typed height.
4. Pull uncorrected scan measurements from the worker output into `scans.csv` (`subject_id, path, scan_id, <nine fields>`).

## After
```bash
uv run python -m styleid_calibration train    --tape tape.csv --scans scans.csv --path lidar --out correction_lidar.json
uv run python -m styleid_calibration train    --tape tape.csv --scans scans.csv --path photo --out correction_photo.json
uv run python -m styleid_calibration evaluate --tape tape.csv --scans scans.csv --path lidar --correction correction_lidar.json
```
The evaluate command exits non-zero when a gate fails. Hold out 20% of subjects for the reported numbers; the leave-one-out MAE printed by `train` is the optimistic estimate.
