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
uv run --project ../backend --locked --no-sync python create_openai_response.py "What is 2 plus 2?"
```

### What you should observe

- Ruff reports no issues.
- The terminal prints that Paris is the capital of France.
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
uv run --project ../backend --locked --no-sync python classify_sample_document.py ../samples/generated/13-nl-fuel-receipt.png
```

### What you should observe

- Ruff reports no issues.
- The happy-path invoice prints `"document_kind": "invoice"` with a short reason.
- The fuel receipt prints `"document_kind": "receipt"`.
- Endpoint, deployment name, and key still come from `Settings` / `backend/.env`.
- Two Responses calls on Global Standard.

### Checkpoint

- [ ] `pydantic-ai-slim[openai]==2.11.0` is pinned and locked.
- [ ] The classifier lives in `backend/app/pipeline/classification.py`.
- [ ] The playground script labels the sample invoice PDF and the fuel receipt PNG correctly.

Continue with the [online tutorial](https://learn.datalumina.com/docs/invoice-review).
