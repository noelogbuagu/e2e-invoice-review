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

## Slice: Pydantic invoice and receipt schemas

SOP so far: credentials, thin Azure client, inspect raw output, then lock a domain model and prove it fills from that output before building more.

### Outcome

`app/schemas/invoice` and `app/schemas/receipt` hold Pydantic models for the Northstar review fields. Mappers read Document Intelligence field names (`VendorTaxId`, `InvoiceId`, `MerchantName`, `ReceiptType`, and so on) and produce those models. A playground script maps a happy-path invoice, a missing-VAT invoice, and the Dutch fuel receipt, then compares them to `samples/manifest.json`.

### Why

The Azure payload has more fields than Maya reviews. The schemas keep the domain names (`vendor_vat_id`, `invoice_number`, `merchant_name`) and leave unused Document Intelligence fields behind. Invoice and receipt stay separate because a receipt is an expense already paid and does not carry invoice number, customer VAT, PO, or due date.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app

cd ../playground
uv run --project ../backend --locked --no-sync python map_schemas.py
```

### What you should observe

- Ruff reports no issues.
- Happy-path invoice fields match the manifest.
- Missing-VAT invoice maps with `vendor_vat_id` empty.
- Fuel receipt maps merchant, transaction date, totals, and an expense category from `ReceiptType`.
- Repeat runs reuse `playground/output/*.json` and do not call Azure.

### Checkpoint

- [ ] Invoice and receipt schemas live under `backend/app/schemas/`.
- [ ] Mapping uses Document Intelligence field names, not SDK types.
- [ ] Playground mapping script compares filled models to the corpus manifest.

## Slice: Azure-free schemas and provider adapter

SOP so far: credentials, inspect raw output, lock a domain model, then split mapping from that model and hide the Azure SDK behind a provider.

### Outcome

`model.py` holds only Northstar fields. `mapping.py` holds Document Intelligence field names (`VendorTaxId` → `vendor_vat_id`). `common.py` holds `ExtractedValue` and the field parsers. `AzureDocumentIntelligenceProvider` is the only module that imports the Azure SDK; it returns plain dicts and mapped schemas.

### Why

The schema is what Maya reviews. Azure field names and SDK types are adapter concerns. Keeping them apart means a later LLM merge can fill the same `Invoice` and `Receipt` models without touching Azure types.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app

cd ../playground
uv run --project ../backend --locked --no-sync python map_schemas.py
```

### What you should observe

- Ruff reports no issues.
- Mapping reuses cached AnalyzeResult JSON and still matches the previous playground comparison.
- `app/schemas/invoice/model.py` and `app/schemas/receipt/model.py` do not mention Azure field names.

### Checkpoint

- [ ] SDK types stop in `backend/app/providers/azure_document_intelligence.py`.
- [ ] Domain models stay Azure-free.
- [ ] Invoice and receipt field maps live in `mapping.py`.

Continue with the [online tutorial](https://learn.datalumina.com/docs/invoice-review).
