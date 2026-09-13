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
)
from app.schemas.invoice.model import Invoice, InvoiceLineItem

FIELDS = {
    "vendor_name": "VendorName",
    "vendor_vat_id": "VendorTaxId",
    "customer_name": "CustomerName",
    "customer_vat_id": "CustomerTaxId",
    "invoice_number": "InvoiceId",
    "invoice_date": "InvoiceDate",
    "due_date": "DueDate",
    "purchase_order": "PurchaseOrder",
    "subtotal": "SubTotal",
    "total_tax": "TotalTax",
    "invoice_total": "InvoiceTotal",
    "items": "Items",
}

LINE_ITEM_FIELDS = {
    "description": "Description",
    "quantity": "Quantity",
    "unit_price": "UnitPrice",
    "amount": "Amount",
}

CURRENCY_FIELDS = ("InvoiceTotal", "SubTotal", "TotalTax")


def from_analyze_result(payload: Mapping[str, Any]) -> Invoice:
    fields = document_fields(payload)
    return Invoice(
        vendor_name=string_value(fields, FIELDS["vendor_name"]).value,
        vendor_vat_id=string_value(fields, FIELDS["vendor_vat_id"]).value,
        customer_name=string_value(fields, FIELDS["customer_name"]).value,
        customer_vat_id=string_value(fields, FIELDS["customer_vat_id"]).value,
        invoice_number=string_value(fields, FIELDS["invoice_number"]).value,
        invoice_date=date_value(fields, FIELDS["invoice_date"]).value,
        due_date=date_value(fields, FIELDS["due_date"]).value,
        purchase_order=string_value(fields, FIELDS["purchase_order"]).value,
        currency=currency_code(fields, *CURRENCY_FIELDS).value,
        subtotal=money_value(fields, FIELDS["subtotal"]).value,
        total_tax=money_value(fields, FIELDS["total_tax"]).value,
        invoice_total=money_value(fields, FIELDS["invoice_total"]).value,
        items=[
            InvoiceLineItem(
                description=string_value(item, LINE_ITEM_FIELDS["description"]).value,
                quantity=decimal_value(item, LINE_ITEM_FIELDS["quantity"]).value,
                unit_price=money_value(item, LINE_ITEM_FIELDS["unit_price"]).value,
                amount=money_value(item, LINE_ITEM_FIELDS["amount"]).value,
            )
            for item in object_items(fields, FIELDS["items"])
        ],
        confidence=document_confidence(payload),
    )
