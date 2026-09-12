"""Azure Document Intelligence client for invoice extraction."""

from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from azure.core.credentials import AzureKeyCredential

from app.config import Settings

INVOICE_MODEL = "prebuilt-invoice"


class DocumentIntelligenceService:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or Settings()
        self._client = DocumentIntelligenceClient(
            endpoint=settings.azure_document_intelligence_endpoint,
            credential=AzureKeyCredential(settings.azure_document_intelligence_key),
        )

    def analyze_invoice(self, document_path: Path | str) -> AnalyzeResult:
        path = Path(document_path)
        if not path.is_file():
            raise FileNotFoundError(f"Invoice document not found: {path}")

        poller = self._client.begin_analyze_document(
            INVOICE_MODEL,
            AnalyzeDocumentRequest(bytes_source=path.read_bytes()),
        )
        return poller.result()
