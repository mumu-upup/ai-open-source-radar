from datetime import datetime
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from zoneinfo import ZoneInfo


WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def workflow_script(workflow, name):
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    step = text.split("      - name: " + name + "\n", 1)[1].split("      - name:", 1)[0]
    lines = step.split("        run: |\n", 1)[1].splitlines()
    return "\n".join(line[10:] for line in lines if line.startswith("          "))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "origin.git"
        self.source = self.root / "source"
        self.worker = self.root / "worker"
        self.day = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "init", "-b", "main", str(self.source))
        self.git(self.source, "config", "user.name", "Workflow test")
        self.git(self.source, "config", "user.email", "test@example.invalid")
        self.git(self.source, "commit", "--allow-empty", "-m", "initial")
        self.git(self.source, "remote", "add", "origin", str(self.remote))

    def git(self, root, *args):
        return subprocess.run(
            ["git", *args], cwd=root, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def write_pair(self, root, day, report="Reviewed report\n", snapshot=True):
        path = root / "reports" / (day + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        if snapshot:
            path = root / "data" / "snapshots" / (day + ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('[]\n', encoding="utf-8")

    def commit(self, message="test artifacts"):
        self.git(self.source, "add", ".")
        self.git(self.source, "commit", "--allow-empty", "-m", message)

    def clone(self):
        self.git(self.source, "push", "origin", "main", "daily-report-staging")
        self.git(self.root, "clone", "--branch", "main", "--single-branch", str(self.remote), str(self.worker))

    def run_step(self, workflow, name):
        script = workflow_script(workflow, name)
        for step in ("existing", "published"):
            script = script.replace("${{ steps." + step + ".outputs.day }}", self.day)
            script = script.replace("${{ steps." + step + ".outputs.complete }}", "false")
        output = self.root / "outputs"
        output.write_text("", encoding="utf-8")
        subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", script], cwd=self.worker,
            env=dict(os.environ, GITHUB_OUTPUT=str(output)), check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        return output.read_text(encoding="utf-8")

    def test_collection_preserves_staging_report_without_aigcnews_pick(self):
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        self.write_pair(self.source, self.day)
        self.commit()
        self.clone()
        result = self.run_step("daily-report-collect.yml", "Check whether today's report is already complete")
        self.assertIn("complete=true", result)

    def test_collection_preserves_already_published_report(self):
        self.git(self.source, "branch", "daily-report-staging")
        self.write_pair(self.source, self.day)
        self.commit()
        self.clone()
        result = self.run_step("daily-report-collect.yml", "Check whether today's report is already complete")
        self.assertIn("complete=true", result)

    def test_collection_does_not_skip_missing_snapshot(self):
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        self.write_pair(self.source, self.day, snapshot=False)
        self.commit()
        self.clone()
        result = self.run_step("daily-report-collect.yml", "Check whether today's report is already complete")
        self.assertIn("complete=false", result)

    def test_publish_syncs_latest_main_and_preserves_existing_report(self):
        self.git(self.source, "branch", "daily-report-staging")
        self.clone()
        self.write_pair(self.source, self.day)
        self.commit()
        baseline = self.git(self.source, "rev-parse", "HEAD")
        self.git(self.source, "push", "origin", "main")
        result = self.run_step("daily-report-publish.yml", "Check whether today's report is already published")
        self.assertIn("complete=true", result)
        self.git(self.worker, "merge-base", "--is-ancestor", baseline, "HEAD")

    def test_publish_copies_only_current_day(self):
        self.write_pair(self.source, "2026-01-01", report="Reviewed historical report\n")
        self.commit()
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        self.write_pair(self.source, "2026-01-01", report="Stale historical report\n")
        self.write_pair(self.source, self.day)
        self.commit()
        self.clone()
        self.git(self.worker, "fetch", "origin", "daily-report-staging:refs/remotes/origin/daily-report-staging")
        self.run_step("daily-report-publish.yml", "Copy collected report and snapshots")
        self.assertEqual((self.worker / "reports" / "2026-01-01.md").read_text(), "Reviewed historical report\n")
        self.assertEqual((self.worker / "reports" / (self.day + ".md")).read_text(), "Reviewed report\n")
        self.assertEqual(
            set(self.git(self.worker, "diff", "--cached", "--name-only").splitlines()),
            {"reports/" + self.day + ".md", "data/snapshots/" + self.day + ".json"},
        )

    def test_collection_push_keeps_staging_history_and_latest_main(self):
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        (self.source / "editorial.md").write_text("Staging editorial notes\n")
        self.commit()
        staging = self.git(self.source, "rev-parse", "HEAD")
        self.git(self.source, "checkout", "main")
        (self.source / "source.txt").write_text("Latest main source\n")
        self.commit()
        baseline = self.git(self.source, "rev-parse", "HEAD")
        self.clone()
        self.run_step("daily-report-collect.yml", "Check whether today's report is already complete")
        self.run_step("daily-report-collect.yml", "Verify collection source from the latest main")
        self.git(self.worker, "merge-base", "--is-ancestor", baseline, "HEAD")
        self.write_pair(self.worker, self.day)
        self.run_step("daily-report-collect.yml", "Save collected files to staging branch")
        self.git(self.remote, "merge-base", "--is-ancestor", staging, "daily-report-staging")
        self.assertIn("Source main: " + baseline, self.git(self.remote, "log", "-1", "--format=%B", "daily-report-staging"))
        self.assertEqual(self.git(self.remote, "show", "daily-report-staging:editorial.md"), "Staging editorial notes")

    def test_collection_uses_main_restored_history_as_baseline(self):
        self.write_pair(self.source, "2026-01-01", report="Reviewed original\n")
        self.commit()
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        self.write_pair(self.source, "2026-01-01", report="Duplicate collection\n")
        (self.source / "data/snapshots/2026-01-01.json").write_text('[{"stars": 999}]\n')
        self.commit("duplicate collection")
        self.git(self.source, "checkout", "main")
        self.write_pair(self.source, "2026-01-01", report="Duplicate collection\n")
        (self.source / "data/snapshots/2026-01-01.json").write_text('[{"stars": 999}]\n')
        self.commit("publish duplicate")
        self.write_pair(self.source, "2026-01-01", report="Reviewed original\n")
        self.commit("restore reviewed report")
        self.clone()
        self.run_step("daily-report-collect.yml", "Check whether today's report is already complete")
        self.run_step("daily-report-collect.yml", "Verify collection source from the latest main")
        self.assertEqual((self.worker / "reports" / "2026-01-01.md").read_text(), "Reviewed original\n")
        self.assertEqual((self.worker / "data/snapshots/2026-01-01.json").read_text(), "[]\n")

    def test_collection_survives_main_only_correction_to_published_report(self):
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        self.write_pair(self.source, "2026-01-01", report="First draft\n")
        self.commit("collection")
        self.git(self.source, "checkout", "main")
        self.write_pair(self.source, "2026-01-01", report="First draft\n")
        self.commit("publication")
        self.write_pair(self.source, "2026-01-01", report="Main editorial correction\n")
        self.commit("correction")
        self.clone()
        self.run_step("daily-report-collect.yml", "Check whether today's report is already complete")
        self.run_step("daily-report-collect.yml", "Verify collection source from the latest main")
        self.assertEqual((self.worker / "reports" / "2026-01-01.md").read_text(), "Main editorial correction\n")

    def collect_complete_pair(self):
        self.run_step("daily-report-collect.yml", "Check whether today's report is already complete")
        self.run_step("daily-report-collect.yml", "Verify collection source from the latest main")
        self.write_pair(self.worker, self.day, report="Completed report\n")
        self.run_step("daily-report-collect.yml", "Save collected files to staging branch")
        self.assertEqual(self.git(self.remote, "show", "daily-report-staging:reports/" + self.day + ".md"), "Completed report")
        self.assertEqual(self.git(self.remote, "show", "daily-report-staging:data/snapshots/" + self.day + ".json"), "[]")

    def test_collection_completes_preliminary_report_on_main(self):
        self.git(self.source, "branch", "daily-report-staging")
        self.write_pair(self.source, self.day, report="Preliminary report\n", snapshot=False)
        self.commit()
        self.clone()
        self.collect_complete_pair()

    def test_collection_completes_preliminary_report_on_staging(self):
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        self.write_pair(self.source, self.day, report="Preliminary report\n", snapshot=False)
        self.commit()
        self.clone()
        self.collect_complete_pair()

    def test_collection_preserves_pair_completed_during_generation(self):
        self.git(self.source, "branch", "daily-report-staging")
        self.clone()
        self.run_step("daily-report-collect.yml", "Check whether today's report is already complete")
        self.run_step("daily-report-collect.yml", "Verify collection source from the latest main")
        self.write_pair(self.worker, self.day, report="Unreviewed collection\n")
        self.git(self.source, "checkout", "daily-report-staging")
        self.write_pair(self.source, self.day, report="Concurrent reviewed report\n")
        self.commit()
        latest = self.git(self.source, "rev-parse", "HEAD")
        self.git(self.source, "push", "origin", "daily-report-staging")
        self.run_step("daily-report-collect.yml", "Save collected files to staging branch")
        self.assertEqual(self.git(self.remote, "rev-parse", "daily-report-staging"), latest)

    def test_publish_stops_when_main_advances_after_validation(self):
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        self.write_pair(self.source, self.day)
        self.commit()
        self.clone()
        self.run_step("daily-report-publish.yml", "Check whether today's report is already published")
        self.run_step("daily-report-publish.yml", "Copy collected report and snapshots")
        self.git(self.source, "checkout", "main")
        (self.source / "source.txt").write_text("Concurrent main update\n")
        self.commit()
        latest = self.git(self.source, "rev-parse", "HEAD")
        self.git(self.source, "push", "origin", "main")
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_step("daily-report-publish.yml", "Publish report to main")
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), latest)

    def test_publish_stops_when_staging_report_changes_after_copy(self):
        self.git(self.source, "checkout", "-b", "daily-report-staging")
        self.write_pair(self.source, self.day)
        self.commit()
        self.clone()
        main = self.git(self.remote, "rev-parse", "main")
        self.run_step("daily-report-publish.yml", "Check whether today's report is already published")
        self.run_step("daily-report-publish.yml", "Copy collected report and snapshots")
        self.write_pair(self.source, self.day, report="New editorial correction\n")
        self.commit()
        self.git(self.source, "push", "origin", "daily-report-staging")
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_step("daily-report-publish.yml", "Publish report to main")
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), main)
