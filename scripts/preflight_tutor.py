#!/usr/bin/env python3
"""Check GPU, adapter, and env before starting the tutor app."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tutor.env_bootstrap import load_project_env

load_project_env()

import torch

from tutor.config import ADAPTER_PATH, MIN_VRAM_GIB


def _gib(bytes_count: int) -> float:
    return bytes_count / (1024**3)


def main() -> int:
    errors: list[str] = []

    if not torch.cuda.is_available():
        errors.append("CUDA is not available (need an NVIDIA GPU and CUDA PyTorch).")
    else:
        free, total = torch.cuda.mem_get_info(0)
        free_gib = _gib(free)
        total_gib = _gib(total)
        print(
            f"preflight: VRAM free {free_gib:.1f} / {total_gib:.1f} GiB "
            f"(need >= {MIN_VRAM_GIB:.1f} GiB)"
        )
        if free_gib < MIN_VRAM_GIB:
            errors.append(
                f"Not enough free VRAM ({free_gib:.1f} GiB < {MIN_VRAM_GIB:.1f} GiB). "
                "Stop other GPU jobs (make serve-api, chat, train). "
                "Run `fuser -v /dev/nvidia0` and kill stale processes."
            )

    if not ADAPTER_PATH.exists():
        errors.append(
            f"LoRA adapter not found at {ADAPTER_PATH}. "
            "Run make train or copy outputs/lora_adapter onto this machine."
        )

    if errors:
        for msg in errors:
            print(f"preflight: {msg}", file=sys.stderr)
        return 1

    print(f"preflight: OK (cuda={torch.cuda.get_device_name(0)}, adapter={ADAPTER_PATH})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
