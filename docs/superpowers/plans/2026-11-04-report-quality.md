# 日报质量纠错 Implementation Plan

> **For agentic workers:** Follow the test-first steps below in this isolated workspace; request an independent code review before integration.

**Goal:** Prevent snapshot intervals and Hermes pipeline tags from being presented as confirmed daily growth or feature releases.

**Architecture:** Keep arithmetic and storage unchanged. Correct report wording and add a narrow, pure feed-entry predicate using URL, tag and summary evidence.

**Tech Stack:** Python standard library, unittest, GitHub Actions.

## Global Constraints

- Dates and report windows use Asia/Shanghai.
- Only mumu-upup/ai-open-source-radar; no force pushes or unrelated project edits.
- Preserve report/snapshot history and user changes.
- Synchronize the actual source with latest main, test, then check remote again before publication.

## Task 1: Reproduce and fix the two observed quality faults

**Files:**
- Modify: `tests/test_report_freshness.py`, `tests/test_collectors.py`, `tests/test_report.py`.
- Modify: `ai_open_source_daily/feeds.py`, `ai_open_source_daily/report.py`, `README.md`.

**Interfaces:** `FeedReader.read` and `render_report` retain their signatures; add `_is_hermes_pipeline_tag(url: str, summary: str) -> bool` inside feeds.py.

- [ ] Update the previous-day and multiday tests to require both table headers to say “两次快照净增”, with unchanged +25 values and comparison dates. Add a negative-delta case.
- [ ] Add Atom fixtures for rc.3-v0.22.6 with truncated attempt/autopublish JSON and abandoned-rc.2-v0.22.6 with encoded attemptRef JSON. Assert neither reaches rendered news/counts.
- [ ] Add preservation cases for normal RC notes, normal Hermes releases, canary, other repositories/hosts and malformed URLs; add canary and stable summary assertions that reject unsupported capability claims.
- [ ] Run `python3 -m unittest tests.test_report_freshness tests.test_collectors tests.test_report -v`; confirm failures are the documented behavior mismatches.
- [ ] Implement the predicate: parse URL safely; require github.com and the Hermes rc tag path; strip markup/unescape summary; require a JSON-object prefix, numeric attempt and autopublish=false or attemptRef string fields. Call it before feed deduplication/appending.
- [ ] Set `growth_label = "两次快照净增"`; explain the snapshot interval limitation. Make Hermes summaries neutral, with an explicit canary caveat. Update README terminology and narrow filter scope.
- [ ] Run the focused tests and full `python3 -m unittest discover -s tests -v`, then report/snapshot validation for 2026-11-03 and `git diff --check`.

## Task 2: Review and publish verified source

- [ ] Commit only the code, tests and documentation listed above; dispatch an independent reviewer with this spec and the baseline/head SHAs.
- [ ] Address findings with tests first when behavior changes.
- [ ] Fetch latest main/staging, integrate main into actual source using a safe fast-forward, verify ancestry, and rerun full validation if the source changed.
- [ ] Recheck remote tips immediately before publishing; update main and staging without rewriting history, retaining their verified report/snapshot blobs.
- [ ] Fast-forward the original checkout, verify remote source/report blobs, and report baseline, actual published commit, conflict outcome and test results.
