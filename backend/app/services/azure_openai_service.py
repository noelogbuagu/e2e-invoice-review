"""Azure OpenAI client for Responses API calls."""

from app.providers.azure_openai import AzureOpenAIProvider


class AzureOpenAIService:
    def __init__(self, provider: AzureOpenAIProvider | None = None) -> None:
        self._provider = provider or AzureOpenAIProvider()

    def create_response(self, prompt: str) -> str:
        return self._provider.create_response(prompt)
