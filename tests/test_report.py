from datetime import date, datetime, timezone
import unittest

from ai_open_source_daily.models import DailyRepo, FeedItem, RepoSnapshot
from ai_open_source_daily.report import render_report


class ReportTests(unittest.TestCase):
    def test_render_report_contains_delta_and_baseline_sections(self):
        repo = RepoSnapshot("a/ai", "AI", "https://github.com/a/ai", "demo", 120, 5, None, None, ["llm"], False, False)
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [DailyRepo(repo, 20, None, False)],
            [repo],
            [],
            ["feed unavailable"],
        )
        self.assertIn("a/ai", text)
        self.assertIn("+20", text)
        self.assertIn("基线建立中", text)
        self.assertIn("feed unavailable", text)

    def test_render_report_contains_total_star_top_ten_rank_change_and_event_source(self):
        repo = RepoSnapshot("a/ai", "AI", "https://github.com/a/ai", "demo", 140, 5, None, None, ["llm"], False, False)
        event = FeedItem(
            "AI launch",
            "https://example.com/ai-launch",
            "2026-10-01T01:00:00+00:00",
            "A concise summary",
            "GitHub Blog",
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [DailyRepo(repo, 40, None, False, rank_change=2)],
            [],
            [event],
            [],
            top_total=[DailyRepo(repo, 40, None, False, rank_change=2)],
            comparison_day=date(2026, 9, 30),
        )
        self.assertIn("总 Star 排名前 10", text)
        self.assertIn("140", text)
        self.assertIn("排名变化", text)
        self.assertIn("+2", text)
        self.assertIn("GitHub Blog", text)
        self.assertIn("2026-10-01", text)

    def test_render_report_uses_chinese_project_description(self):
        repo = RepoSnapshot(
            "tensorflow/tensorflow",
            "TensorFlow",
            "https://github.com/tensorflow/tensorflow",
            "An Open Source Machine Learning Framework for Everyone",
            200000,
            50000,
            None,
            None,
            ["machine-learning"],
            False,
            False,
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [DailyRepo(repo, 20, None, False)],
            [],
            [],
            [],
            top_total=[DailyRepo(repo, 20, None, False)],
            comparison_day=date(2026, 9, 30),
        )
        self.assertIn("深度学习框架", text)
        self.assertNotIn("An Open Source Machine Learning Framework", text)


if __name__ == "__main__":
    unittest.main()
