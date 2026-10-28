# AI 开源雷达

AI 开源雷达每天生成一份“昨天 AI 发生了什么”的 Markdown 简报。读者可以先看 AI 大事，再看 Star 增长明显的项目，最后查看当前总 Star 前 10 的项目。

每期日报包含：

- 昨日 AI 大事：来自 OpenAI、NVIDIA、TechCrunch、GitHub、Hugging Face、Qwen、Mistral 等公开 RSS，以及 Codex、Claude、Gemini、GLM、Kimi、DeepSeek、Hermes、Qwen、Llama、Mistral、Gemma、Grok、Pi、Jev 和 OpenHands、Cline、Aider、SWE-agent、OpenCode、Kilo Code 等官方或主仓库更新源；同时扫描 Hugging Face 上 Qwen、Hermes、Llama、Mistral、Gemma、Phi、MiniMax、Yi 的模型仓库活动，带来源、日期、链接和摘要。
- Star 增长明显的项目：昨天快照到今天快照的 Star 净增，标记新进入追踪的项目。
- 总 Star 排名前 10：当前最受欢迎的项目，同时显示 24h 净增和排名变化。
- GitHub Trending AI 信号：当天热度参考，不等于总 Star 排名。
- 一句话观察、基线说明和采集警告。

日报采用中英文并列展示：项目和 Trending 表格同时提供中文简介与仓库原始英文简介；AI 动态同时提供中文概述和 RSS 原文摘要。中文读者可以先看中文结论，习惯英文的读者可以直接核对原文。

“昨日 AI 大事”按中国时区的自然日统计（昨天 00:00–24:00），最多展示 20 条并按发布时间倒序去重。重点产品区覆盖闭源模型、开源模型和编程 Agent；如果某个产品当天没有公开更新，会明确显示并继续监控，不会编造条目。Hugging Face 条目描述的是模型仓库活动：只有 `createdAt` 和 `lastModified` 都落在窗口内时才标记为新模型仓库，否则写成仓库更新，不把代码或权重同步误报成模型发布。Jev 的官方模型入口是 TypeSafe AI，`browser-use/jev-ultrafast` 单独标为社区集成；Pi 这里监控的是开源 Pi Agent Harness，和 Inflection 的 Pi 助手分开标注。

### 补充选题来源：AIGCNEWS

聊天定时整理还参考 [AIGCNEWS](https://aigcnews.cn/) 及其 [公开 RSS](https://aigcnews.cn/api/feed.xml)，每天最多选 1 条 AI 新闻、模型或 Agent 线索。追溯原始来源、核对发布日期和去重后，以一句中文摘要说明事件，并保留原文链接；来源归属注明“AIGCNEWS 线索／原始来源”。若没有可核实的合适内容则不补选；未核实内容不作为已确认更新，也不凑数。

该站是聚合服务，公开 RSS 混有 GitHub 项目、论文、社交动态和一般热点，部分日期是聚合或采集时间，摘要也可能由 AI 生成。整理时去除订阅宣传，区分原文发布时间、事件日期和聚合时间；若无法核实昨日窗口，明确说明日期待核验。项目 Star 增长继续使用本仓库独立快照。AIGCNEWS 线索若已被主日报收录则不重复；只有核实后仍未覆盖的重要内容才补入。GitHub Actions 的自动 RSS 列表尚未直接接入这个混合订阅，补充筛选由聊天整理任务完成；该任务未运行时，云端日报不保证包含 AIGCNEWS 线索。

## 运行

```bash
python3 -m ai_open_source_daily --root .
```

首次运行会建立 `data/snapshots/YYYY-MM-DD.json` 基线，因此当天新增 Star 会从第二次采集开始计算；总 Star 前 10 在首次运行也会正常显示。日报写入 `reports/YYYY-MM-DD.md`。

在线运行时，如果指定日期的日报和快照都已存在，会保留现有内容，避免重复采集覆盖人工校订；只有日报但缺少快照时仍会尝试采集。离线重新渲染会重写指定日期的日报，操作前请保留需要的人工编辑。

可以离线重新渲染最近快照：

```bash
python3 -m ai_open_source_daily --root . --date 2026-10-01 --offline
```

## 数据和限额

候选仓库按 `config/sources.json` 中的 AI topics 搜索，排除 fork、归档仓库和低于 50 Star 的仓库。匿名 GitHub API 有较低限额；如需扩大覆盖面，可在运行环境设置 `GITHUB_TOKEN`。Token 只用于请求 GitHub，不会写入日报或快照。

日报中的新增 Star 是采集快照的差值，因此会在 Star 被取消时体现为净减少。对比快照相隔超过一天时显示“区间净增”，不能解读为 24 小时增长。采集失败使用历史快照时，明确标注快照日期，不计算今日净增或排名变化。GitHub 搜索限流会按照服务端响应头有限等待重试；RSS 来源失败会写入日报警告，不会阻止项目榜生成。

## GitHub Actions 每天 08:00 采集、09:00 推送

仓库内置两段 GitHub Actions：`Daily AI report - collect` 计划在中国时间 08:00 采集公开来源并保存到 `daily-report-staging`；`Daily AI report - publish` 计划在中国时间 09:00 仅把当天的日报和快照推送到 `main`，保留其他日期的文件。**GitHub 定时触发不保证准点，本仓库已出现数小时延迟。** 可在仓库的 **Actions** 页面手动触发采集，待完成后再触发发布。

两阶段串行执行，先同步最新 main；main 或 staging 已有当天报告和快照时跳过采集，main 已有当天两份文件时跳过发布。跳过与是否有 AIGCNEWS 补充无关。采集使用 main 的源码和历史快照，只将当天产物提交到 staging，通过普通推送保留其历史；提交中记录生成时的 main 版本。发布前重新检查远端，若 main 已前进或待发布文件被修改则停止，重新同步核验后再运行。

GitHub Actions 使用内置 `GITHUB_TOKEN` 访问公开 API，不需要额外配置个人 Token。

维护者另在桌面应用中启用了“AI 开源雷达：08点整理、09点发布”聊天定时任务，每天北京时间 08:00、09:00 检查并补跑流水线，验证远端文件后在原聊天报告结果。本地任务要求电脑开机、应用运行并能联网；GitHub Actions 继续作为云端后备。克隆仓库不会自动创建这项聊天任务。

## 本地每天 08:00 运行（macOS）

```bash
./scripts/install_launchd.sh
```

任务安装在当前用户的 `~/Library/LaunchAgents`，每天 08:00 生成本地日报。输出和错误日志分别写到 `logs/ai-open-source-daily.out.log` 与 `logs/ai-open-source-daily.err.log`。卸载：

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.codex.ai-open-source-daily.plist"
```
