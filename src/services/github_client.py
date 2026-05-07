"""Public GitHub profile + repository summary.

Two modes:

* If a personal access token is stored in keyring (``github_token``), we
  authenticate every request - 5000 requests / hour limit, full read of
  public data.
* Otherwise we go anonymous (60 requests / hour, IP-rate-limited). That is
  enough for one analysis run.

Returned data is intentionally small (top N repos, name, description,
languages, stars, last commit) so the AI Career pipeline can attach it to
the candidate prompt without blowing the context budget. Private repos and
contribution graphs are out of scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from src.services import secrets


GITHUB_API = "https://api.github.com"
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")


@dataclass
class GitHubRepo:
    name: str
    description: str
    languages: list[str]
    stars: int
    forks: int
    url: str
    last_commit: Optional[str]


@dataclass
class GitHubProfile:
    username: str
    name: Optional[str]
    bio: Optional[str]
    location: Optional[str]
    followers: int
    public_repos: int
    profile_url: str
    repos: list[GitHubRepo] = field(default_factory=list)
    error: Optional[str] = None
    authenticated: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


def extract_username(value: str) -> Optional[str]:
    """Accept full URL or bare username. Returns ``None`` if not parseable."""
    value = (value or "").strip()
    if not value:
        return None

    if "://" in value:
        parsed = urlparse(value)
        if "github.com" not in (parsed.netloc or ""):
            return None
        path = (parsed.path or "").strip("/").split("/")
        if not path or not path[0]:
            return None
        username = path[0]
    else:
        username = value.lstrip("@/")

    if _USERNAME_RE.match(username):
        return username
    return None


def _headers() -> tuple[dict[str, str], bool]:
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-hub/0.1",
    }
    token = secrets.get_secret(secrets.GITHUB_TOKEN)
    if token:
        headers["Authorization"] = f"Bearer {token}"
        return headers, True
    return headers, False


def fetch_profile(value: str, *, top_repos: int = 6, timeout: float = 15.0) -> GitHubProfile:
    username = extract_username(value)
    if not username:
        return GitHubProfile(
            username="",
            name=None,
            bio=None,
            location=None,
            followers=0,
            public_repos=0,
            profile_url="",
            error="Cannot parse a GitHub username from the value.",
        )

    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError:
        return GitHubProfile(
            username=username,
            name=None,
            bio=None,
            location=None,
            followers=0,
            public_repos=0,
            profile_url=f"https://github.com/{username}",
            error="The httpx package is missing.",
        )

    headers, authenticated = _headers()

    try:
        with httpx.Client(timeout=timeout, headers=headers) as client:
            user_resp = client.get(f"{GITHUB_API}/users/{username}")
            if user_resp.status_code == 404:
                return GitHubProfile(
                    username=username,
                    name=None,
                    bio=None,
                    location=None,
                    followers=0,
                    public_repos=0,
                    profile_url=f"https://github.com/{username}",
                    error="GitHub user not found.",
                    authenticated=authenticated,
                )
            user_resp.raise_for_status()
            user = user_resp.json()

            repos_resp = client.get(
                f"{GITHUB_API}/users/{username}/repos",
                params={"sort": "updated", "per_page": max(1, min(30, top_repos * 3))},
            )
            repos_resp.raise_for_status()
            repos_raw = repos_resp.json() or []

            repos: list[GitHubRepo] = []
            for raw in repos_raw:
                if raw.get("fork") or raw.get("archived"):
                    continue
                lang_resp = None
                try:
                    lang_resp = client.get(raw.get("languages_url") or "")
                except Exception:
                    lang_resp = None
                languages: list[str] = []
                if lang_resp is not None and lang_resp.status_code == 200:
                    try:
                        languages = list(lang_resp.json().keys())
                    except Exception:
                        languages = []
                repos.append(
                    GitHubRepo(
                        name=raw.get("name") or "",
                        description=raw.get("description") or "",
                        languages=languages,
                        stars=int(raw.get("stargazers_count") or 0),
                        forks=int(raw.get("forks_count") or 0),
                        url=raw.get("html_url") or "",
                        last_commit=raw.get("pushed_at"),
                    )
                )
                if len(repos) >= top_repos:
                    break
    except Exception as exc:
        return GitHubProfile(
            username=username,
            name=None,
            bio=None,
            location=None,
            followers=0,
            public_repos=0,
            profile_url=f"https://github.com/{username}",
            error=f"GitHub request failed: {exc}",
            authenticated=authenticated,
        )

    return GitHubProfile(
        username=username,
        name=user.get("name"),
        bio=user.get("bio"),
        location=user.get("location"),
        followers=int(user.get("followers") or 0),
        public_repos=int(user.get("public_repos") or 0),
        profile_url=user.get("html_url") or f"https://github.com/{username}",
        repos=repos,
        authenticated=authenticated,
    )
