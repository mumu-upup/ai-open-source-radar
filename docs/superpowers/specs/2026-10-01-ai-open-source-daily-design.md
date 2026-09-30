# AI 开源项目每日汇总设计

## 目标

每天中国时间 09:00 生成一份 Markdown 日报，回答两个问题：哪些 AI 相关开源项目在过去一天新增 Star 明显，以及过去一天有哪些值得关注的 AI 开源动态。

## 数据口径

- “新增关注者”统一按 GitHub 仓库 Star 处理。
- 主指标是固定采集时刻的仓库 Star 快照差值：`今日 stargazers_count - 昨日 stargazers_count`。Star 取消会抵消增长，因此称为 24 小时净增。
- 首次运行建立候选项目基线；没有昨日快照的项目显示“基线建立中”，不伪造日增数。
- 候选项目来自 GitHub 搜索的 AI 主题：`artificial-intelligence`、`machine-learning`、`deep-learning`、`llm`、`generative-ai`、`agents`、`rag`、`diffusion`、`inference`。结果按 Star 和最近推送时间合并去重。
- 只收录公开、未归档、非 fork 仓库；默认总 Star 至少 50，避免日报被低质量新仓库淹没。
- 动态部分优先使用候选仓库最近 24 小时的 release、push 和 README 变化，并补充 GitHub Blog 与 Hugging Face Blog 的公开 RSS；单个来源失败不影响项目榜单。

## 输出

每次生成 `reports/YYYY-MM-DD.md`，包含：

1. 采集时间、数据来源、是否使用 GitHub Token。
2. 24 小时净增榜（最多 20 个项目）。
3. 7 日趋势榜（有足够历史时显示）。
4. “基线建立中”项目列表。
5. AI 动态：新 release、仓库活动和 RSS 条目。
6. 失败来源和限流提示。

历史数据写入 `data/snapshots/YYYY-MM-DD.json`，配置写入 `.env.example` 和 `config/sources.json`。不把 Token 或其他凭据写入报告。

## 运行方式

- 主入口：`python -m ai_open_source_daily`。
- 默认按当前日期生成报告，也支持 `--date YYYY-MM-DD` 和 `--offline`。
- 本地定时任务使用 macOS `launchd`，每天 09:00 Asia/Shanghai 运行；任务失败写入日志但保留已有快照。
- GitHub API 使用标准库 `urllib`，无第三方依赖。设置 `GITHUB_TOKEN` 后提高限额；未设置时使用匿名公开 API。

## 错误处理

- 网络、单个查询或单个 RSS 解析失败时记录 warning，继续处理其他来源。
- GitHub 429/403 时保留已有数据，报告中写明限流，并使用可用的本地快照。
- API 返回字段缺失的仓库跳过，不让坏数据中断整份日报。

## 验证

- 单元测试覆盖 Star 增量计算、候选仓库去重过滤、RSS 日期过滤、Markdown 输出和快照读写。
- 使用离线 fixture 运行完整报告生成，确保无网络时仍能从已有快照生成可读报告。
