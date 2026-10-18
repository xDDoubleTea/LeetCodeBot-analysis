"""
Fetch your own LeetCode submission history, signed in with your browser session.

The session comes from `.env` in this directory, which is gitignored:

    LEETCODE_SESSION=...
    CSRFTOKEN=...

Both are cookies on leetcode.com: in the browser's developer tools, open
Application (Chrome) or Storage (Firefox), then Cookies, then
https://leetcode.com, and copy the values of `LEETCODE_SESSION` and `csrftoken`.
The session cookie signs in as you, so keep it out of chats and commits; logging
out of LeetCode in that browser invalidates it.

Running the file checks the session, then writes every submission, accepted or
not, to `cache/submissions.json`, without the submitted code. If LeetCode
throttles the requests partway, whatever was fetched is written before the
error is raised:

    uv run leetcode_auth.py

It prints only the signed-in username and a summary, never the cookie values.
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_PATH = HERE / ".env"
OUT_PATH = HERE / "cache" / "submissions.json"
GRAPHQL_URL = "https://leetcode.com/graphql"
PAGE_SIZE = 20
PAGE_DELAY = 1.5
RETRY_DELAYS = [5, 15, 45]
SUBMISSIONS_QUERY = """
query ($offset: Int!, $limit: Int!, $lastKey: String) {
  submissionList(offset: $offset, limit: $limit, lastKey: $lastKey, questionSlug: "") {
    lastKey
    hasNext
    submissions { id title titleSlug statusDisplay timestamp lang runtime }
  }
}
"""


class SessionError(RuntimeError):
    """The cookies are missing, malformed or no longer signed in."""


class PartialFetch(RuntimeError):
    """Fetching stopped partway; `submissions` holds what was fetched."""

    def __init__(self, message: str, submissions: list[dict]):
        super().__init__(message)
        self.submissions = submissions


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    if not path.exists():
        raise SessionError(f"{path} not found; see this file's docstring")
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    missing = {"LEETCODE_SESSION", "CSRFTOKEN"} - values.keys()
    if missing:
        raise SessionError(f"{path} is missing {', '.join(sorted(missing))}")
    return values


def headers(env: dict[str, str]) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0",
        "Cookie": (
            f"LEETCODE_SESSION={env['LEETCODE_SESSION']}; csrftoken={env['CSRFTOKEN']}"
        ),
        "x-csrftoken": env["CSRFTOKEN"],
    }


def gql(env: dict[str, str], query: str, variables: dict | None = None) -> dict:
    """
    POST one GraphQL query signed in as the `.env` user and return its `data`.

    HTTP 403 and 429 are LeetCode throttling; they are retried after each of
    RETRY_DELAYS seconds before the error is raised.
    """
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    for delay in [*RETRY_DELAYS, None]:
        request = urllib.request.Request(GRAPHQL_URL, data=body, headers=headers(env))
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (403, 429) or delay is None:
                raise
            time.sleep(delay)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0]["message"])
    return payload["data"]


def signed_in_username(env: dict[str, str]) -> str:
    status = gql(env, "query { userStatus { isSignedIn username } }")["userStatus"]
    if not status["isSignedIn"]:
        raise SessionError(
            "LeetCode says not signed in: the cookies are expired or wrong"
        )
    return status["username"]


def fetch_submissions(env: dict[str, str]) -> list[dict]:
    """
    Every submission of the signed-in user, newest first, without code.

    # Raises:
    - PartialFetch, carrying the submissions fetched before the failure
    """
    submissions: list[dict] = []
    offset, last_key = 0, None
    while True:
        try:
            page = gql(
                env,
                SUBMISSIONS_QUERY,
                {"offset": offset, "limit": PAGE_SIZE, "lastKey": last_key},
            )["submissionList"]
        except (urllib.error.HTTPError, RuntimeError) as e:
            raise PartialFetch(f"stopped at offset {offset}: {e}", submissions) from e
        submissions.extend(
            {
                "id": int(s["id"]),
                "title": s["title"],
                "slug": s["titleSlug"],
                "status": s["statusDisplay"],
                "timestamp": int(s["timestamp"]),
                "lang": s["lang"],
                "runtime": s["runtime"],
            }
            for s in page["submissions"]
        )
        if not page["hasNext"]:
            return submissions
        offset += PAGE_SIZE
        last_key = page["lastKey"]
        time.sleep(PAGE_DELAY)


def write(submissions: list[dict]) -> None:
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(submissions))
    accepted = sum(s["status"] == "Accepted" for s in submissions)
    if not submissions:
        print("no submissions returned")
        return
    newest = time.strftime("%Y-%m-%d", time.localtime(submissions[0]["timestamp"]))
    oldest = time.strftime("%Y-%m-%d", time.localtime(submissions[-1]["timestamp"]))
    print(
        f"{len(submissions)} submissions ({accepted} accepted), "
        f"{oldest} to {newest}, written to {OUT_PATH.relative_to(HERE)}"
    )


if __name__ == "__main__":
    env = load_env()
    print(f"signed in as {signed_in_username(env)}")
    try:
        write(fetch_submissions(env))
    except PartialFetch as e:
        write(e.submissions)
        raise
