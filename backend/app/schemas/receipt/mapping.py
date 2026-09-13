from collections.abc import Mapping
from typing import Any

from app.schemas.common import (
    currency_code,
    date_value,
    decimal_value,
    document_confidence,
    document_fields,
    money_value,
    object_items,
    string_value,
    time_value,
)
from app.schemas.receipt.model import Receipt, ReceiptLineItem

FIELDS = {
    "merchant_name": "MerchantName",
    "merchant_address": "MerchantAddress",
    "transaction_date": "TransactionDate",
    "transaction_time": "TransactionTime",
    "expense_category": "ReceiptType",
    "subtotal": "Subtotal",
    "total_tax": "TotalTax",
    "total": "Total",
    "items": "Items",
}

LINE_ITEM_FIELDS = {
    "description": "Description",
    "quantity": "Quantity",
    "unit_price": "Price",
    "amount": "TotalPrice",
}

CURRENCY_FIELDS = ("Total", "Subtotal", "TotalTax")


def from_analyze_result(payload: Mapping[str, Any]) -> Receipt:
    fields = document_fields(payload)
    return Receipt(
        merchant_name=string_value(fields, FIELDS["merchant_name"]).value,
        merchant_address=string_value(fields, FIELDS["merchant_address"]).value,
        transaction_date=date_value(fields, FIELDS["transaction_date"]).value,
        transaction_time=time_value(fields, FIELDS["transaction_time"]).value,
        expense_category=string_value(fields, FIELDS["expense_category"]).value,
        currency=currency_code(fields, *CURRENCY_FIELDS).value,
        subtotal=money_value(fields, FIELDS["subtotal"]).value,
        total_tax=money_value(fields, FIELDS["total_tax"]).value,
        total=money_value(fields, FIELDS["total"]).value,
        items=[
            ReceiptLineItem(
                description=string_value(item, LINE_ITEM_FIELDS["description"]).value,
                quantity=decimal_value(item, LINE_ITEM_FIELDS["quantity"]).value,
                unit_price=money_value(item, LINE_ITEM_FIELDS["unit_price"]).value,
                amount=money_value(item, LINE_ITEM_FIELDS["amount"]).value,
            )
            for item in object_items(fields, FIELDS["items"])
        ],
        confidence=document_confidence(payload),
    )
