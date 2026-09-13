"""Shared extracted-value wrappers and Document Intelligence field parsers."""

from collections.abc import Mapping
from datetime import date, time
from decimal import Decimal
from typing import Any, cast

from pydantic import BaseModel, ConfigDict

type Field = Mapping[str, Any]
type Fields = Mapping[str, Field]


class ExtractedValue[T](BaseModel):
    model_config = ConfigDict(frozen=True)

    value: T | None = None
    confidence: float | None = None


def first_document(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    documents = payload.get("documents") or []
    if not documents:
        raise ValueError("AnalyzeResult contains no documents")
    return cast(Mapping[str, Any], documents[0])


def document_fields(payload: Mapping[str, Any]) -> Fields:
    return first_document(payload).get("fields") or {}


def document_confidence(payload: Mapping[str, Any]) -> float | None:
    confidence = first_document(payload).get("confidence")
    return float(confidence) if confidence is not None else None


def _field(fields: Fields, name: str) -> Field | None:
    value = fields.get(name)
    return value if isinstance(value, Mapping) else None


def _extracted[T](field: Field | None, value: T | None) -> ExtractedValue[T]:
    if field is None or field.get("confidence") is None:
        return ExtractedValue(value=value)
    return ExtractedValue(value=value, confidence=float(field["confidence"]))


def string_value(fields: Fields, name: str) -> ExtractedValue[str]:
    field = _field(fields, name)
    if field is None:
        return ExtractedValue()
    raw = field.get("valueString") or field.get("content")
    if raw is None:
        return _extracted(field, None)
    text = str(raw).strip()
    return _extracted(field, text or None)


def date_value(fields: Fields, name: str) -> ExtractedValue[date]:
    field = _field(fields, name)
    if field is None:
        return ExtractedValue()
    raw = field.get("valueDate")
    if isinstance(raw, date):
        return _extracted(field, raw)
    if isinstance(raw, str) and raw:
        return _extracted(field, date.fromisoformat(raw))
    return _extracted(field, None)


def time_value(fields: Fields, name: str) -> ExtractedValue[time]:
    field = _field(fields, name)
    if field is None:
        return ExtractedValue()
    raw = field.get("valueTime")
    if isinstance(raw, time):
        return _extracted(field, raw)
    if isinstance(raw, str) and raw:
        return _extracted(field, time.fromisoformat(raw))
    return _extracted(field, None)


def decimal_value(fields: Fields, name: str) -> ExtractedValue[Decimal]:
    field = _field(fields, name)
    if field is None:
        return ExtractedValue()
    currency = field.get("valueCurrency")
    if isinstance(currency, Mapping) and currency.get("amount") is not None:
        return _extracted(field, Decimal(str(currency["amount"])))
    number = field.get("valueNumber")
    if number is not None:
        return _extracted(field, Decimal(str(number)))
    return _extracted(field, None)


def money_value(fields: Fields, name: str) -> ExtractedValue[Decimal]:
    extracted = decimal_value(fields, name)
    if extracted.value is None:
        return extracted
    return ExtractedValue(
        value=extracted.value.quantize(Decimal("0.01")),
        confidence=extracted.confidence,
    )


def currency_code(fields: Fields, *names: str) -> ExtractedValue[str]:
    for name in names:
        field = _field(fields, name)
        if field is None:
            continue
        currency = field.get("valueCurrency")
        if not isinstance(currency, Mapping):
            continue
        code = currency.get("currencyCode") or currency.get("currencySymbol")
        if code:
            return _extracted(field, str(code))
    return ExtractedValue()


def object_items(fields: Fields, name: str) -> list[Fields]:
    field = _field(fields, name)
    if field is None:
        return []
    values = field.get("valueArray") or []
    items: list[Fields] = []
    for item in values:
        if not isinstance(item, Mapping):
            continue
        inner = item.get("valueObject")
        items.append(inner if isinstance(inner, Mapping) else item)
    return items
