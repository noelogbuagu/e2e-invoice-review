from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GlAccountCode(StrEnum):
    cleaning = "6100"
    maintenance = "6110"
    electrical = "6120"
    plumbing = "6130"
    equipment = "6140"
    fuel_travel = "6150"
    office_supplies = "6160"
    professional_services = "6170"
    utilities = "6180"
    miscellaneous = "6190"


class GlAccount(BaseModel):
    code: GlAccountCode
    name: str
    description: str


class GlAccountSuggestion(BaseModel):
    account_code: GlAccountCode
    account_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


GL_ACCOUNTS: tuple[GlAccount, ...] = (
    GlAccount(
        code=GlAccountCode.cleaning,
        name="Cleaning services",
        description="Contract cleaning, janitorial, and related site hygiene work.",
    ),
    GlAccount(
        code=GlAccountCode.maintenance,
        name="Building maintenance",
        description="General building upkeep, repairs, and planned maintenance.",
    ),
    GlAccount(
        code=GlAccountCode.electrical,
        name="Electrical services",
        description="Electrical installation, inspection, and repair.",
    ),
    GlAccount(
        code=GlAccountCode.plumbing,
        name="Plumbing services",
        description="Plumbing installation, leaks, and water-system work.",
    ),
    GlAccount(
        code=GlAccountCode.equipment,
        name="Equipment and machinery",
        description="Tools, plant, and equipment purchases or hire.",
    ),
    GlAccount(
        code=GlAccountCode.fuel_travel,
        name="Fuel and travel",
        description="Vehicle fuel, mileage, and related travel expenses.",
    ),
    GlAccount(
        code=GlAccountCode.office_supplies,
        name="Office supplies",
        description="Stationery, consumables, and small office purchases.",
    ),
    GlAccount(
        code=GlAccountCode.professional_services,
        name="Professional services",
        description="Consultancy, inspection, and other professional fees.",
    ),
    GlAccount(
        code=GlAccountCode.utilities,
        name="Utilities",
        description="Energy, water, and similar site utility costs.",
    ),
    GlAccount(
        code=GlAccountCode.miscellaneous,
        name="Miscellaneous expenses",
        description=(
            "Facilities costs that do not fit a more specific account. "
            "Use when line items or receipt category are generic or ambiguous, "
            "including when the vendor name suggests a trade but the document "
            "text does not describe that work."
        ),
    ),
)

GL_ACCOUNTS_BY_CODE = {account.code: account for account in GL_ACCOUNTS}
