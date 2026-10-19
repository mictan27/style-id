# styleid_fit

Pure-Python fit engine. No dependencies. Every verdict is arithmetic plus rules so it can be explained as "4 cm more room at the chest than your grey tee".

## Concepts

- **Zones**: chest, shoulder, waist, hem, bicep, collar (ease zones) and length, sleeve (position zones). `types.ZONE_SPECS` maps each to a garment field and a body field.
- **Ease** `e_z = G_z - B_z` (`ease.body_ease`). Flat garment widths are doubled to circumferences first.
- **Reference delta** `Δ_z = G_new,z - G_ref,z` (`ease.reference_delta`). Wins whenever a reference garment covers the zone.
- **Labels** tight / fitted / regular / relaxed from `thresholds.THRESHOLDS[zone][stretch]`. With a reference, the label is anchored at the middle of the reference's tagged band and shifted by the delta (`labels.label_from_reference`), which skips body error entirely.
- **Positions** for lengths: "hem lands 5 cm below your waist line" (`lengths.hem_position`, `lengths.sleeve_position`).
- **Size pick** `L(s) = Σ w_z (G_z(s) − target_z)²` after hard rules (`sizepick.pick`). Targets come from references, else body plus the population default ease. Per-user `Preferences.shift_cm` moves targets and is nudged by outcomes (`report.nudge`).
- **Report** `report.build_report(candidates, body, refs, prefs)` returns a `FitReport` with pick, runner-up, per-zone results, diffs and confidence.

## Tuning

All numbers live in `thresholds.py`. Golden cases in `tests/golden/*.json` are the product-reviewed expectations; add one when you change a threshold.
