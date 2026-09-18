// Run with: npm test   (node --test "tests/**/*.test.mjs"). Lives outside
// netlify/functions/ because Netlify deploys every file in that directory
// as an endpoint.
import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

process.env.NETLIFY_DEV = "true";
process.env.DEV_BYPASS_SECRET = "t";

const handler = (await import("../netlify/functions/progress.mjs")).default;

const URL_ = "http://localhost/api/progress";
const LEARNER = "123e4567-e89b-42d3-a456-426614174000";

const goodBody = () => ({
  v: 1,
  event: "module_result",
  course: "foundations",
  module: 1,
  passed: true,
  learner_id: LEARNER,
  template_version: "2026.09",
  run_id: "1234",
  run_attempt: "1",
  total_modules: 4,
});

const goodClaims = (overrides = {}) => ({
  event_name: "pull_request",
  workflow: "validate",
  repository: "someone/lab-copy",
  repository_owner: "someone",
  job_workflow_ref: "someone/lab-copy/.github/workflows/validate.yml@refs/heads/module-1",
  run_id: 1234,
  ...overrides,
});

function post(body, { auth = "Bearer dev:t", claims = goodClaims(), headers = {} } = {}) {
  const h = { "content-type": "application/json", ...headers };
  if (auth !== null) h.authorization = auth;
  if (claims !== null) h["x-dev-claims"] = JSON.stringify(claims);
  const raw = typeof body === "string" ? body : JSON.stringify(body);
  if (!("content-length" in h)) h["content-length"] = String(Buffer.byteLength(raw));
  return handler(new Request(URL_, { method: "POST", headers: h, body: raw }));
}

// GA4 fetch stub -------------------------------------------------------------
let ga4Calls;
let ga4Status;
const realFetch = globalThis.fetch;

beforeEach(() => {
  ga4Calls = [];
  ga4Status = 204;
  process.env.GA4_MEASUREMENT_ID = "G-TEST";
  process.env.GA4_API_SECRET = "secret";
  delete process.env.GA4_DEBUG;
  delete process.env.PROGRESS_DENY_OWNERS;
  globalThis.fetch = async (url, init) => {
    ga4Calls.push({ url: String(url), init, body: JSON.parse(init.body) });
    return new Response(null, { status: ga4Status });
  };
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

async function errorOf(res) {
  return (await res.json()).error;
}

// Guards ------------------------------------------------------------------------

test("405 on non-POST", async () => {
  const res = await handler(new Request(URL_, { method: "GET" }));
  assert.equal(res.status, 405);
});

test("413 when content-length exceeds 4096", async () => {
  const res = await post(goodBody(), { headers: { "content-length": "5000" } });
  assert.equal(res.status, 413);
});

test("400 when body is not JSON", async () => {
  const res = await post("{not json");
  assert.equal(res.status, 400);
  assert.match(await errorOf(res), /JSON/);
});

test("400 names a bad module", async () => {
  const res = await post({ ...goodBody(), module: 0 });
  assert.equal(res.status, 400);
  assert.equal(await errorOf(res), "invalid field: module");
});

test("400 names a bad learner_id", async () => {
  const res = await post({ ...goodBody(), learner_id: "not-a-uuid" });
  assert.equal(res.status, 400);
  assert.equal(await errorOf(res), "invalid field: learner_id");
});

// Auth --------------------------------------------------------------------------

test("401 when bearer is missing", async () => {
  const res = await post(goodBody(), { auth: null });
  assert.equal(res.status, 401);
  assert.equal(ga4Calls.length, 0);
});

test("401 on wrong dev secret", async () => {
  const res = await post(goodBody(), { auth: "Bearer dev:wrong" });
  assert.equal(res.status, 401);
});

test("401 when workflow claim is not validate", async () => {
  const res = await post(goodBody(), { claims: goodClaims({ workflow: "deploy" }) });
  assert.equal(res.status, 401);
});

test("401 when run_id claim does not match body", async () => {
  const res = await post(goodBody(), { claims: goodClaims({ run_id: 999 }) });
  assert.equal(res.status, 401);
});

// Deny-list ---------------------------------------------------------------------

test("403 for a deny-listed owner (case-insensitive, trimmed)", async () => {
  process.env.PROGRESS_DENY_OWNERS = " Motionapplied , SOMEONE ";
  const res = await post(goodBody());
  assert.equal(res.status, 403);
  assert.equal(await errorOf(res), "internal");
  assert.equal(ga4Calls.length, 0);
});

// Relay -------------------------------------------------------------------------

test("503 when GA4 env is missing", async () => {
  delete process.env.GA4_API_SECRET;
  const res = await post(goodBody());
  assert.equal(res.status, 503);
  assert.equal(await errorOf(res), "analytics not configured");
});

test("204 happy path relays an anonymous module_result", async () => {
  const res = await post(goodBody());
  assert.equal(res.status, 204);
  assert.equal(ga4Calls.length, 1);

  const { url, init, body } = ga4Calls[0];
  assert.match(url, /^https:\/\/www\.google-analytics\.com\/mp\/collect\?/);
  assert.match(url, /measurement_id=G-TEST/);
  assert.match(url, /api_secret=secret/);
  assert.equal(init.method, "POST");

  assert.equal(body.client_id, LEARNER);
  assert.equal(body.events.length, 1);
  assert.equal(body.events[0].name, "module_result");
  assert.deepEqual(body.events[0].params, {
    course: "foundations",
    module: 1,
    result: "pass",
    template_version: "2026.09",
    session_id: "1234",
    engagement_time_msec: 100,
  });

  const raw = init.body;
  assert.doesNotMatch(raw, /lab-copy/);
  assert.doesNotMatch(raw, /someone/);
  assert.doesNotMatch(raw, /repository/);
  assert.doesNotMatch(raw, /owner/);
});

test("course_complete is emitted when the final module passes", async () => {
  const res = await post({ ...goodBody(), module: 4, total_modules: 4, passed: true });
  assert.equal(res.status, 204);
  const names = ga4Calls[0].body.events.map((e) => e.name);
  assert.deepEqual(names, ["module_result", "course_complete"]);
  assert.equal(ga4Calls[0].body.events[1].params.result, "pass");
});

test("course_complete is not emitted when the final module fails", async () => {
  await post({ ...goodBody(), module: 4, total_modules: 4, passed: false });
  const names = ga4Calls[0].body.events.map((e) => e.name);
  assert.deepEqual(names, ["module_result"]);
  assert.equal(ga4Calls[0].body.events[0].params.result, "fail");
});

test("502 when GA4 returns a non-2xx", async () => {
  ga4Status = 500;
  const res = await post(goodBody());
  assert.equal(res.status, 502);
  assert.equal(await errorOf(res), "relay failed");
});
