from pathlib import Path
import tempfile
import unittest

from ai_open_source_daily.cli import main


class OfflineCliTests(unittest.TestCase):
    def test_offline_cli_creates_report_from_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data" / "snapshots").mkdir(parents=True)
            (root / "reports").mkdir()
            (root / "data" / "snapshots" / "2026-10-01.json").write_text("[]", encoding="utf-8")
            self.assertEqual(main(["--root", str(root), "--date", "2026-10-01", "--offline"]), 0)
            self.assertTrue((root / "reports" / "2026-10-01.md").exists())


if __name__ == "__main__":
    unittest.main()
