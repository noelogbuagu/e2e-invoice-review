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

## Slice: Azure resource group

SOP so far: install locally, then put every Azure resource in one inspectable group before any application code depends on the cloud.

### Outcome

`rg-invoice-review` exists in West Europe. The Azure CLI is signed in to the intended subscription. Child resources can live in other regions; the group is only the lifecycle and cleanup boundary.

### Why

Cloud setup should fail on its own, not in the middle of a feature. One group makes names, regions, and later deletion explicit. The [Azure CLI lesson](https://learn.datalumina.com/docs/invoice-review/azure-cli) is the source; this slice records what this subscription actually did.

### Commands

```bash
az account show --output table

az group create \
  --name rg-invoice-review \
  --location westeurope \
  --output table

az group list --output table
```

Do not run the cleanup command now. When the project is over it deletes the group and everything inside it:

```bash
az group delete --name rg-invoice-review
```

### What you should observe

- `az account show` prints the subscription you intend to bill.
- `az group list` shows `rg-invoice-review` in `westeurope`.
- A resource group's location is only where the group object is stored. Document Intelligence later landed in North Europe because West Europe returned `locationineligible` for new Cognitive Services. Keep the group; put the child resource in a region Azure still allows.

### Checkpoint

- [ ] `az account show` is the intended subscription.
- [ ] `rg-invoice-review` exists in `westeurope`.
- [ ] You know the one command that removes everything later.

## Slice: Azure AI Foundry

SOP so far: one resource group, then a working language-model deployment you have tested yourself before any backend code calls it.

### Outcome

Foundry account `foundry-invoice-review` and project `prj-invoice-review` live in `rg-invoice-review` (Sweden Central). Deployment `gpt-5.6-terra` is Global Standard version `2026-07-09` and reports `Succeeded`. Endpoint, deployment name, and key are in gitignored `backend/.env`.

### Why

On Azure you do not call "the GPT API". You create a resource, then a deployment of a specific model, and code addresses that deployment by name. Provisioning first means region, quota, and model availability fail independently. The [Foundry lesson](https://learn.datalumina.com/docs/invoice-review/azure-foundry) uses the portal; this slice uses the CLI the same way as Document Intelligence.

### Commands

```bash
az cognitiveservices model list \
  --location swedencentral \
  --query "[?model.name=='gpt-5.6-terra'].{version:model.version,skus:join(',',model.skus[].name)}" \
  --output table

az cognitiveservices account create \
  --name foundry-invoice-review \
  --resource-group rg-invoice-review \
  --kind AIServices \
  --sku S0 \
  --location swedencentral \
  --custom-domain foundry-invoice-review \
  --assign-identity \
  --allow-project-management true \
  --yes \
  --output table

az cognitiveservices account project create \
  --name foundry-invoice-review \
  --resource-group rg-invoice-review \
  --project-name prj-invoice-review \
  --location swedencentral \
  --output table

az cognitiveservices account deployment create \
  --name foundry-invoice-review \
  --resource-group rg-invoice-review \
  --deployment-name gpt-5.6-terra \
  --model-name gpt-5.6-terra \
  --model-version "2026-07-09" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name GlobalStandard \
  --output table

az cognitiveservices account deployment show \
  --name foundry-invoice-review \
  --resource-group rg-invoice-review \
  --deployment-name gpt-5.6-terra \
  --query '{state:properties.provisioningState,model:properties.model,sku:sku}' \
  --output json
```

Fetch the values the backend will need. Put them in `backend/.env`. Do not commit them.

```bash
az cognitiveservices account show \
  --name foundry-invoice-review \
  --resource-group rg-invoice-review \
  --query properties.endpoint \
  --output tsv

az cognitiveservices account keys list \
  --name foundry-invoice-review \
  --resource-group rg-invoice-review \
  --query key1 \
  --output tsv
```

`--name` and `--custom-domain` must be globally unique. If create fails on the name, add a suffix. If Sweden Central returns `locationineligible`, retry `northeurope` then `uksouth` and list the model in that region before deploying.

Open the playground at <https://ai.azure.com>, select the `gpt-5.6-terra` deployment, and send a prompt. A response proves quota works before any code depends on it.

### What you should observe

- Model list includes `gpt-5.6-terra` version `2026-07-09` with `GlobalStandard`.
- Deployment show prints `"state": "Succeeded"`, model `gpt-5.6-terra`, sku `GlobalStandard`.
- Endpoint is `https://foundry-invoice-review.cognitiveservices.azure.com/`. Local `.env` uses that host plus `/openai/v1/`.
- The playground returns a response. Token spend for this check is a few thousand tokens; the complete build stays well under a dollar.

### Checkpoint

- [ ] Foundry deployment reports `Succeeded`.
- [ ] Playground returns a response from `gpt-5.6-terra`.
- [ ] `backend/.env` has the endpoint, deployment name, and key. Those values are not in git.

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
uv run --project ../backend --locked --no-sync python analyse_sample_invoice.py
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

`app/schemas/invoice` and `app/schemas/receipt` hold Pydantic models for the Plurobi review fields. Mappers read Document Intelligence field names (`VendorTaxId`, `InvoiceId`, `MerchantName`, `ReceiptType`, and so on) and produce those models. A playground script maps a happy-path invoice, a missing-VAT invoice, and the Dutch fuel receipt, then compares them to `samples/manifest.json`.

### Why

The Azure payload has more fields than Maya reviews. The schemas keep the domain names (`vendor_vat_id`, `invoice_number`, `merchant_name`) and leave unused Document Intelligence fields behind. Invoice and receipt stay separate because a receipt is an expense already paid and does not carry invoice number, customer VAT, PO, or due date.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app

cd ../playground
uv run --project ../backend --locked --no-sync python map_extraction_samples.py
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

`model.py` holds only Plurobi fields. `mapping.py` holds Document Intelligence field names (`VendorTaxId` → `vendor_vat_id`). `common.py` holds `ExtractedValue` and the field parsers. `AzureDocumentIntelligenceProvider` is the only module that imports the Azure SDK; it returns plain dicts and mapped schemas.

### Why

The schema is what Maya reviews. Azure field names and SDK types are adapter concerns. Keeping them apart means a later LLM merge can fill the same `Invoice` and `Receipt` models without touching Azure types.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app

cd ../playground
uv run --project ../backend --locked --no-sync python map_extraction_samples.py
```

### What you should observe

- Ruff reports no issues.
- Mapping reuses cached AnalyzeResult JSON and still matches the previous playground comparison.
- `app/schemas/invoice/model.py` and `app/schemas/receipt/model.py` do not mention Azure field names.

### Checkpoint

- [ ] SDK types stop in `backend/app/providers/azure_document_intelligence.py`.
- [ ] Domain models stay Azure-free.
- [ ] Invoice and receipt field maps live in `mapping.py`.

## Slice: Azure OpenAI service

SOP so far: credentials, thin Azure clients, inspect raw output, lock a domain model, hide Document Intelligence behind a provider, then prove the second extractor the same way.

### Outcome

`AzureOpenAIService` sends a prompt through the Foundry deployment. Endpoint, deployment name, and key come from `Settings`. OpenAI SDK types stop in `AzureOpenAIProvider`. A playground script prints a model reply.

### Why

The one difference from calling OpenAI directly is `base_url`. Against Azure, `model` is the deployment name from `.env`, not a hardcoded model string. Keeping the SDK in the provider matches Document Intelligence and leaves later structured review on the same `Settings` boundary.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app

cd ../playground
uv run --project ../backend --locked --no-sync python create_openai_response.py
```

Or open `create_openai_response.py` in the interactive window, edit `PROMPT` at the top, and run `main()`.

### What you should observe

- Ruff reports no issues.
- The output prints that Paris is the capital of France.
- The call uses `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, and `AZURE_OPENAI_API_KEY` from `backend/.env`.
- `AZURE_OPENAI_ENDPOINT` must end in `/openai/v1/` as in `.env.example`.
- This uses a few thousand tokens on Global Standard.

### Checkpoint

- [ ] `AzureOpenAIProvider` is the only OpenAI SDK import.
- [ ] Deployment name and credentials are not hardcoded.
- [ ] `create_openai_response.py` returns an answer through the Azure endpoint.

## Slice: document classification

SOP so far: credentials, thin Azure clients, inspect raw output, lock a domain model, hide Document Intelligence behind a provider, prove a text Responses call, then classify the original file before any extraction runs.

### Outcome

`DocumentClassifier` sends a PDF or image to the Foundry deployment through Pydantic AI structured output. The model returns `DocumentClassification` (`invoice` or `receipt`, a confidence, and a short reason). A playground script classifies the happy-path invoice and the Dutch fuel receipt.

### Why

Document Intelligence has separate prebuilt extractors and no reliable classifier between them. The LLM takes that first job so later extraction can pick `prebuilt-invoice` or `prebuilt-receipt`. `OpenAIResponsesModel` plus `BinaryContent` is the shortest Pydantic AI pattern that can send the original file; Azure Chat Completions does not accept document parts. `output_type=DocumentClassification` is the structured-output contract.

### Commands

```bash
cd backend
uv sync --locked
uv run --locked --no-sync ruff check app

cd ../playground
uv run --project ../backend --locked --no-sync python classify_sample_document.py
```

Or open `classify_sample_document.py` in the interactive window, set `DOCUMENT_PATH` to the fuel receipt sample, and run `main()` again.

### What you should observe

- Ruff reports no issues.
- The happy-path invoice prints `"document_kind": "invoice"` with a short reason.
- Switching `DOCUMENT_PATH` to the fuel receipt prints `"document_kind": "receipt"`.
- Endpoint, deployment name, and key still come from `Settings` / `backend/.env`.
- Two Responses calls on Global Standard.

### Checkpoint

- [ ] `pydantic-ai-slim[openai]==2.11.0` is pinned and locked.
- [ ] `nest-asyncio==1.6.0` lives in the backend dev group for interactive playground use.
- [ ] `playground/bootstrap.py` patches asyncio and wires backend imports for every playground script.
- [ ] The classifier lives in `backend/app/pipeline/classification.py`.
- [ ] The playground script labels the sample invoice PDF and the fuel receipt PNG correctly.

## Slice: extraction and VAT checks

SOP so far: classify the original file, then chain extraction and deterministic finance checks on the same pipeline context.

### Outcome

`Pipeline` runs `ClassificationStep`, `ExtractionStep`, and `ValidationStep` in order. Classification picks `prebuilt-invoice` or `prebuilt-receipt`. Mapped `Invoice` or `Receipt` models go through offline EU VAT format/checksum checks (invoices) and a one-cent totals reconciliation (invoices and receipts). INFO logs show each step as it starts and finishes.

### Why

Document Intelligence has no classifier, so the LLM label chooses the extractor. Azure field names stay in the provider; the pipeline only sees Plurobi models. VAT and totals are ordinary Python (`python-stdnum`, `Decimal`) so a model cannot approve a bad number. The runner owns step logging so a failed Azure call is still auditable.

### Commands

Open `playground/process_sample_document.py` in the interactive window, keep `DOCUMENT_PATH` on the happy-path invoice, and run `main()`. Then uncomment another sample path and run `main()` again.

```bash
cd backend
uv run --locked --no-sync ruff check app
```

### What you should observe

- INFO logs: `starting classification` → classified kind → `starting extraction` → which prebuilt model → `starting validation` → issue count.
- Happy-path invoice: filled supplier/customer, VAT IDs, dates, PO, currency, totals, line items, and `[]` issues.
- Missing vendor VAT sample: `vendor_vat_id_required`.
- Invalid vendor VAT sample: `vendor_vat_id_invalid`.
- Total-mismatch sample: `invoice_total_mismatch`.
- Fuel receipt: merchant and totals, no VAT-ID check, empty issues if the numbers add up.
- One classification call and one Document Intelligence page per `main()` run.

### Checkpoint

- [ ] `Pipeline` in `backend/app/pipeline/base.py` logs start/finish for each step.
- [ ] `ExtractionStep` calls `prebuilt-invoice` or `prebuilt-receipt` from the classification.
- [ ] `backend/app/invoices/validation.py` is pure (no Azure, no I/O).
- [ ] Interactive `process_sample_document.py` shows the audit log and the extracted model.

## Slice: GL suggestion and Plurobi policy

SOP so far: classify, extract, and run VAT/totals checks, then suggest a GL account from a fixed catalog and apply the rest of Plurobi policy in ordinary Python.

### Outcome

`PipelineContext` has one slot per step: `classification`, `extraction`, `validation`, and `gl_suggestion`. Validation covers invoice vs receipt policy (required fields, EU VAT, customer VAT vs Plurobi, date order, missing PO warning, totals, low confidence, duplicate keys). `GlSuggestionStep` sends normalized invoice or receipt JSON to Azure OpenAI structured output and resolves the code against ten Plurobi GL accounts. The suggestion is a hint; a reviewer override is not stored yet.

### Why

The catalog and selection live in `backend/app/accounting/` so the model cannot invent a posting account. Policy stays in `backend/app/invoices/validation.py`. Duplicate detection uses an injectable in-memory registry until SQLite exists. GL runs after validation so Maya still sees a suggested account while reviewing errors.

### Commands

Open `playground/process_sample_document.py` in the interactive window, keep `DOCUMENT_PATH` on the happy-path invoice, and run `main()`. Then uncomment the duplicate invoice or the fuel receipt and run `main()` again.

```bash
cd backend
uv run --locked --no-sync ruff check app
```

### What you should observe

- INFO logs continue through `starting gl_suggestion` and a suggested account code and name.
- Happy-path invoice: extraction filled, empty or warning-only issues, a catalog GL code.
- `10-de-duplicate.pdf` (seeded registry): `duplicate_invoice`.
- Fuel receipt: no VAT-ID requirement, fuel/travel or similar GL, extra Azure call for the suggestion.
- Two Responses calls (classification + GL) and one Document Intelligence page per `main()` run.

### Checkpoint

- [ ] Ten GL accounts live in `backend/app/accounting/catalog.py`; `resolve_account` rejects unknown codes.
- [ ] `GlSuggestionStep` receives normalized fields only, not the original PDF.
- [ ] Invoice and receipt policies are separate; duplicate check is optional via `DuplicateRegistry`.
- [ ] Interactive `process_sample_document.py` prints each context slot including `gl_suggestion`.

## Slice: Expose the pipeline through FastAPI

SOP so far: classify, extract, validate, and suggest a GL account in the playground, then wrap that same `build_document_pipeline()` flow in HTTP and SQLite so a later UI can upload, list, and delete reviews.

### Outcome

A thin HTTP and SQLite layer wraps the proven pipeline. Upload a PDF or image, persist classification, extraction, validation, and GL suggestion, list or fetch saved reviews, delete a review, and read the fixed Plurobi GL catalog — without corrections, decisions, or correction-email drafts yet. Duplicate checks use the SQLite document table through the existing `DuplicateRegistry` protocol.

### Why this boundary exists

Routes own HTTP parsing and status codes. The service owns orchestration (save file → run pipeline → map status). The repository owns SQLite. Persistence and HTTP now wrap known pipeline behavior instead of becoming the place where extraction and policy are invented. Policy stays in `backend/app/invoices/validation.py`; invoice and receipt models stay as they are.

### Commands

```bash
cd backend
uv run --locked --no-sync ruff check app
uv run --locked --no-sync uvicorn app.main:create_app --factory --reload
```

In a second terminal from the repo root:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/accounting/gl-accounts
curl -F \
  "file=@samples/generated/01-en-happy-classic.pdf;type=application/pdf" \
  http://localhost:8000/api/documents
curl http://localhost:8000/api/documents
```

Upload spends Azure: one classification call, one Document Intelligence page, and one GL suggestion call. Oversized or non-PDF/JPEG/PNG files are rejected locally before any provider call.

### Important locations

- `backend/app/main.py`: FastAPI factory, CORS, `/health`
- `backend/app/config.py`: fixed upload/DB application config and `ALLOWED_ORIGIN`
- `backend/app/database.py`: SQLAlchemy engine and session factory
- `backend/app/documents/routes.py`: upload, list, get, and delete
- `backend/app/documents/service.py`: calls `build_document_pipeline()`
- `backend/app/documents/repository.py` and `models.py`: SQLite persistence
- `backend/app/accounting/routes.py`: `GET /api/accounting/gl-accounts`

### What you should observe

- `GET /health` returns `{"status":"ok"}`.
- `GET /api/accounting/gl-accounts` returns the ten Plurobi accounts (`6100`–`6190`).
- One multipart upload returns a persisted review with `classification`, `extraction`, `validation`, and `gl_suggestion`.
- Status is `needs_review` when validation has errors, otherwise `ready`; pipeline failures become `failed` with `502`.
- Oversized (>4 MB) or non-PDF/JPEG/PNG uploads are rejected before Azure is called.
- `DELETE /api/documents/{id}` removes the SQLite row and the local upload file.

### Checkpoint

- [ ] Backend lint passes for `app`.
- [ ] Health, GL catalog, upload, and list work with curl against a running uvicorn process.
- [ ] You can explain why routes, service, and repository stay separate from the pipeline steps.
- [ ] You can explain why corrections, decisions, and correction-email are deferred until later.

## Slice: Frontend upload scaffold

SOP so far: expose the proven pipeline through FastAPI, then add the smallest browser flow that
previews one document and starts that API call.

### Outcome

The React app opens on a welcome portal, moves to a focused upload screen, validates and previews a
PDF or image locally, and starts the existing document pipeline only after confirmation. While the
synchronous upload request runs, the interface explains the four pipeline stages. Completion opens
a read-only result page with classification, extraction highlights, validation findings, and the GL
suggestion; editing, approval, and history remain later slices.

### Why

The frontend mirrors the backend trust boundary: it gives fast file-type and 4 MB feedback, while
FastAPI repeats those checks before using Azure. `document-api.ts` owns document HTTP calls,
`env.ts` owns the public base URL, and components only consume application types. The solution
branch is a visual reference, but the response types and pipeline copy match the current
development backend.

### Commands

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm exec tsc -b --pretty false
pnpm lint
pnpm build
pnpm dev
```

In another terminal:

```bash
cd backend
uv run --locked --no-sync uvicorn app.main:create_app --factory --reload
```

Open <http://localhost:5173>, choose `samples/generated/01-en-happy-classic.pdf`, inspect the
preview, and select **Process document**. This manual upload consumes one classification call, one
Document Intelligence page, and one GL-suggestion call.

### What you should observe

- The welcome screen explains upload, pipeline, and review in three steps.
- The upload screen accepts PDF, JPEG, or PNG files up to 4 MB and previews the selected document.
- **Process document** calls `POST /api/documents` and shows classification, extraction,
  deterministic validation, and GL suggestion as the active pipeline stages.
- Successful processing opens the result page with the returned status and pipeline evidence.
- Invoice and receipt results share the same summary while keeping their extraction fields distinct.
- FastAPI `detail` messages appear on the upload screen when processing fails.
- History is visibly deferred instead of pretending saved reviews are already implemented.

### Checkpoint

- [ ] The locked frontend install succeeds.
- [ ] Type-check, ESLint, and the production build pass.
- [ ] Welcome → upload → preview works in the browser.
- [ ] A configured backend processes the sample and the result page shows its evidence.
- [ ] No auth, editing, decision, correction-email, or history implementation was introduced.

## Slice: Close the Maya review loop

SOP so far: the browser can upload one file and show a read-only result. This slice finishes the
brief: a hybrid reviewer (Document Intelligence primary, independent LLM secondary), then the human
loop — correct fields, confirm the GL account, approve or reject, draft (never send) a supplier
correction email, and keep a review history with explicit deletion so a demo can be reset.

### Outcome

Processing gains a fifth stage. After Document Intelligence fills the `Invoice` or `Receipt`, an
independent Azure OpenAI reviewer reads the **original file** (not the DI output) through
pydantic-ai `BinaryContent`. A deterministic merge keeps every present DI value, fills only missing
fields from the LLM (`llm_fallback`), and records per-field comparisons. Policy and GL run on the
merged document. The review page shows DI first, then the LLM check, then findings, GL, and the
decision. Maya edits DI fields and saves to re-run policy (`human` provenance), picks a GL account,
approves when there are no errors, rejects otherwise, or drafts a correction email from the DI
section when a supplier-fixable error blocks approval. History lists, reopens (with the stored file),
and deletes reviews.

### Why

Two extractors disagree in useful ways: on `05-nl-missing-vendor-vat.pdf` Document Intelligence
misses the purchase order and the LLM fills it, so Maya sees only the real problem (missing VAT).
The merge never lets the LLM overwrite a present DI value, which is how `06`, `07`, and `08` keep
their intended errors instead of being “fixed” by a model. Decision rules live in `DocumentService`,
not the pipeline: warnings allow approval, errors block it (`409`), decided rows are immutable, and
`duplicate_invoice` revalidation excludes the row being edited so a saved invoice never flags
itself. The correction email is drafted on demand and only for errors the supplier can fix;
`duplicate_invoice` and `low_extraction_confidence` are Plurobi-internal, so the button hides.
Nothing is sent: the modal has Copy and Close.

### Commands

```bash
cd backend
rm -f data/documents.db   # schema gained document_review and selected_gl_account_code
uv run --locked --no-sync ruff check app scripts
uv run --locked --no-sync python -m scripts.evaluate_hybrid 02-nl-happy-compact.pdf 05-nl-missing-vendor-vat.pdf 13-nl-fuel-receipt.png
uv run --locked --no-sync python -m scripts.evaluate_corpus
uv run --locked --no-sync uvicorn app.main:create_app --factory --reload
```

```bash
cd frontend
pnpm exec tsc -b --pretty false
pnpm lint
pnpm build
pnpm dev
```

Then walk the corpus in the browser. Upload `01`, confirm the GL account, **Approve**. Upload `08`,
open **Draft correction email** on the Document Intelligence card, Copy, Close, change the total
`125.00` → `121.00`, **Save and re-check**, **Approve**. Upload `06` and **Reject**. Upload `03` then
`10`, see `duplicate_invoice`, open History, delete `03`, reopen `10`, **Re-check policy**.

Cost: each upload is one Document Intelligence analyze plus three Azure OpenAI calls (classify,
review, GL). A correction-email draft is one more OpenAI call. `evaluate_corpus.py` spends 13 DI
analyses (14 pages) and no OpenAI. `evaluate_hybrid.py` spends one DI page and one OpenAI call per
file.

### Important locations

- `backend/app/document_review/`: `LlmDocumentExtraction` schema, `DocumentReviewer` protocol, and
  `reconciliation.merge_document()` (DI wins, LLM fills gaps, comparisons for the UI)
- `backend/app/pipeline/document_review.py`: `DocumentReviewStep` between extraction and validation;
  an LLM failure stores `document_review.error_message` and keeps the upload alive
- `backend/app/providers/azure_openai_document_review.py` and `azure_openai_correction_email.py`:
  pydantic-ai agents; `providers/azure_openai.py` gained `build_responses_model()`
- `backend/app/correction_email/`: `supplier_fixable_issues()` eligibility and the draft schema
- `backend/app/documents/service.py`: `correct()`, `select_gl_account()`, `decide()`,
  `draft_correction_email()`, plus `status_for_issues()`
- `backend/app/documents/routes.py`: `GET /{id}/file`, `PUT /{id}`, `PUT /{id}/accounting`,
  `POST /{id}/decision`, `POST /{id}/correction-email`
- `frontend/src/components/DocumentReview.tsx`, `ExtractionSection.tsx`, `CrossCheckSection.tsx`,
  `CorrectionEmailDialog.tsx`, `DocumentInbox.tsx`, `StatusBadge.tsx`
- `frontend/src/lib/review-fields.ts` (editable field groups, draft ↔ correction body) and
  `review-outcome.ts` (status copy, cross-check summary, supplier-fixable filter)

### What you should observe

- `evaluate_corpus.py` reports roughly 167–168/169 fields, 11–12/13 exact documents, the same
  number of policy matches, and 0 provider failures on Document Intelligence alone. The `PART`
  rows are Dutch compact invoices (`05`, sometimes `02`): DI skips the `Inkooporder` line on that
  layout, so it adds a `purchase_order_missing` warning. The hybrid pipeline fills that field from
  the LLM, and the app shows only the intended errors.
- `evaluate_hybrid.py` prints `PASS` for `02`, `05`, and `13`; `05` lists `purchase_order` under
  `fallback`, and `13` reports an `expense_category` conflict (`Fuel&Energy.Gas` vs `fuel`) that
  stays on the DI value.
- After upload, the review page order is: summary → Document Intelligence extraction (editable,
  provenance badges) → Independent LLM check (agreement / filled gaps / disagreements table) →
  Validation findings → GL account → Decision.
- `01`–`04`, `09`, `11`–`13` open as **Ready** with Approve enabled; `09` still shows the PO warning.
- `05`–`08` open as **Needs review**, Approve disabled with the reason, and **Draft correction
  email** on the DI card. `10` shows `duplicate_invoice` without the email button.
- Saving a corrected field re-runs policy immediately; the field badge changes to “Edited by
  reviewer”. Approving or rejecting locks every control and hides the Decision card.
- History lists every saved review with status; Delete removes the row and the stored file, and
  re-checking `10` afterwards clears the duplicate.

### Checkpoint

- [ ] Backend lint passes for `app` and `scripts`; frontend type-check, lint, and build pass.
- [ ] `evaluate_corpus.py` shows no provider failures; `evaluate_hybrid.py` passes on `02` and `13`.
- [ ] You can explain why the LLM reviewer never sees Document Intelligence output and never
      overwrites a present DI value.
- [ ] You can explain why `duplicate_invoice` blocks approval but does not offer a correction
      email, and why deleting the peer is the demo reset.
- [ ] The browser walkthrough above completes: approve, correct-and-approve, reject, draft email,
      delete, re-check.
- [ ] No auth, email sending, queues, or accounting integrations were introduced.

## Slice: Make it yours (Plurobi branding)

SOP so far: the review loop is complete under the tutorial's placeholder client. This slice swaps
that identity for your own brand so the demo reads as your product.

### Outcome

The fictional client is now **Plurobi B.V.** everywhere: the customer printed on every corpus
invoice, the customer VAT check's owner, prompts, UI copy, and docs. The React app uses the
Plurobi brand board: Open Sans, black surfaces for the header and welcome hero, orange
`#FF5D00` for primary actions and LLM-related accents, grey `#A7A7A7` for secondary text, and
the logo's green for completed pipeline stages. The ring mark is the favicon and header logo.

### Why

The customer name lives inside the sample PDFs and PNGs, so a text search is not enough; the
corpus is regenerated from `scripts/generate_samples.py` and the manifest follows. Brand tokens
are Tailwind `@theme` variables in `index.css`, so components reference `brand-500` or `mist`
instead of raw hex values and a future palette change is one file. Open Sans is loaded from Google
Fonts with a `<link>`, which adds no package dependency.

One finding worth keeping: a bare `Plurobi` as the customer name made Document Intelligence lose
`customer_name`, `customer_vat_id`, and even `vendor_name` on four samples. Adding the legal form
(`Plurobi B.V.`) restored every party field. DI leans on those cues to separate parties.

### Commands

```bash
cd backend
uv run --locked --no-sync python scripts/generate_samples.py
uv run --locked --no-sync ruff check app scripts
uv run --locked --no-sync python -m scripts.evaluate_corpus
```

```bash
cd frontend
pnpm exec tsc -b --pretty false
pnpm lint
pnpm build
```

Delete `backend/data/documents.db` and `backend/data/uploads/` so old reviews with the previous
customer name do not appear in History.

### What you should observe

- A repo-wide search for the old client name or the tutorial author's name returns nothing
  outside lockfiles and binaries.
- `samples/manifest.json` lists `Plurobi B.V.` as `customer_name` on all twelve invoices.
- `evaluate_corpus.py` still has 0 provider failures; every party field matches.
- The welcome hero and header are black with the ring mark and the `Plurobi.` wordmark; primary
  buttons are orange; the tab title reads `Invoice Review · Plurobi`.

### Checkpoint

- [ ] Corpus regenerated and re-evaluated after the customer rename.
- [ ] Backend lint and frontend type-check/lint/build pass.
- [ ] You can explain why brand colors live in `@theme` rather than in each component.

Continue with the [online tutorial](https://learn.datalumina.com/docs/invoice-review).
