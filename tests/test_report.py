from datetime import date, datetime, timezone
import unittest

from ai_open_source_daily.models import DailyRepo, FeedItem, RepoSnapshot, TrendingRepo
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

    def test_render_report_labels_event_count_as_yesterday(self):
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [],
            [],
            [],
            [],
            comparison_day=date(2026, 9, 30),
        )
        self.assertIn("昨日（Asia/Shanghai）收录 0 条 AI 动态", text)

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
        self.assertIn("An Open Source Machine Learning Framework", text)

    def test_render_report_adds_chinese_event_summary(self):
        event = FeedItem(
            "Open TTS Leaderboard: Scalable Evaluation for Multilingual Text-to-Speech and Voice Cloning",
            "https://example.com/tts",
            "2026-10-01T01:00:00+00:00",
            "A leaderboard for multilingual text-to-speech.",
            "Hugging Face Blog",
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [],
            [],
            [event],
            [],
            comparison_day=date(2026, 9, 30),
        )
        self.assertIn("中文概述", text)
        self.assertIn("文本转语音", text)
        self.assertIn("English summary", text)
        self.assertIn("A leaderboard for multilingual text-to-speech", text)

    def test_render_report_uses_chinese_trending_description(self):
        item = TrendingRepo(
            "huggingface/transformers",
            "https://github.com/huggingface/transformers",
            42,
            "The model-definition framework for state-of-the-art machine learning",
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [],
            [],
            [],
            [],
            trending=[item],
            comparison_day=date(2026, 9, 30),
        )
        self.assertIn("覆盖文本、视觉和音频模型", text)
        self.assertIn("English description", text)
        self.assertIn("The model-definition framework", text)

    def test_render_report_shows_more_than_ten_events_and_product_context(self):
        events = [
            FeedItem(
                "0.161.0",
                "https://example.com/codex",
                "2026-09-30T01:00:00+00:00",
                "Release notes",
                "OpenAI Codex Release",
            )
            for _ in range(12)
        ]
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [],
            [],
            events,
            [],
            comparison_day=date(2026, 9, 30),
        )
        self.assertEqual(text.count("- **OpenAI Codex Release"), 1)
        self.assertIn("Codex 发布版本更新", text)

    def test_render_report_shows_focus_product_status(self):
        event = FeedItem(
            "0.161.0",
            "https://example.com/codex",
            "2026-09-30T01:00:00+00:00",
            "Release notes",
            "OpenAI Codex Release",
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [],
            [],
            [event],
            [],
            comparison_day=date(2026, 9, 30),
        )
        self.assertIn("## 重点产品更新", text)
        self.assertIn("**Codex**：昨日收录 1 条", text)
        self.assertIn("**GLM**：昨日未发现公开更新", text)

    def test_render_report_adds_chinese_summary_for_openai_news(self):
        event = FeedItem(
            "Disrupting a coordinated model-distillation campaign",
            "https://example.com/openai",
            "2026-09-30T10:30:00+00:00",
            "OpenAI strengthened defenses against adversarial distillation.",
            "OpenAI News",
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [], [], [event], [], comparison_day=date(2026, 9, 30),
        )
        self.assertIn("阻止模型蒸馏攻击", text)

    def test_render_report_marks_prerelease_product_updates(self):
        event = FeedItem(
            "0.161.0-alpha.4",
            "https://example.com/codex",
            "2026-09-30T11:58:01+00:00",
            "Release notes",
            "OpenAI Codex Release",
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [], [], [event], [], comparison_day=date(2026, 9, 30),
        )
        self.assertIn("预发布版本", text)

    def test_render_report_does_not_mark_stable_claude_release_as_prerelease(self):
        event = FeedItem(
            "v2.1.285",
            "https://example.com/claude",
            "2026-09-29T19:27:30+00:00",
            "Added a preview helper in the changelog details.",
            "Anthropic Claude Code Release",
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [], [], [event], [], comparison_day=date(2026, 9, 30),
        )
        self.assertNotIn("Claude 发布版本更新，具体改动和修复请查看英文发布说明。当前标记为预发布版本", text)

    def test_render_report_tracks_popular_model_and_agent_updates(self):
        events = [
            FeedItem(
                "v1.0.0",
                "https://example.com/hermes",
                "2026-09-30T01:00:00+00:00",
                "Hermes agent release notes",
                "NousResearch Hermes Agent Release",
            ),
            FeedItem(
                "Improve Jev SDK tools",
                "https://example.com/jev",
                "2026-09-30T02:00:00+00:00",
                "TypeSafe System One SDK update",
                "TypeSafe Jev SDK Activity",
            ),
        ]
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [], [], events, [], comparison_day=date(2026, 9, 30),
        )
        self.assertIn("**Hermes**：昨日收录 1 条", text)
        self.assertIn("**Jev**：昨日收录 1 条", text)
        self.assertIn("Jev / TypeSafe System One", text)

    def test_render_report_prioritizes_configured_source_for_product_labels(self):
        events = [
            FeedItem(
                "v4.1.22",
                "https://example.com/cline",
                "2026-09-30T01:00:00+00:00",
                "Anthropic fallback support for Claude models",
                "Cline Release",
            ),
            FeedItem(
                "v0.1.0",
                "https://example.com/pi",
                "2026-09-30T02:00:00+00:00",
                "Codex-compatible tools for Pi Agent",
                "Pi Agent Release",
            ),
        ]
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [], [], events, [], comparison_day=date(2026, 9, 30),
        )
        self.assertIn("**Cline**：昨日收录 1 条（来源：Cline Release）", text)
        self.assertIn("**Pi**：昨日收录 1 条（来源：Pi Agent Release）", text)
        self.assertIn("**Claude**：昨日未发现公开更新", text)

    def test_render_report_prioritizes_event_source_diversity(self):
        events = [
            FeedItem(
                "Hermes release %d" % index,
                "https://example.com/hermes/%d" % index,
                "2026-09-30T%02d:00:00+00:00" % (23 - index),
                "Hermes details",
                "Hermes Agent Release",
            )
            for index in range(25)
        ] + [
            FeedItem(
                "OpenCode release",
                "https://example.com/opencode",
                "2026-09-30T01:00:00+00:00",
                "OpenCode details",
                "OpenCode Release",
            )
        ]
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [], [], events, [], comparison_day=date(2026, 9, 30),
        )
        self.assertIn("OpenCode release", text)
        self.assertIn("**Hermes**：昨日收录 25 条", text)

    def test_render_report_does_not_leave_trailing_spaces_after_summary_truncation(self):
        event = FeedItem(
            "Long update",
            "https://example.com/long",
            "2026-09-30T01:00:00+00:00",
            "word " * 100,
            "OpenAI News",
        )
        text = render_report(
            date(2026, 10, 1),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            [], [], [event], [], comparison_day=date(2026, 9, 30),
        )
        self.assertNotIn(" \n", text)


if __name__ == "__main__":
    unittest.main()
