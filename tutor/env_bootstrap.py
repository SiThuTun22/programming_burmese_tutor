"""Load repo `.env` into os.environ before importing torch."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
_LOADED = False


def load_project_env() -> None:
    global _LOADED
    if _LOADED:
        return
    load_dotenv(_ROOT / ".env", override=False)
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
    _LOADED = True


load_project_env()
