# Backend agent instructions

Read [../AGENTS.md](../AGENTS.md) first. The root file contains the project-wide product boundaries, dependency policy, teaching rules, and verification policy. This file adds backend-specific conventions.

## Stack

- Python 3.12 or newer.
- `uv` for dependency and project management.
- FastAPI and uvicorn for the HTTP service.
- Pydantic v2 and pydantic-settings for typed boundaries and provider settings.
- SQLAlchemy 2 with local SQLite persistence.
- Azure AI Document Intelligence and Azure OpenAI behind provider adapters.
- Ruff for linting and import/style checks.

The stack is locked unless Obi explicitly approves a change.

## Layout

The starter branch intentionally contains only `app/.gitkeep`. Create the implementation during the build using these boundaries:

```text
backend/
├── app/
│   ├── main.py              # FastAPI construction and dependency wiring
│   ├── config.py            # Provider settings and fixed application config
│   ├── database.py          # SQLAlchemy engine and session factory
│   ├── documents/           # HTTP, orchestration, and SQLite persistence
│   ├── invoices/            # Deterministic invoice and receipt policy
│   ├── pipeline/            # Ordered classify → extract → validate → GL steps
│   ├── accounting/          # Fixed GL catalog, validated selections, and catalog HTTP
│   ├── schemas/             # Typed Document Intelligence invoice/receipt models
│   ├── services/            # Thin Azure clients used by pipeline/playground
│   ├── providers/           # Azure SDK adapters; SDK types stop here
│   ├── document_review/     # Provider-independent review and reconciliation (later)
│   └── correction_email/    # Eligibility and provider-independent draft models (later)
├── scripts/                 # Explicit provider checks and corpus evaluations
├── pyproject.toml
└── uv.lock
```

Do not create empty architectural layers before the tutorial reaches them.

## Boundaries and code style

- Routes own HTTP parsing, response models, and status-code translation.
- Services orchestrate the user workflow and depend on explicit interfaces.
- Repositories own SQLAlchemy and SQLite access.
- Provider adapters are the only modules allowed to expose third-party SDK types.
- Deterministic validation and reconciliation remain separate from AI extraction or generation.
- Keep public functions typed and modules focused. Prefer dataclasses, enums, `pathlib`, and other standard-library capabilities over helper packages.
- Validate files, HTTP input, provider output, and database writes at their boundaries. Do not repeatedly validate trusted internal calls.
- The current Azure and SQLite clients are synchronous. Use normal FastAPI `def` handlers for synchronous request paths instead of blocking an async event loop.
- Do not add auth, queues, workers, caching, analytics, deployment code, or accounting integrations unless the user story changes.

## Configuration

- `app/config.py` is the only backend configuration boundary.
- Provider endpoints, deployments, and credentials are read through its Pydantic `Settings` model.
- Fixed tutorial policy belongs in its immutable application configuration, not environment variables.
- Never call `os.getenv`, read `os.environ`, or call `load_dotenv` in application modules or scripts.
- Fail clearly when required provider configuration is absent. Do not hide configuration failures behind silent fallbacks.
- Never commit `.env`, Azure keys, uploaded documents, SQLite databases, or generated runtime data.

## Dependencies

- Never add a dependency without Obi's explicit approval.
- Use exact direct versions and commit `uv.lock` with every approved dependency change.
- Keep `add-bounds = "exact"` and `exclude-newer = "7 days"` under `[tool.uv]`.
- Install with `uv sync --locked`.
- Commands that must use the existing environment run through `uv run --locked --no-sync`.
- Prefer a small local function when a dependency would only replace a few clear standard-library lines.

## Verification

The starter has no backend implementation. Verify it only with:

```bash
uv sync --locked
```

As implementation is added, keep the documented backend check green:

```bash
uv run --locked --no-sync ruff check app
```

If the SQLite schema changes during development, delete `backend/data/documents.db` so `create_all` recreates the table with the new columns.

Provider checks and corpus evaluations may consume paid or limited Azure capacity. Document the tier, expected calls, limits, and cleanup command before running them. Complete verification also includes startup readiness and the manual end-to-end workflow.

Do not add `tests/`, `pytest`, or committed automated test files. This weekly teaching project uses linting, explicit provider/corpus checks, and manual workflow verification as defined by the root instructions.
