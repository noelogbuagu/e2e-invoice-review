"""Shared setup for interactive playground scripts.

Import this module first in every playground script so paths, backend imports,
and nest-asyncio patching are ready for the interactive window.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nest_asyncio

nest_asyncio.apply()

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
SAMPLES = REPO_ROOT / "samples" / "generated"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

_backend_path = str(BACKEND_ROOT)
if _backend_path not in sys.path:
    sys.path.append(_backend_path)
