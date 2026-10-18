"""
A vendored copy of LeetCodeBot's description parser.

Copied from `utils/embed_presenters.py` and `config/constants.py` so this
directory can be analysed without importing the bot, whose import chain reaches
`config/secrets.py` and therefore needs a configured environment.

Being a copy, it drifts the moment the bot's parser changes. Re-copy
`LeetCodeMarkdownConverter`, `_fix_truncated_markdown` and `parse_problem_desc`
before trusting a fresh run.
"""

import re2
from markdownify import MarkdownConverter

PREVIEW_LEN = 4000


class LeetCodeMarkdownConverter(MarkdownConverter):
    """markdownify strips <sup>/<sub> content instead of marking it, so
    exponents like <sup>5</sup> collapse into surrounding text."""

    def convert_sup(self, el, text, parent_tags):
        if not text:
            return text
        return f"^{text}" if " " not in text else f"^({text})"

    def convert_sub(self, el, text, parent_tags):
        if not text:
            return text
        underscore = "_" if "_noformat" in parent_tags else "\\_"
        return f"{underscore}{text}" if " " not in text else f"{underscore}({text})"


def _markdownify(html: str, **options) -> str:
    return LeetCodeMarkdownConverter(**options).convert(html)


def _fix_truncated_markdown(text: str) -> str:
    text = re2.sub(r"`{1,2}$", "", text)

    if len(re2.findall(r"```", text)) % 2 != 0:
        if not text.endswith("\n"):
            text += "\n"
        return text + "```"

    if text.count("`") % 2 != 0:
        text += "`"
    if text.count("**") % 2 != 0:
        text += "**"
    elif re2.sub(r"\*\*", "", text).count("*") % 2 != 0:
        text += "*"

    return text


def parse_problem_desc(content: str) -> str:
    if not content:
        return "No description available."

    content = re2.sub(
        r"(?s)<table.*?>.*?</table>", "\n<em>[Table omitted for preview]<em>\n", content
    )

    md_text = _markdownify(content, heading_style="ATX", strip=["img"]).strip()
    md_text = re2.sub(r"\n\s*\n", "\n\n", md_text)

    if len(md_text) <= PREVIEW_LEN:
        return md_text

    truncated = md_text[:PREVIEW_LEN].rsplit(" ", 1)[0]
    truncated = _fix_truncated_markdown(truncated)

    return truncated + ("\n..." if truncated.endswith("```") else "...")
