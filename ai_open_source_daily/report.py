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

_KNOWN_EVENT_SUMMARIES_ZH = {
    "open tts leaderboard": "发布多语言文本转语音与声音克隆评测榜单，方便比较不同方案的效果。",
    "nvidia kumo": "NVIDIA 介绍面向表格数据预测的 Kumo 方案，重点提升准确率和效率。",
    "source right": "研究如何让 MCP Agent 正确引用信息来源，减少回答中的事实错误。",
    "android vulnerabilities": "GitHub 介绍开源 AI 安全 Agent，展示其发现 Android 漏洞的实践。",
    "policy update": "GitHub 更新开发者政策，重点涉及透明度、平台治理和开源生态。",
    "distillation campaign": "OpenAI 介绍如何阻止模型蒸馏攻击，强化对模型能力和推理过程的保护。",
    "small businesses": "OpenAI 与美国小企业发展中心合作，帮助小企业培训和使用 AI。",
    "cerebras systems": "Cerebras 讨论 AI 规模化发展面临的算力、能源和基础设施挑战。",
    "restate lands": "Restate 获得融资，重点建设面向 AI Agent 的持久化执行基础设施。",
    "airbnb adds ai": "Airbnb 更新 AI 搜索和社交功能，探索把 AI 融入旅行服务。",
}

_PRODUCT_SOURCE_SUMMARIES_ZH = {
    "codex": "Codex 发布版本更新，具体改动和修复请查看英文发布说明。",
    "claude": "Claude 发布版本更新，具体改动和修复请查看英文发布说明。",
    "gemini": "Gemini 发布版本更新，具体改动和修复请查看英文发布说明。",
    "glm": "GLM 发布版本更新，具体改动和修复请查看英文发布说明。",
    "kimi": "Kimi 发布版本更新，具体改动和修复请查看英文发布说明。",
    "deepseek": "DeepSeek 发布版本更新，具体改动和修复请查看英文发布说明。",
    "hermes": "Hermes Agent 发布更新，重点关注自主任务执行、记忆和工具调用能力。",
    "qwen": "Qwen 模型或工具发布更新，具体改动请查看英文发布说明。",
    "llama": "Llama 模型生态发布更新，具体改动请查看英文发布说明。",
    "mistral": "Mistral 模型或开发工具发布更新，具体改动请查看英文发布说明。",
    "gemma": "Gemma 模型生态发布更新，具体改动请查看英文发布说明。",
    "grok": "Grok 模型生态发布更新，具体改动请查看英文发布说明。",
    "pi": "Pi Agent Harness 发布更新，重点关注 AI 编程和 Agent 工作流。",
    "jev": "Jev / TypeSafe System One 相关更新，重点关注浏览器 Agent 和工具调用能力。",
    "openhands": "OpenHands 开源编程 Agent 发布更新，重点关注软件工程任务执行。",
    "cline": "Cline 编程 Agent 发布更新，重点关注 IDE 内的代码协作能力。",
    "aider": "Aider 编程 Agent 发布更新，重点关注终端代码修改和协作。",
    "swe-agent": "SWE-agent 软件工程 Agent 发布更新，重点关注自动修复代码问题。",
    "opencode": "OpenCode 开源编程 Agent 发布更新，具体改动请查看英文发布说明。",
    "kilo": "Kilo Code 编程 Agent 发布更新，具体改动请查看英文发布说明。",
    "phi": "Phi 系列模型生态发布更新，具体改动请查看英文发布说明。",
    "minimax": "MiniMax 模型或平台发布更新，具体改动请查看英文发布说明。",
    "yi": "Yi 系列模型生态发布更新，具体改动请查看英文发布说明。",
}

_FOCUS_PRODUCTS = (
    "Codex", "Claude", "Gemini", "GLM", "Kimi", "DeepSeek",
    "Hermes", "Qwen", "Llama", "Mistral", "Gemma", "Grok", "Pi", "Jev",
    "OpenHands", "Cline", "Aider", "SWE-agent", "OpenCode", "Kilo Code",
    "Phi", "MiniMax", "Yi",
)


def _focus_product(item: FeedItem) -> Optional[str]:
    source = (item.source or "").lower()
    source_markers = (
        ("codex", "Codex"),
        ("claude", "Claude"),
        ("gemini", "Gemini"),
        ("glm", "GLM"),
        ("zhipu", "GLM"),
        ("kimi", "Kimi"),
        ("moonshot", "Kimi"),
        ("deepseek", "DeepSeek"),
        ("hermes", "Hermes"),
        ("qwen", "Qwen"),
        ("llama", "Llama"),
        ("mistral", "Mistral"),
        ("gemma", "Gemma"),
        ("grok", "Grok"),
        ("jev", "Jev"),
        ("typesafe", "Jev"),
        ("pi agent", "Pi"),
        ("pi-mono", "Pi"),
        ("openhands", "OpenHands"),
        ("cline", "Cline"),
        ("aider", "Aider"),
        ("swe-agent", "SWE-agent"),
        ("opencode", "OpenCode"),
        ("kilo", "Kilo Code"),
        ("phi", "Phi"),
        ("minimax", "MiniMax"),
        ("01.ai", "Yi"),
    )
    for marker, product in source_markers:
        if marker in source:
            return product

    title = (item.title or "").lower()
    title_markers = (
        ("codex", "Codex"),
        ("claude", "Claude"),
        ("gemini", "Gemini"),
        ("glm", "GLM"),
        ("zhipu", "GLM"),
        ("kimi", "Kimi"),
        ("moonshot", "Kimi"),
        ("deepseek", "DeepSeek"),
        ("hermes", "Hermes"),
        ("qwen", "Qwen"),
        ("llama", "Llama"),
        ("mistral", "Mistral"),
        ("gemma", "Gemma"),
        ("grok", "Grok"),
        ("jev", "Jev"),
        ("typesafe", "Jev"),
        ("pi agent", "Pi"),
        ("pi-mono", "Pi"),
        ("openhands", "OpenHands"),
        ("cline", "Cline"),
        ("aider", "Aider"),
        ("swe-agent", "SWE-agent"),
        ("opencode", "OpenCode"),
        ("kilo", "Kilo Code"),
        ("phi", "Phi"),
        ("minimax", "MiniMax"),
        ("01.ai", "Yi"),
        (" yi ", "Yi"),
    )
    for marker, product in title_markers:
        if marker in title:
            return product
    return None


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


def _zh_event_summary(item: FeedItem) -> str:
    text = "%s %s" % (item.title, item.summary)
    lowered = text.lower()
    source_lowered = (item.source or "").lower()
    for marker, summary in _PRODUCT_SOURCE_SUMMARIES_ZH.items():
        if marker in source_lowered:
            title_lowered = (item.title or "").lower()
            if any(tag in title_lowered for tag in ("alpha", "beta", "preview", "nightly", "experimental", " rc")):
                return summary + "当前标记为预发布版本。"
            return summary
    for marker, summary in _KNOWN_EVENT_SUMMARIES_ZH.items():
        if marker in lowered:
            return summary
    directions = []
    if any(term in lowered for term in ("agent", "agents")):
        directions.append("AI Agent")
    if any(term in lowered for term in ("tts", "voice", "speech", "audio")):
        directions.append("语音与音频")
    if any(term in lowered for term in ("model", "llm", "inference", "transformer")):
        directions.append("大语言模型")
    if any(term in lowered for term in ("security", "vulnerabil")):
        directions.append("AI 安全")
    if not directions:
        directions.append("AI 技术与开源生态")
    return "该动态聚焦于%s，具体内容请查看原文。" % "、".join(dict.fromkeys(directions))


def _zh_trending_description(item: TrendingRepo) -> str:
    known = _KNOWN_DESCRIPTIONS_ZH.get(item.repo)
    if known:
        return known
    text = "%s %s" % (item.repo, item.description)
    lowered = text.lower()
    if any(term in lowered for term in ("agent", "agents")):
        direction = "AI Agent"
    elif any(term in lowered for term in ("model", "llm", "transformer")):
        direction = "大语言模型"
    elif any(term in lowered for term in ("image", "vision", "diffusion")):
        direction = "图像与视觉生成"
    else:
        direction = "AI 应用与开发工具"
    return "AI 开源项目，主要方向：%s。" % direction


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


def _select_event_items(items: List[FeedItem], limit: int = 20) -> List[FeedItem]:
    """Keep the dated brief readable while giving each source one first slot."""
    ordered = list(items)
    selected: List[FeedItem] = []
    selected_keys = set()
    sources = set()
    for item in ordered:
        source = item.source or "公开 RSS"
        key = item.url or item.title
        if source in sources or key in selected_keys:
            continue
        selected.append(item)
        sources.add(source)
        selected_keys.add(key)
        if len(selected) >= limit:
            return selected
    for item in ordered:
        key = item.url or item.title
        if key in selected_keys:
            continue
        selected.append(item)
        selected_keys.add(key)
        if len(selected) >= limit:
            break
    return selected


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
    current_data_available: bool = True,
    snapshot_day: Optional[date] = None,
) -> str:
    trending = trending or []
    top_total = top_total or []
    comparison_text = comparison_day.isoformat() if comparison_day else "暂无前一日快照（基线建立中）"
    growth_label = "区间净增" if comparison_day and (day - comparison_day).days != 1 else "24h 净增"
    star_status = "> Star 对比：%s → %s；正数表示净增，负数表示净减少。" % (comparison_text, day.isoformat())
    if not current_data_available:
        star_status = "> 今日 Star 数据不可用；%s。净增与排名变化暂不计算。" % (
            "历史快照截至 %s" % snapshot_day.isoformat() if snapshot_day else "没有完整项目快照")
    lines = [
        "# AI 每日简报｜%s" % day.isoformat(),
        "",
        "> 采集时间：%s（Asia/Shanghai）" % generated_at.isoformat(),
        star_status,
        "",
        "## 昨日 AI 大事",
        "",
    ]
    displayed_events = _select_event_items(feed_items)
    if displayed_events:
        for item in displayed_events:
            source = item.source or "公开 RSS"
            english_summary = _clean(item.summary)[:260].strip() if item.summary else "—"
            summary = "；中文概述：%s；English summary: %s" % (_zh_event_summary(item), english_summary)
            lines.append(
                "- **%s · %s** [%s](%s)%s"
                % (source, _published_date(item.published_at), item.title, item.url or "#", summary)
            )
    else:
        lines.append("昨日（Asia/Shanghai）没有成功获取到新的公开 AI 动态。")

    focus_events = {product: [] for product in _FOCUS_PRODUCTS}
    for item in feed_items:
        product = _focus_product(item)
        if product:
            focus_events[product].append(item)
    lines.extend(["", "## 重点产品更新", ""])
    for product in _FOCUS_PRODUCTS:
        entries = focus_events[product]
        if entries:
            sources = "、".join(dict.fromkeys(item.source or "公开来源" for item in entries))
            lines.append("- **%s**：昨日收录 %d 条（来源：%s）。" % (product, len(entries), sources))
        else:
            lines.append("- **%s**：昨日未发现公开更新，已持续监控官方新闻、文档和 GitHub 更新源。" % product)

    lines.extend(["", "## Star 增长明显的项目", ""])
    if not current_data_available:
        lines.append("今日 Star 数据不可用，暂不判断项目增长。")
    elif rankings:
        lines.extend([
            "| 排名 | 项目 | %s | 当前总 Star | 状态 | 中文简介 | English description |" % growth_label,
            "| ---: | --- | ---: | ---: | --- | --- | --- |",
        ])
        for index, item in enumerate(rankings, 1):
            repo = item.repo
            status = "新进入追踪" if item.baseline else "—"
            lines.append(
                "| %d | [%s](%s) | %s | %d | %s | %s | %s |"
                % (
                    index,
                    repo.repo,
                    repo.url,
                    _delta_text(item.delta_24h),
                    repo.stars,
                    status,
                    _zh_description(repo),
                    _clean(repo.description)[:160].strip() or "—",
                )
            )
    elif comparison_day is None:
        lines.append("今天先建立 Star 基线；明天开始显示昨天到今天的净增。")
    else:
        lines.append("对比区间内没有正增长明显的项目。")

    lines.extend(["", "## 总 Star 排名前 10", ""])
    if top_total:
        lines.extend([
            "| 排名 | 项目 | %s | %s | 排名变化 | 中文简介 | English description |" % (
                "当前总 Star" if current_data_available else "历史快照 Star", growth_label),
            "| ---: | --- | ---: | ---: | ---: | --- | --- |",
        ])
        for index, item in enumerate(top_total, 1):
            repo = item.repo
            lines.append(
                "| %d | [%s](%s) | %d | %s | %s | %s | %s |"
                % (
                    index,
                    repo.repo,
                    repo.url,
                    repo.stars,
                    _delta_text(item.delta_24h) if current_data_available else "—",
                    _rank_change_text(item.rank_change) if current_data_available else "—",
                    _zh_description(repo),
                    _clean(repo.description)[:160].strip() or "—",
                )
            )
    else:
        lines.append("当前没有可用的项目快照。")

    lines.extend(["", "## GitHub Trending AI 信号", ""])
    if trending:
        lines.extend(["> Trending 代表当天热度，不等于总 Star 排名。", "", "| 项目 | 今日 Trending 新增 Star | 中文简介 | English description |", "| --- | ---: | --- | --- |"])
        for item in trending[:10]:
            lines.append("| [%s](%s) | +%d | %s | %s |" % (item.repo, item.url, item.stars_today, _zh_trending_description(item), _clean(item.description)[:160].strip() or "—"))
    else:
        lines.append("今日未获取到 AI 相关 Trending 项目。")

    lines.extend(["", "## 一句话观察", ""])
    observations = []
    if not current_data_available:
        observations.append("今日 Star 数据不可用，不能据此判断有无增长。")
    elif rankings:
        first = rankings[0]
        observations.append("Star 增长最快的是 %s（%s）。" % (first.repo.repo, _delta_text(first.delta_24h)))
    elif comparison_day is None:
        observations.append("今天是基线日，明天开始可以观察 Star 的日变化。")
    else:
        observations.append("对比区间内没有项目出现正 Star 增长。")
    if top_total:
        observations.append("%s总 Star 第一是 %s（%d）。" % (
            "当前" if current_data_available else "历史快照中", top_total[0].repo.repo, top_total[0].repo.stars))
    observations.append("昨日（Asia/Shanghai）收录 %d 条 AI 动态。" % len(feed_items))
    lines.extend("- " + observation for observation in observations)

    lines.extend(["", "## 新进入追踪", ""])
    if not current_data_available:
        lines.append("今日项目数据不可用，暂不判断新增追踪项目。")
    elif baseline:
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
        "- AI 动态按 Asia/Shanghai 自然日（昨日 00:00–24:00）从配置的公开 RSS 和官方 Release 源统计；Trending 是独立的当天热度信号。",
    ])
    if warnings:
        lines.extend(["", "## 采集警告", ""])
        lines.extend("- " + warning for warning in warnings)
    lines.append("")
    return "\n".join(lines)
