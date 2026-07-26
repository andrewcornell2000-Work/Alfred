---
name: web-release-hardening
description: Run an evidence-based pre-launch or release-readiness gate for web applications across environment configuration, managed services, tests, browser flows, deployment health, and handoff. Use when the user asks for a launch audit, production readiness review, release hardening, go-live check, or final pre-deploy validation.
---

# Web Release Hardening

Use this workflow in the current agent. It coordinates existing Supabase, Vercel, browser,
testing, and handoff capabilities; it does not replace their domain skills.

## Safety boundary

- Start read-only. Do not deploy, migrate, rotate secrets, merge, or change production data
  unless the user explicitly asks.
- Record environment variable names and presence only. Never print values.
- Distinguish local, preview, and production evidence. A local mock does not prove production.
- Stop on a P0 finding instead of hiding it behind a passing build.

## 1. Establish the release contract

1. Name the target: preview, staging, or production.
2. Identify the release commit/branch and whether the working tree is clean.
3. Read project guidance and use Graphify before broad code search when a graph exists.
4. Discover actual scripts and services from manifests; do not assume framework commands.
5. List critical user journeys and irreversible operations (billing, email, OAuth, writes).

Output a short checklist of required evidence before running expensive tests.

## 2. Check environment and service parity

Compare required variable **names** across local, hosting, and managed services. Classify each:

- present and target-appropriate
- missing
- points at the wrong environment
- intentionally local/mock only

Use the Supabase and Vercel skills/MCPs when those services are present. Check, as applicable:

- database migrations and advisors
- authentication redirect URLs and provider configuration
- storage policies and public/private boundaries
- webhook destinations and signing-secret presence
- deployment project, branch, domain, and runtime configuration

Do not infer parity from similarly named variables.

## 3. Run the repository's validation ladder

Use commands defined by the repository, ordered cheapest to most expensive:

1. typecheck or compile check
2. lint
3. focused unit/integration tests
4. production build
5. browser smoke tests
6. full end-to-end flows when credentials and target safety are confirmed

For each command record: exact command, exit result, and whether failures are new or
pre-existing. Do not add dependencies or rewrite test configuration just to make the gate run.

## 4. Verify critical browser journeys

Run against the intended target and label mock versus live integrations. Prefer a small,
release-specific matrix:

- public navigation and redirects
- sign-up/sign-in/sign-out and protected-route behavior
- primary create/edit/save flow
- billing or entitlement boundary without making a real charge
- provider/OAuth readiness without publishing real content
- error recovery, refresh, and retry paths

Capture console/network failures and screenshots only when they provide evidence. Never use
production credentials in generated test artifacts.

## 5. Inspect deployment health

For the release commit, verify:

- build completed for the expected commit and environment
- no material build warnings were ignored
- runtime logs contain no new critical errors
- domains and redirects resolve as intended
- health endpoints and critical server routes respond

A green deployment status is necessary but not sufficient; connect it to browser and service
evidence.

## 6. Produce the release gate

Classify findings:

- **P0 — NO-GO:** security, data loss, broken critical journey, wrong environment, or unsafe
  production mutation
- **P1 — FIX BEFORE RELEASE:** material regression with a known workaround or limited scope
- **P2 — FOLLOW-UP:** non-blocking quality, observability, or maintainability issue

Return:

1. **Verdict:** GO, CONDITIONAL GO, or NO-GO
2. **Target and commit**
3. **Evidence run:** commands, browser flows, service/deployment checks
4. **Findings:** severity, proof, owner action
5. **Residual risk:** what was not tested and why
6. **Next step:** the smallest action that changes the verdict

Only create a `HANDOFF.md` when requested; use `agent-handoff.md` and include current release
evidence without secrets.

## Anti-patterns

- Spawning a fan-out of overlapping audit agents
- Treating `npm run build` as a complete release audit
- Testing mocks and reporting live integrations as verified
- Deploying first to discover whether configuration is correct
- Dumping environment values, tokens, private data, or full logs into chat
