from datetime import date, datetime
from typing import List, Optional

from .models import DailyRepo, FeedItem, RepoSnapshot, TrendingRepo


def _delta_text(value: Optional[int]) -> str:
    if value is None:
        return "基线建立中"
    return "%+d" % value


def _rank_change_text(value: Optional[int]) -> str:
    if value is None:
        return "基线建立中"
    if value == 0:
        return "—"
    return "%+d" % value


def _clean(text: str) -> str:
    return " ".join((text or "").split())


def _published_date(value: str) -> str:
    return (value or "")[:10] or "日期未知"


def render_report(
    day: date,
    generated_at: datetime,
    rankings: List[DailyRepo],
    baseline: List[RepoSnapshot],
    feed_items: List[FeedItem],
    warnings: List[str],
    trending: Optional[List[TrendingRepo]] = None,
    top_total: Optional[List[DailyRepo]] = None,
    comparison_day: Optional[date] = None,
) -> str:
    trending = trending or []
    top_total = top_total or []
    comparison_text = comparison_day.isoformat() if comparison_day else "暂无前一日快照（基线建立中）"
    lines = [
        "# AI 每日简报｜%s" % day.isoformat(),
        "",
        "> 采集时间：%s（Asia/Shanghai）" % generated_at.isoformat(),
        "> Star 对比：%s → %s；正数表示净增，负数表示净减少。" % (comparison_text, day.isoformat()),
        "",
        "## 昨日 AI 大事",
        "",
    ]
    if feed_items:
        for item in feed_items[:10]:
            source = item.source or "公开 RSS"
            summary = "：%s" % _clean(item.summary)[:260] if item.summary else ""
            lines.append(
                "- **%s · %s** [%s](%s)%s"
                % (source, _published_date(item.published_at), item.title, item.url or "#", summary)
            )
    else:
        lines.append("过去 24 小时没有成功获取到新的公开 AI 动态。")

    lines.extend(["", "## Star 增长明显的项目", ""])
    if rankings:
        lines.extend([
            "| 排名 | 项目 | 24h 净增 | 当前总 Star | 状态 | 简介 |",
            "| ---: | --- | ---: | ---: | --- | --- |",
        ])
        for index, item in enumerate(rankings, 1):
            repo = item.repo
            status = "新进入追踪" if item.baseline else "—"
            lines.append(
                "| %d | [%s](%s) | %s | %d | %s | %s |"
                % (
                    index,
                    repo.repo,
                    repo.url,
                    _delta_text(item.delta_24h),
                    repo.stars,
                    status,
                    _clean(repo.description)[:160] or "—",
                )
            )
    elif comparison_day is None:
        lines.append("今天先建立 Star 基线；明天开始显示昨天到今天的净增。")
    else:
        lines.append("过去 24 小时没有正增长明显的项目。")

    lines.extend(["", "## 总 Star 排名前 10", ""])
    if top_total:
        lines.extend([
            "| 排名 | 项目 | 当前总 Star | 24h 净增 | 排名变化 |",
            "| ---: | --- | ---: | ---: | ---: |",
        ])
        for index, item in enumerate(top_total, 1):
            repo = item.repo
            lines.append(
                "| %d | [%s](%s) | %d | %s | %s |"
                % (index, repo.repo, repo.url, repo.stars, _delta_text(item.delta_24h), _rank_change_text(item.rank_change))
            )
    else:
        lines.append("当前没有可用的项目快照。")

    lines.extend(["", "## GitHub Trending AI 信号", ""])
    if trending:
        lines.extend(["> Trending 代表当天热度，不等于总 Star 排名。", "", "| 项目 | 今日 Trending 新增 Star | 简介 |", "| --- | ---: | --- |"])
        for item in trending[:10]:
            lines.append("| [%s](%s) | +%d | %s |" % (item.repo, item.url, item.stars_today, _clean(item.description)[:160] or "—"))
    else:
        lines.append("今日未获取到 AI 相关 Trending 项目。")

    lines.extend(["", "## 一句话观察", ""])
    observations = []
    if rankings:
        first = rankings[0]
        observations.append("Star 增长最快的是 %s（%s）。" % (first.repo.repo, _delta_text(first.delta_24h)))
    elif comparison_day is None:
        observations.append("今天是基线日，明天开始可以观察 Star 的日变化。")
    else:
        observations.append("今天没有项目出现正 Star 增长。")
    if top_total:
        observations.append("当前总 Star 第一是 %s（%d）。" % (top_total[0].repo.repo, top_total[0].repo.stars))
    observations.append("过去 24 小时收录 %d 条 AI 动态。" % len(feed_items))
    lines.extend("- " + observation for observation in observations)

    lines.extend(["", "## 新进入追踪", ""])
    if baseline:
        lines.append("以下项目在对比快照中不存在，今天首次进入追踪：")
        lines.extend("- [%s](%s)：当前 %d Star" % (repo.repo, repo.url, repo.stars) for repo in baseline[:10])
        if len(baseline) > 10:
            lines.append("- 另有 %d 个项目首次进入追踪。" % (len(baseline) - 10))
    else:
        lines.append("没有新进入追踪的项目。")

    lines.extend([
        "",
        "## 数据说明",
        "",
        "- 项目候选按 AI 相关 GitHub topics 合并去重，排除 fork、归档仓库和低于最低 Star 阈值的仓库。",
        "- Star 增长是固定采集时刻的快照净差；首次出现的项目不会伪造增量。",
        "- AI 动态来自配置的公开 RSS；Trending 是独立的当天热度信号。",
    ])
    if warnings:
        lines.extend(["", "## 采集警告", ""])
        lines.extend("- " + warning for warning in warnings)
    lines.append("")
    return "\n".join(lines)
