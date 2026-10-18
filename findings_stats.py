"""
Recompute every number in `findings.md`.

Reads the bot's test database for descriptions and tags, and `problems.csv` for
the per-command parse times. Output is grouped by `findings.md` section. Run it
after regenerating `problems.csv`, then copy the numbers across:

    uv run findings_stats.py

Section 4 uses `markdown_length` from the CSV, the length after the 4,000
character cap, and population moments. Every other Markdown length is
uncapped. Timings are the median of 5 runs per description, measured on
whichever machine runs this.
"""

import re
import sqlite3
import statistics
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from desc_parser import parse_problem_desc_bs4, parse_problem_desc_uncapped

DB_PATH = Path("~/programming/LeetCodeBot/db/testbot.db").expanduser()
CSV_PATH = Path(__file__).resolve().parent / "problems.csv"
REPEATS = 5


def moments(x) -> tuple[float, float]:
    """Population skewness and excess kurtosis."""
    x = np.asarray(x, dtype=float)
    centred = x - x.mean()
    variance = (centred**2).mean()
    return (
        (centred**3).mean() / variance**1.5,
        (centred**4).mean() / variance**2 - 3,
    )


def qq_correlation(x) -> float:
    """Correlation of the sorted data with normal quantiles at R's ppoints."""
    n = len(x)
    a = 3 / 8 if n <= 10 else 0.5
    probabilities = (np.arange(1, n + 1) - a) / (n + 1 - 2 * a)
    normal = statistics.NormalDist()
    quantiles = [normal.inv_cdf(p) for p in probabilities]
    return float(np.corrcoef(np.sort(x), quantiles)[0, 1])


def median_ms(fn, content: str) -> float:
    samples = []
    for _ in range(REPEATS):
        started = time.perf_counter()
        fn(content)
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples)


def spread(values) -> str:
    values = np.asarray(values)
    return (
        f"median {np.median(values):,.0f}  mean {values.mean():,.0f}  "
        f"p99 {np.percentile(values, 99):,.0f}  max {values.max():,}"
    )


with sqlite3.connect(DB_PATH) as db:
    problems = pd.read_sql_query("select id, description from problems", db)
    problem_tags = pd.read_sql_query(
        "select a.problem_id as id, t.tag_name as tag from problem_tags a "
        "join topic_tags t on t.id = a.tag_id",
        db,
    )

problems["tags"] = problems["id"].map(problem_tags.groupby("id")["tag"].agg(set))
problems["tags"] = problems["tags"].apply(lambda t: t if isinstance(t, set) else set())
problems["is_database"] = problems["tags"].map(lambda t: "Database" in t)
described = problems[problems["description"].fillna("") != ""].copy()
described["html"] = described["description"].str.len()
described["markdown"] = described["description"].map(
    lambda html: len(parse_problem_desc_uncapped(html))
)
described["table"] = described["description"].str.contains("<table", regex=False)
described["is_design"] = described["tags"].map(lambda t: "Design" in t)
csv = pd.read_csv(CSV_PATH)
n = len(described)

print(f"rows: {n} described, {len(problems)} in DB, {len(csv)} in problems.csv")

print("\n## 2. Parse time")
started = time.perf_counter()
for html in described["description"]:
    parse_problem_desc_bs4(html)
print(f"BeautifulSoup total, one pass: {time.perf_counter() - started:.1f} s")
bs4_ms = np.array(
    [median_ms(parse_problem_desc_bs4, html) for html in described["description"]]
)
for label, ms in [("BeautifulSoup", bs4_ms), ("markdownify (CSV)", csv["parse_ms"])]:
    print(
        f"{label}: p50 {np.median(ms):.1f}  p99 {np.percentile(ms, 99):.1f}  "
        f"max {np.max(ms):.0f} ms"
    )

print("\n## 3. Length distribution")
print(f"HTML                {spread(described['html'])}")
print(f"Markdown, uncapped  {spread(described['markdown'])}")
for cap in (1000, 2000, 4000):
    print(f"fits in {cap:,}: {(described['markdown'] <= cap).mean():.1%}")

print("\n## 4. Lognormal")
capped = csv["markdown_length"].to_numpy()
html = described["html"].to_numpy()
for label, values in [
    ("Markdown (capped), raw", capped),
    ("Markdown (capped), log", np.log(capped)),
    ("HTML, raw", html),
    ("HTML, log", np.log(html)),
]:
    skewness, kurtosis = moments(values)
    print(
        f"{label:<24} skewness {skewness:.2f}  excess kurtosis {kurtosis:.2f}  "
        f"Q-Q {qq_correlation(values):.3f}"
    )

print("\n## 5. Tables and the HTML tail")
for label, mask in [
    ("No <table>", ~described["table"]),
    ("Has <table>", described["table"]),
    ("Database tag", described["is_database"]),
    ("Design tag", described["is_design"]),
]:
    print(
        f"{label:<13} n {int(mask.sum()):>5,}  median HTML "
        f"{described.loc[mask, 'html'].median():,.0f}"
    )
longest = described.nlargest(8, "html")
print(
    f"{int(longest['table'].sum())} of the 8 longest HTML have a <table>; "
    f"{described['table'].mean():.1%} of all do"
)
overlap = described["table"] & (described["is_database"] | described["is_design"])
print(f"<table> problems tagged Database or Design: {int(overlap.sum())}")
table_tags = Counter(
    t for tags in described.loc[described["table"], "tags"] for t in tags
)
print(f"top tags of <table> problems: {table_tags.most_common(3)}")
ascii_tables = described.loc[described["is_database"], "description"].map(
    lambda html: bool(re.search(r"<pre>.*?\+-+.*?</pre>", html, re.DOTALL))
)
print(
    f"Database problems with +--- in <pre>: {int(ascii_tables.sum())} of "
    f"{int(described['is_database'].sum())}"
)

print("\n## 6. Missing data")
print(
    f"{n:,} of {len(problems):,} have a description; Database tag "
    f"{int(described['is_database'].sum())} of {int(problems['is_database'].sum())}"
)

print("\n## 7. Ideas")
over = described["markdown"] > 4000
print(
    f"over 4,000: {int(over.sum())} of {n:,} = {over.mean():.2%}; "
    f"np >= 10 needs n >= {10 / over.mean():,.0f}; worst case "
    f"{described['markdown'].max():,}"
)
