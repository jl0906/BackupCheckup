"use strict";

import fs from "node:fs";
import vm from "node:vm";

class FakeNode {
  constructor(tag = "div") {
    this.tagName = String(tag).toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.style = {};
    this.textContent = "";
    this.scrollLeft = 0;
    this.scrollTop = 0;
    this.scrollHeight = 0;
    this.clientHeight = 0;
    this._html = "";
    this.classList = { add() {}, remove() {}, contains() { return false; } };
  }

  set innerHTML(value) { this._html = String(value); }
  get innerHTML() { return this._html; }
  get firstElementChild() { return this.children[0] || null; }

  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return name in this.attributes ? this.attributes[name] : null; }
  hasAttribute(name) { return name in this.attributes; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener() {}
  removeEventListener() {}
  insertBefore(node) { this.children.unshift(node); return node; }
  appendChild(node) { this.children.push(node); return node; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  scrollIntoView() {}
  scrollTo() {}
  focus() {}
  click() {}
}

class FakeCard extends FakeNode {
  constructor(host, key, html) {
    super("article");
    this.host = host;
    this.key = key;
    this.listeners = 0;
    this.bindCalls = 0;
    this._html = html;
  }

  querySelectorAll(selector) {
    this.bindCalls += 1;
    return super.querySelectorAll(selector);
  }

  set outerHTML(value) {
    this.host.replaceCard(this.key, String(value));
  }

  addEventListener() { this.listeners += 1; }
}

class FakeCardHost extends FakeNode {
  constructor() {
    super();
    this.cards = new Map();
    this.replacements = [];
  }

  set innerHTML(value) {
    this._html = String(value);
    this.cards = new Map();
    for (const match of this._html.matchAll(/data-card="([^"]+)"/g)) {
      this.cards.set(match[1], new FakeCard(this, match[1], this._html));
    }
  }

  get innerHTML() { return this._html; }

  replaceCard(key, html) {
    this.replacements.push(key);
    this.cards.set(key, new FakeCard(this, key, html));
    this._html = this._html.replace(
      new RegExp(`<[^>]*data-card="${key}"[\\s\\S]*?$`),
      html,
    );
  }

  querySelector(selector) {
    const match = /^\[data-card="([^"]+)"\]$/.exec(selector);
    if (match) return this.cards.get(match[1]) || null;
    return null;
  }

  querySelectorAll(selector) {
    this.bindCalls = (this.bindCalls || 0) + 1;
    return super.querySelectorAll(selector);
  }
}

class FakeShadowRoot extends FakeNode {
  constructor() {
    super();
    this.cards = new FakeCardHost();
    this.header = new FakeNode("header");
    this.activeElement = null;
  }

  querySelector(selector) {
    if (selector === "[data-cards]") return this.cards;
    if (selector === "header") return this.header;
    return null;
  }

  querySelectorAll() { return []; }
}

class FakeHTMLElement extends FakeNode {
  constructor() {
    super();
    this.isConnected = true;
    this.parentElement = null;
  }

  attachShadow() {
    this.shadowRoot = new FakeShadowRoot();
    return this.shadowRoot;
  }

  toggleAttribute(name, force) {
    if (force) this.attributes[name] = "";
    else delete this.attributes[name];
  }

  dispatchEvent() {}
  getRootNode() { return null; }
}

let PanelClass;
const context = {
  Blob,
  URL,
  HTMLElement: FakeHTMLElement,
  CustomEvent: class {},
  customElements: {
    get() { return undefined; },
    define(_name, constructor) { PanelClass = constructor; },
  },
  document: {
    documentElement: { lang: "en" },
    scrollingElement: null,
    createElement(tag) { return new FakeNode(tag); },
  },
  window: { confirm() { return true; } },
  requestAnimationFrame(callback) { callback(); },
  console,
  setTimeout,
  clearTimeout,
  setInterval() { return 1; },
  clearInterval() {},
};

vm.createContext(context);
const panelUrl = new URL(
  "../../custom_components/backup_checkup/frontend/backup-checkup-panel.js",
  import.meta.url,
);
const source = fs.readFileSync(panelUrl, "utf8");
vm.runInContext(source, context, { filename: "backup-checkup-panel.js" });
if (!PanelClass) throw new Error("Panel custom element was not registered");

const VERIFICATION_STEPS = [
  "prepare", "staging", "download", "archive_scan",
  "nested_archives", "database_check", "evaluate", "cleanup",
];
const RUNTIME_STEPS = [
  "runtime_prepare", "runtime_upload", "runtime_restore",
  "runtime_boot", "runtime_probe", "runtime_cleanup", "runtime_complete",
];

function steps(keys, running, overrides = {}) {
  return keys.map((key) => ({
    key,
    label_key: `step_${key}`,
    weight: 10,
    state: overrides[key]?.state
      ?? (keys.indexOf(key) < keys.indexOf(running) ? "passed" : key === running ? "running" : "pending"),
    determinate: overrides[key]?.determinate ?? true,
    percent: overrides[key]?.percent ?? null,
    done: overrides[key]?.done ?? null,
    total: overrides[key]?.total ?? null,
    unit: overrides[key]?.unit ?? null,
    started_at: null,
    finished_at: null,
    heartbeat_at: overrides[key]?.heartbeat_at ?? null,
    detail: overrides[key]?.detail ?? null,
  }));
}

const NOW = Date.now();
// Pin the panel's clock to the fixture time. The rendered durations are
// rounded, so a slow machine would otherwise show 1:43 instead of 1:42.
vm.runInContext(`Date.now = () => ${NOW};`, context);
const ago = (seconds) => new Date(NOW - seconds * 1000).toISOString();

function job(name, status, running, overall, stepList, extra = {}) {
  return {
    job: name,
    status,
    running: status === "running",
    current_step: running,
    steps: stepList,
    overall_percent: overall,
    progress_percent: overall,
    determinate: stepList.find((step) => step.key === running)?.determinate ?? false,
    started_at: ago(102),
    updated_at: ago(2),
    finished_at: null,
    heartbeat_at: ago(2),
    error_code: null,
    source: "integration",
    runner_version: null,
    backup_reference: "reference",
    duration_seconds: 62,
    stage: running,
    stages: Object.fromEntries(stepList.map((step) => [step.key, step.state])),
    ...extra,
  };
}

const IDLE_VERIFICATION = job(
  "verification", "passed", "cleanup", 100, steps(VERIFICATION_STEPS, "cleanup")
);
const RUNNING_VERIFICATION = job(
  "verification", "running", "archive_scan", 55,
  steps(VERIFICATION_STEPS, "archive_scan", {
    archive_scan: {
      state: "running", determinate: true, percent: 50,
      done: 2_300_000_000, total: 5_100_000_000, unit: "bytes",
      heartbeat_at: ago(2),
    },
  })
);
const RUNNING_RUNTIME = job(
  "runtime_test", "running", "runtime_boot", 58,
  steps(RUNTIME_STEPS, "runtime_boot", {
    runtime_boot: {
      state: "running", determinate: false,
      heartbeat_at: ago(2),
    },
  }),
  { source: "runner", runner_version: "3" }
);
const STALE_RUNTIME = job(
  "runtime_test", "running", "runtime_probe", 58,
  steps(RUNTIME_STEPS, "runtime_probe", {
    runtime_probe: { state: "running", determinate: false, heartbeat_at: ago(200) },
  }),
  { source: "runner", runner_version: "3", heartbeat_at: ago(200) }
);
const NOT_STARTED_RUNTIME = job(
  "runtime_test", "not_started", null, 0,
  steps(RUNTIME_STEPS, null),
  { error_code: "runner_unavailable", runner_reachable: false, runner_configured: true }
);

function buildHass(simulation, runtime) {
  return {
    states: {
      "sensor.backup_checkup_status": {
        state: "ok",
        last_updated: "2026-01-01T10:00:00+00:00",
        attributes: {
          checked_at: "2026-01-01T10:00:00+00:00",
          active_problems: [],
          problem: false,
        },
      },
      "sensor.backup_checkup_health_score": {
        state: "94",
        attributes: { component_deductions: { integrity: 6 } },
      },
      "sensor.backup_checkup_stored_backups": {
        state: "7",
        attributes: {
          agents: [
            { agent_id: "backup.local", storage_name: "Local", backup_count: 7 },
          ],
        },
      },
      "sensor.backup_checkup_latest_backup_age": { state: "1", attributes: {} },
      "sensor.backup_checkup_latest_backup_size": { state: "2.4", attributes: {} },
      "sensor.backup_checkup_integrity_status": {
        state: "valid",
        attributes: {
          checked_at: "2026-01-01T09:00:00+00:00",
          duration_seconds: 120,
          verified_size_mb: 2400,
          file_count: 1200,
          warnings: [],
        },
      },
      "sensor.backup_checkup_recovery_readiness": {
        state: "88",
        attributes: {
          status: "ready",
          recommendation: "none",
          evidence: { level: "structurally_verified" },
          restore_simulation: simulation,
          runtime_test: runtime,
          checks: {},
          preparedness: { checklist: {}, dependencies: {} },
          recovery_plan: {},
          open_risks: [],
          adaptive_policy: { presentation: "balanced" },
        },
      },
      "sensor.backup_checkup_recovery_status": { state: "ready", attributes: {} },
      "sensor.backup_checkup_recovery_recommendation": { state: "none", attributes: {} },
      "sensor.backup_checkup_recommendation": { state: "none", attributes: {} },
      "sensor.backup_checkup_activity_log": {
        state: "5",
        attributes: { enabled: true, entries: [], persistent: false },
      },
      "binary_sensor.backup_checkup_problem": { state: "off", attributes: {} },
    },
    locale: { language: "en" },
    user: { is_admin: true },
    localize() { return undefined; },
    formatEntityState(state) { return state ? String(state.state) : "unknown"; },
    async callService() {},
    async callWS() { return null; },
  };
}

function mount(simulation, runtime, { narrow = false, language = "en" } = {}) {
  const panel = new PanelClass();
  panel.panel = { config: { entry_id: "probe", entities: {} } };
  const hass = buildHass(simulation, runtime);
  hass.locale.language = language;
  panel.hass = hass;
  if (narrow) panel.narrow = true;
  panel.connectedCallback();
  return panel;
}

function rendered(panel) {
  return `${panel.shadowRoot.innerHTML}\n${panel.shadowRoot.cards.innerHTML}`;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function assertClean(html, label) {
  for (const marker of ["undefined", "[object Object]", "NaN%"]) {
    assert(!html.includes(marker), `${label} contains ${marker}`);
  }
}

// (a) A finished overview renders the three status cards.
const idle = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME);
const idleHtml = rendered(idle);
assert(idleHtml.includes("Backup overview"), "Panel did not render its overview");
for (const card of ["backups", "integrity", "runner", "problems", "storage"]) {
  assert(idleHtml.includes(`data-card="${card}"`), `Overview is missing the ${card} card`);
}
assertClean(idleHtml, "overview");

// (b) A running verification renders a determinate live block.
const running = mount(RUNNING_VERIFICATION, NOT_STARTED_RUNTIME);
const runningHtml = rendered(running);
assert(runningHtml.includes('data-progress="verification"'), "Missing live verification block");
assert(runningHtml.includes('aria-valuenow="55"'), "Live block does not show the measured percentage");
assert(runningHtml.includes('aria-busy="false"'), "A determinate step must not be marked busy");
assert(runningHtml.includes("Read archive"), "The current step label is missing");
assert(runningHtml.includes("2.3 GB"), "The measured byte counters are missing");
assert(runningHtml.includes("running for 1:42"), "The runtime is not shown");
assert(runningHtml.includes("sign of life 2 s"), "The heartbeat is not shown");
assert(!runningHtml.includes("progress-block warning"), "A fresh heartbeat must not warn");
assertClean(runningHtml, "running verification");

// (c) A running runtime test renders an indeterminate live block.
const runtime = mount(IDLE_VERIFICATION, RUNNING_RUNTIME);
const runtimeHtml = rendered(runtime);
assert(runtimeHtml.includes('data-progress="runtime_test"'), "Missing live runtime block");
assert(runtimeHtml.includes("progress-bar indeterminate"), "Indeterminate step must pulse");
assert(runtimeHtml.includes('aria-busy="true"'), "Indeterminate steps must be marked busy");
assert(
  runtimeHtml.includes("This step reports no measurable progress."),
  "The indeterminate hint is missing",
);
assert(!runtimeHtml.includes('aria-valuenow="100"'), "A running test must not report 100 %");
assertClean(runtimeHtml, "running runtime test");

// (c2) A silent runner is called out instead of pretending to be alive.
const stale = mount(IDLE_VERIFICATION, STALE_RUNTIME);
const staleHtml = rendered(stale);
assert(staleHtml.includes("progress-block danger"), "A long silence must be marked red");
assert(staleHtml.includes("no response for"), "A long silence must be named");
assertClean(staleHtml, "stale runtime test");

// (d) not_started never contradicts itself and never fills the bar.
const notStarted = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME);
const notStartedHtml = rendered(notStarted);
assert(
  notStartedHtml.includes("The runner was not reachable, so the test was not started."),
  "The not_started explanation is missing",
);
assert(
  notStartedHtml.includes("The Runtime Runner add-on did not answer."),
  "The runner error code is not translated",
);
assertClean(notStartedHtml, "not started");

// (e) A narrow layout offers a way into the Home Assistant sidebar.
const narrow = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME, { narrow: true });
assert(narrow.hasAttribute("narrow"), "The narrow attribute is not reflected");
const menu = narrow.shadowRoot.header.children.find((child) =>
  child.dataset.menu !== undefined,
);
assert(Boolean(menu), "Narrow layouts must render a menu button");
assert(
  menu.tagName === "HA-MENU-BUTTON" || menu.innerHTML.includes("mdi:menu"),
  "The menu fallback must show a menu icon",
);
assertClean(rendered(narrow), "narrow overview");

// (f) German renders the same structure without leaking placeholders.
const german = mount(RUNNING_VERIFICATION, RUNNING_RUNTIME, { language: "de" });
const germanHtml = rendered(german);
assert(germanHtml.includes("Archiv lesen"), "German step labels are missing");
assertClean(germanHtml, "german overview");

// (g) A state update replaces only the card whose model really changed.
const targeted = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME);
const host = targeted.shadowRoot.cards;
const before = new Map(host.cards);
host.replacements.length = 0;
const hostBindCalls = host.bindCalls || 0;
targeted.hass = buildHass(RUNNING_VERIFICATION, NOT_STARTED_RUNTIME);
assert(
  host.replacements.includes("integrity"),
  `The changed card must be replaced, replaced: ${host.replacements}`,
);
for (const key of ["hero", "backups", "runner", "problems", "storage"]) {
  assert(
    !host.replacements.includes(key),
    `The ${key} card must not be replaced by a progress update`,
  );
  assert(
    host.cards.get(key) === before.get(key),
    `The ${key} card node must survive a progress update`,
  );
}
assert(
  host.cards.get("integrity") !== before.get("integrity"),
  "The integrity card node must be replaced",
);
assert(
  hostBindCalls === (host.bindCalls || 0),
  "A targeted update must not rebind every card of the view",
);
assert(
  host.cards.get("integrity").bindCalls > 0,
  "The replaced card must be bound again",
);

// (h) A skipped verification names the backup-manager state that caused it.
const skippedRequest = {
  action: "integrity_check_request",
  outcome: "skipped",
  details: {
    reason: "backup_in_progress",
    source: "simulation",
    manager_state: "create_backup",
  },
};
for (const [language, label] of [
  ["en", "Backup manager state"],
  ["de", "Zustand des Backup-Managers"],
  ["sv", "Backup manager state"],
]) {
  const logPanel = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME, { language });
  const details = logPanel._activityDetails(skippedRequest, logPanel._text());
  assert(
    details.includes(`${label}: create_backup`),
    `The ${language} log entry does not show the manager state: ${details}`,
  );
  assertClean(details, `${language} skipped verification details`);
}

// (i) A passed runtime test never shows a reason line; runner codes stay readable.
for (const language of ["en", "de", "sv"]) {
  const journal = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME, { language });
  const text = journal._text();
  const reasonLabel = text.detailLabels.error_code;
  for (const details of [
    { status: "passed" },
    { status: "passed", error_code: "none" },
    { status: "passed", error_code: "" },
    { status: "passed", error_code: null },
  ]) {
    const line = journal._activityDetails(
      { action: "runtime_test", outcome: "completed", details },
      text,
    );
    assert(
      !line.includes(reasonLabel) && !line.includes(text.unknownError),
      `A passed ${language} runtime test shows a reason line: ${line}`,
    );
    assert(line.includes("passed"), `The ${language} status is missing: ${line}`);
    assertClean(line, `${language} passed runtime test`);
  }
  const completedWithCode = journal._activityDetails(
    { action: "runtime_test", outcome: "completed", details: { error_code: "runner_timeout" } },
    text,
  );
  assert(
    completedWithCode.includes("Runner timeout")
      && !completedWithCode.includes(text.recovery.runnerErrors.runner_timeout),
    `A completed ${language} entry must not render an error text: ${completedWithCode}`,
  );
  const translated = text.recovery.runnerErrors.runner_unsupported_archive_member;
  assert(Boolean(translated), `${language} lacks the runner 3 link message`);
  for (const code of ["runner_unsupported_archive_member", "unsupported_archive_member"]) {
    const failed = { action: "runtime_test", outcome: "failed", details: { status: "failed", error_code: code } };
    const line = journal._activityDetails(failed, text);
    assert(line.includes(translated), `${language} ${code} is not translated: ${line}`);
    assert(
      journal._activityAdvice(failed, text).includes(translated),
      `${language} ${code} advice is not translated`,
    );
  }
  const unknown = journal._activityDetails(
    { action: "runtime_test", outcome: "failed", details: { error_code: "runner_xyz_abc" } },
    text,
  );
  assert(
    unknown.includes("Runner xyz abc") && !unknown.includes(text.unknownError),
    `An unknown ${language} code must be shown as readable text: ${unknown}`,
  );
  assert(
    journal._friendlyError("", text) === text.unknownError,
    "A missing code keeps the generic message",
  );
  const warnings = journal._warningSummary(
    ["archive_links_unsafe", "archive_members_skipped", "checksum_changed"],
    text,
  );
  assert(
    warnings.startsWith("3 · ")
      && warnings.includes(text.recovery.integrityWarningLabels.archive_links_unsafe)
      && warnings.includes(text.recovery.integrityWarningLabels.archive_members_skipped)
      && warnings.includes("Checksum changed"),
    `The ${language} integrity warnings are not named: ${warnings}`,
  );
  assert(journal._warningSummary([], text) === "0", "No warnings must render as 0");
}
// A rejected backup copy carries the status code and the internal rule code.
// Both lines need their own label, and the two documented rule codes are
// translated while every other code stays readable text.
const rejectedCopy = (reason) => ({
  action: "backup_extract",
  outcome: "failed",
  level: "warning",
  details: { error_code: "archive_invalid", reason },
});
for (const [language, folders, missing] of [
  [
    "en",
    "The backup metadata lists a folder name that is not supported.",
    "The backup contains no metadata file; it is incomplete or was interrupted.",
  ],
  [
    "de",
    "Die Backup-Metadaten enthalten einen nicht unterstützten Ordnernamen.",
    "Das Backup enthält keine Metadaten-Datei; es ist unvollständig oder wurde abgebrochen.",
  ],
]) {
  const journal = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME, { language });
  const text = journal._text();
  assert(
    text.detailLabels.error_code !== text.detailLabels.reason,
    `The ${language} live log labels error_code and reason identically`,
  );
  const foldersLine = journal._activityDetails(
    rejectedCopy("backup_metadata_folders_invalid"), text,
  );
  assert(
    foldersLine
      === `${text.detailLabels.error_code}: Archive invalid · ${text.detailLabels.reason}: ${folders}`,
    `The ${language} rejected copy is not explained: ${foldersLine}`,
  );
  assert(
    journal._activityDetails(rejectedCopy("backup_metadata_missing"), text).endsWith(missing),
    `The ${language} missing metadata reason is not translated`,
  );
  assert(
    journal._activityDetails(rejectedCopy("database_path_invalid"), text)
      .endsWith(`${text.detailLabels.reason}: Database path invalid`),
    `An untranslated ${language} rule code must stay readable text`,
  );
}
for (const language of ["da", "es", "fr", "it", "nl", "pl", "sv"]) {
  const labels = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME, { language })._text().detailLabels;
  assert(
    labels.error_code !== labels.reason,
    `The ${language} live log labels error_code and reason identically`,
  );
}
const englishText = mount(IDLE_VERIFICATION, NOT_STARTED_RUNTIME)._text();
assert(
  englishText.recovery.runnerErrors.runner_unsupported_archive_member
    === "Backup contains link entries; update the Runtime Runner to version 4.",
  "The runner 3 link message changed",
);
assert(
  englishText.recovery.integrityWarningLabels.archive_links_unsafe === "Unsafe links skipped",
  "The unsafe link warning label is missing",
);

console.log("Frontend runtime render passed");
