from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple, Protocol


class InvoiceKey(NamedTuple):
    vendor_name: str
    invoice_number: str


class DuplicateRegistry(Protocol):
    def is_registered(self, key: InvoiceKey) -> bool: ...


class InMemoryDuplicateRegistry:
    def __init__(self, keys: Iterable[InvoiceKey] = ()) -> None:
        self._keys = set(keys)

    def register(self, key: InvoiceKey) -> None:
        self._keys.add(key)

    def is_registered(self, key: InvoiceKey) -> bool:
        return key in self._keys
