# Runbook: flat-lay accuracy check (gate: ≤ 1 cm per measurement)

Needs an iPhone with an EAS development build and a tape measure. Takes about an hour for ten garments.

1. Pick 10 tops across kinds (tees, a hoodie, a shirt) and fabrics. Number them.
2. Tape-measure each one laid flat: chest (pit to pit), length (HPS to hem), shoulder (seam to seam), sleeve (seam to cuff), hem width, bicep width 2.5 cm below the armpit. Record in `flatlay_tape.csv` with columns `garment_id, field, cm`.
3. In the app, Closet → Measure with camera. Lay the garment on a plain floor, hold the phone level overhead at about 1 m, wait for the plane indicator, capture. Accept the proposed landmarks without dragging first; save. Repeat with corrections dragged. Record both runs.
4. Export the garments from the API (`GET /v1/closet/garments`) and compute absolute error per field against the tape CSV.
5. Pass when mean absolute error is ≤ 1 cm per field on the corrected run. If the uncorrected run is far worse, the landmark proposal needs work before beta, not the scale.
6. File the results CSV under `docs/runbooks/results/` with the build number and device model.
