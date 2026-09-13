from pathlib import Path
from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

from app.config import Settings
from app.schemas.invoice.mapping import from_analyze_result as invoice_from_analyze_result
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.mapping import from_analyze_result as receipt_from_analyze_result
from app.schemas.receipt.model import Receipt

INVOICE_MODEL = "prebuilt-invoice"
RECEIPT_MODEL = "prebuilt-receipt"


class AzureDocumentIntelligenceProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or Settings()
        self._client = DocumentIntelligenceClient(
            endpoint=settings.azure_document_intelligence_endpoint,
            credential=AzureKeyCredential(settings.azure_document_intelligence_key),
        )

    def analyze(self, document_path: Path | str, model_id: str) -> dict[str, Any]:
        path = Path(document_path)
        if not path.is_file():
            raise FileNotFoundError(f"Document not found: {path}")

        poller = self._client.begin_analyze_document(
            model_id,
            AnalyzeDocumentRequest(bytes_source=path.read_bytes()),
        )
        return poller.result().as_dict()

    def analyze_invoice(self, document_path: Path | str) -> Invoice:
        return invoice_from_analyze_result(self.analyze(document_path, INVOICE_MODEL))

    def analyze_receipt(self, document_path: Path | str) -> Receipt:
        return receipt_from_analyze_result(self.analyze(document_path, RECEIPT_MODEL))
