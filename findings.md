# LeetCodeBot description analysis: findings

Data: `problems.csv`, from LeetCodeBot's `db/testbot.db` (2026-10-16). Timings measured on the desktop (Ryzen 7 7800X3D).

## 1. The decision being analysed

- **Before PR #29 (2026-07-19):** on every start, `on_ready` started `weekly_cache_refresh` (a `tasks.loop`, whose first run is immediate). It downloaded every problem and parsed all descriptions with BeautifulSoup, storing parsed text.
- **After:** the DB stores raw HTML and `parse_problem_desc` runs only when a command builds an embed.
- **Why:** shorter startup, keeping the HTML for possible future uses (e.g. per-guild formatting from a web dashboard), and no migration tool at the time (Alembic came later, in #57).
- **PR #36:** preview cap 1,000 → 4,000 characters, Markdown-aware truncation.

## 2. Parse time: startup vs per command

| | Total for 3,296 | Per description p50 / p99 / max |
| --- | --- | --- |
| Old: BeautifulSoup, all at startup | 2.6 s | 0.7 / 2.1 / 16 ms |
| Now: markdownify, per command | n/a | 1.1 / 3.0 / 17 ms |

Even the slowest description (~17 ms) is far below Discord's 3 s interaction deadline. The 2.6 s excludes the download, which wasn't measured.

## 3. Length distribution

n = 3,296 (every problem with a description, a census rather than a sample of these).

| | Median | Mean | p99 | Max |
| --- | --- | --- | --- | --- |
| HTML | 2,024 | 2,256 | 6,053 | 25,400 |
| Markdown, uncapped | 1,188 | 1,320 | 3,677 | 5,785 |

Share of problems that fit in a preview of N characters (Markdown): 1,000 → 35.5%, 2,000 → 87.7%, 4,000 → 99.3%.

Charts: `LeetCodeBot/scripts/description_lengths.png`, `uncapped_lengths.png`, `preview_lengths.png`.

## 4. Lengths are close to lognormal

| | Skewness | Excess kurtosis | Normal Q-Q correlation |
| --- | --- | --- | --- |
| Markdown, raw | 1.38 | 2.81 | 0.953 |
| **Markdown, log** | **−0.08** | **0.04** | **0.999** |
| HTML, raw | 4.93 | 67.15 | 0.865 |
| HTML, log | 0.25 | 0.76 | 0.997 |

- A normal distribution has skewness 0 and excess kurtosis 0. Log Markdown length is almost exactly normal.
- Why: length behaves like a product of many factors (paragraphs × sentences × words…). Log turns the product into a sum, and the CLT makes the sum close to normal.
- Show it with a histogram of log length and a normal Q-Q plot: `qqnorm(log(x)); qqline(log(x))` in R.
- A Shapiro–Wilk test with n = 3,296 will reject tiny deviations (likely for HTML), even though the Q-Q plot looks fine: statistical vs practical significance.

## 5. Tables and the HTML tail

| Group | n | Median HTML length |
| --- | --- | --- |
| No `<table>` | 3,206 | 1,992 |
| Has `<table>` | 90 | 4,698 |
| Database tag | 94 | 2,307 |
| Design tag | 99 | 2,609 |

- 7 of the 8 longest HTML descriptions contain a `<table>` (2.7% of all problems do).
- Markdown replaces each table with `[Table omitted for preview]`, since Discord can't render tables and an image is overkill for a preview. That removes the extreme tail, which is why log Markdown is closer to normal than log HTML.
- None of the 90 `<table>` problems is tagged Database or Design. Top tags: Array (65), Math (23), Dynamic Programming (21).
- Database problems draw their tables as ASCII art (`+----+`) in `<pre>` blocks (all 94). These are not omitted and render as code blocks.
- Design problems are longer without tables (API method lists).

## 6. Limitation: missing data

- 3,296 of 4,082 problems in the DB have a description; for the Database tag only 94 of 310.
- So the "population" is problems with a description, not all of LeetCode, and the missing ones are not missing at random.

## 7. Ideas for the course

| Topic | Use |
| --- | --- |
| Sampling distribution, CLT | Draw repeated samples of size n = 5, 30, 100 from the 3,296 and plot the sample means: skewed population, increasingly normal means. |
| Sample proportion | Share over 4,000 characters ≈ 0.7%; the normal approximation needs about n ≥ 1,400 (np ≥ 10). |
| Why a census | A sample's maximum almost always underestimates the true worst case (5,785), and the decision was about the worst case. |
| Hypothesis testing | Table vs no table: Welch t-test on log length, or Mann–Whitney on raw length. |
| Regression | `parse_ms ~ markdown_length` (or html_length) with `lm`; predict the worst case. |

Open question: how many problems are requested per day? If the bot logs commands, count them to measure the "few per day" usage claim.
