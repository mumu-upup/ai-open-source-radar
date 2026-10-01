# AI Daily Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the repository into a readable AI daily brief that explains yesterday's major AI events, highlights projects with the largest Star growth, and shows the current top 10 projects by total Stars.

**Architecture:** Keep network collection in `cli.py`, immutable report data in `models.py`, snapshot lookup in `storage.py`, and Markdown presentation in `report.py`. A daily run saves one Asia/Shanghai-dated snapshot, computes comparison metrics against the nearest earlier snapshot, then renders independent growth and total-Star sections so truncating one list cannot hide the other.

**Tech Stack:** Python 3.11 standard library, GitHub REST/Trending HTML, RSS XML, Markdown, `unittest`.

## Global Constraints

- Keep GitHub and RSS data public; no external LLM API or new runtime dependency.
- Use `Asia/Shanghai` for report and snapshot dates.
- Preserve `workflow_dispatch` and schedule the workflow away from the top of the hour (`7 1 * * *` UTC).
- A missing previous snapshot must produce an explicit baseline message and must never fabricate a Star delta.
- Existing tests and offline CLI behavior must remain working.

---

### Task 1: Add failing coverage for comparison metrics and report sections

**Files:**
- Modify: `tests/test_storage_and_metrics.py`
- Modify: `tests/test_report.py`
- Modify: `tests/test_collectors.py`

**Interfaces:**
- Tests will target `DailyRepo.rank_change`, the report's `总 Star 排名前 10` section, event source/time rendering, and nearest-snapshot comparison.

- [ ] **Step 1: Write the failing tests**

Add tests that construct two snapshots and assert:

```python
current = RepoSnapshot("acme/ai", "AI", "https://github.com/acme/ai", "demo", 140, 4, None, None, ["llm"], False, False)
previous = RepoSnapshot("acme/ai", "AI", "https://github.com/acme/ai", "demo", 100, 4, None, None, ["llm"], False, False)
item = DailyRepo(current, 40, None, False, rank_change=2)
text = render_report(day, generated_at, [item], [], [], [], [item], comparison_day=date(2026, 9, 30))
assert "总 Star 排名前 10" in text
assert "140" in text
assert "排名变化" in text
assert "+2" in text
```

Add a feed test asserting a configured source name is present in the rendered event line, and add a storage test asserting the nearest previous snapshot date can be identified when the immediately previous day is missing.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_report tests.test_storage_and_metrics tests.test_collectors -v
```

Expected: failures for the missing `rank_change` field, missing total-Star section, and missing source/date output.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_report.py tests/test_storage_and_metrics.py tests/test_collectors.py
git commit -m "test: specify AI daily brief metrics"
```

### Task 2: Implement snapshot comparison and ranking data

**Files:**
- Modify: `ai_open_source_daily/models.py`
- Modify: `ai_open_source_daily/storage.py`
- Modify: `ai_open_source_daily/cli.py`
- Test: `tests/test_storage_and_metrics.py`

**Interfaces:**
- `DailyRepo` gains `rank_change: Optional[int] = None` while preserving the existing four-argument constructor.
- `SnapshotStore.find_previous_with_day(repo, before, days)` returns `(date, RepoSnapshot)` or `None`.
- `cli._rank_repositories(store, day, repos)` returns `(growth, top_total, baseline, comparison_day)`.

- [ ] **Step 1: Add the minimal data fields and nearest-snapshot helper**

Implement the new optional field and helper without changing report formatting yet. The helper must scan dates from `before - 1 day` through `before - days` and return the first matching repository plus its snapshot date.

- [ ] **Step 2: Run focused tests and verify the comparison test passes while report tests still fail**

Run:

```bash
python3 -m unittest tests.test_storage_and_metrics -v
```

Expected: all storage tests pass; report section assertions remain red until Task 3.

- [ ] **Step 3: Compute independent growth and total-Star rankings**

For every current repository, use the comparison snapshot to calculate `delta_24h`. Build a previous ranking map from the comparison snapshot sorted by `(-stars, repo)`, then calculate `rank_change = previous_rank - current_rank` so a positive value means the project moved up. Sort growth by positive `delta_24h`, keep the top 10, and sort total Star entries by current `stars`, keeping the top 10. Keep baseline/new entries separate.

- [ ] **Step 4: Run the focused metric tests and commit**

```bash
python3 -m unittest tests.test_storage_and_metrics tests.test_report -v

git add ai_open_source_daily/models.py ai_open_source_daily/storage.py ai_open_source_daily/cli.py tests/test_storage_and_metrics.py
git commit -m "feat: compute growth and total star rankings"
```

### Task 3: Render the readable daily brief

**Files:**
- Modify: `ai_open_source_daily/models.py`
- Modify: `ai_open_source_daily/feeds.py`
- Modify: `ai_open_source_daily/report.py`
- Modify: `ai_open_source_daily/cli.py`
- Modify: `tests/test_report.py`
- Modify: `tests/test_collectors.py`

**Interfaces:**
- `FeedItem` gains `source: str = ""` without breaking existing constructors.
- `FeedReader.read(xml_text, since, source="")` stores the configured source.
- `render_report(..., top_total=None, comparison_day=None)` keeps old call sites valid and emits the new sections.

- [ ] **Step 1: Render events with source and publication date**

Change the event bullets to include `[来源]`, the publication date, title, link, and cleaned summary. Keep the latest 10 items.

- [ ] **Step 2: Render growth, total-Star, Trending, observation, and baseline sections**

Use the exact section order from the design. The total-Star table must show rank, project, total Stars, 24h delta, rank change, and link. Use `基线建立中` when comparison data is unavailable. Generate a deterministic observation sentence from the first growth item, first total-Star item, and event count.

- [ ] **Step 3: Run all unit tests and commit**

```bash
python3 -m unittest discover -s tests -v

git add ai_open_source_daily tests/test_report.py tests/test_collectors.py
git commit -m "feat: render readable AI daily brief"
```

### Task 4: Align schedule, README, and generate a local preview

**Files:**
- Modify: `.github/workflows/daily-report.yml`
- Modify: `README.md`
- Create: `reports/preview-2026-10-01.md` (local review artifact only; do not push until approved)

**Interfaces:**
- Workflow cron becomes `7 1 * * *`; commit message uses the Asia/Shanghai report date supplied by the CLI.
- README documents the five report sections, first-day baseline, and approximate 09:07 schedule.

- [ ] **Step 1: Write the failing workflow/documentation assertions if needed**

Verify the workflow contains `7 1 * * *`, retains `workflow_dispatch`, and does not describe UTC date as the report date.

- [ ] **Step 2: Update workflow and README**

Keep the existing permissions and generated-file commit behavior. Update user-facing examples to match the new report sections and explain why the first run cannot show a 24h delta.

- [ ] **Step 3: Generate the local preview from a deterministic two-day fixture**

Run the offline CLI against a temporary fixture containing yesterday and today snapshots, then copy the generated Markdown to `reports/preview-2026-10-01.md` for review. Confirm it contains all five sections and a non-empty growth table, total-Star top 10, and rank changes.

- [ ] **Step 4: Run final verification**

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q ai_open_source_daily tests
python3 -m ai_open_source_daily --help
```

Review the preview manually. Do not push the implementation commits or preview until the user approves the generated report.
