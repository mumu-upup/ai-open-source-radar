import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .candidates import collect_candidates
from .feeds import FeedReader
from .github_client import DEFAULT_TOPICS, GitHubClient, TrendingClient
from .models import DailyRepo, FeedItem, RepoSnapshot
from .report import render_report
from .storage import SnapshotStore, calculate_delta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


def local_now() -> datetime:
    if ZoneInfo:
        return datetime.now(ZoneInfo("Asia/Shanghai"))
    return datetime.now(timezone(timedelta(hours=8)))


def _yesterday_window(day: date) -> Tuple[datetime, datetime]:
    """Return the previous Shanghai calendar day as a UTC half-open interval."""
    if ZoneInfo:
        local_zone = ZoneInfo("Asia/Shanghai")
    else:  # pragma: no cover - Python versions without zoneinfo
        local_zone = timezone(timedelta(hours=8))
    start_local = datetime.combine(day - timedelta(days=1), datetime.min.time(), tzinfo=local_zone)
    end_local = datetime.combine(day, datetime.min.time(), tzinfo=local_zone)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _load_config(root: Path) -> Dict:
    path = root / "config" / "sources.json"
    if not path.exists():
        return {"topics": DEFAULT_TOPICS, "min_stars": 50, "search_limit": 30, "feeds": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _fetch_feed(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ai-open-source-daily/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _previous_snapshot(store: SnapshotStore, day: date, days: int = 7) -> Tuple[Optional[date], List[RepoSnapshot]]:
    for offset in range(1, days + 1):
        snapshot_day = day - timedelta(days=offset)
        items = store.load(snapshot_day)
        if items is not None:
            return snapshot_day, items
    return None, []


def _rank_repositories(
    store: SnapshotStore,
    day: date,
    repos: List[RepoSnapshot],
) -> Tuple[List[DailyRepo], List[DailyRepo], List[RepoSnapshot], Optional[date]]:
    comparison_day, previous_repos = _previous_snapshot(store, day)
    previous_by_name = {repo.repo: repo for repo in previous_repos}
    previous_rank = {
        repo.repo: index
        for index, repo in enumerate(sorted(previous_repos, key=lambda item: (-item.stars, item.repo.lower())), 1)
    }
    current_rank = {
        repo.repo: index
        for index, repo in enumerate(sorted(repos, key=lambda item: (-item.stars, item.repo.lower())), 1)
    }

    all_items: List[DailyRepo] = []
    baseline: List[RepoSnapshot] = []
    for repo in repos:
        previous = previous_by_name.get(repo.repo)
        previous_week = store.find_previous(repo.repo, day, 7)
        delta = calculate_delta(repo.stars, previous.stars if previous else None)
        delta_week = calculate_delta(repo.stars, previous_week.stars if previous_week else None)
        rank_change = None
        if repo.repo in previous_rank and repo.repo in current_rank:
            rank_change = previous_rank[repo.repo] - current_rank[repo.repo]
        item = DailyRepo(repo, delta, delta_week, previous is None, rank_change)
        all_items.append(item)
        if previous is None:
            baseline.append(repo)

    growth = sorted(
        [item for item in all_items if item.delta_24h is not None and item.delta_24h > 0],
        key=lambda item: (-item.delta_24h, -item.repo.stars, item.repo.repo.lower()),
    )
    top_total = sorted(all_items, key=lambda item: (-item.repo.stars, item.repo.repo.lower()))[:10]
    return growth, top_total, baseline, comparison_day


def _offline_snapshot(store: SnapshotStore, day: date) -> Tuple[Optional[date], List[RepoSnapshot]]:
    current = store.load(day)
    if current is not None:
        return day, current
    for offset in range(1, 31):
        previous = store.load(day - timedelta(days=offset))
        if previous is not None:
            return day - timedelta(days=offset), previous
    return None, []


def _dedupe_feed_items(items: List[FeedItem]) -> List[FeedItem]:
    seen = set()
    result = []
    for item in sorted(items, key=lambda value: value.published_at, reverse=True):
        key = item.url or item.title
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _github_collection_failed(warnings: List[str]) -> bool:
    return any(warning.startswith("GitHub API ") for warning in warnings)


def _collect_repositories(client: GitHubClient, config: Dict) -> List[RepoSnapshot]:
    """Collect topic candidates plus explicit canonical repositories to watch."""
    topics = config.get("topics") or DEFAULT_TOPICS
    min_stars = int(config.get("min_stars", 50))
    search_limit = int(config.get("search_limit", 30))
    return collect_candidates(
        client,
        topics,
        config.get("watch_repositories") or [],
        min_stars,
        search_limit,
    )


def _read_feed_items(
    reader: FeedReader,
    content: str,
    source: Dict,
    since: datetime,
    until: datetime,
) -> List[FeedItem]:
    source_format = source.get("format", "xml")
    if source_format == "markdown":
        return reader.read_markdown(content, since, source.get("name", ""), until=until, base_url=source.get("url", ""))
    if source_format == "update_markup":
        return reader.read_update_markup(content, since, source.get("name", ""), until=until, base_url=source.get("url", ""))
    if source_format == "deepseek_html":
        return reader.read_deepseek_html(content, since, source.get("name", ""), until=until, base_url=source.get("url", ""))
    if source_format == "huggingface_models":
        return reader.read_huggingface_models(content, since, source.get("name", ""), until=until, base_url=source.get("url", ""))
    return reader.read(content, since, source.get("name", ""), ai_only=bool(source.get("ai_only", True)), until=until)


def run(root: Path, day: date, offline: bool, limit: int) -> Path:
    config = _load_config(root)
    store = SnapshotStore(root / "data" / "snapshots")
    warnings: List[str] = []
    generated_at = local_now()
    feed_items: List[FeedItem] = []
    trending = []
    snapshot_day = None

    if offline:
        snapshot_day, repos = _offline_snapshot(store, day)
        warnings.append("离线模式：未请求 GitHub 或 RSS，项目数据来自本地快照。")
    else:
        client = GitHubClient()
        repos = _collect_repositories(client, config)
        warnings.extend(client.warnings)
        trending_client = TrendingClient()
        trending = trending_client.fetch_daily()
        warnings.extend(trending_client.warnings)
        cached_day, cached = _offline_snapshot(store, day)
        if _github_collection_failed(client.warnings):
            if cached:
                repos = cached
                snapshot_day = cached_day
                warnings.append("GitHub API 返回限流或错误，使用上一份完整本地快照，避免覆盖项目榜。")
            elif repos:
                warnings.append("GitHub API 返回限流或错误，当前项目榜可能不完整，未保存为新快照。")
                repos = []
        elif repos:
            store.save(day, repos)
            snapshot_day = day
        elif cached:
            repos = cached
            snapshot_day = cached_day
            warnings.append("GitHub 没有返回候选仓库，使用最近一次本地快照。")
        reader = FeedReader()
        since, until = _yesterday_window(day)
        for source in config.get("feeds") or []:
            try:
                content = _fetch_feed(source["url"])
                items = _read_feed_items(reader, content, source, since, until)
                feed_items.extend(items)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
                warnings.append("RSS %s 获取失败：%s" % (source.get("name", source.get("url", "未知来源")), error))
        feed_items = _dedupe_feed_items(feed_items)

    current_data_available = snapshot_day == day
    if current_data_available:
        rankings, top_total, baseline, comparison_day = _rank_repositories(store, day, repos)
    else:
        rankings, baseline, comparison_day = [], [], None
        top_total = [DailyRepo(repo, None, None, False) for repo in
                     sorted(repos, key=lambda item: (-item.stars, item.repo.lower()))[:10]]
    rankings = rankings[:limit]
    report = render_report(
        day,
        generated_at,
        rankings,
        baseline,
        feed_items,
        warnings,
        trending,
        top_total=top_total,
        comparison_day=comparison_day,
        current_data_available=current_data_available,
        snapshot_day=snapshot_day,
    )
    report_path = root / "reports" / (day.isoformat() + ".md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the daily AI open-source report")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--date", dest="day", help="report date in YYYY-MM-DD")
    parser.add_argument("--offline", action="store_true", help="use local snapshots only")
    parser.add_argument("--limit", type=int, default=10, help="number of growth-ranked projects")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    day = date.fromisoformat(args.day) if args.day else local_now().date()
    path = run(root, day, args.offline, max(1, args.limit))
    print("Wrote %s" % path)
    return 0
