# Playground

Scratch scripts for inspecting live Azure output before it becomes application code.

Run scripts from this folder. They resolve samples and write JSON relative to the repository root.

```bash
cd playground
uv run --project ../backend --locked --no-sync python inspect_invoice.py
uv run --project ../backend --locked --no-sync python inspect_invoice.py ../samples/generated/05-nl-missing-vendor-vat.pdf
uv run --project ../backend --locked --no-sync python map_schemas.py
uv run --project ../backend --locked --no-sync python create_openai_response.py
uv run --project ../backend --locked --no-sync python create_openai_response.py "What is 2 plus 2?"
uv run --project ../backend --locked --no-sync python classify_sample_document.py
uv run --project ../backend --locked --no-sync python classify_sample_document.py ../samples/generated/13-nl-fuel-receipt.png
```

`inspect_invoice.py` dumps a raw `AnalyzeResult` (default happy-path invoice, or any document path). `map_schemas.py` fills the Pydantic invoice and receipt models and compares them to `samples/manifest.json`. Cached files under `output/` are reused so repeat runs do not spend extra Azure pages. `create_openai_response.py` sends a prompt, or the contents of a text file, through the Azure OpenAI Responses API. `classify_sample_document.py` sends the original PDF or image through the Pydantic AI classifier and prints a typed invoice/receipt label.
