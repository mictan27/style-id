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

The app runs on an iPhone, talking to the API over Wi-Fi. Expo Go cannot open it, because it has custom Swift modules (ARKit capture, Vision masks). You need your own build of the app, and iOS builds need a Mac with Xcode. A paid Apple Developer account is not required to develop.

| Path | Cost | What works |
|---|---|---|
| A. Your iPhone, built on your Mac with a free Apple ID | free | Everything except Sign in with Apple and the Safari share sheet. Reinstall every 7 days. |
| B. iOS Simulator on your Mac | free | All screens; no camera, ARKit or LiDAR. |
| C. EAS cloud build | $99/yr Apple account | Everything, no Mac needed, shareable with testers. |

**1. Start the API** (any machine on the same Wi-Fi as the phone; no Postgres, Docker or API key needed)

```bash
uv sync --all-packages
uv run alembic -c services/api/alembic.ini upgrade head
uv run uvicorn styleid_api.main:app --host 0.0.0.0 --port 8000 --reload
curl -H 'X-Dev-User: alice' localhost:8000/v1/me      # smoke test; http://localhost:8000/docs for the UI
```

Chart extraction against Claude only runs when `ANTHROPIC_API_KEY` is exported.

**2A. Free build on your iPhone (Mac)**

One-time setup: install Xcode from the App Store, open it once, then Xcode, Settings, Accounts, and add your normal Apple ID. On the iPhone, enable Settings, Privacy & Security, Developer Mode (it appears after the first install attempt; the phone restarts).

```bash
cd apps/mobile
pnpm install
STYLEID_FREE_SIGNING=1 npx expo run:ios --device     # pick your plugged-in iPhone from the list
```

If Xcode reports a signing error, open `apps/mobile/ios/styleid.xcworkspace`, select the `styleid` target, Signing & Capabilities, and choose your "Personal Team". If it says the bundle id is taken, rerun with `IOS_BUNDLE_ID=id.style.app.dev.<yourname>`. On the phone, trust the developer profile under Settings, General, VPN & Device Management.

`STYLEID_FREE_SIGNING=1` leaves out the two capabilities free accounts cannot sign: Sign in with Apple (use the developer sign-in field instead) and the share extension (paste product links into the Check tab instead). The build expires after 7 days; rerun the command to reinstall. You only rerun it when native code or `app.config.ts` changes; day to day, `pnpm start` is enough and JS changes hot-reload.

**2B. Simulator (Mac)**: `cd apps/mobile && pnpm install && pnpm ios`.

**2C. EAS cloud build** (paid Apple account, no Mac): `pnpm dlx eas-cli login`, `pnpm dlx eas-cli device:create` to register the phone, then `pnpm build:dev` and install from the link. The Expo project (`styleid`) is already linked in `app.config.ts`.

**3. Point the app at the API**

```bash
cd apps/mobile
EXPO_PUBLIC_API_URL=http://<api-machine-LAN-IP>:8000 pnpm start
```

Open style.id on the phone; it connects to Metro (scan the QR code if asked). On the sign-in screen use the developer field with any handle, which sends `X-Dev-User` instead of an Apple token.

Do not commit `apps/mobile/ios/`: `expo run:ios` generates it and it is gitignored.

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
