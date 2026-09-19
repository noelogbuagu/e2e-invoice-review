from fastapi import APIRouter

from app.accounting.catalog import GL_ACCOUNTS, GlAccount

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


@router.get("/gl-accounts", response_model=list[GlAccount])
def list_gl_accounts() -> list[GlAccount]:
    return list(GL_ACCOUNTS)
