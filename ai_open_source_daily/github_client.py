import json
import os
import re
import time
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import RepoSnapshot, TrendingRepo


DEFAULT_TOPICS = [
    "artificial-intelligence",
    "machine-learning",
    "deep-learning",
    "llm",
    "generative-ai",
    "agents",
    "rag",
    "diffusion",
    "inference",
]


def _rate_limit_info(error: HTTPError, attempt: int) -> Tuple[Optional[float], str]:
    """Return a server-directed retry delay and safe numeric diagnostics."""
    values = {}
    for name, header in (
        ("remaining", "X-RateLimit-Remaining"),
        ("reset", "X-RateLimit-Reset"),
        ("retry_after", "Retry-After"),
    ):
        try:
            value = int((error.headers or {}).get(header, ""))
            if value >= 0:
                values[name] = value
        except (TypeError, ValueError):
            continue
    details = "; " + ", ".join("%s=%d" % item for item in values.items()) if values else ""
    if error.code not in (403, 429):
        return None, details

    delays = []
    if "retry_after" in values:
        delays.append(max(1, values["retry_after"]))
    if values.get("remaining") == 0 and "reset" in values:
        delays.append(max(1, values["reset"] - time.time() + 1))
    if delays:
        return max(delays), details

    limited = error.code == 429 or values.get("remaining") == 0
    if not limited:
        try:
            payload = json.loads(error.read(8192).decode("utf-8"))
            message = str(payload.get("message", "")).lower() if isinstance(payload, dict) else ""
            limited = "secondary rate limit" in message or "abuse detection" in message
        except (OSError, ValueError):
            pass
    return (60 * (attempt + 1) if limited else None), details


class GitHubClient:
    def __init__(self, token: Optional[str] = None, timeout: int = 20):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.timeout = timeout
        self.warnings: List[str] = []

    def _get_json(self, path: str, params: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        query = ("?" + urlencode(params)) if params else ""
        request = Request("https://api.github.com" + path + query)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "ai-open-source-daily/1.0")
        if self.token:
            request.add_header("Authorization", "Bearer " + self.token)
        for attempt in range(3):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                delay, details = _rate_limit_info(error, attempt)
                error.close()
                if attempt < 2 and delay is not None and delay <= 120:
                    time.sleep(delay)
                    continue
                self.warnings.append("GitHub API %s returned HTTP %s%s" % (path, error.code, details))
            except (URLError, TimeoutError, ValueError) as error:
                self.warnings.append("GitHub API %s failed: %s" % (path, error))
            break
        return None

    def search_repositories(self, topic: str, min_stars: int = 50, limit: int = 30) -> List[Dict[str, Any]]:
        data = self._get_json(
            "/search/repositories",
            {
                "q": "topic:%s stars:>=%d archived:false fork:false" % (topic, min_stars),
                "sort": "stars",
                "order": "desc",
                "per_page": str(min(max(limit, 1), 100)),
            },
        )
        return list((data or {}).get("items") or [])

    def repository(self, owner_repo: str) -> Optional[Dict[str, Any]]:
        return self._get_json("/repos/" + owner_repo)


class TrendingClient:
    _ai_terms = re.compile(r"\b(ai|artificial intelligence|llm|agent|machine learning|model|inference|rag|diffusion|embedding|vision|voice|tts|stt)\b", re.I)

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.warnings: List[str] = []

    def fetch_daily(self) -> List[TrendingRepo]:
        request = Request(
            "https://github.com/trending?since=daily&spoken_language_code=en",
            headers={"User-Agent": "ai-open-source-daily/1.0"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return self.parse_daily(response.read().decode("utf-8", errors="replace"))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
            self.warnings.append("GitHub Trending 获取失败：%s" % error)
            return []

    def parse_daily(self, html: str) -> List[TrendingRepo]:
        results: List[TrendingRepo] = []
        for article in re.findall(r"<article\b.*?</article>", html, flags=re.I | re.S):
            match = re.search(r"<h2\b.*?<a\b[^>]+href=['\"]/(%s/%s)['\"]" % (r"[^/'\"]+", r"[^/'\"]+"), article, flags=re.I | re.S)
            stars = re.search(r"([0-9][0-9,]*)\s+stars\s+today", article, flags=re.I)
            if not match or not stars:
                continue
            repo = unescape(match.group(1))
            text = re.sub(r"<[^>]+>", " ", unescape(article))
            text = " ".join(text.split())
            if not self._ai_terms.search(repo + " " + text):
                continue
            description_match = re.search(r"<p\b[^>]*>(.*?)</p>", article, flags=re.I | re.S)
            description = " " .join(re.sub(r"<[^>]+>", " ", unescape(description_match.group(1))).split()) if description_match else ""
            results.append(TrendingRepo(repo, "https://github.com/" + repo, int(stars.group(1).replace(",", "")), description))
        return sorted(results, key=lambda item: item.stars_today, reverse=True)


def merge_repositories(items: List[Dict[str, Any]], min_stars: int = 50) -> List[RepoSnapshot]:
    by_name: Dict[str, RepoSnapshot] = {}
    for item in items:
        repo_name = item.get("full_name") or item.get("repo")
        if not repo_name or item.get("archived") or item.get("fork"):
            continue
        stars = int(item.get("stargazers_count", item.get("stars", 0)) or 0)
        if stars < min_stars:
            continue
        snapshot = RepoSnapshot(
            repo=str(repo_name),
            name=str(item.get("name") or str(repo_name).split("/", 1)[-1]),
            url=str(item.get("html_url") or item.get("url") or "https://github.com/" + str(repo_name)),
            description=str(item.get("description") or "").strip(),
            stars=stars,
            forks=int(item.get("forks_count", item.get("forks", 0)) or 0),
            pushed_at=item.get("pushed_at"),
            updated_at=item.get("updated_at"),
            topics=list(item.get("topics") or []),
            archived=False,
            fork=False,
        )
        current = by_name.get(snapshot.repo)
        if current is None or snapshot.stars > current.stars:
            by_name[snapshot.repo] = snapshot
    return sorted(by_name.values(), key=lambda repo: (-repo.stars, repo.repo.lower()))
