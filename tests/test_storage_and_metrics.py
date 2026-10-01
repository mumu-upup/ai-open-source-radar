from datetime import date
from pathlib import Path
import unittest

from ai_open_source_daily.models import RepoSnapshot
from ai_open_source_daily.storage import SnapshotStore, calculate_delta


class StorageAndMetricsTests(unittest.TestCase):
    def test_calculate_delta_marks_missing_history_as_baseline(self):
        self.assertIsNone(calculate_delta(120, None))
        self.assertEqual(calculate_delta(120, 100), 20)
        self.assertEqual(calculate_delta(100, 120), -20)

    def test_snapshot_store_round_trips_repo_snapshots(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory) / "snapshots")
            repo = RepoSnapshot("acme/ai", "AI", "https://github.com/acme/ai", "demo", 100, 4, None, None, ["llm"], False, False)
            store.save(date(2026, 10, 1), [repo])
            self.assertEqual(store.load(date(2026, 10, 1)), [repo])

    def test_find_previous_returns_nearest_available_snapshot(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory) / "snapshots")
            repo = RepoSnapshot("acme/ai", "AI", "https://github.com/acme/ai", "demo", 100, 4, None, None, ["llm"], False, False)
            store.save(date(2026, 9, 29), [repo])
            self.assertEqual(store.find_previous("acme/ai", date(2026, 10, 1), 7), repo)

    def test_find_previous_with_day_returns_snapshot_date(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory) / "snapshots")
            repo = RepoSnapshot("acme/ai", "AI", "https://github.com/acme/ai", "demo", 100, 4, None, None, ["llm"], False, False)
            store.save(date(2026, 9, 29), [repo])
            self.assertEqual(
                store.find_previous_with_day("acme/ai", date(2026, 10, 1), 7),
                (date(2026, 9, 29), repo),
            )


if __name__ == "__main__":
    unittest.main()
