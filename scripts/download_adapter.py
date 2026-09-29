#!/usr/bin/env python3
"""Download LoRA adapter from Hugging Face Hub into outputs/lora_adapter."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

from huggingface_hub import snapshot_download

from tutor.config import ADAPTER_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download tutor LoRA from Hugging Face Hub")
    parser.add_argument(
        "--repo",
        default=os.environ.get("TUTOR_ADAPTER_HF_REPO", "").strip(),
        help="Hub repo id (default: TUTOR_ADAPTER_HF_REPO from .env)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ADAPTER_PATH,
        help=f"Local directory (default: {ADAPTER_PATH})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.repo:
        print(
            "Set TUTOR_ADAPTER_HF_REPO in .env or pass --repo user/model-name",
            file=sys.stderr,
        )
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("HF_TOKEN", "").strip() or None

    print(f"Downloading {args.repo} -> {args.output}")
    path = snapshot_download(
        repo_id=args.repo,
        local_dir=str(args.output),
        local_dir_use_symlinks=False,
        token=token,
    )
    safetensors = Path(path) / "adapter_model.safetensors"
    if not safetensors.is_file():
        print(f"Warning: expected {safetensors} after download", file=sys.stderr)
        return 1
    print(f"Done. Adapter at {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
