"""
Turn the bot's latency log lines into `cache/perf.csv`, one row per command.

Reads every `bot.log*` and `perf.log*` under `logs/prod/`. Both files carry the
same latency lines, so a line found in more than one file is kept once:

    uv run perf_csv.py

Columns are `timestamp`, `command`, then every `key=value` field in the order
it first appears, so a metric added to the bot shows up as a new column without
changing this script. That includes the arguments the user passed, as
`arg_<name>`, and `linked_user_id` when `/user-info` or `/recent-submissions`
fell back to the caller's linked account. Values are split with `shlex`, so a
quoted argument such as `arg_title='two sum'` stays one cell. Fields a line does not have, and the `-` and `?`
placeholders, are left empty, so a spreadsheet's MEDIAN and AVERAGE skip them.
Timestamps are as the bot logged them.
"""

import csv
import re
import shlex
from pathlib import Path

LOG_DIR = Path("logs/prod")
LOG_GLOBS = ("bot.log*", "perf.log*")
OUT = Path("cache/perf.csv")
EMPTY_VALUES = {"-", "?"}

LINE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\] \[[A-Z ]+\] utils\.perf: latency (?P<fields>.+)$"
)

lines = {
    line
    for pattern in LOG_GLOBS
    for path in LOG_DIR.glob(pattern)
    for line in path.read_text(encoding="utf-8").splitlines()
    if "utils.perf: latency " in line
}

rows = []
columns = ["timestamp", "command"]
for line in sorted(lines):
    match = LINE.match(line)
    if not match:
        continue
    row = {"timestamp": match["timestamp"]}
    for pair in shlex.split(match["fields"]):
        key, _, value = pair.partition("=")
        row[key] = "" if value in EMPTY_VALUES else value
        if key not in columns:
            columns.append(key)
    rows.append(row)

OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=columns, restval="")
    writer.writeheader()
    writer.writerows(rows)

print(f"wrote {len(rows)} rows, {len(columns)} columns to {OUT}")
