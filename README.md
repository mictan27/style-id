# style.id

Measurement-based fit for tops. Answers one question before checkout: will this exact item fit me, and where will it be tight or loose?

The product is described in the MVP proposal (Oct 2026). Stack and structure decisions are in `docs/adr/`.

## Layout

| Path | What |
|---|---|
| `packages/fitengine` | `styleid_fit`: pure Python fit engine (ease, labels, lengths, size pick). stdlib only. |
| `packages/schema` | `styleid_schema`: Pydantic models shared by API, workers and the mobile client (via OpenAPI). |
| `packages/chartextract` | `styleid_charts`: product page fetch → size-chart extraction (Claude) → normalised garment measurements, plus an offline eval harness. |
| `packages/bodyfit` | `styleid_bodyfit`: GPU body-fit worker (SAM 3D Body → MHR → measurements) and a fake fitter for local runs. |
| `packages/calibration` | Calibration-study tooling: tape entry, pairing with scans, correction model training. |
| `services/api` | FastAPI service: auth, closet, products, fit reports, outcomes. |
| `services/worker` | CPU worker: chart extraction jobs, scan cleanup. |
| `apps/mobile` | Expo (React Native, TypeScript) iPhone app with Swift Expo Modules for ARKit and Vision. |
| `docs/` | ADRs, metrics definitions, runbooks. |
| `infra/` | docker-compose and Dockerfiles. |

## Run it end to end

There is no simulator path on Linux: the app needs an iPhone running an EAS development build, talking to the API on this box over Wi-Fi. Expo Go cannot load it (two Swift modules, Skia, share extension).

**1. Backend on this machine (2 minutes)**

```bash
export PATH="$HOME/.local/bin:$PATH"          # uv
uv sync --all-packages
uv run alembic -c services/api/alembic.ini upgrade head
uv run uvicorn styleid_api.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/docs` for the interactive API. Everything works with SQLite and dev auth; no Postgres, Docker or API key needed. Chart extraction against Claude only runs when `ANTHROPIC_API_KEY` is exported.

Smoke test without the app:

```bash
curl -H 'X-Dev-User: alice' localhost:8000/v1/me
```

**2. One-time phone build (needs Expo account + Apple Developer account, ~15 min in the cloud)**

```bash
cd apps/mobile
pnpm install
pnpm dlx eas-cli login
pnpm dlx eas-cli init                # links the project, sets EAS_PROJECT_ID
pnpm dlx eas-cli device:create       # register your iPhone UDID (follow the link on the phone)
pnpm build:dev                       # eas build --profile development --platform ios
```

Install the build on the phone from the link EAS prints. Rebuild only when native code or `app.config.ts` changes; JS changes hot-reload.

**3. Run the app**

```bash
cd apps/mobile
EXPO_PUBLIC_API_URL=http://<this-machine-LAN-IP>:8000 pnpm start
```

Open the dev build on the phone and scan the QR code (phone and this box on the same network; `hostname -I` gives the IP). On the sign-in screen use the developer field with any handle, which sends `X-Dev-User` instead of an Apple token.

**With a Mac instead:** `pnpm ios` runs `expo run:ios` in the Simulator (Xcode 16+). Camera, LiDAR and Vision screens show a "needs an iPhone build" message there; closet manual entry, product checks, fit reports and outcomes all work.

## Develop

```bash
# Python (uv workspace)
uv sync --all-packages
uv run pytest                      # all packages and services
uv run ruff check . && uv run ruff format --check .
uv run mypy packages/*/src services/*/src

# Chart extraction eval (offline, recorded fixtures)
uv run python packages/chartextract/eval/run_eval.py --fake
# ... or live against Claude: export ANTHROPIC_API_KEY=... && uv run python packages/chartextract/eval/run_eval.py --record

# API
uv run alembic -c services/api/alembic.ini upgrade head
uv run uvicorn styleid_api.main:app --reload     # dev auth: header X-Dev-User: <handle>

# Mobile
uv run python -m styleid_api.openapi > apps/mobile/openapi.json   # regenerate when routes change
cd apps/mobile && pnpm install && pnpm gen:api && pnpm typecheck && pnpm lint && pnpm test
```

Only the server side runs on a Linux box. iOS builds are produced with `eas build --profile development` from `apps/mobile`; Expo Go cannot run the app because of the two native modules. Details, native module notes and EAS profiles: `apps/mobile/README.md`. API settings and auth: `services/api/README.md`.

## Where things stand

See `docs/adr/0001-stack.md` for decisions, `docs/metrics.md` for the gates, and `docs/runbooks/` for the device and calibration procedures. The 12-week sequence is in the approved implementation plan; weeks 1 and 2 (fit engine, schema, chart extraction, API skeleton, body-fit seam, calibration tooling, Expo scaffold) are in this tree.
