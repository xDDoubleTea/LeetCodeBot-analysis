"""
Summarize the bot's activity tables: problem opens and code blocks posted in
problem threads.

Reads `cache/problem_opens.csv` and `cache/thread_solutions.csv`, exported from
the production database with Datasette, and `problems.csv` for difficulty:

    uv run activity_stats.py

Users are printed as U1, U2, ... in descending order of activity, never as
Discord ids. Hours and days are in UTC+8; the tables store UTC.
"""

import pandas as pd

TAIPEI = pd.Timedelta(hours=8)

opens = pd.read_csv("cache/problem_opens.csv", parse_dates=["opened_at"])
code = pd.read_csv("cache/thread_solutions.csv", parse_dates=["posted_at"])
difficulty = pd.read_csv("problems.csv")[["title", "difficulty"]]

ranked = pd.concat([opens.discord_user_id, code.discord_user_id]).value_counts()
alias = {user: f"U{i + 1}" for i, user in enumerate(ranked.index)}
opens["user"] = opens.discord_user_id.map(alias)
code["user"] = code.discord_user_id.map(alias)
opens["local"] = opens.opened_at + TAIPEI
code["local"] = code.posted_at + TAIPEI
opens = opens.merge(
    difficulty, left_on="problem_db_id_label", right_on="title", how="left"
)
code = code.merge(
    difficulty, left_on="problem_db_id_label", right_on="title", how="left"
)

print("span (UTC):", opens.opened_at.min(), "->", code.posted_at.max())
print(
    "guilds:",
    opens.guild_id.nunique(),
    "| problems opened:",
    opens.problem_db_id.nunique(),
    "| threads with code:",
    code.problem_db_id.nunique(),
)

print("\nopens by command:\n", opens.command.value_counts().to_string())

per_user = pd.DataFrame(
    {
        "opens": opens.user.value_counts(),
        "code": code.user.value_counts(),
        "problems": code.groupby("user").problem_db_id.nunique(),
    }
)
print("\nper user (opens, code blocks, problems with code):")
print(per_user.fillna(0).astype(int).to_string())

print("\nlanguages:\n", code.language.value_counts(dropna=False).to_string())
print("\nlanguages per user:")
print(code.pivot_table(index="user", columns="language", aggfunc="size", fill_value=0))
print(
    "\ndifficulty of opens:\n", opens.difficulty.value_counts(dropna=False).to_string()
)
solved = code.drop_duplicates(["user", "problem_db_id"])
print("\ndifficulty of problems with code:")
print(solved.difficulty.value_counts(dropna=False).to_string())

first = (
    code.groupby(["user", "problem_db_id"])
    .posted_at.min()
    .rename("first_code")
    .reset_index()
)
funnel = opens.merge(first, on=["user", "problem_db_id"], how="left")
funnel["minutes"] = (funnel.first_code - funnel.opened_at).dt.total_seconds() / 60
converted = funnel[funnel.minutes >= 0]
print(f"\nopens followed by the same user's code: {len(converted)}/{len(opens)}")
print("minutes from open to first code:", sorted(converted.minutes.round(1)))

opened_pairs = opens[["user", "problem_db_id"]].drop_duplicates()
unopened = first.merge(opened_pairs, how="left", indicator=True)
print(
    "(user, problem) with code but not opened by that user:",
    (unopened._merge == "left_only").sum(),
    "of",
    len(first),
)

hours = pd.concat(
    [
        opens.local.dt.hour.rename("hour").to_frame().assign(kind="open"),
        code.local.dt.hour.rename("hour").to_frame().assign(kind="code"),
    ]
)
print("\nhour (UTC+8):")
print(hours.pivot_table(index="hour", columns="kind", aggfunc="size", fill_value=0))

days = pd.DataFrame(
    {
        "opens": opens.local.dt.date.value_counts(),
        "code": code.local.dt.date.value_counts(),
    }
)
print("\nper day (UTC+8):")
print(days.fillna(0).astype(int).sort_index().to_string())
