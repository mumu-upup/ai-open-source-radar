import json
import os
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import RepoSnapshot


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
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            self.warnings.append("GitHub API %s returned HTTP %s" % (path, error.code))
        except (URLError, TimeoutError, ValueError) as error:
            self.warnings.append("GitHub API %s failed: %s" % (path, error))
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
