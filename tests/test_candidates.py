import unittest

from ai_open_source_daily.candidates import collect_candidates


def _repo(full_name, stars=100, *, topics=None, fork=False, archived=False):
    owner, name = full_name.split("/", 1)
    return {
        "full_name": full_name,
        "name": name,
        "html_url": "https://github.com/" + full_name,
        "description": "",
        "stargazers_count": stars,
        "forks_count": 0,
        "topics": topics or [],
        "archived": archived,
        "fork": fork,
    }


class FakeClient:
    def __init__(self, search_results=None, repositories=None, failing_topics=None):
        self.search_results = search_results or {}
        self.repositories = repositories or {}
        self.failing_topics = set(failing_topics or ())
        self.search_calls = []
        self.repository_calls = []
        self.warnings = ["existing warning"]

    def search_repositories(self, topic, min_stars, limit):
        self.search_calls.append((topic, min_stars, limit))
        if topic in self.failing_topics:
            raise RuntimeError("search failed")
        return list(self.search_results.get(topic, []))

    def repository(self, owner_repo):
        self.repository_calls.append(owner_repo)
        return self.repositories.get(owner_repo.lower())


class CandidateCollectionTests(unittest.TestCase):
    def test_deduplicates_watchlist_names_and_skips_repos_already_fetched(self):
        client = FakeClient(
            search_results={"llm": [_repo("Acme/Pi", 200)]},
            repositories={"owner/hermes": _repo("Owner/Hermes", 150)},
        )

        result = collect_candidates(
            client,
            topics=["llm"],
            watch_repositories=["acme/pi", "Owner/Hermes", "owner/hermes"],
            min_stars=50,
            search_limit=10,
        )

        self.assertEqual([repo.repo for repo in result], ["Acme/Pi", "Owner/Hermes"])
        self.assertEqual(client.repository_calls, ["Owner/Hermes"])
        self.assertEqual(client.search_calls, [("llm", 50, 10)])

    def test_includes_no_topic_watch_repo_and_filters_forks_and_min_stars(self):
        client = FakeClient(
            repositories={
                "owner/hermes": _repo("Owner/Hermes", 120),
                "owner/small": _repo("Owner/Small", 49),
                "owner/fork": _repo("Owner/Fork", 120, fork=True),
            }
        )

        result = collect_candidates(
            client,
            topics=[],
            watch_repositories=["owner/hermes", "owner/small", "owner/fork"],
            min_stars=50,
            search_limit=10,
        )

        self.assertEqual([repo.repo for repo in result], ["Owner/Hermes"])
        self.assertEqual([repo.topics for repo in result], [[]])

    def test_search_failures_do_not_prevent_watchlist_collection_or_clear_warnings(self):
        client = FakeClient(
            search_results={"working": [_repo("Owner/Working", 80)]},
            repositories={"owner/hermes": _repo("Owner/Hermes", 100)},
            failing_topics={"broken"},
        )

        result = collect_candidates(
            client,
            topics=["broken", "working"],
            watch_repositories=["owner/hermes"],
            min_stars=50,
            search_limit=10,
        )

        self.assertEqual([repo.repo for repo in result], ["Owner/Hermes", "Owner/Working"])
        self.assertEqual(client.warnings, ["existing warning"])


if __name__ == "__main__":
    unittest.main()
