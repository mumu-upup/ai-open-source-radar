from datetime import date
from pathlib import Path
import tempfile
import unittest

from ai_open_source_daily.cli import main
from ai_open_source_daily.cli import _collect_repositories, _github_collection_failed, _read_feed_items, _yesterday_window


class OfflineCliTests(unittest.TestCase):
    def test_read_feed_items_supports_huggingface_model_activity(self):
        from datetime import datetime, timezone

        from ai_open_source_daily.feeds import FeedReader

        items = _read_feed_items(
            FeedReader(),
            '[{"id":"Qwen/Qwen-Next","lastModified":"2026-09-30T05:00:00Z"}]',
            {"name": "Qwen on Hugging Face", "format": "huggingface_models"},
            datetime(2026, 9, 30, tzinfo=timezone.utc),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(items[0].source, "Qwen on Hugging Face")

    def test_collect_repositories_includes_explicit_watchlist(self):
        class FakeClient:
            warnings = []

            def search_repositories(self, topic, min_stars, limit):
                return []

            def repository(self, owner_repo):
                return {
                    "full_name": owner_repo,
                    "name": owner_repo.split("/", 1)[-1],
                    "html_url": "https://github.com/" + owner_repo,
                    "description": "watched model",
                    "stargazers_count": 123,
                    "forks_count": 0,
                    "topics": ["model"],
                    "archived": False,
                    "fork": False,
                }

        repos = _collect_repositories(
            FakeClient(),
            {"topics": ["llm"], "watch_repositories": ["NousResearch/hermes-agent"], "min_stars": 50, "search_limit": 10},
        )
        self.assertEqual([repo.repo for repo in repos], ["NousResearch/hermes-agent"])

    def test_github_collection_failure_detects_rate_limit_warnings(self):
        self.assertTrue(_github_collection_failed(["GitHub API /search/repositories returned HTTP 403"]))
        self.assertFalse(_github_collection_failed([]))

    def test_yesterday_window_uses_shanghai_calendar_day(self):
        start, end = _yesterday_window(date(2026, 10, 1))
        self.assertEqual(start.isoformat(), "2026-09-29T16:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-09-30T16:00:00+00:00")

    def test_offline_cli_creates_report_from_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data" / "snapshots").mkdir(parents=True)
            (root / "reports").mkdir()
            (root / "data" / "snapshots" / "2026-10-01.json").write_text("[]", encoding="utf-8")
            self.assertEqual(main(["--root", str(root), "--date", "2026-10-01", "--offline"]), 0)
            self.assertTrue((root / "reports" / "2026-10-01.md").exists())


if __name__ == "__main__":
    unittest.main()
