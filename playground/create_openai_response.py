"""Send a prompt through the Azure OpenAI Responses API.

Edit PROMPT below, then run main() in the interactive window.
Terminal: uv run --project ../backend --locked --no-sync python create_openai_response.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import bootstrap  # noqa: F401

from app.providers.azure_openai import AzureOpenAIProvider

PROMPT = "What is the capital of France?"


def main() -> None:
    response = AzureOpenAIProvider().create_response_result(PROMPT)
    print(json.dumps(response.model_dump(mode="json"), indent=2, default=str))
    print(response.output_text)


if __name__ == "__main__":
    main()
