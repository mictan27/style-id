# ADR 0001: Stack and repo structure

Date: 2026-10-19. Status: accepted.

## Context

The MVP proposal (Oct 18, 2026) calls for an iPhone shopper app, a server for GPU work and page fetching, and a fit engine that stays explainable. The team is two to three engineers aiming for a closed beta in about 12 weeks.

## Decisions

- **Mobile: Expo (React Native, TypeScript).** Chosen by the founder over native Swift. ARKit depth capture, Apple Vision masks and the Safari share extension are not available in Expo Go, so the app uses EAS development builds with two small iOS-only Swift Expo Modules (`ar-capture`, `vision-masks`). The avatar fit map is rendered with three.js on `expo-gl` rather than a native RealityKit view.
- **Backend: Python 3.12, FastAPI, Pydantic v2, Postgres 16, SQLAlchemy 2, Alembic.** One language across the API, the fit engine and the PyTorch body fitter.
- **Queue: Postgres-backed (procrastinate).** One fewer service; jobs commit transactionally with their rows. Revisit only if throughput demands it.
- **Chart extraction: Anthropic SDK with structured outputs.** The model id is configuration; the eval harness decides the cost/accuracy trade-off.
- **Body model: SAM 3D Body predicting MHR.** The SMPL family is excluded for licensing reasons.
- **Fit engine is stdlib-only.** `styleid_fit` owns the domain enums; `styleid_schema` wraps them in Pydantic for the API. Nothing in `packages/` imports from `services/`.
- **Units: cm internally and in the UI.** Chart extraction classifies and converts inches.
- **First category: tees and knits.** Collar handling exists but shirt-specific rules are deferred.

## Consequences

- Every Python package lives in the uv workspace with a `src/` layout and its own tests.
- The mobile client's API types are generated from the FastAPI OpenAPI document; nothing is hand-written.
- Local development on Linux runs unit tests on SQLite and the fake body fitter. Postgres and GPU paths run in CI and on a rented GPU box.
