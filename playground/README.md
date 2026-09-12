# Playground

Scratch scripts for inspecting live Azure output before it becomes application code.

Run inspect scripts from this folder. They resolve sample invoices and write JSON relative to the repository root, so the current working directory does not matter as long as you use the command below.

```bash
cd playground
uv run --project ../backend --locked --no-sync python inspect_invoice.py
```

That call uses one Document Intelligence page against `samples/generated/01-en-happy-classic.pdf`. The terminal prints extracted invoice fields; the full `AnalyzeResult` lands in `playground/output/`.
