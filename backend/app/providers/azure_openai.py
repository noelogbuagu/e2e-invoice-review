from openai import OpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.azure import AzureProvider

from app.config import Settings, get_settings


def build_responses_model(settings: Settings | None = None) -> OpenAIResponsesModel:
    """Pydantic AI model bound to the Foundry deployment for structured-output agents."""
    resolved = settings or get_settings()
    return OpenAIResponsesModel(
        model_name=resolved.azure_openai_deployment,
        provider=AzureProvider(
            azure_endpoint=resolved.azure_openai_endpoint,
            api_key=resolved.azure_openai_api_key,
        ),
    )


class AzureOpenAIProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or Settings()
        self._client = OpenAI(
            base_url=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
        )
        self._deployment = settings.azure_openai_deployment

    def create_response_result(self, prompt: str):
        return self._client.responses.create(
            model=self._deployment,
            input=prompt,
        )

    def create_response(self, prompt: str) -> str:
        response = self.create_response_result(prompt)
        text = response.output_text
        if not text:
            raise ValueError("Azure OpenAI response contained no text")
        return text
