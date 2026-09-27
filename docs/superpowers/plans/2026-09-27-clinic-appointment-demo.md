# Clinic Appointment Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, account-free clinic appointment demo with a WeChat-style patient conversation, a daily-Sheet assistant view, tomorrow's mock schedule, booking, cancellation, speech playback, and durable local data.

**Architecture:** A single Node.js/Express process serves both browser interfaces and JSON APIs. Domain services own scheduling, booking, cancellation, and deterministic Chinese intent parsing; a local JSON workbook stores one date-keyed Sheet per day using atomic file replacement and a serialized mutation queue.

**Tech Stack:** Node.js 20+ (verified with Node.js 25.9), Express 5, browser-native HTML/CSS/JavaScript, browser SpeechSynthesis, Node built-in test runner, Supertest.

## Global Constraints

- Use the `Asia/Shanghai` time zone for all date calculations.
- Generate 63 ten-minute slots per day: 08:30–11:20 and 13:00–20:20.
- Support one doctor only.
- Store no symptoms, diagnoses, ID numbers, or full phone numbers.
- Use only fictional demonstration patients and phone suffixes.
- Persist runtime data locally and exclude it from Git.
- Do not connect to Feishu, Tencent Docs, Enterprise WeChat, or unofficial WeChat protocols.
- Mark the patient interface clearly as an appointment demo, not an official medical service.

---

## File Map

- `package.json`: scripts and minimal runtime/test dependencies.
- `.gitignore`: excludes dependencies and runtime workbook files.
- `src/domain/schedule.js`: Shanghai dates, slot generation, and period filtering.
- `src/store/json-workbook.js`: local workbook persistence and atomic slot mutations.
- `src/services/booking-service.js`: validated booking/cancellation operations and codes.
- `src/services/intent-parser.js`: deterministic parsing of Chinese dates, times, and intents.
- `src/services/conversation-service.js`: per-session multi-turn appointment dialogue.
- `src/http/app.js`: Express API and static-page composition.
- `src/server.js`: production entry point and mock-data startup.
- `public/index.html`, `public/patient.js`, `public/shared.css`, `public/patient.css`: patient demo.
- `public/assistant.html`, `public/assistant.js`, `public/assistant.css`: assistant Sheet demo.
- `test/*.test.js`: domain, store, service, conversation, and API coverage.
- `README.md`: start, reset, demonstration, and LAN-access instructions.

---

### Task 1: Project scaffold and schedule domain

**Files:**
- Create: `package.json`
- Create: `.gitignore`
- Create: `src/domain/schedule.js`
- Test: `test/schedule.test.js`

**Interfaces:**
- Produces: `dateInShanghai(now) -> string`
- Produces: `addCalendarDays(date, days) -> string`
- Produces: `generateSlots(date) -> Slot[]`
- Produces: `filterSlotsByPeriod(slots, period) -> Slot[]`

- [ ] **Step 1: Add the test runner and write failing schedule tests**

Create `package.json` and `test/schedule.test.js` with these assertions:

```json
{
  "name": "clinic-appointment-demo",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "node --watch src/server.js",
    "start": "node src/server.js",
    "test": "node --test",
    "test:watch": "node --test --watch"
  },
  "dependencies": {
    "express": "^5.1.0"
  },
  "devDependencies": {
    "supertest": "^7.1.4"
  }
}
```

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  addCalendarDays,
  dateInShanghai,
  filterSlotsByPeriod,
  generateSlots,
} from '../src/domain/schedule.js';

test('dateInShanghai honors the Shanghai calendar day', () => {
  assert.equal(dateInShanghai(new Date('2026-09-27T16:30:00.000Z')), '2026-09-28');
});

test('generateSlots creates 63 slots and excludes lunch', () => {
  const slots = generateSlots('2026-09-28');
  assert.equal(slots.length, 63);
  assert.equal(slots[0].time, '08:30');
  assert.equal(slots.at(-1).time, '20:20');
  assert.equal(slots.some(({ time }) => time >= '11:30' && time < '13:00'), false);
});

test('period filters split morning, afternoon, and evening', () => {
  const slots = generateSlots('2026-09-28');
  assert.equal(filterSlotsByPeriod(slots, 'morning').at(-1).time, '11:20');
  assert.equal(filterSlotsByPeriod(slots, 'afternoon').at(-1).time, '17:50');
  assert.equal(filterSlotsByPeriod(slots, 'evening')[0].time, '18:00');
});

test('addCalendarDays advances a date without changing its format', () => {
  assert.equal(addCalendarDays('2026-09-30', 1), '2026-10-01');
});
```

- [ ] **Step 2: Run the schedule tests and confirm the missing-module failure**

Run: `npm install && node --test test/schedule.test.js`

Expected: FAIL because `src/domain/schedule.js` does not exist.

- [ ] **Step 3: Implement the schedule domain**

Create `src/domain/schedule.js` with a private range generator and the four exported functions. Each generated slot has this exact shape:

```js
{
  id: '2026-09-28-0830',
  date: '2026-09-28',
  time: '08:30',
  endTime: '08:40',
  status: 'available',
  patientName: '',
  phoneLast4: '',
  bookingCode: '',
  updatedAt: ''
}
```

Generate morning minutes `[510, 690)` and afternoon minutes `[780, 1230)` in increments of ten. Define period boundaries as morning before 11:30, afternoon from 13:00 through 17:50, and evening from 18:00 onward. Use `Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' })` for the current date.

- [ ] **Step 4: Run the schedule tests**

Run: `node --test test/schedule.test.js`

Expected: 4 tests pass.

- [ ] **Step 5: Ignore runtime files and commit**

Create `.gitignore` containing:

```gitignore
node_modules/
data/*.json
data/*.tmp
.DS_Store
```

Run:

```bash
git add package.json package-lock.json .gitignore src/domain/schedule.js test/schedule.test.js
git commit -m "feat: add clinic schedule domain"
```

---

### Task 2: Local JSON workbook with daily Sheets

**Files:**
- Create: `src/store/json-workbook.js`
- Test: `test/json-workbook.test.js`

**Interfaces:**
- Consumes: `generateSlots(date)` from Task 1.
- Produces: `new JsonWorkbook({ filePath, now })`
- Produces: `ensureSheet(date)`, `listSheets()`, `listSlots(date)`, `bookSlot(input)`, `cancelBooking(input)`, `setSlotAvailability(input)`, and `resetDemo(date)`.

- [ ] **Step 1: Write failing persistence and mutation tests**

Use `mkdtemp(join(tmpdir(), 'clinic-demo-'))` for isolation. Cover these exact cases:

```js
test('ensureSheet persists 63 slots and survives a new store instance', async () => {
  const first = new JsonWorkbook({ filePath });
  await first.ensureSheet('2026-09-28');
  const second = new JsonWorkbook({ filePath });
  assert.equal((await second.listSlots('2026-09-28')).length, 63);
});

test('bookSlot serializes competing writes', async () => {
  await store.ensureSheet('2026-09-28');
  const inputs = ['A12345', 'B12345'].map((bookingCode) =>
    store.bookSlot({
      date: '2026-09-28', time: '14:00', patientName: '演示患者',
      phoneLast4: '5678', bookingCode, updatedAt: '2026-09-27T10:00:00.000Z',
    })
  );
  const results = await Promise.allSettled(inputs);
  assert.equal(results.filter(({ status }) => status === 'fulfilled').length, 1);
  assert.equal(results.filter(({ status }) => status === 'rejected').length, 1);
});

test('cancelBooking requires both code and phone suffix', async () => {
  await assert.rejects(
    store.cancelBooking({ bookingCode: 'A12345', phoneLast4: '0000' }),
    /预约信息不匹配/,
  );
});

test('setSlotAvailability cannot reopen a booked slot', async () => {
  await assert.rejects(
    store.setSlotAvailability({ date: '2026-09-28', time: '14:00', status: 'available' }),
    /已预约号源不能直接修改/,
  );
});
```

- [ ] **Step 2: Verify the workbook tests fail**

Run: `node --test test/json-workbook.test.js`

Expected: FAIL because `JsonWorkbook` is missing.

- [ ] **Step 3: Implement atomic local persistence**

Implement `JsonWorkbook` with this on-disk schema:

```js
{
  version: 1,
  sheets: {
    '2026-09-28': {
      date: '2026-09-28',
      slots: []
    }
  }
}
```

Serialize every mutation through a promise queue. Read the newest workbook inside the queued operation, apply exactly one mutation, write JSON to `${filePath}.${process.pid}.tmp`, then rename it over `filePath`. Throw Chinese user-safe errors for unavailable, booked, missing, and mismatched records. `resetDemo(date)` must replace runtime data with 63 slots and seed these fictional rows:

```js
[
  { time: '09:30', status: 'booked', patientName: '王阿姨', phoneLast4: '1024', bookingCode: 'W39281' },
  { time: '14:20', status: 'booked', patientName: '李先生', phoneLast4: '6677', bookingCode: 'L58126' },
  { time: '16:00', status: 'closed', patientName: '', phoneLast4: '', bookingCode: '' }
]
```

- [ ] **Step 4: Run store tests**

Run: `node --test test/json-workbook.test.js`

Expected: all workbook tests pass and no temporary file remains.

- [ ] **Step 5: Commit the workbook**

```bash
git add src/store/json-workbook.js test/json-workbook.test.js
git commit -m "feat: persist daily appointment sheets locally"
```

---

### Task 3: Booking service

**Files:**
- Create: `src/services/booking-service.js`
- Test: `test/booking-service.test.js`

**Interfaces:**
- Consumes: workbook methods from Task 2.
- Produces: `new BookingService({ workbook, now, codeFactory })`.
- Produces: `getAvailability({ date, period, limit })`, `book(input)`, `cancel(input)`, `setAvailability(input)`, and `reset(date)`.

- [ ] **Step 1: Write failing booking tests**

Inject `codeFactory: () => 'D24680'` and a fixed clock. Assert:

```js
const result = await service.book({
  date: '2026-09-28', time: '14:00', patientName: '赵阿姨', phoneLast4: '7788',
});
assert.equal(result.bookingCode, 'D24680');
assert.equal(result.status, 'booked');

await assert.rejects(
  service.book({ date: '2026-09-28', time: '12:00', patientName: '赵阿姨', phoneLast4: '7788' }),
  /不在坐诊时间/,
);

await assert.rejects(
  service.book({ date: '2026-09-28', time: '14:10', patientName: '', phoneLast4: '7788' }),
  /请输入患者称呼/,
);

await assert.rejects(
  service.book({ date: '2026-09-28', time: '14:10', patientName: '赵阿姨', phoneLast4: '88' }),
  /手机后四位/,
);
```

Also test period filtering, a five-result default limit, valid cancellation, invalid cancellation, and closing/restoring a slot.

- [ ] **Step 2: Run booking tests and confirm failure**

Run: `node --test test/booking-service.test.js`

Expected: FAIL because `BookingService` is missing.

- [ ] **Step 3: Implement validation and service responses**

Validate `YYYY-MM-DD`, ten-minute time strings, non-empty names of at most 20 characters, and exactly four phone digits. Generate codes from the unambiguous alphabet `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`; default codes contain one letter followed by five characters. Delegate atomic mutation to the workbook and return copies of stored slot objects.

- [ ] **Step 4: Run booking tests**

Run: `node --test test/booking-service.test.js`

Expected: all booking-service tests pass.

- [ ] **Step 5: Commit the booking service**

```bash
git add src/services/booking-service.js test/booking-service.test.js
git commit -m "feat: add validated booking operations"
```

---

### Task 4: Chinese intent parser and multi-turn conversation

**Files:**
- Create: `src/services/intent-parser.js`
- Create: `src/services/conversation-service.js`
- Test: `test/intent-parser.test.js`
- Test: `test/conversation-service.test.js`

**Interfaces:**
- Consumes: `dateInShanghai`, `addCalendarDays`, and `BookingService`.
- Produces: `parseIntent(message, { today }) -> ParsedIntent`.
- Produces: `new ConversationService({ bookingService, now })` and `reply({ sessionId, message })`.

- [ ] **Step 1: Write failing parser tests**

Cover exact expected objects:

```js
assert.deepEqual(parseIntent('明天下午有号吗', { today: '2026-09-27' }), {
  type: 'query', date: '2026-09-28', period: 'afternoon',
});
assert.deepEqual(parseIntent('预约明天下午2点', { today: '2026-09-27' }), {
  type: 'book', date: '2026-09-28', time: '14:00',
});
assert.deepEqual(parseIntent('预约2026-09-28 14:10', { today: '2026-09-27' }), {
  type: 'book', date: '2026-09-28', time: '14:10',
});
assert.deepEqual(parseIntent('取消预约 D24680 手机后四位7788', { today: '2026-09-27' }), {
  type: 'cancel', bookingCode: 'D24680', phoneLast4: '7788',
});
assert.deepEqual(parseIntent('你好', { today: '2026-09-27' }), { type: 'unknown' });
```

- [ ] **Step 2: Implement the deterministic parser and pass parser tests**

Normalize full-width punctuation and whitespace. Recognize today, tomorrow, explicit ISO dates, `H点`, `H点半`, `H点M分`, and `HH:MM`. Convert afternoon/evening hours 1–11 to 13–23. Intent priority is cancellation, booking, availability query, greeting, unknown.

Run: `node --test test/intent-parser.test.js`

Expected: all parser tests pass.

- [ ] **Step 3: Write failing multi-turn conversation tests**

Test this complete exchange with a fixed tomorrow date:

```js
assert.match((await chat.reply({ sessionId: 's1', message: '预约明天下午2点' })).reply, /患者称呼/);
assert.match((await chat.reply({ sessionId: 's1', message: '赵阿姨' })).reply, /手机后四位/);
const booked = await chat.reply({ sessionId: 's1', message: '7788' });
assert.match(booked.reply, /预约成功/);
assert.match(booked.reply, /D24680/);
assert.deepEqual(booked.suggestions, ['查看明天号源', '取消预约']);
```

Also test direct cancellation, unknown input, query output limited to five times, `查看更多` returning the next available times without repeating the first page, and separate state for two session IDs.

- [ ] **Step 4: Implement the conversation state machine**

Use an in-memory `Map` keyed by opaque browser-generated session IDs. States are `idle`, `awaitingName`, `awaitingPhone`, `awaitingCancelCode`, and `awaitingCancelPhone`; each session can also hold the last availability query and its next offset so `查看更多` returns the following page. Every response has this exact shape:

```js
{
  reply: '患者可见的中文回复',
  suggestions: ['快捷操作一', '快捷操作二'],
  speakText: '适合语音朗读的简短文本'
}
```

Clear pending booking state after success or any terminal error. Never echo another patient's name or phone suffix in availability responses.

- [ ] **Step 5: Run conversation tests and commit**

Run: `node --test test/intent-parser.test.js test/conversation-service.test.js`

Expected: all parser and conversation tests pass.

```bash
git add src/services/intent-parser.js src/services/conversation-service.js test/intent-parser.test.js test/conversation-service.test.js
git commit -m "feat: add appointment conversation flow"
```

---

### Task 5: Express APIs and startup seeding

**Files:**
- Create: `src/http/app.js`
- Create: `src/server.js`
- Test: `test/api.test.js`

**Interfaces:**
- Consumes: workbook, booking service, and conversation service.
- Produces: `createApp({ workbook, bookingService, conversationService, now }) -> Express`.
- Produces HTTP endpoints used by both browser pages.

- [ ] **Step 1: Write failing API tests with Supertest**

Cover:

```js
const meta = await request(app).get('/api/meta').expect(200);
assert.equal(meta.body.tomorrow, '2026-09-28');
assert.equal(meta.body.timeZone, 'Asia/Shanghai');

const slots = await request(app).get('/api/slots?date=2026-09-28').expect(200);
assert.equal(slots.body.slots.length, 63);

await request(app)
  .post('/api/chat')
  .send({ sessionId: 'browser-1', message: '明天下午有号吗' })
  .expect(200)
  .expect(({ body }) => assert.match(body.reply, /可预约/));

await request(app)
  .patch('/api/slots/2026-09-28/15:00')
  .send({ status: 'closed' })
  .expect(200);

await request(app).post('/api/reset').send({ date: '2026-09-28' }).expect(200);
```

Assert invalid request bodies return status 400 with `{ error: '中文错误信息' }` and unexpected errors return status 500 without stack traces.

- [ ] **Step 2: Run API tests and confirm failure**

Run: `node --test test/api.test.js`

Expected: FAIL because the HTTP app is missing.

- [ ] **Step 3: Implement the app and server**

Add JSON parsing with a 16 KB body limit, static serving from `public`, and these routes:

```text
GET    /api/meta
GET    /api/sheets
GET    /api/slots?date=YYYY-MM-DD
POST   /api/chat
PATCH  /api/slots/:date/:time
POST   /api/reset
```

`src/server.js` uses `data/demo-workbook.json`. When the file is absent, it calls `resetDemo(tomorrow)` once so the fictional bookings and closed slot appear; when the file already exists, it calls `ensureSheet(tomorrow)` so previous demonstration changes survive a restart. Listen on `HOST` defaulting to `0.0.0.0` and `PORT` defaulting to `4173`. Log both patient and assistant URLs without logging patient messages.

- [ ] **Step 4: Run API and full backend tests**

Run: `npm test`

Expected: all backend tests pass.

- [ ] **Step 5: Commit the web API**

```bash
git add src/http/app.js src/server.js test/api.test.js
git commit -m "feat: expose local appointment APIs"
```

---

### Task 6: Patient WeChat-style demo page

**Files:**
- Create: `public/index.html`
- Create: `public/shared.css`
- Create: `public/patient.css`
- Create: `public/patient.js`
- Test: extend `test/api.test.js`

**Interfaces:**
- Consumes: `/api/meta` and `/api/chat`.
- Produces: accessible mobile patient UI at `/`.

- [ ] **Step 1: Add a failing static-page API assertion**

```js
await request(app)
  .get('/')
  .expect(200)
  .expect('Content-Type', /html/)
  .expect(({ text }) => {
    assert.match(text, /诊所预约助手/);
    assert.match(text, /预约 Demo/);
  });
```

Run: `node --test test/api.test.js`

Expected: FAIL because the patient page is absent.

- [ ] **Step 2: Build the semantic patient page**

The HTML must contain a fixed phone-sized shell on desktop and full-width layout on small screens, a header, privacy notice, message list with `aria-live="polite"`, quick-action container, text input, send button, and user-triggered speech button. Copy must say “本页面仅演示预约，不提供诊断或用药建议，请勿输入真实病历资料”。

- [ ] **Step 3: Implement patient interaction**

Generate and persist a random session ID in `sessionStorage`. Render user and assistant bubbles using `textContent`, never `innerHTML`. Disable the composer while a request is pending. Post `{ sessionId, message }` to `/api/chat`, render returned suggestions as large tap targets, keep the latest `speakText`, and call `speechSynthesis.speak(new SpeechSynthesisUtterance(speakText))` only after the user presses the speech button.

- [ ] **Step 4: Style for older patients and verify manually**

Use a minimum 18 px body font, 48 px tap targets, high-contrast text, a WeChat-inspired green header, off-white chat background, clear focus rings, and no hover-only actions. Start the server and verify at 390 px and 1280 px viewport widths.

Run: `npm start`

Expected: `http://localhost:4173/` opens the chat page and “明天下午有号吗” returns mock times.

- [ ] **Step 5: Commit the patient page**

```bash
git add public/index.html public/shared.css public/patient.css public/patient.js test/api.test.js
git commit -m "feat: add accessible patient booking demo"
```

---

### Task 7: Assistant daily-Sheet page

**Files:**
- Create: `public/assistant.html`
- Create: `public/assistant.css`
- Create: `public/assistant.js`
- Test: extend `test/api.test.js`

**Interfaces:**
- Consumes: `/api/meta`, `/api/sheets`, `/api/slots`, `/api/slots/:date/:time`, and `/api/reset`.
- Produces: assistant UI at `/assistant.html`.

- [ ] **Step 1: Add a failing assistant-page assertion**

```js
await request(app)
  .get('/assistant.html')
  .expect(200)
  .expect(({ text }) => {
    assert.match(text, /每日排班 Sheet/);
    assert.match(text, /重置演示数据/);
  });
```

Run: `node --test test/api.test.js`

Expected: FAIL because the assistant page is absent.

- [ ] **Step 2: Build the Sheet interface**

The page must contain date tabs, summary cards for available/booked/closed counts, a responsive table with the seven approved columns, refresh status, an explicit “重置演示数据” button, and a link back to the patient page. Status labels use text and color together.

- [ ] **Step 3: Implement live updates and controls**

Load tomorrow by default, poll the active Sheet every two seconds, and pause polling while the page is hidden. Available rows expose “关闭”，closed rows expose “恢复”，and booked rows expose no status mutation. Use `window.confirm('确定恢复明天的初始演示数据吗？')` before reset. Render all values using `textContent`.

- [ ] **Step 4: Verify cross-page synchronization**

Open `/` and `/assistant.html` side by side. Book 14:00 in the patient page, verify the row becomes booked within two seconds, cancel it, then verify it returns to available. Close 15:00 from the assistant page and confirm a patient booking attempt is rejected.

- [ ] **Step 5: Commit the assistant page**

```bash
git add public/assistant.html public/assistant.css public/assistant.js test/api.test.js
git commit -m "feat: add assistant daily sheet view"
```

---

### Task 8: Documentation and final verification

**Files:**
- Create: `README.md`
- Modify: files found by verification only when required to fix a demonstrated defect.

**Interfaces:**
- Consumes: complete demo.
- Produces: reproducible handoff instructions and verified release state.

- [ ] **Step 1: Write the run and demo guide**

Document exactly:

```bash
npm install
npm start
```

List patient URL `http://localhost:4173/`, assistant URL `http://localhost:4173/assistant.html`, the seven-step manual acceptance flow from the design, local data path `data/demo-workbook.json`, and reset behavior. Explain that another phone can open `http://<电脑局域网IP>:4173/` only while it is on the same network and the computer firewall permits Node.js.

- [ ] **Step 2: Run automated verification**

Run:

```bash
npm test
npm start
```

Expected: all tests pass; server reports both demo URLs without errors.

- [ ] **Step 3: Run manual acceptance**

Perform the seven design acceptance steps. Confirm 63 rows, correct lunch exclusion, booking synchronization, duplicate rejection, invalid cancellation protection, valid cancellation, and closed-slot rejection.

- [ ] **Step 4: Inspect the final diff and runtime hygiene**

Run:

```bash
git status --short
git diff --check
git ls-files data
```

Expected: no whitespace errors and no runtime JSON file tracked.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md
git commit -m "docs: add clinic demo instructions"
```

- [ ] **Step 6: Open both pages for user review**

Open the patient page and assistant page in the Codex browser panel after the server is running, then provide the user with both URLs and the commands required to restart the Demo.
