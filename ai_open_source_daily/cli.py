import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .feeds import FeedReader
from .github_client import DEFAULT_TOPICS, GitHubClient, TrendingClient, merge_repositories
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


def _load_config(root: Path) -> Dict:
    path = root / "config" / "sources.json"
    if not path.exists():
        return {"topics": DEFAULT_TOPICS, "min_stars": 50, "search_limit": 30, "feeds": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _fetch_feed(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ai-open-source-daily/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _daily_repos(store: SnapshotStore, day: date, repos: List[RepoSnapshot]) -> Tuple[List[DailyRepo], List[RepoSnapshot]]:
    rankings: List[DailyRepo] = []
    baseline: List[RepoSnapshot] = []
    for repo in repos:
        previous = store.find_previous(repo.repo, day, 1)
        previous_week = store.find_previous(repo.repo, day, 7)
        delta = calculate_delta(repo.stars, previous.stars if previous else None)
        delta_week = calculate_delta(repo.stars, previous_week.stars if previous_week else None)
        if delta is None:
            baseline.append(repo)
        else:
            rankings.append(DailyRepo(repo, delta, delta_week, False))
    rankings.sort(key=lambda item: ((item.delta_24h is not None, item.delta_24h or 0), item.repo.stars), reverse=True)
    return rankings, baseline


def _offline_repos(store: SnapshotStore, day: date) -> List[RepoSnapshot]:
    current = store.load(day)
    if current is not None:
        return current
    for offset in range(1, 31):
        previous = store.load(day - timedelta(days=offset))
        if previous is not None:
            return previous
    return []


def run(root: Path, day: date, offline: bool, limit: int) -> Path:
    config = _load_config(root)
    store = SnapshotStore(root / "data" / "snapshots")
    warnings: List[str] = []
    generated_at = local_now()
    feed_items: List[FeedItem] = []
    trending = []

    if offline:
        repos = _offline_repos(store, day)
        warnings.append("离线模式：未请求 GitHub 或 RSS，项目数据来自本地快照。")
    else:
        client = GitHubClient()
        raw_items: List[dict] = []
        topics = config.get("topics") or DEFAULT_TOPICS
        min_stars = int(config.get("min_stars", 50))
        search_limit = int(config.get("search_limit", 30))
        for topic in topics:
            raw_items.extend(client.search_repositories(str(topic), min_stars, search_limit))
        repos = merge_repositories(raw_items, min_stars)
        warnings.extend(client.warnings)
        trending_client = TrendingClient()
        trending = trending_client.fetch_daily()
        warnings.extend(trending_client.warnings)
        if repos:
            store.save(day, repos)
        else:
            cached = _offline_repos(store, day)
            if cached:
                repos = cached
                warnings.append("GitHub 没有返回候选仓库，使用最近一次本地快照。")
        reader = FeedReader()
        since = generated_at.astimezone(timezone.utc) - timedelta(hours=24)
        for source in config.get("feeds") or []:
            try:
                feed_items.extend(reader.read(_fetch_feed(source["url"]), since))
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
                warnings.append("RSS %s 获取失败：%s" % (source.get("name", source.get("url", "未知来源")), error))
        feed_items.sort(key=lambda item: item.published_at, reverse=True)

    rankings, baseline = _daily_repos(store, day, repos)
    rankings = rankings[:limit]
    report = render_report(day, generated_at, rankings, baseline, feed_items, warnings, trending)
    report_path = root / "reports" / (day.isoformat() + ".md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the daily AI open-source report")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--date", dest="day", help="report date in YYYY-MM-DD")
    parser.add_argument("--offline", action="store_true", help="use local snapshots only")
    parser.add_argument("--limit", type=int, default=20, help="number of ranked projects")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    day = date.fromisoformat(args.day) if args.day else local_now().date()
    path = run(root, day, args.offline, max(1, args.limit))
    print("Wrote %s" % path)
    return 0
