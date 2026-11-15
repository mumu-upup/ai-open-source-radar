import json
from unittest.mock import patch
import unittest
from pathlib import Path
from urllib.error import HTTPError

from ai_open_source_daily.cli import _fetch_feed


class SourceConfigTests(unittest.TestCase):
    def test_linux_do_topic_rss_is_registered_as_supplementary_source(self):
        config_path = Path(__file__).parents[1] / "config" / "sources.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        source = next(
            item for item in config["feeds"]
            if item.get("url") == "https://linux.do/t/topic/211016.rss"
        )
        self.assertEqual(source["name"], "Linux.do 主题线索")
        self.assertTrue(source["ai_only"])

    def test_fetch_feed_falls_back_to_curl_for_cloudflare_403(self):
        error = HTTPError(
            "https://linux.do/t/topic/211016.rss",
            403,
            "Forbidden",
            hdrs=None,
            fp=None,
        )
        with patch("ai_open_source_daily.cli.urlopen", side_effect=error), patch(
            "ai_open_source_daily.cli.subprocess.run",
            return_value=type("Result", (), {"stdout": b"<rss/>"})(),
        ) as run:
            self.assertEqual(_fetch_feed("https://linux.do/t/topic/211016.rss"), "<rss/>")
        self.assertEqual(run.call_args.args[0][0:2], ["curl", "-fsSL"])


if __name__ == "__main__":
    unittest.main()
