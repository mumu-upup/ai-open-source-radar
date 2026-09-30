from datetime import date, datetime
from typing import List

from .models import DailyRepo, FeedItem, RepoSnapshot, TrendingRepo


def _delta_text(value):
    if value is None:
        return "基线建立中"
    return "%+d" % value


def _clean(text: str) -> str:
    return " ".join((text or "").split())


def render_report(
    day: date,
    generated_at: datetime,
    rankings: List[DailyRepo],
    baseline: List[RepoSnapshot],
    feed_items: List[FeedItem],
    warnings: List[str],
    trending: List[TrendingRepo] = None,
) -> str:
    lines = [
        "# AI 开源项目每日汇总｜%s" % day.isoformat(),
        "",
        "> 采集时间：%s  |  指标：GitHub Star 24 小时净增" % generated_at.isoformat(),
        "> 数据来源：GitHub REST API、配置的公开 RSS；首次出现的仓库显示为“基线建立中”。",
        "",
        "## 24 小时新增 Star 榜",
        "",
    ]
    if rankings:
        lines.extend([
            "| 排名 | 项目 | 24h 净增 | 总 Star | Fork | 最近推送 | 简介 |",
            "| ---: | --- | ---: | ---: | ---: | --- | --- |",
        ])
        for index, item in enumerate(rankings, 1):
            repo = item.repo
            lines.append(
                "| %d | [%s](%s) | %s | %d | %d | %s | %s |" % (
                    index,
                    repo.repo,
                    repo.url,
                    _delta_text(item.delta_24h),
                    repo.stars,
                    repo.forks,
                    repo.pushed_at or "—",
                    _clean(repo.description)[:160] or "—",
                )
            )
    else:
        lines.append("今日暂无可计算的新增 Star 数据。首次运行会先建立基线。")

    lines.extend(["", "## 7 日趋势", ""])
    seven_day = [item for item in rankings if item.delta_7d is not None]
    if seven_day:
        for item in sorted(seven_day, key=lambda row: row.delta_7d or 0, reverse=True)[:10]:
            lines.append("- [%s](%s)：7 日净增 %+d Star。" % (item.repo.repo, item.repo.url, item.delta_7d))
    else:
        lines.append("历史快照不足 7 天，后续日报会逐步补充趋势。")

    lines.extend(["", "## AI 相关动态", ""])
    if feed_items:
        for item in feed_items[:20]:
            summary = "：%s" % _clean(item.summary)[:220] if item.summary else ""
            lines.append("- [%s](%s)%s" % (item.title, item.url or "#", summary))
    else:
        lines.append("过去 24 小时没有成功获取到新的公开 RSS 条目。")

    lines.extend(["", "## 今日 GitHub Trending（AI 相关）", ""])
    if trending:
        lines.extend(["| 项目 | 今日 Trending 新增 Star | 简介 |", "| --- | ---: | --- |"])
        for item in trending[:20]:
            lines.append("| [%s](%s) | +%d | %s |" % (item.repo, item.url, item.stars_today, _clean(item.description)[:160] or "—"))
    else:
        lines.append("今日未获取到 AI 相关 Trending 项目。")

    lines.extend(["", "## 基线建立中", ""])
    if baseline:
        lines.extend("- [%s](%s)：当前 %d Star" % (repo.repo, repo.url, repo.stars) for repo in baseline[:50])
    else:
        lines.append("无。")

    lines.extend(["", "## 采集说明", "", "- 项目候选按 AI 相关 GitHub topics 合并去重，排除 fork、归档仓库和低于最低 Star 阈值的仓库。", "- 日增是固定采集时刻的快照差值；负数表示 Star 净减少。"])
    if warnings:
        lines.extend(["", "## 采集警告", ""])
        lines.extend("- " + warning for warning in warnings)
    lines.append("")
    return "\n".join(lines)
