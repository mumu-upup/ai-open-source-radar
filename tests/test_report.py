from datetime import date, datetime, timezone
import unittest

from ai_open_source_daily.models import DailyRepo, RepoSnapshot
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


if __name__ == "__main__":
    unittest.main()
