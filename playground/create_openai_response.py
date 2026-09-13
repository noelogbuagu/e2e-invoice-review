"""Send a prompt through AzureOpenAIService.

Run from this folder. Pass a prompt, or a text file to read:

    uv run --project ../backend --locked --no-sync python create_openai_response.py
    uv run --project ../backend --locked --no-sync python create_openai_response.py "What is 2 plus 2?"
    uv run --project ../backend --locked --no-sync python create_openai_response.py notes.txt
"""

from __future__ import annotations


import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"


sys.path.insert(0, str(BACKEND_ROOT))


from app.providers.azure_openai import AzureOpenAIProvider  # noqa: E402


def main() -> None:
    prompt = "What is the capital of France?"
    provider = AzureOpenAIProvider()
    response = provider.create_response_result(prompt)
    print(json.dumps(response.model_dump(mode="json"), indent=2, default=str))
    print(response.output_text)


if __name__ == "__main__":
    main()
