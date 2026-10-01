from datetime import datetime, timedelta, timezone
import json
import unittest

from ai_open_source_daily.feeds import FeedReader


class HuggingFaceModelFeedTests(unittest.TestCase):
    def setUp(self):
        self.reader = FeedReader()
        self.since = datetime(2026, 9, 30, tzinfo=timezone.utc)
        self.until = datetime(2026, 10, 1, tzinfo=timezone.utc)

    def read_models(self, rows, **kwargs):
        return self.reader.read_huggingface_models(
            json.dumps(rows), self.since, until=self.until, **kwargs
        )

    def test_new_repository_uses_activity_timestamp_and_model_metadata(self):
        items = self.read_models(
            [{
                "id": "Qwen/Qwen-Next",
                "createdAt": "2026-09-30T01:00:00Z",
                "lastModified": "2026-09-30T05:00:00Z",
                "pipeline_tag": "text-generation",
                "tags": ["transformers", "safetensors"],
            }],
            source="Qwen on Hugging Face",
            base_url="https://huggingface.co/api/models?author=Qwen",
        )

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.title, "Qwen/Qwen-Next — New model repository")
        self.assertEqual(item.url, "https://huggingface.co/Qwen/Qwen-Next")
        self.assertEqual(item.published_at, "2026-09-30T05:00:00+00:00")
        self.assertEqual(item.source, "Qwen on Hugging Face")
        self.assertIn("2026-09-30T01:00:00+00:00", item.summary)
        self.assertIn("text-generation", item.summary)
        self.assertIn("safetensors", item.summary)
        self.assertNotIn("launch", item.summary.lower())

    def test_existing_repository_activity_is_an_update_not_a_new_model(self):
        items = self.read_models([{
            "id": "NousResearch/Hermes-Existing",
            "createdAt": "2025-01-01T00:00:00Z",
            "lastModified": "2026-09-30T05:00:00Z",
        }])

        self.assertEqual(items[0].title, "NousResearch/Hermes-Existing — Model repository update")
        self.assertIn("repository", items[0].summary.lower())
        self.assertIn("updated", items[0].summary.lower())
        self.assertNotIn("launch", items[0].summary.lower())
        self.assertNotIn("new model", items[0].summary.lower())

    def test_window_is_half_open_and_results_are_sorted_by_last_modified(self):
        items = self.read_models([
            {"id": "test/at-start", "lastModified": "2026-09-30T00:00:00Z"},
            {"id": "test/too-old", "lastModified": "2026-09-29T23:59:59Z"},
            {"id": "test/at-end", "lastModified": "2026-10-01T00:00:00Z"},
            {"id": "test/later", "lastModified": "2026-09-30T23:59:59Z"},
        ])

        self.assertEqual([item.url for item in items], [
            "https://huggingface.co/test/later", "https://huggingface.co/test/at-start"
        ])

    def test_naive_window_dates_are_utc_and_aware_activity_is_normalized(self):
        items = self.reader.read_huggingface_models(
            json.dumps([{"id": "microsoft/Phi", "lastModified": "2026-09-30T08:00:00+08:00"}]),
            datetime(2026, 9, 30),
            until=datetime(2026, 10, 1, 8, tzinfo=timezone(timedelta(hours=8))),
        )
        self.assertEqual(items[0].published_at, "2026-09-30T00:00:00+00:00")

    def test_unknown_or_inconsistent_creation_date_does_not_imply_new_repository(self):
        for created in (None, "bad date", 42, "2026-09-30T09:00:00Z"):
            with self.subTest(created=created):
                items = self.read_models([{
                    "id": "MiniMaxAI/MiniMax",
                    "createdAt": created,
                    "lastModified": "2026-09-30T05:00:00Z",
                }])
                self.assertEqual(len(items), 1)
                self.assertIn("Model repository update", items[0].title)

    def test_malformed_rows_are_ignored_without_losing_valid_activity(self):
        items = self.read_models([
            None, "row", [], 10,
            {"lastModified": "2026-09-30T05:00:00Z"},
            {"id": "", "lastModified": "2026-09-30T05:00:00Z"},
            {"id": 42, "lastModified": "2026-09-30T05:00:00Z"},
            {"id": "test/no-date"},
            {"id": "test/bad-date", "lastModified": "bad date"},
            {"id": "test/object-date", "lastModified": {"date": "2026-09-30"}},
            {"id": "test/valid", "lastModified": "2026-09-30T05:00:00Z", "tags": [None, 42, "gguf"], "pipeline_tag": 42},
        ])
        self.assertEqual([item.url for item in items], ["https://huggingface.co/test/valid"])
        self.assertIn("gguf", items[0].summary)
        self.assertNotIn("42", items[0].summary)

    def test_rejects_non_list_payloads(self):
        for payload in ({"error": "Unauthorized"}, {"models": []}, None, "models", 42):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    self.read_models(payload)

    def test_rejects_invalid_json(self):
        with self.assertRaises(ValueError):
            self.reader.read_huggingface_models("{broken", self.since)

    def test_until_is_optional(self):
        items = self.reader.read_huggingface_models(
            '[{"id":"test/newer","lastModified":"2026-10-02T00:00:00Z"}]', self.since
        )
        self.assertEqual(len(items), 1)


class NamedModelFilterTests(unittest.TestCase):
    def test_named_models_are_included_without_generic_ai_keywords(self):
        for name in ("Hermes", "Gemma", "Grok", "Phi", "MiniMax", "Jev"):
            with self.subTest(name=name):
                xml = """<rss><channel><item><title>%s announcement</title>
                <link>https://example.com/item</link><pubDate>2026-09-30T05:00:00Z</pubDate>
                </item></channel></rss>""" % name
                items = FeedReader().read(xml, datetime(2026, 9, 30, tzinfo=timezone.utc), ai_only=True)
                self.assertEqual(len(items), 1)

    def test_model_name_substrings_do_not_match_unrelated_words(self):
        for title in ("Hermesville", "Gemmatic", "Grokking", "Philadelphia", "MiniMaximum", "Jevons"):
            with self.subTest(title=title):
                xml = """<rss><channel><item><title>%s</title>
                <link>https://example.com/item</link><pubDate>2026-09-30T05:00:00Z</pubDate>
                </item></channel></rss>""" % title
                items = FeedReader().read(xml, datetime(2026, 9, 30, tzinfo=timezone.utc), ai_only=True)
                self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
