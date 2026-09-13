from openai import OpenAI

from app.config import Settings


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
