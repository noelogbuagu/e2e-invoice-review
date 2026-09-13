"""Orchestrates Document Intelligence extraction into domain schemas."""

from pathlib import Path

from app.providers.azure_document_intelligence import AzureDocumentIntelligenceProvider
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt


class DocumentIntelligenceService:
    def __init__(self, provider: AzureDocumentIntelligenceProvider | None = None) -> None:
        self._provider = provider or AzureDocumentIntelligenceProvider()

    def analyze_invoice(self, document_path: Path | str) -> Invoice:
        return self._provider.analyze_invoice(document_path)

    def analyze_receipt(self, document_path: Path | str) -> Receipt:
        return self._provider.analyze_receipt(document_path)
