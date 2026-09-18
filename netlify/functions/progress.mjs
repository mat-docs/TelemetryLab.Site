// POST /api/progress - opt-in course-progress relay.
//
// A learner's own GitHub Actions run of validate.yml sends one anonymous
// module_result event here. We verify the request came from such a run (GitHub
// OIDC JWT), then relay it to GA4 via the Measurement Protocol. Nothing is
// stored here, and nothing identifying is logged: the repository name and
// owner inside the token are used only for the checks below and never leave
// this function.
//
// The JWT proves "an Actions run of a validate.yml in some repo sent this". It
// does not prove the grade is genuine - a learner can edit their own workflow.
// That is fine for an opt-in counter.
//
// There is deliberately no replay store. The JWT's short exp plus the run_id
// binding bound any replay to one run for a few minutes, and an anonymous
// self-replay is not worth infrastructure.

import { createRemoteJWKSet, jwtVerify } from "jose";

const ISSUER = "https://token.actions.githubusercontent.com";
const AUDIENCE = "atlas-telemetry-lab";
const MAX_BODY_BYTES = 4096;
const COURSES = ["foundations"];
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DIGITS_RE = /^[0-9]+$/;
const GA4_TIMEOUT_MS = 5000;

// Module scope: the JWKS is fetched once and cached per function instance.
const jwks = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`));

export const config = { path: "/api/progress" };

export default async (req) => {
  try {
    return await handle(req);
  } catch {
    return json(500, { error: "internal" });
  }
};

async function handle(req) {
  if (req.method !== "POST") return json(405, { error: "method not allowed" });

  const length = Number(req.headers.get("content-length") ?? 0);
  if (length > MAX_BODY_BYTES) return json(413, { error: "body too large" });

  let body;
  try {
    body = await req.json();
  } catch {
    return json(400, { error: "body is not JSON" });
  }
  const badField = validate(body);
  if (badField) return json(400, { error: `invalid field: ${badField}` });

  const token = bearer(req);
  if (!token) return json(401, { error: "unauthorized" });

  const claims = await authenticate(token, req);
  if (!claims || !claimsMatch(claims, body)) return json(401, { error: "unauthorized" });

  if (isDenied(claims.repository_owner)) return json(403, { error: "internal" });

  return relay(body);
}

// --- request validation ------------------------------------------------------

function validate(body) {
  if (body === null || typeof body !== "object" || Array.isArray(body)) return "body";
  if (body.v !== 1) return "v";
  if (body.event !== "module_result") return "event";
  if (!COURSES.includes(body.course)) return "course";
  if (!isIntInRange(body.module, 1, 20)) return "module";
  if (typeof body.passed !== "boolean") return "passed";
  if (typeof body.learner_id !== "string" || !UUID_RE.test(body.learner_id)) return "learner_id";
  if (typeof body.run_id !== "string" || !DIGITS_RE.test(body.run_id)) return "run_id";
  if (typeof body.run_attempt !== "string" || !DIGITS_RE.test(body.run_attempt)) return "run_attempt";
  if (typeof body.template_version !== "string" || body.template_version.length > 40) return "template_version";
  if (!isIntInRange(body.total_modules, 1, 20)) return "total_modules";
  return null;
}

function isIntInRange(value, min, max) {
  return Number.isInteger(value) && value >= min && value <= max;
}

// --- auth ---------------------------------------------------------------------

function bearer(req) {
  const header = req.headers.get("authorization") ?? "";
  const match = /^Bearer\s+(\S+)$/i.exec(header);
  return match ? match[1] : null;
}

// Returns the token claims, or null if the token is not acceptable.
async function authenticate(token, req) {
  // Dev bypass: only under `netlify dev` with an explicit local secret. Never
  // active in a deploy, where NETLIFY_DEV is unset.
  const devSecret = process.env.DEV_BYPASS_SECRET;
  if (process.env.NETLIFY_DEV === "true" && devSecret) {
    if (token !== `dev:${devSecret}`) return null;
    try {
      return JSON.parse(req.headers.get("x-dev-claims") ?? "");
    } catch {
      return null;
    }
  }

  try {
    const { payload } = await jwtVerify(token, jwks, { issuer: ISSUER, audience: AUDIENCE });
    return payload;
  } catch {
    // Signature, issuer, audience or expiry failed. Do not log the token.
    console.log("progress: jwt verification failed");
    return null;
  }
}

function claimsMatch(payload, body) {
  if (payload === null || typeof payload !== "object") return false;
  if (payload.event_name !== "pull_request") return false;
  if (payload.workflow !== "validate") return false;
  if (typeof payload.repository !== "string") return false;
  if (
    typeof payload.job_workflow_ref !== "string" ||
    !payload.job_workflow_ref.startsWith(`${payload.repository}/.github/workflows/validate.yml@`)
  ) {
    return false;
  }
  if (String(payload.run_id) !== body.run_id) return false;
  return true;
}

// Our own and test-account repos never pollute the numbers. Set only in
// Netlify's production context so deploy previews accept test events.
function isDenied(owner) {
  if (typeof owner !== "string") return false;
  const denied = (process.env.PROGRESS_DENY_OWNERS ?? "")
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  return denied.includes(owner.toLowerCase());
}

// --- GA4 relay ----------------------------------------------------------------

async function relay(body) {
  const measurementId = process.env.GA4_MEASUREMENT_ID;
  const apiSecret = process.env.GA4_API_SECRET;
  if (!measurementId || !apiSecret) return json(503, { error: "analytics not configured" });

  const debug = process.env.GA4_DEBUG === "1";
  const url = new URL(`https://www.google-analytics.com/${debug ? "debug/" : ""}mp/collect`);
  url.searchParams.set("measurement_id", measurementId);
  url.searchParams.set("api_secret", apiSecret);

  const params = {
    course: body.course,
    module: body.module,
    result: body.passed ? "pass" : "fail",
    template_version: body.template_version,
    session_id: body.run_id,
    engagement_time_msec: 100,
  };
  const events = [{ name: "module_result", params }];
  if (body.passed && body.module === body.total_modules) {
    events.push({ name: "course_complete", params: { ...params } });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), GA4_TIMEOUT_MS);
  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ client_id: body.learner_id, events }),
      signal: controller.signal,
    });
  } catch {
    console.log("progress: ga4 relay network error");
    return json(502, { error: "relay failed" });
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    console.log(`progress: ga4 relay status ${res.status}`);
    return json(502, { error: "relay failed" });
  }

  if (debug) {
    let validation = {};
    try {
      validation = await res.json();
    } catch {
      // The debug endpoint always returns JSON; an empty object is fine otherwise.
    }
    return json(200, validation);
  }

  return new Response(null, { status: 204 });
}

// --- helpers ------------------------------------------------------------------

function json(status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}
