"""Validate a daily report against its dated repository snapshot.

The validator is intentionally independent from collection.  It checks the
files that are about to cross the staging/main boundary, so an old or edited
report cannot silently be published with a mismatched snapshot.
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from .models import RepoSnapshot


_SHANGHAI = ZoneInfo("Asia/Shanghai")
_TITLE_RE = re.compile(r"^# AI 每日简报｜(?P<day>\d{4}-\d{2}-\d{2})$")
_COLLECTION_RE = re.compile(r"^> 采集时间：(?P<value>.+)（Asia/Shanghai）$")
_COMPARISON_RE = re.compile(
    r"^> Star 对比：(?P<previous>\d{4}-\d{2}-\d{2}|暂无前一日快照（基线建立中）)"
    r" → (?P<current>\d{4}-\d{2}-\d{2})；"
)
_TOTAL_ROW_RE = re.compile(
    r"^\|\s*(?P<rank>\d+)\s*\|\s*\[(?P<repo>[^]]+)\]\([^)]*\)\s*\|\s*"
    r"(?P<stars>\d+)\s*\|\s*(?P<delta>[^|]+?)\s*\|"
)
_GROWTH_ROW_RE = re.compile(
    r"^\|\s*(?P<rank>\d+)\s*\|\s*\[(?P<repo>[^]]+)\]\([^)]*\)\s*\|\s*"
    r"(?P<delta>[^|]+?)\s*\|\s*(?P<stars>\d+)\s*\|"
)
_SNAPSHOT_FIELDS = {
    "repo", "name", "url", "description", "stars", "forks", "pushed_at",
    "updated_at", "topics", "archived", "fork",
}


class ReportValidationError(ValueError):
    """Raised when a report pair fails one or more publication checks."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _snapshot_path(root: Path, snapshot_day: date) -> Path:
    return root / "data" / "snapshots" / (snapshot_day.isoformat() + ".json")


def _read_snapshot(root: Path, snapshot_day: date, errors: List[str]) -> Optional[List[RepoSnapshot]]:
    path = _snapshot_path(root, snapshot_day)
    if not path.is_file():
        errors.append("快照文件不存在：%s" % path)
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append("快照 JSON 无法解析：%s（%s）" % (path, exc))
        return None
    if not isinstance(value, list):
        errors.append("快照 JSON 顶层必须是列表：%s" % path)
        return None

    repos: List[RepoSnapshot] = []
    seen = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append("快照第 %d 项必须是对象" % (index + 1))
            continue
        repo_name = item.get("repo")
        stars = item.get("stars")
        if not isinstance(repo_name, str) or not repo_name.strip():
            errors.append("快照第 %d 项缺少有效 repo" % (index + 1))
        missing = sorted(_SNAPSHOT_FIELDS - set(item))
        if missing:
            errors.append("快照第 %d 项缺少字段：%s" % (index + 1, ", ".join(missing)))
        if isinstance(stars, bool) or not isinstance(stars, int) or stars < 0:
            errors.append("快照第 %d 项的 stars 必须是非负整数" % (index + 1))
        if not isinstance(item.get("name"), str):
            errors.append("快照第 %d 项的 name 必须是字符串" % (index + 1))
        if not isinstance(item.get("url"), str):
            errors.append("快照第 %d 项的 url 必须是字符串" % (index + 1))
        if not isinstance(item.get("description"), str):
            errors.append("快照第 %d 项的 description 必须是字符串" % (index + 1))
        forks = item.get("forks")
        if isinstance(forks, bool) or not isinstance(forks, int) or forks < 0:
            errors.append("快照第 %d 项的 forks 必须是非负整数" % (index + 1))
        topics = item.get("topics")
        if not isinstance(topics, list) or not all(isinstance(topic, str) for topic in topics):
            errors.append("快照第 %d 项的 topics 必须是字符串列表" % (index + 1))
        for field in ("archived", "fork"):
            if not isinstance(item.get(field), bool):
                errors.append("快照第 %d 项的 %s 必须是布尔值" % (index + 1, field))
        for field in ("pushed_at", "updated_at"):
            if item.get(field) is not None and not isinstance(item.get(field), str):
                errors.append("快照第 %d 项的 %s 必须是字符串或 null" % (index + 1, field))
        if not isinstance(repo_name, str) or repo_name in seen:
            if isinstance(repo_name, str) and repo_name in seen:
                errors.append("快照包含重复项目：%s" % repo_name)
            continue
        try:
            repo = RepoSnapshot.from_dict(item)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append("快照第 %d 项字段无效：%s" % (index + 1, exc))
            continue
        seen.add(repo.repo)
        repos.append(repo)
    return repos


def _parse_report_metadata(report: str, day: date, errors: List[str]) -> Optional[date]:
    lines = report.splitlines()
    if not lines:
        errors.append("报告为空")
        return None

    title = _TITLE_RE.match(lines[0].strip())
    if not title:
        errors.append("报告标题日期格式错误")
    elif title.group("day") != day.isoformat():
        errors.append("标题日期与目标日期不一致：%s != %s" % (title.group("day"), day.isoformat()))

    collection_line = next((line.strip() for line in lines if line.startswith("> 采集时间：")), None)
    if collection_line is None:
        errors.append("缺少 Asia/Shanghai 采集时间")
    else:
        match = _COLLECTION_RE.match(collection_line)
        if not match:
            errors.append("采集时间格式错误")
        else:
            value = match.group("value").replace("Z", "+00:00")
            try:
                generated_at = datetime.fromisoformat(value)
            except ValueError:
                errors.append("采集时间无法解析：%s" % value)
            else:
                if generated_at.tzinfo is None:
                    errors.append("采集时间必须包含时区")
                else:
                    if generated_at.astimezone(_SHANGHAI).date() != day:
                        errors.append("采集时间日期与目标日期不一致")
                    if generated_at.utcoffset() != generated_at.astimezone(_SHANGHAI).utcoffset():
                        errors.append("采集时间时区与 Asia/Shanghai 不一致")

    comparison_line = next((line.strip() for line in lines if line.startswith("> Star 对比：")), None)
    if comparison_line is None:
        if any(line.startswith("> 今日 Star 数据不可用") for line in lines):
            errors.append("当前快照存在时报告不应标记今日 Star 数据不可用")
        else:
            errors.append("缺少 Star 对比日期")
        return None
    comparison = _COMPARISON_RE.match(comparison_line)
    if not comparison:
        errors.append("Star 对比日期格式错误")
        return None
    current_text = comparison.group("current")
    if current_text != day.isoformat():
        errors.append("Star 对比当前日期与目标日期不一致：%s != %s" % (current_text, day.isoformat()))
    previous_text = comparison.group("previous")
    if previous_text.startswith("暂无前一日快照"):
        return None
    try:
        return date.fromisoformat(previous_text)
    except ValueError:
        errors.append("Star 对比日期格式错误")
        return None


def _parse_total_rows(report: str, errors: List[str]) -> List[Tuple[str, int, str]]:
    lines = report.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == "## 总 Star 排名前 10")
    except StopIteration:
        errors.append("缺少总 Star 排名前 10 表格")
        return []

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    rows: List[Tuple[str, int, str]] = []
    for line in lines[start + 1:end]:
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        if "当前总 Star" in line and "项目" in line:
            continue
        match = _TOTAL_ROW_RE.match(line.strip())
        if not match:
            errors.append("总 Star 表格存在无法解析的行：%s" % line)
            continue
        rows.append((match.group("repo"), int(match.group("stars")), match.group("delta").strip()))
    if not rows and not any("当前没有可用的项目快照" in line for line in lines[start + 1:end]):
        errors.append("总 Star 排名表没有数据行")
    return rows


def _parse_growth_rows(report: str, errors: List[str]) -> List[Tuple[str, int, str]]:
    lines = report.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == "## Star 增长明显的项目")
    except StopIteration:
        errors.append("缺少 Star 增长明显的项目章节")
        return []

    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    rows: List[Tuple[str, int, str]] = []
    for line in lines[start + 1:end]:
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        if "当前总 Star" in line and "项目" in line:
            continue
        match = _GROWTH_ROW_RE.match(line.strip())
        if not match:
            errors.append("Star 增长表格存在无法解析的行：%s" % line)
            continue
        rows.append((match.group("repo"), int(match.group("stars")), match.group("delta").strip()))
    if not rows:
        section_text = "\n".join(lines[start + 1:end])
        allowed_fallbacks = (
            "今天先建立 Star 基线",
            "昨日没有正增长明显的项目",
            "对比区间内没有正增长明显的项目",
            "今日 Star 数据不可用",
        )
        if not any(fallback in section_text for fallback in allowed_fallbacks):
            errors.append("Star 增长表格没有数据行或有效说明")
    return rows


def _validate_aigcnews_count(report: str, errors: List[str]) -> None:
    lines = report.splitlines()
    headings = [index for index, line in enumerate(lines) if line.strip() == "## AIGCNEWS 补充线索"]
    if len(headings) > 1:
        errors.append("AIGCNEWS 补充线索章节重复")
        return
    if not headings:
        return
    start = headings[0] + 1
    end = next((index for index in range(start, len(lines)) if lines[index].startswith("## ")), len(lines))
    bullets = [line for line in lines[start:end] if line.strip().startswith("- ")]
    if len(bullets) > 1:
        errors.append("AIGCNEWS 补充线索最多 1 条，实际 %d 条" % len(bullets))


def _validate_star_rows(
    rows: List[Tuple[str, int, str]],
    current: Optional[List[RepoSnapshot]],
    previous: Optional[List[RepoSnapshot]],
    errors: List[str],
    label: str = "",
) -> None:
    if current is None:
        return
    current_by_repo: Dict[str, RepoSnapshot] = {repo.repo: repo for repo in current}
    previous_by_repo: Dict[str, RepoSnapshot] = {repo.repo: repo for repo in (previous or [])}
    seen = set()
    for repo_name, stars, delta_text in rows:
        if repo_name in seen:
            errors.append("%s包含重复项目：%s" % (label or "总 Star 表格", repo_name))
            continue
        seen.add(repo_name)
        snapshot = current_by_repo.get(repo_name)
        if snapshot is None:
            errors.append("%s项目不在当天快照中：%s" % (label or "总 Star 表格", repo_name))
            continue
        if stars != snapshot.stars:
            errors.append("%sStar 与快照不一致：%s 报告 %d，快照 %d" % (label, repo_name, stars, snapshot.stars))
        baseline = previous_by_repo.get(repo_name)
        expected = None if baseline is None else snapshot.stars - baseline.stars
        if delta_text == "基线建立中":
            actual = None
        else:
            try:
                actual = int(delta_text)
            except ValueError:
                errors.append("净增格式错误：%s（%s）" % (repo_name, delta_text))
                continue
        if actual != expected:
            expected_text = "基线建立中" if expected is None else "%+d" % expected
            errors.append("%s净增与快照不一致：%s 报告 %s，快照应为 %s" % (label, repo_name, delta_text, expected_text))


def validate_report_pair(root: Path, day: date, previous_day: Optional[date] = None) -> None:
    """Validate the report and snapshot for ``day``.

    ``previous_day`` is optional; when omitted, the comparison date embedded
    in the report is used.  A :class:`ReportValidationError` contains every
    detected issue so workflow logs show the complete reason for rejection.
    """

    root = Path(root)
    report_path = root / "reports" / (day.isoformat() + ".md")
    errors: List[str] = []
    if not report_path.is_file():
        errors.append("报告文件不存在：%s" % report_path)
        raise ReportValidationError(errors)
    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReportValidationError(["报告无法读取：%s" % exc])

    comparison_day = _parse_report_metadata(report, day, errors)
    if previous_day is not None:
        comparison_day = previous_day
    if comparison_day is not None and comparison_day >= day:
        errors.append("对比日期必须早于目标日期：%s >= %s" % (comparison_day, day))
    current = _read_snapshot(root, day, errors)
    previous = _read_snapshot(root, comparison_day, errors) if comparison_day is not None else None
    rows = _parse_total_rows(report, errors)
    if current and not rows:
        errors.append("总 Star 排名表为空但当天快照包含项目")
    _validate_star_rows(rows, current, previous, errors)
    growth_rows = _parse_growth_rows(report, errors)
    _validate_star_rows(growth_rows, current, previous, errors, label="增长表")
    _validate_aigcnews_count(report, errors)
    if errors:
        raise ReportValidationError(errors)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a daily AI report and its snapshot")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--date", dest="day", required=True, help="report date in YYYY-MM-DD")
    parser.add_argument("--previous-date", dest="previous_day", help="comparison snapshot date")
    args = parser.parse_args(argv)
    try:
        day = date.fromisoformat(args.day)
        previous_day = date.fromisoformat(args.previous_day) if args.previous_day else None
        validate_report_pair(Path(args.root).expanduser().resolve(), day, previous_day)
    except (ValueError, ReportValidationError) as exc:
        print("Report validation failed: %s" % exc, file=sys.stderr)
        return 1
    print("Report validation passed: %s" % day.isoformat())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
