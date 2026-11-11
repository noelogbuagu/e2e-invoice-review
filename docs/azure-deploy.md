# Deploy Invoice Review to Azure

This is the complete runbook: build everything from an empty subscription, and tear everything down again. Follow "Build from nothing" top to bottom to deploy. Follow "Tear everything down" to stop all Azure charges.

The result is one container in `rg-invoice-review`. It serves the React build and the FastAPI API on one HTTPS URL. SQLite and uploads sit on an Azure Files share. The shared password is `APP_ACCESS_PASSWORD`. Nylas stays on the US API (`https://api.us.nylas.com`) even though this container runs in North Europe.

Run every command from the repo root unless a step says otherwise. Deploy from a branch that contains the root `Dockerfile` and this file (currently `dev`).

## Prerequisites

- Azure CLI signed in to the intended subscription, with the `containerapp` extension (`az extension add --name containerapp --upgrade`).
- `uv`, `python3`, `openssl`, `curl`.
- A Nylas sandbox: API key, client ID, and the grant ID of the demo mailbox. These live only in the Nylas dashboard and your gitignored `backend/.env`. Nothing in Azure holds them. Keep a copy of `backend/.env` outside the repo before any teardown.
- `backend/.env` exists (copy `backend/.env.example`). The steps below overwrite its Azure endpoints and keys with the new ones.

## Names

```bash
RG=rg-invoice-review
RG_LOCATION=westeurope
LOCATION=northeurope            # hosting + Document Intelligence
AI_LOCATION=swedencentral       # Foundry + model deployment
DI_NAME=di-invoice-review
FOUNDRY_NAME=foundry-invoice-review
FOUNDRY_PROJECT=prj-invoice-review
MODEL_DEPLOYMENT=gpt-5.6-terra
ACR_NAME=acrinvreviewweu
STORAGE_NAME=stinvreviewweu
SHARE_NAME=invoice-review-data
ENV_NAME=cae-invoice-review
APP_NAME=ca-invoice-review
STORAGE_DEF=invoice-review-files

az account show --output table
```

ACR, storage, Foundry, and Document Intelligence names are globally unique. If create fails on a name, append a short suffix and use it everywhere. The group is in West Europe, but West Europe returned `locationineligible` for new Container Registry and new Cognitive Services resources, so those use North Europe. (The `weu` in two resource names is historical; they are in North Europe.) The Nylas sandbox stays on `https://api.us.nylas.com`.

## Build from nothing

### 1. Resource group

```bash
az group create --name "$RG" --location "$RG_LOCATION" --output table
```

### 2. Document Intelligence

Free tier: 500 analyzed pages per month, no standing cost. Only one F0 per subscription is allowed, so a leftover soft-deleted account blocks this (see "Tear everything down").

```bash
az cognitiveservices account create \
  --name "$DI_NAME" \
  --resource-group "$RG" \
  --kind FormRecognizer \
  --sku F0 \
  --location "$LOCATION" \
  --custom-domain "$DI_NAME" \
  --yes \
  --output table

az cognitiveservices account show -n "$DI_NAME" -g "$RG" \
  --query "{state:properties.provisioningState,endpoint:properties.endpoint}" -o json
```

The first deployment of this project created this account in the portal. The command above is the CLI equivalent, checked against `az cognitiveservices account create --help` and `list-skus` but not yet run end to end. If it fails on the custom domain, append a suffix to `--custom-domain`, or drop the flag and use the regional endpoint it returns. The app only needs the endpoint and key from the next step.

### 3. Foundry and the model deployment

```bash
az cognitiveservices model list \
  --location "$AI_LOCATION" \
  --query "[?model.name=='$MODEL_DEPLOYMENT'].{version:model.version,skus:join(',',model.skus[].name)}" \
  --output table

az cognitiveservices account create \
  --name "$FOUNDRY_NAME" \
  --resource-group "$RG" \
  --kind AIServices \
  --sku S0 \
  --location "$AI_LOCATION" \
  --custom-domain "$FOUNDRY_NAME" \
  --assign-identity \
  --allow-project-management true \
  --yes \
  --output table

az cognitiveservices account project create \
  --name "$FOUNDRY_NAME" \
  --resource-group "$RG" \
  --project-name "$FOUNDRY_PROJECT" \
  --location "$AI_LOCATION" \
  --output table

az cognitiveservices account deployment create \
  --name "$FOUNDRY_NAME" \
  --resource-group "$RG" \
  --deployment-name "$MODEL_DEPLOYMENT" \
  --model-name "$MODEL_DEPLOYMENT" \
  --model-version "2026-07-09" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name GlobalStandard \
  --output table

az cognitiveservices account deployment show \
  --name "$FOUNDRY_NAME" --resource-group "$RG" --deployment-name "$MODEL_DEPLOYMENT" \
  --query '{state:properties.provisioningState,model:properties.model.name,sku:sku.name}' -o json
```

Expect `Succeeded`. If the model version is no longer listed, use the version the list prints. If the region returns `locationineligible`, retry `northeurope`, then `uksouth`, and list the model there first. The deployment is pay per token with no standing cost.

### 4. Point `backend/.env` at the new resources

Both accounts get new keys on every rebuild. Print the values and paste them into `backend/.env` over the old ones. Do not commit that file.

```bash
echo "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=$(az cognitiveservices account show -n "$DI_NAME" -g "$RG" --query properties.endpoint -o tsv)"
echo "AZURE_DOCUMENT_INTELLIGENCE_KEY=$(az cognitiveservices account keys list -n "$DI_NAME" -g "$RG" --query key1 -o tsv)"
echo "AZURE_OPENAI_ENDPOINT=$(az cognitiveservices account show -n "$FOUNDRY_NAME" -g "$RG" --query properties.endpoint -o tsv)openai/v1/"
echo "AZURE_OPENAI_DEPLOYMENT=$MODEL_DEPLOYMENT"
echo "AZURE_OPENAI_API_KEY=$(az cognitiveservices account keys list -n "$FOUNDRY_NAME" -g "$RG" --query key1 -o tsv)"
```

Keep the Nylas values (`NYLAS_API_KEY`, `NYLAS_CLIENT_ID`, `NYLAS_GRANT_ID`) as they are. `WEBHOOK_SECRET` and `SERVER_URL` are set again in "Point Nylas at the app".

Optional check before hosting: `./scripts/dev.sh`, then process one sample from `samples/generated/`.

## Hosting

Continue in order: Secrets, Registry and image, Storage for SQLite, Container Apps environment, Create the app, Mount Azure Files, Point Nylas at the app, Verify. The variables from "Names" must still be set in your shell.

## Secrets

From the repo root, load the local provider settings and generate the password. Save the password somewhere outside the repo. It is not written back to `backend/.env`, so local `./scripts/dev.sh` stays unlocked.

```bash
set -a
source backend/.env
set +a

APP_ACCESS_PASSWORD="$(openssl rand -base64 18)"
APP_SESSION_SECRET="$(openssl rand -hex 32)"
printf '%s\n' "$APP_ACCESS_PASSWORD" > "$HOME/.invoice-review-access-password"
chmod 600 "$HOME/.invoice-review-access-password"

OPENAI_EP="$AZURE_OPENAI_ENDPOINT"
case "$OPENAI_EP" in
  */openai/v1|*/openai/v1/) ;;
  */) OPENAI_EP="${OPENAI_EP}openai/v1/" ;;
  *) OPENAI_EP="${OPENAI_EP}/openai/v1/" ;;
esac
```

## Registry and image

`az acr build` builds the root `Dockerfile` on Azure. Docker Desktop is optional. The frontend build bakes `VITE_API_BASE_URL=/`.

```bash
az acr create \
  --resource-group "$RG" \
  --name "$ACR_NAME" \
  --sku Basic \
  --location "$LOCATION"

az acr update --name "$ACR_NAME" --admin-enabled true

ACR_USER="$(az acr credential show -n "$ACR_NAME" --query username -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR_NAME" --query 'passwords[0].value' -o tsv)"

az acr build \
  --registry "$ACR_NAME" \
  --resource-group "$RG" \
  --image invoice-review:latest \
  .
```

## Storage for SQLite

```bash
az storage account create \
  --resource-group "$RG" \
  --name "$STORAGE_NAME" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2

STORAGE_KEY="$(az storage account keys list \
  --resource-group "$RG" \
  --account-name "$STORAGE_NAME" \
  --query '[0].value' -o tsv)"

az storage share create \
  --account-name "$STORAGE_NAME" \
  --account-key "$STORAGE_KEY" \
  --name "$SHARE_NAME"
```

## Container Apps environment

```bash
az containerapp env create \
  --resource-group "$RG" \
  --name "$ENV_NAME" \
  --location "$LOCATION"

az containerapp env show -g "$RG" -n "$ENV_NAME" \
  --query properties.provisioningState -o tsv
```

Wait until that prints `Succeeded`.

```bash
az containerapp env storage set \
  --resource-group "$RG" \
  --name "$ENV_NAME" \
  --storage-name "$STORAGE_DEF" \
  --azure-file-account-name "$STORAGE_NAME" \
  --azure-file-account-key "$STORAGE_KEY" \
  --azure-file-share-name "$SHARE_NAME" \
  --access-mode ReadWrite
```

## Create the app

Min and max replicas stay at 1. A second replica on this share fails with `sqlite3.OperationalError: database is locked`.

```bash
az containerapp create \
  --resource-group "$RG" \
  --name "$APP_NAME" \
  --environment "$ENV_NAME" \
  --image "$ACR_NAME.azurecr.io/invoice-review:latest" \
  --registry-server "$ACR_NAME.azurecr.io" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --secrets \
    "di-key=$AZURE_DOCUMENT_INTELLIGENCE_KEY" \
    "openai-key=$AZURE_OPENAI_API_KEY" \
    "access-password=$APP_ACCESS_PASSWORD" \
    "session-secret=$APP_SESSION_SECRET" \
    "nylas-key=$NYLAS_API_KEY" \
    "nylas-grant=$NYLAS_GRANT_ID" \
    "webhook-secret=$WEBHOOK_SECRET" \
  --env-vars \
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=$AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT" \
    "AZURE_DOCUMENT_INTELLIGENCE_KEY=secretref:di-key" \
    "AZURE_OPENAI_ENDPOINT=$OPENAI_EP" \
    "AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT:-gpt-5.6-terra}" \
    "AZURE_OPENAI_API_KEY=secretref:openai-key" \
    "APP_ACCESS_PASSWORD=secretref:access-password" \
    "APP_SESSION_SECRET=secretref:session-secret" \
    "NYLAS_API_KEY=secretref:nylas-key" \
    "NYLAS_GRANT_ID=secretref:nylas-grant" \
    "NYLAS_API_URI=https://api.us.nylas.com" \
    "WEBHOOK_SECRET=secretref:webhook-secret" \
    "FRONTEND_DIST_DIR=/app/frontend/dist"
```

Keys, the password, the session secret, the Nylas key, the grant id, and the webhook secret are secrets. Endpoints, the deployment name, and `NYLAS_API_URI` are plain variables.

```bash
FQDN="$(az containerapp show -g "$RG" -n "$APP_NAME" --query properties.configuration.ingress.fqdn -o tsv)"
echo "App URL: https://$FQDN"

az containerapp update \
  --resource-group "$RG" \
  --name "$APP_NAME" \
  --set-env-vars \
    "ALLOWED_ORIGIN=https://$FQDN" \
    "SERVER_URL=https://$FQDN"
```

## Mount Azure Files at /app/data

`az containerapp create` cannot attach the volume. Export the app, add the mount, and apply it. This Python uses only the standard library.

```bash
az containerapp show -g "$RG" -n "$APP_NAME" -o json > /tmp/ca-app.json

python3 - <<'PY'
import json
from pathlib import Path

def scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return json.dumps(value)

def dump(value, level=0):
    space = "  " * level
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for key, item in value.items():
            key_s = key if key.replace("-", "_").isidentifier() else json.dumps(key)
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{space}{key_s}:")
                lines.append(dump(item, level + 1))
            else:
                lines.append(f"{space}{key_s}: {scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)) and item:
                nested = dump(item, level + 1).splitlines()
                lines.append(f"{space}- {nested[0].strip()}")
                lines.extend(nested[1:])
            else:
                lines.append(f"{space}- {scalar(item)}")
        return "\n".join(lines)
    return scalar(value)

app = json.loads(Path("/tmp/ca-app.json").read_text())
template = app["properties"]["template"]
template["volumes"] = [
    {"name": "data", "storageType": "AzureFile", "storageName": "invoice-review-files"}
]
container = template["containers"][0]
container["volumeMounts"] = [{"volumeName": "data", "mountPath": "/app/data"}]
kept = {key: app[key] for key in ("identity", "location", "properties", "tags") if key in app}
Path("/tmp/ca-app.yaml").write_text(dump(kept) + "\n")
PY

az containerapp update \
  --resource-group "$RG" \
  --name "$APP_NAME" \
  --yaml /tmp/ca-app.yaml

az containerapp show -g "$RG" -n "$APP_NAME" \
  --query "{volumes:properties.template.volumes,mounts:properties.template.containers[0].volumeMounts,scale:properties.template.scale}" \
  -o json
```

`scale.minReplicas` and `scale.maxReplicas` must both be 1. A failed revision can sit next to a healthy one. Traffic goes to `latestReadyRevisionName`, not the latest attempt. SQLite on this share uses `nolock` because Azure Files does not honor SQLite's file locks. That is safe only while a single replica is writing.

## Point Nylas at the app

The sandbox is the US app. Keep `NYLAS_API_URI=https://api.us.nylas.com`. Register a webhook for this URL, then store the new secret on the container. Replace the notification address with yours. Delete older Pinggy destinations in the Nylas dashboard. Nylas calls every active webhook.

```bash
cd backend
SERVER_URL="https://$FQDN" uv run --locked --no-sync \
  python -m scripts.config_nylas_webhook you@example.com
cd ..
```

Copy the printed `WEBHOOK_SECRET` into the container. Do not commit it.

```bash
az containerapp secret set \
  --resource-group "$RG" \
  --name "$APP_NAME" \
  --secrets "webhook-secret=$WEBHOOK_SECRET"

az containerapp update \
  --resource-group "$RG" \
  --name "$APP_NAME" \
  --set-env-vars "WEBHOOK_SECRET=secretref:webhook-secret"
```

`secret set` changes the stored value. The env var already points at `secretref:webhook-secret`; the update makes the new revision pick it up.

## Verify

```bash
curl -s "https://$FQDN/health"
curl -s -o /dev/null -w "%{http_code}\n" "https://$FQDN/api/documents"

curl -s -c /tmp/ir-cookies.txt -b /tmp/ir-cookies.txt \
  -H "Content-Type: application/json" \
  -d "{\"password\":\"$APP_ACCESS_PASSWORD\"}" \
  "https://$FQDN/api/auth/login"
```

Expect `{"status":"ok"}`, `401`, then `{"auth_enabled":true,"authenticated":true}`. Open `https://$FQDN`, sign in with the saved password, and process one fictional invoice. Restart the active revision and confirm History still lists it.

## Tear everything down

This removes every Azure resource this project created and stops all charges. Nothing in the repo or in Nylas is touched. The review history (SQLite and uploads) is deleted with the storage account unless you back it up first.

### 1. Back up what Azure will delete

```bash
BACKUP="$HOME/invoice-review-backup-$(date +%F)"
mkdir -p "$BACKUP/data" && chmod 700 "$BACKUP"
STORAGE_KEY="$(az storage account keys list -g "$RG" --account-name "$STORAGE_NAME" --query '[0].value' -o tsv)"

az storage file download-batch \
  --account-name "$STORAGE_NAME" --account-key "$STORAGE_KEY" \
  --source "$SHARE_NAME" --destination "$BACKUP/data"

cp backend/.env "$BACKUP/backend.env"
ls -lR "$BACKUP"
```

Keep the backup outside the repo. It holds `documents.db`, the uploaded files, and your keys. To restore after a rebuild, once the share exists (step "Storage for SQLite"), upload `$BACKUP/data` back before the app first starts: `az storage file upload-batch --account-name "$STORAGE_NAME" --account-key "$STORAGE_KEY" --destination "$SHARE_NAME" --source "$BACKUP/data"`.

### 2. Delete the Azure resources

Order matters. Delete the Cognitive Services accounts, purge them, then delete the group.

```bash
az containerapp delete --resource-group "$RG" --name "$APP_NAME" --yes
az containerapp env delete --resource-group "$RG" --name "$ENV_NAME" --yes
az acr delete --resource-group "$RG" --name "$ACR_NAME" --yes
az storage account delete --resource-group "$RG" --name "$STORAGE_NAME" --yes

az cognitiveservices account delete --resource-group "$RG" --name "$FOUNDRY_NAME"
az cognitiveservices account delete --resource-group "$RG" --name "$DI_NAME"
```

Azure keeps a deleted Cognitive Services account in a soft-deleted state and reserves its name and custom domain. Rebuilding with the same names fails until it is purged. Purge both:

```bash
az cognitiveservices account list-deleted --query "[].{name:name,location:location}" -o table

az cognitiveservices account purge --name "$FOUNDRY_NAME" --resource-group "$RG" --location "$AI_LOCATION"
az cognitiveservices account purge --name "$DI_NAME" --resource-group "$RG" --location "$LOCATION"

az cognitiveservices account list-deleted -o table    # expect no rows
```

Then delete the group. This also removes the Log Analytics workspace the Container Apps environment created (`workspace-rginvoicereview...`).

```bash
az group delete --name "$RG" --yes
```

### 3. Confirm nothing is left

```bash
az group list -o table                   # rg-invoice-review is gone
az resource list -o table                # no invoice-review resources
az cognitiveservices account list-deleted -o table
```

### 4. Clean up outside Azure

- Nylas dashboard: delete the webhook destination that points at the old app URL. The next deployment gets a new URL, and Nylas calls every active webhook.
- Remove stale local values: the old `WEBHOOK_SECRET` and `SERVER_URL` in `backend/.env`, and the old Azure keys (they stop working after the teardown).
- `~/.invoice-review-access-password` and `~/.invoice-review-session-secret` are regenerated on the next deployment. Delete them if you want.
- Azure Cost Management can lag by a day. Check the subscription's cost page the next day to confirm charges stopped.

### Rebuilding the next day

Follow "Build from nothing" from step 1. After step 4, run the Hosting sections in order, restore the backup if you want the old history, then "Point Nylas at the app" and "Verify". If step 2 or 3 fails on a name, the soft-deleted account was not purged: run `az cognitiveservices account list-deleted` and purge it.
