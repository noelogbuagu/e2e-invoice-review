# Deploy Invoice Review to Azure

One container in the existing `rg-invoice-review` group. It serves the React build and the FastAPI API on one HTTPS URL. SQLite and uploads sit on an Azure Files share. The shared password is `APP_ACCESS_PASSWORD`. Nylas stays on the US API (`https://api.us.nylas.com`) even though this container runs in West Europe.

Do not recreate Document Intelligence or Foundry. Do not run `az group delete`.

## Names

```bash
RG=rg-invoice-review
LOCATION=northeurope
ACR_NAME=acrinvreviewweu
STORAGE_NAME=stinvreviewweu
SHARE_NAME=invoice-review-data
ENV_NAME=cae-invoice-review
APP_NAME=ca-invoice-review
STORAGE_DEF=invoice-review-files

az account show --output table
az group show --name "$RG" --query "{name:name,location:location}" --output table
```

ACR and storage account names are globally unique. If create fails on the name, append a short suffix and use it everywhere below. The resource group stays in West Europe. New hosting resources use North Europe: West Europe returned `locationineligible` for a new Container Registry, the same constraint that placed Document Intelligence outside West Europe. The Nylas sandbox stays on `https://api.us.nylas.com`.

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

## Clean up the host only

```bash
az containerapp delete --resource-group "$RG" --name "$APP_NAME" --yes
az containerapp env delete --resource-group "$RG" --name "$ENV_NAME" --yes
az acr delete --resource-group "$RG" --name "$ACR_NAME" --yes
az storage account delete --resource-group "$RG" --name "$STORAGE_NAME" --yes
```

The environment creates a Log Analytics workspace. Delete that too if it is still in the group. Leave the resource group, Document Intelligence, and Foundry in place.
