"""Collect and merge GitHub repository candidates for the daily report."""

from typing import Any, Iterable, List

from .github_client import merge_repositories
from .models import RepoSnapshot


def collect_candidates(
    client: Any,
    topics: Iterable[str],
    watch_repositories: Iterable[str],
    min_stars: int,
    search_limit: int,
) -> List[RepoSnapshot]:
    """Collect topic search results plus explicitly watched repositories.

    A watched repository is fetched only when it was not returned by any topic
    search. Search and watch requests are independent, so one failed request
    does not prevent the remaining candidates from being merged. Request
    warnings stay on ``client.warnings`` for the caller to report.
    """

    raw_items: List[dict] = []
    fetched_names = set()

    for topic in topics or ():
        try:
            items = client.search_repositories(str(topic), min_stars, search_limit) or []
        except Exception:
            continue
        raw_items.extend(items)
        for item in items:
            repo_name = item.get("full_name") or item.get("repo")
            if repo_name:
                fetched_names.add(str(repo_name).strip().lower())

    seen_watch_names = set()
    for owner_repo in watch_repositories or ():
        name = str(owner_repo).strip()
        key = name.lower()
        if not key or key in seen_watch_names or key in fetched_names:
            continue
        seen_watch_names.add(key)
        try:
            item = client.repository(name)
        except Exception:
            continue
        if item:
            raw_items.append(item)

    return merge_repositories(raw_items, min_stars=min_stars)
