#!/usr/bin/env python3
"""ISO 5807 flowcharts (no in-image titles) for the NLP report."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "figures"
ASK_PNG = OUT_DIR / "figure_4_1_ask.png"
INDEX_PNG = OUT_DIR / "figure_4_2_index.png"

STROKE = 1.15
FONT = "Times New Roman"
BLACK = "#111111"


def _text(ax, x: float, y: float, text: str, *, size: float = 8.0) -> None:
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=size,
        fontfamily=FONT,
        color=BLACK,
        linespacing=1.15,
        zorder=4,
    )


def capsule(ax, x: float, y: float, w: float, h: float, text: str) -> dict[str, tuple[float, float]]:
    pad = h / 2.0
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2.0, y - h / 2.0),
            w,
            h,
            boxstyle=f"round,pad=0,rounding_size={pad}",
            linewidth=STROKE,
            edgecolor=BLACK,
            facecolor="white",
            zorder=2,
        )
    )
    _text(ax, x, y, text, size=9)
    return _ports(x, y, w, h)


def rect(ax, x: float, y: float, w: float, h: float, text: str, *, size: float = 8.0) -> dict:
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2.0, y - h / 2.0),
            w,
            h,
            boxstyle="square,pad=0",
            linewidth=STROKE,
            edgecolor=BLACK,
            facecolor="white",
            zorder=2,
        )
    )
    _text(ax, x, y, text, size=size)
    return _ports(x, y, w, h)


def diamond(ax, x: float, y: float, w: float, h: float, text: str) -> dict:
    pts = [
        (x, y + h / 2.0),
        (x + w / 2.0, y),
        (x, y - h / 2.0),
        (x - w / 2.0, y),
    ]
    ax.add_patch(
        Polygon(pts, closed=True, linewidth=STROKE, edgecolor=BLACK, facecolor="white", zorder=2)
    )
    _text(ax, x, y, text, size=7.4)
    return _ports(x, y, w, h)


def parallelogram(ax, x: float, y: float, w: float, h: float, text: str) -> dict:
    skew = 0.18 * w
    pts = [
        (x - w / 2.0 + skew, y + h / 2.0),
        (x + w / 2.0, y + h / 2.0),
        (x + w / 2.0 - skew, y - h / 2.0),
        (x - w / 2.0, y - h / 2.0),
    ]
    ax.add_patch(
        Polygon(pts, closed=True, linewidth=STROKE, edgecolor=BLACK, facecolor="white", zorder=2)
    )
    _text(ax, x, y, text, size=8)
    return _ports(x, y, w, h)


def connector(ax, x: float, y: float, r: float = 0.07) -> dict[str, tuple[float, float]]:
    ax.add_patch(
        Circle((x, y), r, facecolor=BLACK, edgecolor=BLACK, linewidth=STROKE, zorder=3)
    )
    return {
        "c": (x, y),
        "n": (x, y + r),
        "s": (x, y - r),
        "e": (x + r, y),
        "w": (x - r, y),
    }


def _ports(x: float, y: float, w: float, h: float) -> dict[str, tuple[float, float]]:
    return {
        "c": (x, y),
        "n": (x, y + h / 2.0),
        "s": (x, y - h / 2.0),
        "e": (x + w / 2.0, y),
        "w": (x - w / 2.0, y),
    }


def arrow(ax, p0: tuple[float, float], p1: tuple[float, float], *, label: str = "", loff=(0.0, 0.0)) -> None:
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.95,
            color=BLACK,
            shrinkA=0.4,
            shrinkB=0.4,
            zorder=1,
        )
    )
    if label:
        mx = (p0[0] + p1[0]) / 2.0 + loff[0]
        my = (p0[1] + p1[1]) / 2.0 + loff[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=7, fontfamily=FONT, color=BLACK, zorder=5)


def poly_arrow(ax, pts: list[tuple[float, float]], *, label: str = "", lp: tuple[float, float] | None = None) -> None:
    if len(pts) < 2:
        return
    if len(pts) > 2:
        xs = [p[0] for p in pts[:-1]]
        ys = [p[1] for p in pts[:-1]]
        ax.plot(xs, ys, color=BLACK, linewidth=0.95, zorder=1, solid_capstyle="round")
    arrow(ax, pts[-2], pts[-1])
    if label and lp:
        ax.text(lp[0], lp[1], label, ha="center", va="center", fontsize=7, fontfamily=FONT, color=BLACK, zorder=5)


def _new_fig(w: float, h: float, xmax: float, ymax: float):
    fig, ax = plt.subplots(figsize=(w, h), dpi=220)
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0.03, right=0.97, top=0.98, bottom=0.02)
    return fig, ax


def build_ask() -> None:
    """One Ask turn: ISO 5807; each diamond has one in and two Yes/No outs."""
    fig, ax = _new_fig(6.5, 9.55, 10.15, 14.55)
    ax.set_ylim(-0.32, 14.55)
    cx = 5.2
    rail_x = 9.2
    left_x = 1.78
    retr_x = 2.78
    prog_x = 7.72

    start = capsule(ax, cx, 14.12, 1.55, 0.42, "Start")
    inp = parallelogram(ax, cx, 13.28, 3.55, 0.52, "Student question\nand optional code")
    hints = diamond(ax, cx, 12.08, 2.85, 1.08, "Keyword hints\nfor MIIT or\nCE / coding?")
    follow = diamond(ax, cx, 10.48, 2.85, 1.08, "Follow-up with\na prior topic?")
    router = rect(ax, cx, 9.05, 2.85, 0.52, "Optional JSON\nclassifier", size=8)
    oos = diamond(ax, cx, 7.85, 2.55, 1.0, "Out of\nscope?")
    refuse = parallelogram(ax, left_x, 7.85, 2.4, 0.55, "Fixed Burmese\nrefusal")
    end_oos = capsule(ax, left_x, 6.88, 1.45, 0.4, "End")
    c_h = connector(ax, rail_x, hints["e"][1])
    c_f = connector(ax, rail_x, follow["e"][1])
    m1 = connector(ax, cx, 6.78)
    miit = diamond(ax, cx, 5.72, 2.7, 1.0, "MIIT\nretrieval?")
    retrieve = rect(ax, retr_x, 4.42, 2.4, 0.5, "Retrieve note\npassages", size=8)
    sim = diamond(ax, retr_x, 3.28, 2.45, 0.95, "Similarity\nhigh enough?")
    miit_p = rect(ax, retr_x, 2.18, 2.4, 0.5, "Build MIIT\nprompt", size=8)
    m2 = connector(ax, prog_x, 3.28)
    prog_p = rect(ax, prog_x, 2.18, 2.55, 0.5, "Build CE / coding\nprompt", size=7.8)
    m3 = connector(ax, cx, 1.58)
    gen = rect(ax, cx, 1.12, 2.85, 0.42, "Generate with Gemini", size=8)
    save = rect(ax, cx, 0.68, 2.45, 0.36, "Save chat turn", size=8)
    out = parallelogram(ax, cx, 0.28, 2.75, 0.36, "Burmese answer")
    end_ok = capsule(ax, cx, -0.02, 1.45, 0.36, "End")

    arrow(ax, start["s"], inp["n"])
    arrow(ax, inp["s"], hints["n"])
    arrow(ax, hints["s"], follow["n"], label="No", loff=(-0.24, 0.0))
    arrow(ax, hints["e"], c_h["w"], label="Yes", loff=(0.0, 0.16))
    arrow(ax, follow["s"], router["n"], label="No", loff=(-0.24, 0.0))
    arrow(ax, follow["e"], c_f["w"], label="Yes", loff=(0.0, 0.16))
    arrow(ax, c_h["s"], c_f["n"])
    arrow(ax, router["s"], oos["n"])
    arrow(ax, oos["w"], refuse["e"], label="Yes", loff=(0.0, 0.16))
    arrow(ax, refuse["s"], end_oos["n"])
    arrow(ax, oos["s"], m1["n"], label="No", loff=(-0.24, 0.0))
    poly_arrow(ax, [c_f["s"], (rail_x, m1["e"][1]), m1["e"]])
    arrow(ax, m1["s"], miit["n"])

    poly_arrow(
        ax,
        [miit["w"], (retr_x, miit["w"][1]), retrieve["n"]],
        label="Yes",
        lp=(3.42, miit["w"][1] + 0.16),
    )
    poly_arrow(
        ax,
        [miit["e"], (prog_x, miit["e"][1]), m2["n"]],
        label="No",
        lp=(6.72, miit["e"][1] + 0.16),
    )
    arrow(ax, retrieve["s"], sim["n"])
    arrow(ax, sim["s"], miit_p["n"], label="Yes", loff=(-0.28, 0.0))
    arrow(ax, sim["e"], m2["w"], label="No", loff=(0.0, 0.16))
    arrow(ax, m2["s"], prog_p["n"])
    poly_arrow(ax, [miit_p["s"], (retr_x, m3["w"][1]), m3["w"]])
    poly_arrow(ax, [prog_p["s"], (prog_x, m3["e"][1]), m3["e"]])
    arrow(ax, m3["s"], gen["n"])
    arrow(ax, gen["s"], save["n"])
    arrow(ax, save["s"], out["n"])
    arrow(ax, out["s"], end_ok["n"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASK_PNG, dpi=220, facecolor="white")
    plt.close(fig)


def build_index() -> None:
    fig, ax = _new_fig(6.4, 3.35, 10.0, 5.55)
    ax.set_ylim(1.05, 5.50)
    cx = 5.0
    start = capsule(ax, cx, 5.15, 1.55, 0.42, "Start")
    load = rect(ax, cx, 4.22, 3.2, 0.52, "Load MIIT JSONL notes")
    embed = rect(ax, cx, 3.28, 3.6, 0.52, "Embed with gemini-embedding-001")
    write = parallelogram(ax, cx, 2.32, 3.2, 0.52, "Write index.json")
    end = capsule(ax, cx, 1.38, 1.55, 0.42, "End")
    arrow(ax, start["s"], load["n"])
    arrow(ax, load["s"], embed["n"])
    arrow(ax, embed["s"], write["n"])
    arrow(ax, write["s"], end["n"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(INDEX_PNG, dpi=220, facecolor="white")
    plt.close(fig)


def main() -> int:
    build_ask()
    build_index()
    print(f"Wrote {ASK_PNG}")
    print(f"Wrote {INDEX_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
