# Build-along guide

The complete guided build lives at <https://learn.datalumina.com/docs/invoice-review>. This local guide records the first checkpoint represented by the `main` branch.

## Starter outcome

The repository installs reproducibly, starts a minimal FastAPI service and React interface, and includes the business brief plus fictional source documents.

## Why this boundary exists

The starter removes the completed workflow while preserving every prerequisite needed to build it. You begin with the user, the source documents, and explicit service boundaries instead of reverse-engineering a finished application.

## Commands

```bash
cd backend
uv sync --locked

cd ../frontend
pnpm install --frozen-lockfile

cd ..
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
./scripts/dev.sh --check
./scripts/dev.sh
```

## Important locations

- `docs/client-brief.md`: the recurring finance problem and definition of done
- `docs/architecture.md`: the intended boundaries and data flow
- `samples/`: the fictional evaluation corpus and manifest
- `backend/app/main.py`: the initial API boundary
- `frontend/src/App.tsx`: the initial interface boundary

## What you should observe

- `GET http://localhost:8000/health` returns `{"status":"ok"}`.
- `http://localhost:5173` shows the Invoice Review starter screen.
- No Azure request occurs at this checkpoint.

## Checkpoint

- [ ] Locked backend and frontend installs succeed.
- [ ] Backend lint passes.
- [ ] Frontend type-check, lint, and production build pass.
- [ ] `./scripts/dev.sh --check` reports that Invoice Review is ready to start.
- [ ] The health endpoint and starter screen load locally.

## Slice: inspect Document Intelligence output

SOP so far: put credentials in `backend/.env`, keep a thin service that talks to Azure, then inspect a real sample from `playground/` before adding more code.

### Outcome

A `DocumentIntelligenceService` sends a local invoice to `prebuilt-invoice`. The playground script prints the extracted fields and writes the full Azure `AnalyzeResult` so the data model is visible before any normalization.

### Why

The Azure payload is the thing to understand first. Moving the run loop into `playground/` keeps the service class as a client, and writing JSON to disk is easier to inspect than scrolling a terminal dump.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app

cd ../playground
uv run --project ../backend --locked --no-sync python inspect_invoice.py
```

### What you should observe

- Ruff reports no issues.
- The terminal lists invoice fields for `samples/generated/01-en-happy-classic.pdf` (vendor, customer, dates, totals, line items).
- `playground/output/01-en-happy-classic.json` contains the full `AnalyzeResult`.
- One Document Intelligence page is consumed.

### Checkpoint

- [ ] `backend/.env` has the Document Intelligence endpoint and key.
- [ ] `DocumentIntelligenceService.analyze_invoice` is the only Azure call site.
- [ ] The playground inspect script runs from `playground/` and writes output next to itself.
- [ ] Extracted fields for the English happy-path invoice match `samples/manifest.json`.

Continue with the [online tutorial](https://learn.datalumina.com/docs/invoice-review).
