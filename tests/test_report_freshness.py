from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ai_open_source_daily.cli import run
from ai_open_source_daily.models import DailyRepo, RepoSnapshot
from ai_open_source_daily.report import render_report
from ai_open_source_daily.storage import SnapshotStore


class ReportFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.repo = RepoSnapshot("a/ai", "ai", "https://github.com/a/ai", "AI tool", 100,
                                 1, None, None, ["llm"], False, False)

    def test_failed_collection_labels_historical_snapshot_without_zero_growth(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SnapshotStore(root / "data" / "snapshots")
            store.save(date(2026, 10, 1), [self.repo])
            client = SimpleNamespace(warnings=["GitHub API /search/repositories returned HTTP 403"])
            with patch("ai_open_source_daily.cli.GitHubClient", return_value=client), \
                 patch("ai_open_source_daily.cli._collect_repositories", return_value=[]), \
                 patch("ai_open_source_daily.cli.TrendingClient") as trending:
                trending.return_value.fetch_daily.return_value = []
                trending.return_value.warnings = []
                report = run(root, date(2026, 10, 4), False, 10).read_text()
            self.assertIn("历史快照截至 2026-10-01", report)
            self.assertIn("今日 Star 数据不可用", report)
            self.assertNotIn("今天没有项目出现正 Star 增长", report)
            self.assertNotIn("昨日没有正增长明显的项目", report)
            self.assertNotIn("| +0 |", report)
            self.assertNotIn("2026-10-01 → 2026-10-04", report)
            self.assertIsNone(store.load(date(2026, 10, 4)))

    def test_offline_old_snapshot_is_not_presented_as_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            SnapshotStore(root / "data" / "snapshots").save(date(2026, 10, 1), [self.repo])
            report = run(root, date(2026, 10, 4), True, 10).read_text()
            self.assertIn("今日 Star 数据不可用", report)
            self.assertIn("历史快照截至 2026-10-01", report)

    def test_multiday_growth_uses_interval_label(self):
        report = render_report(date(2026, 10, 4), datetime(2026, 10, 4, tzinfo=timezone.utc),
                               [DailyRepo(self.repo, 25, None, False)], [], [], [],
                               top_total=[DailyRepo(self.repo, 25, None, False)],
                               comparison_day=date(2026, 10, 1))
        self.assertIn("区间净增", report)
        self.assertNotIn("24h 净增", report)
        self.assertIn("2026-10-01 → 2026-10-04", report)

    def test_previous_day_growth_retains_daily_label(self):
        report = render_report(date(2026, 10, 4), datetime(2026, 10, 4, tzinfo=timezone.utc),
                               [DailyRepo(self.repo, 25, None, False)], [], [], [],
                               comparison_day=date(2026, 10, 3))
        self.assertIn("24h 净增", report)


if __name__ == "__main__":
    unittest.main()
