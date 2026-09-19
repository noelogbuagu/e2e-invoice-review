from __future__ import annotations

from app.accounting.catalog import GL_ACCOUNTS, GL_ACCOUNTS_BY_CODE, GlAccount, GlAccountCode


def catalog_text() -> str:
    lines = [
        f"{account.code} {account.name}: {account.description}" for account in GL_ACCOUNTS
    ]
    return "\n".join(lines)


def resolve_account(code: GlAccountCode | str) -> GlAccount:
    resolved = GlAccountCode(code)
    account = GL_ACCOUNTS_BY_CODE.get(resolved)
    if account is None:
        raise ValueError(f"Unknown GL account code: {code}")
    return account
