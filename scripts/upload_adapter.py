#!/usr/bin/env python3
"""Upload outputs/lora_adapter to Hugging Face Hub."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

from huggingface_hub import HfApi

from tutor.config import ADAPTER_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload tutor LoRA to Hugging Face Hub")
    parser.add_argument(
        "--repo",
        default=os.environ.get("TUTOR_ADAPTER_HF_REPO", "").strip(),
        help="Hub repo id (default: TUTOR_ADAPTER_HF_REPO from .env)",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=ADAPTER_PATH,
        help=f"Local adapter folder (default: {ADAPTER_PATH})",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create repo as private if it does not exist",
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
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("Set HF_TOKEN in .env for upload.", file=sys.stderr)
        return 1
    if not args.source.is_dir():
        print(f"Adapter folder not found: {args.source}", file=sys.stderr)
        return 1
    weights = args.source / "adapter_model.safetensors"
    if not weights.is_file():
        print(f"Missing {weights}", file=sys.stderr)
        return 1

    api = HfApi(token=token)
    api.create_repo(
        repo_id=args.repo,
        repo_type="model",
        exist_ok=True,
        private=args.private,
    )
    print(f"Uploading {args.source} -> {args.repo}")
    api.upload_folder(
        folder_path=str(args.source),
        repo_id=args.repo,
        repo_type="model",
        commit_message="Update Myanmar programming tutor LoRA adapter",
    )
    print(f"Done: https://huggingface.co/{args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
