from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, Field


class ReceiptLineItem(BaseModel):
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class Receipt(BaseModel):
    merchant_name: str | None = None
    merchant_address: str | None = None
    transaction_date: date | None = None
    transaction_time: time | None = None
    expense_category: str | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    total_tax: Decimal | None = None
    total: Decimal | None = None
    items: list[ReceiptLineItem] = Field(default_factory=list)
    confidence: float | None = None
