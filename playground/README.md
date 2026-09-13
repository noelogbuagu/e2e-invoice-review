# Playground

Scratch scripts for inspecting live Azure output before it becomes application code.

Run scripts from this folder. They resolve samples and write JSON relative to the repository root.

```bash
cd playground
uv run --project ../backend --locked --no-sync python inspect_invoice.py
uv run --project ../backend --locked --no-sync python map_schemas.py
```

`inspect_invoice.py` dumps a raw `AnalyzeResult`. `map_schemas.py` fills the Pydantic invoice and receipt models and compares them to `samples/manifest.json`. Cached files under `output/` are reused so repeat runs do not spend extra Azure pages.
