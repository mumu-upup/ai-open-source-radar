# AI 开源雷达

AI 开源雷达每天生成一份 Markdown 日报，跟踪 AI 相关 GitHub 项目的 Star 增长，并汇总最近 24 小时的公开 AI 动态。

## 运行

```bash
python3 -m ai_open_source_daily --root .
```

首次运行会建立 `data/snapshots/YYYY-MM-DD.json` 基线，因此当天新增 Star 会从第二次采集开始计算。日报写入 `reports/YYYY-MM-DD.md`。

可以离线重新渲染最近快照：

```bash
python3 -m ai_open_source_daily --root . --date 2026-10-01 --offline
```

## 数据和限额

候选仓库按 `config/sources.json` 中的 AI topics 搜索，排除 fork、归档仓库和低于 50 Star 的仓库。匿名 GitHub API 有较低限额；如需扩大覆盖面，可在运行环境设置 `GITHUB_TOKEN`。Token 只用于请求 GitHub，不会写入日报或快照。

日报中的新增 Star 是固定采集时刻的快照差值，因此会在 Star 被取消时体现为净减少。RSS 来源失败会写入日报警告，不会阻止项目榜生成。

## GitHub Actions 每天 09:00 自动更新

仓库内置 GitHub Actions，使用 `01:00 UTC`（中国时间 09:00）运行，自动更新 `reports/` 和 `data/snapshots/` 并提交到 `main`。也可以在仓库的 **Actions → Daily AI open-source report → Run workflow** 手动触发。

GitHub Actions 使用内置 `GITHUB_TOKEN` 访问公开 API，不需要额外配置个人 Token。GitHub 的定时任务可能有少量排队延迟。

## 本地每天 09:00 运行（macOS）

```bash
./scripts/install_launchd.sh
```

任务安装在当前用户的 `~/Library/LaunchAgents`。输出和错误日志分别写到 `logs/ai-open-source-daily.out.log` 与 `logs/ai-open-source-daily.err.log`。卸载：

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.codex.ai-open-source-daily.plist"
```
