#!/usr/bin/env python3
"""Run Litestar tutor API (POST /v1/chat, GET /health)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import uvicorn

from tutor.api import app
from tutor.config import API_HOST, API_PORT


def main() -> None:
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")


if __name__ == "__main__":
    main()
