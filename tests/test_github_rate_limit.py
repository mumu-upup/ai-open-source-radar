import io
import json
from email.message import Message
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from ai_open_source_daily.github_client import GitHubClient


def http_error(status=403, headers=None, message="API rate limit exceeded"):
    response_headers = Message()
    for name, value in (headers or {}).items():
        response_headers[name] = str(value)
    return HTTPError(
        "https://api.github.com/search/repositories",
        status,
        "Forbidden",
        response_headers,
        io.BytesIO(json.dumps({"message": message}).encode()),
    )


def response():
    return io.BytesIO(b'{"items": [{"full_name": "owner/project"}]}')


class GitHubRateLimitTests(unittest.TestCase):
    def setUp(self):
        self.sleep = patch("time.sleep").start()
        self.clock = patch("time.time", return_value=1000).start()
        self.urlopen = patch("ai_open_source_daily.github_client.urlopen").start()
        self.addCleanup(patch.stopall)
        self.client = GitHubClient(token="secret-test-token")

    def test_search_waits_until_rate_limit_reset_then_returns_fresh_results(self):
        self.urlopen.side_effect = [
            http_error(headers={"X-RateLimit-Remaining": 0, "X-RateLimit-Reset": 1020}),
            response(),
        ]
        self.assertEqual(self.client.search_repositories("llm"), [{"full_name": "owner/project"}])
        self.sleep.assert_called_once_with(21)
        self.assertEqual(self.urlopen.call_count, 2)
        self.assertEqual(self.client.warnings, [])

    def test_retry_after_is_respected_on_secondary_limit(self):
        self.urlopen.side_effect = [
            http_error(headers={"Retry-After": 7, "X-RateLimit-Remaining": 10}),
            response(),
        ]
        self.assertTrue(self.client.search_repositories("llm"))
        self.sleep.assert_called_once_with(7)
        self.assertEqual(self.client.warnings, [])

    def test_wait_respects_both_retry_after_and_primary_reset(self):
        self.urlopen.side_effect = [
            http_error(headers={"Retry-After": 7, "X-RateLimit-Remaining": 0, "X-RateLimit-Reset": 1020}),
            response(),
        ]
        self.assertTrue(self.client.search_repositories("llm"))
        self.sleep.assert_called_once_with(21)

    def test_secondary_limit_without_timing_header_waits_one_minute(self):
        self.urlopen.side_effect = [
            http_error(message="You have exceeded a secondary rate limit."),
            response(),
        ]
        self.assertTrue(self.client.search_repositories("llm"))
        self.sleep.assert_called_once_with(60)

    def test_429_without_timing_headers_retries_with_bounded_backoff(self):
        self.urlopen.side_effect = [http_error(429), http_error(429), response()]
        self.assertTrue(self.client.search_repositories("llm"))
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [60, 120])
        self.assertEqual(self.client.warnings, [])

    def test_plain_forbidden_does_not_retry_or_expose_body_or_token(self):
        self.urlopen.side_effect = http_error(message="Access denied: secret-test-token")
        self.assertEqual(self.client.search_repositories("llm"), [])
        self.sleep.assert_not_called()
        self.assertEqual(self.urlopen.call_count, 1)
        self.assertEqual(self.client.warnings, ["GitHub API /search/repositories returned HTTP 403"])

    def test_retries_are_limited_to_two_and_final_warning_has_safe_rate_values(self):
        self.urlopen.side_effect = [
            http_error(headers={"Retry-After": 1, "X-RateLimit-Remaining": 0, "X-RateLimit-Reset": 1000})
            for _ in range(3)
        ]
        self.assertEqual(self.client.search_repositories("llm"), [])
        self.assertEqual(self.urlopen.call_count, 3)
        self.assertEqual(self.sleep.call_count, 2)
        self.assertEqual(len(self.client.warnings), 1)
        warning = self.client.warnings[0]
        self.assertIn("HTTP 403", warning)
        self.assertIn("remaining=0", warning)
        self.assertIn("reset=1000", warning)
        self.assertIn("retry_after=1", warning)
        self.assertNotIn("secret-test-token", warning)

    def test_server_wait_over_120_seconds_stops_without_retry(self):
        self.urlopen.side_effect = http_error(headers={"Retry-After": 121})
        self.assertEqual(self.client.search_repositories("llm"), [])
        self.sleep.assert_not_called()
        self.assertEqual(self.urlopen.call_count, 1)
        self.assertIn("retry_after=121", self.client.warnings[0])

    def test_malformed_rate_headers_are_not_logged_or_treated_as_retry_instructions(self):
        self.urlopen.side_effect = http_error(
            headers={"Retry-After": "secret-test-token", "X-RateLimit-Reset": "NaN"},
            message="Access denied",
        )
        self.assertEqual(self.client.search_repositories("llm"), [])
        self.sleep.assert_not_called()
        self.assertEqual(self.client.warnings, ["GitHub API /search/repositories returned HTTP 403"])


if __name__ == "__main__":
    unittest.main()
