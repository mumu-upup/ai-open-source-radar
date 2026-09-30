# AI Open Source Daily Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free Python job that snapshots AI GitHub repositories, calculates daily Star growth, collects AI activity, and writes `reports/YYYY-MM-DD.md` every day at 09:00 Asia/Shanghai.

**Architecture:** `GitHubClient` handles HTTP and API pagination, `SnapshotStore` persists one JSON snapshot per day, `Collector` merges topic searches and repository metadata, `FeedReader` parses configured RSS feeds, and `MarkdownReport` renders the final report. The CLI composes these pieces and supports online and offline modes; a launchd plist runs the CLI daily.

**Tech Stack:** Python 3.11+ standard library (`urllib`, `json`, `xml.etree.ElementTree`, `argparse`, `datetime`, `pathlib`, `unittest`), macOS launchd.

## Global Constraints

- “新增关注者” means GitHub `stargazers_count`; daily growth is the difference between fixed-time snapshots.
- First-run repositories without a previous snapshot must be labeled “基线建立中”.
- Exclude archived and fork repositories; default minimum total stars is 50.
- Keep credentials out of Markdown, snapshots, logs, and committed files.
- Continue when an individual GitHub query, repository, or RSS feed fails; report warnings.
- No third-party Python dependency is required.

---

### Task 1: Domain calculations and persistence

**Files:**
- Create: `ai_open_source_daily/models.py`
- Create: `ai_open_source_daily/storage.py`
- Test: `tests/test_storage_and_metrics.py`

**Interfaces:**
- `RepoSnapshot(repo: str, name: str, url: str, description: str, stars: int, forks: int, pushed_at: str | None, updated_at: str | None, topics: list[str], archived: bool, fork: bool)` dataclass.
- `DailyRepo(repo: RepoSnapshot, delta_24h: int | None, delta_7d: int | None, baseline: bool)` dataclass.
- `calculate_delta(current: int, previous: int | None) -> int | None`.
- `SnapshotStore(root: Path)` with `save(day: date, repos: list[RepoSnapshot]) -> Path`, `load(day: date) -> list[RepoSnapshot] | None`, and `find_previous(repo: str, before: date, days: int) -> RepoSnapshot | None`.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date
from pathlib import Path
from ai_open_source_daily.models import RepoSnapshot
from ai_open_source_daily.storage import SnapshotStore, calculate_delta

def test_calculate_delta_marks_missing_history_as_baseline():
    assert calculate_delta(120, None) is None
    assert calculate_delta(120, 100) == 20
    assert calculate_delta(100, 120) == -20

def test_snapshot_store_round_trips_repo_snapshots(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    repo = RepoSnapshot("acme/ai", "AI", "https://github.com/acme/ai", "demo", 100, 4, None, None, ["llm"], False, False)
    store.save(date(2026, 10, 1), [repo])
    assert store.load(date(2026, 10, 1)) == [repo]

def test_find_previous_returns_nearest_available_snapshot(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    repo = RepoSnapshot("acme/ai", "AI", "https://github.com/acme/ai", "demo", 100, 4, None, None, ["llm"], False, False)
    store.save(date(2026, 9, 29), [repo])
    assert store.find_previous("acme/ai", date(2026, 10, 1), 7) == repo
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_storage_and_metrics -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_open_source_daily'`.

- [ ] **Step 3: Implement the minimal models and JSON store**

```python
# ai_open_source_daily/storage.py
import json
from datetime import date, timedelta
from pathlib import Path
from .models import RepoSnapshot

def calculate_delta(current: int, previous: int | None) -> int | None:
    return None if previous is None else current - previous

class SnapshotStore:
    def __init__(self, root: Path): self.root = root
    def _path(self, day: date) -> Path: return self.root / f"{day.isoformat()}.json"
    def save(self, day, repos):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(day)
        path.write_text(json.dumps([r.to_dict() for r in repos], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path
    def load(self, day):
        path = self._path(day)
        if not path.exists(): return None
        return [RepoSnapshot.from_dict(item) for item in json.loads(path.read_text(encoding="utf-8"))]
    def find_previous(self, repo, before, days):
        for offset in range(1, days + 1):
            items = self.load(before - timedelta(days=offset))
            if items:
                for item in items:
                    if item.repo == repo: return item
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_storage_and_metrics -v`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_open_source_daily/models.py ai_open_source_daily/storage.py tests/test_storage_and_metrics.py
git commit -m "feat: add snapshot storage and star delta metrics"
```

### Task 2: GitHub collection and RSS activity

**Files:**
- Create: `ai_open_source_daily/github_client.py`
- Create: `ai_open_source_daily/feeds.py`
- Modify: `ai_open_source_daily/models.py`
- Test: `tests/test_collectors.py`

**Interfaces:**
- `GitHubClient.search_repositories(topic: str, min_stars: int, limit: int) -> list[dict]`.
- `GitHubClient.repository(owner_repo: str) -> dict`.
- `merge_repositories(items: list[dict], min_stars: int) -> list[RepoSnapshot]`.
- `FeedReader.read(xml_text: str, since: datetime) -> list[FeedItem]`.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime, timezone
from ai_open_source_daily.github_client import merge_repositories
from ai_open_source_daily.feeds import FeedReader

def test_merge_repositories_deduplicates_and_filters_forks_and_archived():
    items = [
        {"full_name":"a/ok","name":"ok","html_url":"https://github.com/a/ok","description":"x","stargazers_count":80,"forks_count":2,"pushed_at":None,"updated_at":None,"topics":["llm"],"archived":False,"fork":False},
        {"full_name":"a/ok","name":"ok","html_url":"https://github.com/a/ok","description":"x","stargazers_count":80,"forks_count":2,"pushed_at":None,"updated_at":None,"topics":["llm"],"archived":False,"fork":False},
        {"full_name":"a/old","name":"old","html_url":"https://github.com/a/old","description":"x","stargazers_count":80,"forks_count":2,"pushed_at":None,"updated_at":None,"topics":[],"archived":True,"fork":False},
        {"full_name":"a/small","name":"small","html_url":"https://github.com/a/small","description":"x","stargazers_count":49,"forks_count":2,"pushed_at":None,"updated_at":None,"topics":[],"archived":False,"fork":False},
    ]
    result = merge_repositories(items, min_stars=50)
    assert [item.repo for item in result] == ["a/ok"]

def test_feed_reader_returns_recent_items_only():
    xml = """<rss><channel><item><title>AI launch</title><link>https://example.com/a</link><pubDate>Thu, 01 Oct 2026 01:00:00 GMT</pubDate><description>summary</description></item><item><title>Old</title><link>https://example.com/old</link><pubDate>Wed, 30 Sep 2026 01:00:00 GMT</pubDate></item></channel></rss>"""
    items = FeedReader().read(xml, datetime(2026, 9, 30, 12, tzinfo=timezone.utc))
    assert [item.title for item in items] == ["AI launch"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_collectors -v`
Expected: FAIL because collector modules do not exist.

- [ ] **Step 3: Implement HTTP, repository filtering, and RSS parsing**

Use `urllib.request.Request` with `Authorization: Bearer <GITHUB_TOKEN>` only when the environment variable exists. Parse GitHub JSON into `RepoSnapshot`; catch per-request `HTTPError` and return an empty result plus a warning. Parse RSS with `xml.etree.ElementTree`, support RFC 2822 and ISO-8601 dates, and ignore entries older than `since`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_collectors -v`
Expected: all collector tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_open_source_daily/github_client.py ai_open_source_daily/feeds.py ai_open_source_daily/models.py tests/test_collectors.py
git commit -m "feat: collect AI repositories and recent feed activity"
```

### Task 3: Markdown report and CLI

**Files:**
- Create: `ai_open_source_daily/report.py`
- Create: `ai_open_source_daily/cli.py`
- Create: `ai_open_source_daily/__main__.py`
- Create: `config/sources.json`
- Create: `.env.example`
- Test: `tests/test_report.py`

**Interfaces:**
- `render_report(day: date, generated_at: datetime, rankings: list[DailyRepo], baseline: list[RepoSnapshot], feed_items: list[FeedItem], warnings: list[str]) -> str`.
- `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date, datetime, timezone
from ai_open_source_daily.models import DailyRepo, RepoSnapshot
from ai_open_source_daily.report import render_report

def test_render_report_contains_delta_and_baseline_sections():
    repo = RepoSnapshot("a/ai", "AI", "https://github.com/a/ai", "demo", 120, 5, None, None, ["llm"], False, False)
    text = render_report(date(2026, 10, 1), datetime(2026, 10, 1, tzinfo=timezone.utc), [DailyRepo(repo, 20, None, False)], [repo], [], ["feed unavailable"])
    assert "a/ai" in text
    assert "+20" in text
    assert "基线建立中" in text
    assert "feed unavailable" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_report -v`
Expected: FAIL because the renderer does not exist.

- [ ] **Step 3: Implement renderer and CLI**

The CLI should load sources from `config/sources.json`, gather one page per topic, merge repositories, load yesterday and seven-day snapshots, render the report, save today’s snapshot, and write `reports/YYYY-MM-DD.md`. `--offline` must skip network calls and render from the latest snapshot. Use `argparse` for `--date`, `--root`, `--offline`, and `--limit`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_report -v`
Expected: renderer test PASS.

- [ ] **Step 5: Commit**

```bash
git add ai_open_source_daily/report.py ai_open_source_daily/cli.py ai_open_source_daily/__main__.py config/sources.json .env.example tests/test_report.py
git commit -m "feat: generate daily AI open source markdown reports"
```

### Task 4: Schedule, offline fixture, and end-to-end verification

**Files:**
- Create: `scripts/install_launchd.sh`
- Create: `launchd/com.codex.ai-open-source-daily.plist`
- Create: `tests/fixtures/empty-snapshot.json`
- Create: `README.md`
- Modify: `ai_open_source_daily/cli.py`
- Test: `tests/test_cli_offline.py`

**Interfaces:**
- `scripts/install_launchd.sh` installs the user-level launchd job with the repository absolute path.
- Offline CLI writes a report without network access.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from ai_open_source_daily.cli import main

def test_offline_cli_creates_report_from_snapshot(tmp_path: Path):
    (tmp_path / "data/snapshots").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    (tmp_path / "data/snapshots/2026-10-01.json").write_text("[]", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--date", "2026-10-01", "--offline"]) == 0
    assert (tmp_path / "reports/2026-10-01.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli_offline -v`
Expected: FAIL because CLI and launchd files are not implemented.

- [ ] **Step 3: Implement launchd installation and documentation**

Use a plist with `StartCalendarInterval` hour `9`, minute `0`, `StandardOutPath` and `StandardErrorPath` under `logs/`, and `ProgramArguments` invoking the repository’s `.venv/bin/python -m ai_open_source_daily`. The installer replaces `__ROOT__` with the absolute repository path, creates `~/Library/LaunchAgents`, loads the plist, and prints the loaded label. Document optional `GITHUB_TOKEN`, first-run baseline behavior, report paths, and uninstall command.

- [ ] **Step 4: Run all tests and an online smoke run**

Run: `python -m unittest discover -v`.
Expected: all tests PASS.

Run: `python -m ai_open_source_daily --root . --date 2026-10-01 --limit 20`.
Expected: creates `reports/2026-10-01.md` and `data/snapshots/2026-10-01.json`; if GitHub or RSS is unavailable, report contains a warning and exits 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/install_launchd.sh launchd/com.codex.ai-open-source-daily.plist tests/fixtures/empty-snapshot.json README.md tests/test_cli_offline.py
 git commit -m "feat: schedule daily AI open source reports"
```
