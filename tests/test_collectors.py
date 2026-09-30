from datetime import datetime, timezone
import unittest

from ai_open_source_daily.feeds import FeedReader
from ai_open_source_daily.github_client import TrendingClient, merge_repositories


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
