from datetime import date, datetime
from typing import List, Optional

from .models import DailyRepo, FeedItem, RepoSnapshot, TrendingRepo


_KNOWN_DESCRIPTIONS_ZH = {
    "affaan-m/ECC": "面向 AI 编程与工程协作的工具集。",
    "NousResearch/hermes-agent": "面向自主任务执行的 AI Agent 项目。",
    "tensorflow/tensorflow": "成熟的机器学习与深度学习框架。",
    "Significant-Gravitas/AutoGPT": "可自主拆解并执行任务的 AI Agent 平台。",
    "firecrawl/firecrawl": "把网页内容抓取并转换成适合 LLM 使用的数据。",
    "ollama/ollama": "在本地下载、运行和管理大语言模型。",
    "f/prompts.chat": "提示词、工作流和 AI 应用资源集合。",
    "huggingface/transformers": "覆盖文本、视觉和音频模型的开源模型库。",
    "AUTOMATIC1111/stable-diffusion-webui": "Stable Diffusion 图像生成与模型管理界面。",
    "langgenius/dify": "用于搭建、编排和部署 LLM 应用的平台。",
    "langflow-ai/langflow": "可视化编排 Agent 和 LLM 工作流的开发平台。",
    "open-webui/open-webui": "面向本地和远程模型的友好型 AI 对话界面。",
    "langchain-ai/langchain": "构建 LLM 应用、Agent 和检索流程的开发框架。",
    "browser-use/browser-use": "让 AI Agent 能够理解并操作浏览器。",
    "vllm-project/vllm": "高性能大语言模型推理和服务框架。",
    "infiniflow/ragflow": "面向企业知识库和 RAG 应用的检索增强平台。",
    "unslothai/unsloth": "用于本地训练和微调大语言模型的工具。",
    "openbq-org/OpenBB": "面向分析师、量化和 AI Agent 的数据平台。",
    "PostHog/posthog": "包含 AI 可观测能力的产品分析和开发者工具平台。",
    "microsoft/generative-ai-for-beginners": "面向初学者的生成式 AI 学习课程。",
    "hacksider/Deep-Live-Cam": "实时人脸替换和视频生成工具。",
    "PaddlePaddle/PaddleOCR": "把图像和 PDF 转成结构化数据的 OCR 与文档解析工具。",
    "rtk-ai/rtk": "减少 LLM 命令行 Token 消耗的开发者工具。",
    "scikit-learn/scikit-learn": "提供经典机器学习算法和数据分析能力的 Python 库。",
}


def _zh_description(repo: RepoSnapshot) -> str:
    known = _KNOWN_DESCRIPTIONS_ZH.get(repo.repo)
    if known:
        return known
    text = " ".join([repo.repo, repo.name, repo.description, " ".join(repo.topics)]).lower()
    directions = []
    if any(term in text for term in ("agent", "agents", "智能体")):
        directions.append("AI Agent")
    if any(term in text for term in ("llm", "language model", "大语言模型", "transformer")):
        directions.append("大语言模型")
    if any(term in text for term in ("rag", "retrieval", "knowledge base")):
        directions.append("知识库与 RAG")
    if any(term in text for term in ("diffusion", "image generation", "vision")):
        directions.append("图像与视觉生成")
    if any(term in text for term in ("speech", "voice", "audio", "tts", "stt")):
        directions.append("语音与音频")
    if any(term in text for term in ("framework", "library", "inference", "training")):
        directions.append("模型开发与推理")
    if not directions:
        directions.append("AI 应用与开发工具")
    return "AI 开源项目，主要方向：" + "、".join(dict.fromkeys(directions)) + "。"


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
                    _zh_description(repo),
                )
            )
    elif comparison_day is None:
        lines.append("今天先建立 Star 基线；明天开始显示昨天到今天的净增。")
    else:
        lines.append("过去 24 小时没有正增长明显的项目。")

    lines.extend(["", "## 总 Star 排名前 10", ""])
    if top_total:
        lines.extend([
            "| 排名 | 项目 | 当前总 Star | 24h 净增 | 排名变化 | 中文简介 |",
            "| ---: | --- | ---: | ---: | ---: | --- |",
        ])
        for index, item in enumerate(top_total, 1):
            repo = item.repo
            lines.append(
                "| %d | [%s](%s) | %d | %s | %s | %s |"
                % (
                    index,
                    repo.repo,
                    repo.url,
                    repo.stars,
                    _delta_text(item.delta_24h),
                    _rank_change_text(item.rank_change),
                    _zh_description(repo),
                )
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
