# Playground

Scratch scripts for inspecting live Azure output before it becomes application code.

**Primary workflow:** open a script in the interactive window, edit the constants at the top (`DOCUMENT_PATH`, `PROMPT`, and so on), then run `main()`. `bootstrap.py` patches asyncio, turns on INFO logging, and wires up backend imports so sync APIs work from a notebook kernel.

**Secondary workflow:** run from the terminal when you need a copy-paste command for the build-along.

```bash
cd playground
uv run --project ../backend --locked --no-sync python analyse_sample_invoice.py
uv run --project ../backend --locked --no-sync python map_extraction_samples.py
uv run --project ../backend --locked --no-sync python create_openai_response.py
uv run --project ../backend --locked --no-sync python classify_sample_document.py
uv run --project ../backend --locked --no-sync python process_sample_document.py
```

`analyse_sample_invoice.py` dumps a raw `AnalyzeResult` for one sample. `map_extraction_samples.py` fills the Pydantic invoice and receipt models and compares them to `samples/manifest.json`. Cached files under `output/` are reused so repeat runs do not spend extra Azure pages. `create_openai_response.py` sends a prompt through the Azure OpenAI Responses API. `classify_sample_document.py` sends the original PDF or image through the Pydantic AI classifier and prints a typed invoice/receipt label. `process_sample_document.py` chains classification, extraction, Northstar policy, and a GL suggestion; INFO logs show each pipeline step. The GL suggestion is a hint only — a reviewer can override it later.
