# Metrics and gates

From the MVP proposal. The first four are model metrics and gate each build phase; the last four are product metrics and decide whether the MVP works. Targets are starting points, to be confirmed after the first calibration run.

| Metric | Target | How it is measured | Where |
|---|---|---|---|
| Chest and waist error, LiDAR path | ≤ 1.5 cm MAE | Held-out subjects from the calibration study | `python -m styleid_calibration evaluate --path lidar` |
| Chest and waist error, photo path | ≤ 2.5 cm MAE | Same held-out set | `python -m styleid_calibration evaluate --path photo` |
| Flat-lay garment error | ≤ 1 cm per measurement | 100 garments measured by tape vs the app | Device checklist; results CSV in `docs/runbooks/` |
| Size-chart extraction | ≥ 95% of cells correct | 200 hand-labelled product pages | `packages/chartextract/eval/run_eval.py` |
| Size pick matches the size kept | ≥ 80% of purchases | Post-delivery check-in | `purchase_outcomes` vs `fit_reports.result.pick` |
| Report judged accurate | ≥ 75% of check-ins | One-tap question after delivery | check-in flow |
| Fit returns among beta users | Lower than their own last 6 months | Self-reported baseline at sign-up | onboarding survey + outcomes |
| Product checks per active user | ≥ 3 per month | App analytics | API logs on `POST /v1/fit/reports` |

Every fit report carries `engine_version` so threshold changes can be evaluated against outcomes recorded under earlier versions.
