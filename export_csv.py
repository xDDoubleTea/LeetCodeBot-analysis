"""Export per-problem description lengths and parse times to problems.csv.

Run from the LeetCodeBot checkout so its parser and database are used:
    cd ~/programming/LeetCodeBot && .venv/bin/python ~/programming/leetcodebot-analysis/export_csv.py
Only lengths and timings are exported, not the description text itself.
"""

import csv
import sqlite3
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
from utils.embed_presenters import parse_problem_desc  # noqa: E402

REPEATS = 5
OUT = Path(__file__).resolve().parent / "problems.csv"

rows = sqlite3.connect("db/testbot.db").execute(
    "select problem_frontend_id, title, difficulty, premium, description from problems "
    "where description is not null and length(description) > 0 order by problem_frontend_id"
).fetchall()

DIFFICULTY = {0: "Easy", 1: "Medium", 2: "Hard"}

with OUT.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "title", "difficulty", "premium", "html_length", "markdown_length", "parse_ms"])
    for pid, title, diff, premium, html in rows:
        times = []
        for _ in range(REPEATS):
            t0 = time.perf_counter()
            md = parse_problem_desc(html)
            times.append((time.perf_counter() - t0) * 1000)
        w.writerow([pid, title, DIFFICULTY.get(diff, diff), int(premium), len(html), len(md), f"{statistics.median(times):.4f}"])
print(f"wrote {len(rows)} rows to {OUT}")
