from datetime import date, datetime, timezone
import unittest
from xml.sax.saxutils import escape

from ai_open_source_daily.feeds import FeedReader
from ai_open_source_daily.github_client import TrendingClient, merge_repositories
from ai_open_source_daily.report import render_report


class HermesPipelineFeedTests(unittest.TestCase):
    prefix = "https://github.com/NousResearch/hermes-agent/releases/tag/"
    metadata = '{"attempt":3,"autopublish":false,"claimEpoch":1793635086,"commit":"f0…'

    def read_entries(self, rows):
        entries = []
        for title, url, summary in rows:
            entries.append(
                '<entry><title>%s</title><link href="%s"/>'
                '<updated>2026-11-02T10:00:00Z</updated>'
                '<content type="html">%s</content></entry>'
                % (escape(title), escape(url), escape(summary))
            )
        return FeedReader().read(
            '<feed xmlns="http://www.w3.org/2005/Atom">%s</feed>' % "".join(entries),
            datetime(2026, 11, 1, 16, tzinfo=timezone.utc),
            source="Hermes Agent Release",
            until=datetime(2026, 11, 2, 16, tzinfo=timezone.utc),
        )

    def test_pipeline_tags_are_excluded_before_news_counts(self):
        items = self.read_entries([
            ("rc.1-v0.22.6", self.prefix + "rc.1-v0.22.6", '{"attempt":1,"autopublish":false}'),
            ("rc.3-v0.22.6", self.prefix + "rc.3-v0.22.6", "<pre>" + self.metadata + "</pre>"),
            ("abandoned-rc.2-v0.22.6", self.prefix + "abandoned-rc.2-v0.22.6",
             '<p>{&quot;attempt&quot;:2,&quot;attemptRef&quot;:&quot;rc.2-v0.22.6&quot;,&quot;schema&quot;:1}</p>'),
            ("v0.22.6", self.prefix + "v0.22.6", "Fix tool timeout handling."),
        ])
        self.assertEqual([item.title for item in items], ["v0.22.6"])
        report = render_report(date(2026, 11, 3), datetime(2026, 11, 3, tzinfo=timezone.utc),
                               [], [], items, [], comparison_day=date(2026, 11, 2))
        self.assertIn("**Hermes**：昨日收录 1 条", report)
        self.assertIn("收录 1 条 AI 动态", report)
        self.assertNotIn("rc.3-v0.22.6", report)
        self.assertNotIn("abandoned-rc", report)

    def test_normal_release_candidates_and_unrelated_entries_are_preserved(self):
        cases = [
            (self.prefix + "rc.3-v0.22.6", "Fix tool timeout handling."),
            (self.prefix + "rc.3-v0.22.6", 'Changes include {"attempt":3,"autopublish":false} diagnostics.'),
            (self.prefix + "rc.3-v0.22.6", '{"attempt":3,"autopublish":true}'),
            (self.prefix + "v0.22.6-rc.3", self.metadata),
            (self.prefix + "v0.22.5%2Bcanary.20261102T065013Z", "Hermes Agent canary 20261102T065013Z"),
            (self.prefix.replace("NousResearch/hermes-agent", "other/agent") + "rc.3-v0.22.6", self.metadata),
            (self.prefix.replace("github.com", "example.com") + "rc.3-v0.22.6", self.metadata),
            (self.prefix.replace("releases/tag", "discussions") + "rc.3-v0.22.6", self.metadata),
            ("https://[malformed", self.metadata),
        ]
        for url, summary in cases:
            with self.subTest(url=url, summary=summary):
                items = self.read_entries([("rc.3-v0.22.6", url, summary)])
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0].url, url)

    def test_rc_metadata_followed_by_real_release_notes_is_preserved(self):
        for prefix in ('{"attempt":3,"autopublish":false}', self.metadata):
            for ending in (".", "…", "..."):
                for markup in (True, False):
                    with self.subTest(prefix=prefix, ending=ending, markup=markup):
                        notes = "Fixed tool timeout handling and added retries" + ending
                        summary = ("<pre>%s</pre><h2>What changed</h2><p>%s</p>" % (prefix, notes)
                                   if markup else prefix + "\nWhat changed\n" + notes)
                        items = self.read_entries([("rc.3-v0.22.6", self.prefix + "rc.3-v0.22.6", summary)])
                        self.assertEqual(len(items), 1)
                        self.assertIn("Fixed tool timeout handling", items[0].summary)


class CollectorTests(unittest.TestCase):
    def test_merge_repositories_deduplicates_and_filters_forks_and_archived(self):
        items = [
            {"full_name": "a/ok", "name": "ok", "html_url": "https://github.com/a/ok", "description": "x", "stargazers_count": 80, "forks_count": 2, "pushed_at": None, "updated_at": None, "topics": ["llm"], "archived": False, "fork": False},
            {"full_name": "a/ok", "name": "ok", "html_url": "https://github.com/a/ok", "description": "x", "stargazers_count": 80, "forks_count": 2, "pushed_at": None, "updated_at": None, "topics": ["llm"], "archived": False, "fork": False},
            {"full_name": "a/old", "name": "old", "html_url": "https://github.com/a/old", "description": "x", "stargazers_count": 80, "forks_count": 2, "pushed_at": None, "updated_at": None, "topics": [], "archived": True, "fork": False},
            {"full_name": "a/small", "name": "small", "html_url": "https://github.com/a/small", "description": "x", "stargazers_count": 49, "forks_count": 2, "pushed_at": None, "updated_at": None, "topics": [], "archived": False, "fork": False},
            {"full_name": "a/fork", "name": "fork", "html_url": "https://github.com/a/fork", "description": "x", "stargazers_count": 80, "forks_count": 2, "pushed_at": None, "updated_at": None, "topics": [], "archived": False, "fork": True},
        ]
        result = merge_repositories(items, min_stars=50)
        self.assertEqual([item.repo for item in result], ["a/ok"])

    def test_feed_reader_returns_recent_items_only(self):
        xml = """<rss><channel><item><title>AI launch</title><link>https://example.com/a</link><pubDate>Thu, 01 Oct 2026 01:00:00 GMT</pubDate><description>summary</description></item><item><title>Old</title><link>https://example.com/old</link><pubDate>Wed, 30 Sep 2026 01:00:00 GMT</pubDate></item></channel></rss>"""
        items = FeedReader().read(xml, datetime(2026, 9, 30, 12, tzinfo=timezone.utc))
        self.assertEqual([item.title for item in items], ["AI launch"])

    def test_feed_reader_keeps_configured_source(self):
        xml = """<rss><channel><item><title>AI launch</title><link>https://example.com/a</link><pubDate>Thu, 01 Oct 2026 01:00:00 GMT</pubDate></item></channel></rss>"""
        items = FeedReader().read(xml, datetime(2026, 9, 30, 12, tzinfo=timezone.utc), source="GitHub Blog")
        self.assertEqual(items[0].source, "GitHub Blog")

    def test_feed_reader_can_filter_non_ai_events(self):
        xml = """<rss><channel>
        <item><title>Git 2.56 release</title><link>https://example.com/git</link><pubDate>Thu, 01 Oct 2026 01:00:00 GMT</pubDate><description>Source control updates</description></item>
        <item><title>New AI agent security tool</title><link>https://example.com/ai</link><pubDate>Thu, 01 Oct 2026 02:00:00 GMT</pubDate><description>Machine learning agent</description></item>
        </channel></rss>"""
        items = FeedReader().read(
            xml,
            datetime(2026, 9, 30, 12, tzinfo=timezone.utc),
            source="GitHub Blog",
            ai_only=True,
        )
        self.assertEqual([item.title for item in items], ["New AI agent security tool"])

    def test_feed_reader_keeps_named_model_events(self):
        xml = """<rss><channel>
        <item><title>Introducing GPT-6.1 Sol</title><link>https://example.com/gpt</link><pubDate>Thu, 01 Oct 2026 01:00:00 GMT</pubDate><description>New model</description></item>
        <item><title>Gemini developer update</title><link>https://example.com/gemini</link><pubDate>Thu, 01 Oct 2026 02:00:00 GMT</pubDate><description>Product update</description></item>
        </channel></rss>"""
        items = FeedReader().read(xml, datetime(2026, 9, 30, 12, tzinfo=timezone.utc), ai_only=True)
        self.assertEqual([item.title for item in items], ["Gemini developer update", "Introducing GPT-6.1 Sol"])

    def test_feed_reader_respects_calendar_window_and_deduplicates(self):
        xml = """<rss><channel>
        <item><title>Codex release</title><link>https://example.com/codex</link><pubDate>Wed, 30 Sep 2026 12:00:00 GMT</pubDate><description>Release notes</description></item>
        <item><title>Codex release duplicate</title><link>https://example.com/codex</link><pubDate>Wed, 30 Sep 2026 12:01:00 GMT</pubDate><description>Duplicate notes</description></item>
        <item><title>Today release</title><link>https://example.com/today</link><pubDate>Thu, 01 Oct 2026 01:00:00 GMT</pubDate><description>Release notes</description></item>
        </channel></rss>"""
        items = FeedReader().read(
            xml,
            datetime(2026, 9, 30, 0, tzinfo=timezone.utc),
            source="Codex Release",
            until=datetime(2026, 10, 1, 0, tzinfo=timezone.utc),
        )
        self.assertEqual([item.title for item in items], ["Codex release"])

    def test_feed_reader_parses_markdown_release_notes_by_date(self):
        markdown = """### September 30, 2026

* We launched Claude Sonnet 5.5.

### September 29, 2026

* Older note.
"""
        items = FeedReader().read_markdown(
            markdown,
            datetime(2026, 9, 29, 16, tzinfo=timezone.utc),
            source="Anthropic Claude Platform",
            until=datetime(2026, 9, 30, 16, tzinfo=timezone.utc),
            base_url="https://platform.claude.com/docs/en/release-notes/overview",
        )
        self.assertEqual(len(items), 1)
        self.assertIn("Claude Sonnet 5.5", items[0].title)
        self.assertEqual(items[0].source, "Anthropic Claude Platform")

    def test_feed_reader_parses_update_markup_for_domestic_model_sources(self):
        markup = """<Update label="2026-09-30" description="GLM-5.3 Flash 上线">
  * Native multimodal model for coding agents.
</Update>
<Update label="2026-09-29" description="Older update">
  * Older note.
</Update>"""
        items = FeedReader().read_update_markup(
            markup,
            datetime(2026, 9, 29, 16, tzinfo=timezone.utc),
            source="Zhipu GLM Changelog",
            until=datetime(2026, 9, 30, 16, tzinfo=timezone.utc),
            base_url="https://docs.bigmodel.cn/cn/update/new-releases.md",
        )
        self.assertEqual(len(items), 1)
        self.assertIn("GLM-5.3 Flash", items[0].title)
        self.assertIn("multimodal", items[0].summary)

    def test_feed_reader_parses_deepseek_dated_html_sections(self):
        html = """<main>
        <h2 id="date-2026-09-30">Date: 2026-09-30</h2>
        <h3>DeepSeek-V4.1-Flash Release</h3>
        <p>Native multimodal visual understanding.</p>
        <h2 id="date-2026-09-29">Date: 2026-09-29</h2>
        <h3>Older update</h3><p>Old note.</p>
        </main>"""
        items = FeedReader().read_deepseek_html(
            html,
            datetime(2026, 9, 29, 16, tzinfo=timezone.utc),
            source="DeepSeek API Changelog",
            until=datetime(2026, 9, 30, 16, tzinfo=timezone.utc),
            base_url="https://api-docs.deepseek.com/updates/",
        )
        self.assertEqual(len(items), 1)
        self.assertIn("DeepSeek-V4.1-Flash", items[0].title)

    def test_trending_owner_and_contributors_are_not_ai_evidence(self):
        html = """
        <article class='Box-row'>
          <h2><a href='/ai/nanoid'>ai / nanoid</a></h2>
          <p>A tiny, secure, URL-friendly, unique string ID generator for JavaScript</p>
          <span>34 stars today</span>
        </article>
        <article class='Box-row'>
          <h2><a href='/tools/formatter'>tools / formatter</a></h2>
          <p>Source code formatting</p><span>Built by ai</span>
          <span>12 stars today</span>
        </article>
        <article class='Box-row'>
          <h2><a href='/ai/helper'>ai / helper</a></h2>
          <p>An AI agent toolkit</p><span>10 stars today</span>
        </article>
        <article class='Box-row'>
          <h2><a href='/tools/llm-runner'>tools / llm-runner</a></h2>
          <span>8 stars today</span>
        </article>
        """
        self.assertEqual([item.repo for item in TrendingClient().parse_daily(html)],
                         ["ai/helper", "tools/llm-runner"])

    def test_trending_client_extracts_ai_repositories_and_daily_stars(self):
        html = """
        <article class='Box-row'>
          <h2><a href='/owner/ai-repo'>owner / ai-repo</a></h2>
          <p>LLM agent toolkit</p>
          <a href='/owner/ai-repo/stargazers'>1,234</a>
          <span>+321 stars today</span>
        </article>
        <article class='Box-row'>
          <h2><a href='/owner/game'>owner / game</a></h2>
          <p>game engine</p>
          <span>+999 stars today</span>
        </article>
        """
        items = TrendingClient().parse_daily(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].repo, "owner/ai-repo")
        self.assertEqual(items[0].stars_today, 321)


if __name__ == "__main__":
    unittest.main()
