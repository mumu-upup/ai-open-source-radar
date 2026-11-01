from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from ai_open_source_daily.validation import ReportValidationError, validate_report_pair


class ValidationTests(unittest.TestCase):
    day = date(2026, 11, 1)
    previous_day = date(2026, 10, 31)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_snapshot(self, day, repos):
        path = self.root / "data" / "snapshots" / (day.isoformat() + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(repos) + "\n", encoding="utf-8")

    def write_report(self, text):
        path = self.root / "reports" / (self.day.isoformat() + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def current_repo(self, stars=120):
        return {
            "repo": "a/ai",
            "name": "ai",
            "url": "https://github.com/a/ai",
            "description": "AI tool",
            "stars": stars,
            "forks": 1,
            "pushed_at": None,
            "updated_at": None,
            "topics": ["llm"],
            "archived": False,
            "fork": False,
        }

    def valid_report(self, stars="120", delta="+20"):
        growth = ""
        if delta != "基线建立中":
            growth = """
## Star 增长明显的项目

| 排名 | 项目 | 24h 净增 | 当前总 Star | 状态 | 中文简介 | English description |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 1 | [a/ai](https://github.com/a/ai) | %s | %s | — | AI 工具 | AI tool |
""" % (delta, stars)
        else:
            growth = """
## Star 增长明显的项目

今天先建立 Star 基线；明天开始显示昨天到今天的净增。
"""
        return """# AI 每日简报｜2026-11-01

> 采集时间：2026-11-01T08:00:00+08:00（Asia/Shanghai）
> Star 对比：2026-10-31 → 2026-11-01；正数表示净增，负数表示净减少。

%s
## 总 Star 排名前 10

| 排名 | 项目 | 当前总 Star | 24h 净增 | 排名变化 | 中文简介 | English description |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 1 | [a/ai](https://github.com/a/ai) | %s | %s | — | AI 工具 | AI tool |
""" % (growth, stars, delta)

    def test_valid_pair_matches_current_and_previous_snapshot(self):
        self.write_snapshot(self.previous_day, [self.current_repo(100)])
        self.write_snapshot(self.day, [self.current_repo(120)])
        self.write_report(self.valid_report())

        validate_report_pair(self.root, self.day)

    def test_rejects_report_with_wrong_date_title(self):
        self.write_snapshot(self.day, [self.current_repo()])
        self.write_report(self.valid_report().replace("2026-11-01", "2026-10-31", 1))

        with self.assertRaisesRegex(ReportValidationError, "标题日期"):
            validate_report_pair(self.root, self.day)

    def test_rejects_collection_time_from_another_shanghai_day(self):
        self.write_snapshot(self.day, [self.current_repo()])
        self.write_report(
            self.valid_report().replace(
                "2026-11-01T08:00:00+08:00",
                "2026-10-31T23:59:59+08:00",
            )
        )

        with self.assertRaisesRegex(ReportValidationError, "采集时间日期"):
            validate_report_pair(self.root, self.day)

    def test_rejects_missing_snapshot(self):
        self.write_report(self.valid_report())

        with self.assertRaisesRegex(ReportValidationError, "快照文件不存在"):
            validate_report_pair(self.root, self.day)

    def test_rejects_non_list_snapshot_json(self):
        path = self.root / "data" / "snapshots" / (self.day.isoformat() + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        self.write_report(self.valid_report())

        with self.assertRaisesRegex(ReportValidationError, "顶层必须是列表"):
            validate_report_pair(self.root, self.day)

    def test_rejects_more_than_one_aigcnews_supplement(self):
        self.write_snapshot(self.day, [self.current_repo()])
        self.write_report(
            self.valid_report()
            + "\n## AIGCNEWS 补充线索\n\n"
            + "- 第一条（AIGCNEWS 线索）\n"
            + "- 第二条（AIGCNEWS 线索）\n"
        )

        with self.assertRaisesRegex(ReportValidationError, "AIGCNEWS 补充线索最多 1 条"):
            validate_report_pair(self.root, self.day)

    def test_rejects_star_value_that_differs_from_snapshot(self):
        self.write_snapshot(self.previous_day, [self.current_repo(100)])
        self.write_snapshot(self.day, [self.current_repo(120)])
        self.write_report(self.valid_report(stars="121"))

        with self.assertRaisesRegex(ReportValidationError, "Star 与快照不一致"):
            validate_report_pair(self.root, self.day)

    def test_rejects_delta_value_that_differs_from_previous_snapshot(self):
        self.write_snapshot(self.previous_day, [self.current_repo(100)])
        self.write_snapshot(self.day, [self.current_repo(120)])
        self.write_report(self.valid_report(delta="+21"))

        with self.assertRaisesRegex(ReportValidationError, "净增与快照不一致"):
            validate_report_pair(self.root, self.day)

    def test_rejects_growth_table_value_that_differs_from_snapshot(self):
        self.write_snapshot(self.previous_day, [self.current_repo(100)])
        self.write_snapshot(self.day, [self.current_repo(120)])
        report = self.valid_report().replace(
            "| 1 | [a/ai](https://github.com/a/ai) | +20 | 120 | — |",
            "| 1 | [a/ai](https://github.com/a/ai) | +999 | 999 | — |",
            1,
        )
        self.write_report(report)

        with self.assertRaisesRegex(ReportValidationError, "增长表.*Star"):
            validate_report_pair(self.root, self.day)

    def test_rejects_snapshot_with_missing_required_fields(self):
        self.write_snapshot(self.previous_day, [self.current_repo(100)])
        self.write_snapshot(self.day, [{"repo": "a/ai", "stars": 120}])
        self.write_report(self.valid_report())

        with self.assertRaisesRegex(ReportValidationError, "缺少字段"):
            validate_report_pair(self.root, self.day)

    def test_rejects_future_comparison_date(self):
        self.write_snapshot(self.day, [self.current_repo()])
        report = self.valid_report().replace("2026-10-31 → 2026-11-01", "2026-11-02 → 2026-11-01")
        self.write_report(report)

        with self.assertRaisesRegex(ReportValidationError, "对比日期"):
            validate_report_pair(self.root, self.day)

    def test_rejects_report_without_growth_section(self):
        self.write_snapshot(self.previous_day, [self.current_repo(100)])
        self.write_snapshot(self.day, [self.current_repo(120)])
        report = self.valid_report().split("## Star 增长明显的项目", 1)[0] + "## 总 Star 排名前 10" + self.valid_report().split("## 总 Star 排名前 10", 1)[1]
        self.write_report(report)

        with self.assertRaisesRegex(ReportValidationError, "缺少 Star 增长明显的项目章节"):
            validate_report_pair(self.root, self.day)

    def test_rejects_empty_total_ranking_when_snapshot_has_repositories(self):
        self.write_snapshot(self.previous_day, [self.current_repo(100)])
        self.write_snapshot(self.day, [self.current_repo(120)])
        report = self.valid_report().split("## 总 Star 排名前 10", 1)[0] + (
            "## 总 Star 排名前 10\n\n当前没有可用的项目快照。\n"
        )
        self.write_report(report)

        with self.assertRaisesRegex(ReportValidationError, "总 Star 排名表为空"):
            validate_report_pair(self.root, self.day)

    def test_allows_first_snapshot_baseline(self):
        self.write_snapshot(self.day, [self.current_repo()])
        self.write_report(
            self.valid_report(delta="基线建立中").replace(
                "> Star 对比：2026-10-31 → 2026-11-01；正数表示净增，负数表示净减少。",
                "> Star 对比：暂无前一日快照（基线建立中） → 2026-11-01；正数表示净增，负数表示净减少。",
            )
        )

        validate_report_pair(self.root, self.day)


if __name__ == "__main__":
    unittest.main()
