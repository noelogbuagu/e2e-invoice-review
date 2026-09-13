from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


class PipelineContext(BaseModel):
    document_path: Path
    classification: Any = None
