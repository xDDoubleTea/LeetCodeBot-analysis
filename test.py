"""
Plot the distribution of problem description lengths, before and after parsing.

Two samples, both from the bot's test database (`DB_PATH` below):

html
    `problems.description` as LeetCode returns it.

markdown
    The same descriptions through `parse_problem_desc`, which is what an embed
    actually carries.

The lengths span three orders of magnitude with a long right tail, so the x axis
and the bin edges are both logarithmic -- on a linear axis every problem lands in
the first two bins.

Parsing comes from the vendored `desc_parser`, not from the bot, so this needs
nothing from the checkout but the database:

    uv run test.py
"""

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from desc_parser import PREVIEW_LEN, parse_problem_desc, parse_problem_desc_uncapped

DB_PATH = Path("~/programming/LeetCodeBot/db/testbot.db").expanduser()
OUT_DIR = Path(__file__).resolve().parent


def plot_lengths(lengths, title: str, xlabel: str, out_path: Path, cap=None) -> None:
    mean = lengths.mean()
    p25, p50, p75, p99 = np.percentile(lengths, [25, 50, 75, 99])

    fig, ax = plt.subplots(figsize=(11, 6))
    bins = np.logspace(np.log10(lengths.min()), np.log10(lengths.max()), 60)
    ax.hist(lengths, bins=bins, color="#4c72b0", edgecolor="white", linewidth=0.5)
    ax.set_xscale("log")

    # p25, mean and p75 sit close together on a log axis, so their labels
    # alternate between two heights; p99 sits lower to clear the stats box.
    for value, label, colour, height in [
        (p25, "p25", "#55a868", 0.97),
        (mean, "mean", "#c44e52", 0.88),
        (p75, "p75", "#55a868", 0.97),
        (p99, "p99", "#8172b2", 0.62),
    ]:
        ax.axvline(value, color=colour, linestyle="--", linewidth=1.4)
        ax.annotate(
            f"{label} {value:,.0f}",
            xy=(value, height),
            xycoords=("data", "axes fraction"),
            ha="center",
            va="top",
            fontsize=9,
            color=colour,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.5},
        )

    if cap is not None:
        ax.axvline(cap, color="#937860", linewidth=1.4)
        ax.annotate(
            f"PREVIEW_LEN {cap:,}\n{(lengths >= cap - 60).sum()} truncated",
            xy=(cap, 0.44),
            xycoords=("data", "axes fraction"),
            xytext=(-8, 0),
            textcoords="offset points",
            ha="right",
            va="top",
            fontsize=9,
            color="#937860",
        )

    stats = "\n".join(
        [
            f"n         {len(lengths):>12,}",
            f"mean      {mean:>12,.1f}",
            f"median    {p50:>12,.0f}",
            f"p25       {p25:>12,.0f}",
            f"p75       {p75:>12,.0f}",
            f"p99       {p99:>12,.0f}",
            f"std dev   {lengths.std(ddof=1):>12,.1f}",
            f"variance  {lengths.var(ddof=1):>12,.3g}",
            f"min / max {lengths.min():>5,} / {lengths.max():,}",
        ]
    )
    ax.text(
        0.98,
        0.95,
        stats,
        transform=ax.transAxes,
        ha="right",
        va="top",
        family="monospace",
        fontsize=9,
        bbox={
            "facecolor": "white",
            "edgecolor": "#cccccc",
            "boxstyle": "round,pad=0.6",
        },
    )

    ax.set_xlabel(xlabel)
    ax.set_ylabel("problems")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    ax.margins(y=0.12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"wrote {out_path}")


with sqlite3.connect(DB_PATH) as db:
    descriptions = [
        row[0]
        for row in db.execute(
            "select description from problems "
            "where description is not null and length(description) > 0"
        )
    ]

html_lengths = np.array([len(content) for content in descriptions])
markdown_lengths = np.array([len(parse_problem_desc(c)) for c in descriptions])
uncapped_lengths = np.array([len(parse_problem_desc_uncapped(c)) for c in descriptions])

plot_lengths(
    html_lengths,
    "LeetCode problem description lengths (html)",
    "description length (characters, log scale)",
    OUT_DIR / "description_lengths.png",
)
plot_lengths(
    markdown_lengths,
    "LeetCode problem description lengths (parsed markdown)",
    "parse_problem_desc output length (characters, log scale)",
    OUT_DIR / "preview_lengths.png",
    cap=PREVIEW_LEN,
)
plot_lengths(
    uncapped_lengths,
    "LeetCode problem description lengths (parsed markdown, no cap)",
    "uncapped parse_problem_desc output length (characters, log scale)",
    OUT_DIR / "uncapped_lengths.png",
    cap=PREVIEW_LEN,
)

over = uncapped_lengths[uncapped_lengths > PREVIEW_LEN]
print(
    f"\nuncapped max {uncapped_lengths.max():,}  "
    f"over PREVIEW_LEN {len(over)} ({len(over) / len(uncapped_lengths):.2%})  "
    f"characters discarded {int((over - PREVIEW_LEN).sum()):,}"
)
