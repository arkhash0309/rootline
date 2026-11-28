# Rootline Implementation Plan — Week 6: Console and End-to-End Test

> **For agentic workers:** Execute this week with the swarm protocol in `2026-11-26-rootline-00-overview.md` §7: the Haiku 5.5 coordinator runs the stages in the **Execution schedule** below, dispatching Sonnet 5.5 implementers (high effort, one worktree per task in parallel stages), Opus 5.5 reviewers (high effort) and, when re-planning is needed, the Opus 5.5 planner (high effort) — `CLAUDE.md` → "Agent models and roles". Within each task, follow superpowers:subagent-driven-development's discipline (implement → spec-compliance review → code-quality review). Steps use checkbox (`- [ ]`) syntax for tracking. For UI work also load `frontend-design:frontend-design` and, for charts, the `dataviz` skill (UI-040).

**Goal:** A Next.js console with a secure BFF (PKCE, encrypted server-side sessions, CSRF, passkey step-up) and every UI-010 page, including the live investigation screen and the proposal screen; eval API endpoints and import; and the end-to-end test TST-E2E-001 running in CI on kind.

**Architecture:** The browser talks only to the console origin. Route handlers under `app/(bff)/` hold the OIDC client, store tokens encrypted in `bff.sessions`, proxy `/bff/api/*` to `api` with the access token, and stream SSE through. Pages are React Server Components for initial data plus client components with TanStack Query for refresh and SSE.

**Tech Stack:** Next.js 16 (App Router, Node runtime), React 19, TypeScript strict, Tailwind 4, shadcn/ui, TanStack Query 5, `openapi-typescript` + `openapi-fetch`, `oauth4webapi`, `pg`, Recharts, `@xyflow/react`, `diff2html`, `eventsource-parser`, vitest + Testing Library, Playwright + `@axe-core/playwright`.

## Global Constraints

All constraints in `2026-11-26-rootline-00-overview.md` → "Global Constraints" apply. Week-specific additions:

- Add to `versions.yaml` (W1-T02 rules): `oauth4webapi` (latest 3.x), `pg` (8.x), `@tanstack/react-query` (5.x), `recharts` (latest), `@xyflow/react` (12.x), `diff2html` (3.x), `eventsource-parser` (3.x), `openapi-typescript` (7.x), `openapi-fetch` (0.x latest), `vitest` (latest), `@testing-library/react` (16.x), `@axe-core/playwright` (4.x), `@tanstack/react-virtual` (3.x), `msw` (2.x), `@testcontainers/postgresql` (latest).
- API types only from `services/api/openapi.json` (UI-001). No hand-written duplicates.
- Accessibility WCAG 2.2 AA (UI-051); states loading/empty/error everywhere (UI-052).
- Week 6 acceptance (MS-001): TST-UI-001/010, TST-SEC-025 pass; TST-E2E-001 passes (or the TST-071 fallback is invoked).


## Execution schedule

Mirrors `2026-11-26-rootline-schedule.yaml` (week 6); `uv run python scripts/swarm_schedule.py table --week 6` must print exactly this table. Parallel stages run in separate worktrees (at most 3 implementers at once), then pass the integration gate (overview §7.6–§7.7) before one squash-merged PR reaches `develop`. Owned paths per task are listed in the YAML only. Deferred steps (overview §7.3) run at the start of the named sequential stage.

| Stage | Mode | After | Tasks (branch) | Deferred steps → stage |
|---|---|---|---|---|
| W6-P1 | parallel | — | W6-T01 (`feat/w6-console-bff`); W6-T07 (`feat/w6-eval-api`) | — |
| W6-S1 | sequential | W6-P1 | W6-T02 (`feat/w6-incidents-ui`) | — |
| W6-P2 | parallel | W6-S1 | W6-T03 (`feat/w6-live-investigation`); W6-T04 (`feat/w6-proposal-ui`); W6-T05 (`feat/w6-lab-eval-ui`); W6-T06 (`feat/w6-audit-ui`) | — |
| W6-S2 | sequential | W6-P2 | W6-T08 (`feat/w6-console-deploy`); W6-T09 (`feat/w6-e2e-env`); W6-T10 (`feat/w6-e2e-test`) | — |

---

### Task W6-T01: Console scaffold, design tokens, BFF sessions and auth routes

**Requirement IDs:** UI-001, UI-002, UI-003, UI-004, UI-005, UI-050, DB-010 (session cleanup), SEC-023a (BFF side), SEC-030 (console client), TST-SEC-025.
**Depends on:** W5 complete. **Branch:** `feat/w6-console-bff`.

**Files:**
- Create: `apps/console/{package.json,tsconfig.json,next.config.ts,postcss.config.mjs,vitest.config.ts,Dockerfile,.eslintrc.json}`
- Create: `apps/console/app/{layout.tsx,globals.css,page.tsx}`, `apps/console/app/fonts/` (self-hosted Inter and JetBrains Mono woff2, OFL licences included)
- Create: `apps/console/lib/{env.ts,crypto.ts,sessions.ts,oidc.ts,csrf.ts,returnTo.ts,api-types.ts (generated),api.ts,security-headers.ts}`
- Create: `apps/console/app/(bff)/auth/{login,callback,step-up}/route.ts`, `app/(bff)/auth/logout/route.ts`, `app/(bff)/bff/csrf/route.ts`, `app/(bff)/bff/api/[...path]/route.ts`, `middleware.ts`
- Create: `services/api/migrations/versions/0006_bff.py`
- Test: `apps/console/tests/bff/{crypto,sessions,returnTo,csrf,proxy,cookies}.test.ts`

**Interfaces:**
- `lib/crypto.ts`: `sealTokens(key: Buffer, tokens: TokenSet): {ciphertext: Buffer, nonce: Buffer}`; `openTokens(key, ciphertext, nonce): TokenSet` (AES-256-GCM; key = `sha256(BFF_SESSION_KEY)`; tag appended to ciphertext).
- `lib/sessions.ts`: `createSession(sub, tokens) -> {cookieValue, csrfToken}` (32 random bytes base64url; `id_hash = sha256 hex`; `expires_at = now + 10 h`; `csrf_token` 32 random bytes base64url = 43 chars); `getSession(cookieValue) -> Session | null` (rejects when `now > expires_at` or `now − last_used_at > 30 min`; touches `last_used_at`); `replaceTokens(id, tokens)`; `deleteSession(cookieValue)`; `cleanupExpired()` (every 10 min via an in-process interval started from `instrumentation.ts`, DB-010).
- `lib/returnTo.ts`: `safeReturnTo(value: string | null): string` — accepts only paths matching `^/(?!/)[A-Za-z0-9/_\-.?=&%]*$` and not containing `\`, `//`, `://` or control characters; otherwise `/incidents`.
- `lib/oidc.ts` (oauth4webapi): discovery from `KEYCLOAK_ISSUER` (cached), `authorizeUrl({state, nonce, codeChallenge, acr, prompt?})` with `scope = "openid profile roles delegation:client:rootline-agent"`, `acr_values`, `code_challenge_method=S256`, `redirect_uri = https://console.<D>/auth/callback`; `exchangeCode(...)`, `refresh(refreshToken)`, `revoke(refreshToken)`, `endSessionUrl(idToken)`.
- Cookie names: `__Host-rootline_session` (session) and `__Host-rootline_oauth` (10-minute signed cookie holding `{verifier, state, nonce, returnTo, acr}` as a sealed value with the same key).

- [ ] **Step 1: Scaffold** — `npx create-next-app@<versions.next> apps/console --ts --tailwind --eslint --app --no-src-dir --import-alias "@/*"` then pin versions from `versions.yaml`; `next.config.ts`: `output: "standalone"`, `poweredByHeader: false`, headers via `security-headers.ts` (UI-005 exactly; CSP nonce generated in `middleware.ts` per request and passed through the `x-nonce` request header, `script-src 'self' 'nonce-<n>'`); scripts `dev`, `build`, `start`, `lint`, `typecheck` (`tsc --noEmit`), `test` (`vitest`), `gen:api` (`openapi-typescript ../../services/api/openapi.json -o lib/api-types.ts`). `globals.css` defines the UI-050 tokens for dark (default) and light (`[data-theme=light]`), e.g. `--bg: #0b0d10; --fg: #e6e8eb; --muted: #8a93a0; --accent: #6aa9ff; --ok: #3fb950; --warn: #d29922; --crit: #f85149; --info: #58a6ff;` with light counterparts meeting 4.5:1 contrast (verify with the `dataviz` skill's contrast guidance). Add `scripts/check_contracts.py` coverage for `lib/api-types.ts` drift (CI `contracts`).
- [ ] **Step 2: Failing BFF tests (TST-SEC-025)** — vitest with a testcontainers Postgres (`@testcontainers/postgresql`, image `pgvector/pgvector:pg16`, migrated with `alembic upgrade head` before the suite), and Route Handlers invoked directly with `new NextRequest(...)`:
  1. `cookies.test.ts`: login response sets `__Host-rootline_oauth` with `HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=600`; callback sets `__Host-rootline_session` with `HttpOnly; Secure; SameSite=Lax; Path=/` and no `Domain`.
  2. `csrf.test.ts`: `POST /bff/api/proposals/x/approve` without `X-CSRF-Token` → 403 `{"code":"forbidden","detail":"csrf token missing or invalid"}` problem+json; with a wrong token → 403; with the session token → proxied; `GET` without token → proxied.
  3. `returnTo.test.ts`: `//evil.com`, `https://evil.com`, `/\evil`, `/%2F%2Fevil.com` (after decoding), `javascript:alert(1)` → `/incidents`; `/investigations/01ARZ3NDEKTSV4RRFFQ69G5FAV?tab=evidence` → unchanged.
  4. `sessions.test.ts`: idle 31 min → null; absolute 10 h 1 min → null; DB stores only `sha256(cookie)` and ciphertext (assert the raw access token string is not in any column).
  5. `proxy.test.ts`: forwards `Authorization: Bearer <access>`, `X-Request-Id`, `Idempotency-Key`; strips `Cookie`, `Connection`, `Transfer-Encoding`, `Host`; refreshes when `exp − now < 60 s` (mock OIDC) and persists rotated tokens; refresh failure deletes the session and returns 401 with header `X-Rootline-Reauth: /auth/login?returnTo=<path>`; upstream problem+json passed through unchanged.
  6. `callback` rejects mismatched `state` and mismatched `nonce` (400 problem) and expired oauth cookie.
- [ ] **Step 3: Implement** the routes per UI-003: `/auth/step-up` = login with `acr=step-up` and `prompt=login`; on callback with `acr=step-up` the session tokens are replaced and the BFF calls `GET /v1/me` (which audits `auth.step_up_succeeded`). `/auth/logout` (POST, CSRF required): revoke refresh token, delete session, redirect 303 to the end-session URL with `post_logout_redirect_uri=https://console.<D>/`. `/bff/csrf` returns `{csrf_token}`. `middleware.ts`: unauthenticated page requests (no session cookie) redirect to `/auth/login?returnTo=<path>`; `(bff)` routes excluded.
- [ ] **Step 4: Migration `0006_bff`** — `bff.sessions` verbatim (§13.6) + index; grants `rootline_console` per DB-002. TST-DB-001 re-run.
- [ ] **Step 5: Run** `npm --prefix apps/console run test -- --run --coverage` (≥ 70% lines for `app/(bff)/` and `lib/`), lint, typecheck; **commit** `feat(console): add console scaffold and secure BFF`.

---

### Task W6-T02: Shell, incidents list and incident detail

**Requirement IDs:** UI-010 (`/`, `/incidents`, `/incidents/[id]`, `/settings`), UI-050, UI-051, UI-052, §12.3.
**Depends on:** W6-T01. **Branch:** `feat/w6-incidents-ui`.

**Files:** `apps/console/app/(app)/layout.tsx` (nav with links to **every** UI-010 page, including pages built later in W6-P2, so later tasks never edit the layout; theme toggle; banner slot rendering `components/Banners.tsx`, which this task creates as an empty component that W6-T06 fills), `app/(app)/incidents/page.tsx`, `app/(app)/incidents/[id]/page.tsx`, `app/(app)/settings/page.tsx`, `components/{StatusChip,Severity,RelativeTime,DataState,RoleGate,ProblemAlert,Badge}.tsx`, `lib/queries.ts`; tests `tests/ui/incidents.test.tsx`.

- [ ] **Step 1: Tests** — with MSW mocking `/bff/api/*` from fixtures generated from `openapi.json` examples: the incidents table renders the UI-010 columns; status filter writes `?status=open&status=investigating` and refetches; auto-refresh interval is 10,000 ms (`refetchInterval`); empty state text "No incidents yet. Incidents appear when a Rootline alert fires or when the Fault Lab runs a demo."; error state shows `title`, `detail`, `request_id` and a Retry button; on the detail page the Investigate button is hidden for viewers (RoleGate), disabled with tooltip "An investigation is already running" when one is active; Close requires a reason (1–300 chars) and sends `Idempotency-Key`; status chips have icon + text (never colour only).
- [ ] **Step 2: Implement; commit** `feat(console): add shell, incidents and settings pages`.

---

### Task W6-T03: Live investigation screen (TST-UI-001)

**Requirement IDs:** UI-020, API-070, TST-UI-001.
**Depends on:** W6-T02. **Branch:** `feat/w6-live-investigation`.

**Files:** `app/(app)/investigations/[id]/page.tsx`, `components/investigation/{Timeline,HypothesisBoard,ReportPanel,EvidenceDrawer,TopologyPanel,BudgetMeter,Badges}.tsx`, `lib/sse.ts`, `lib/investigationReducer.ts`; tests `tests/ui/live-investigation.test.tsx`, fixture `tests/fixtures/events-diagnosed.jsonl` (recorded from the W4-T13 investigation via `GET /v1/investigations/{id}/events` and anonymised).

**Interfaces:**
- `lib/sse.ts`: `useEventStream(url, {onEvent, lastEventId})` — `fetch` with `Accept: text/event-stream`, parse with `eventsource-parser`, reconnect backoff 1 s, 2 s, 4 s, 8 s, 15 s (cap) using the last received `id` as `Last-Event-ID`; exposes `status: "connecting"|"open"|"reconnecting"|"closed"`; "Reconnecting…" shown when not open for > 3 s; stops after `investigation.completed`.
- `lib/investigationReducer.ts`: pure reducer `(state, event) -> state` handling every API-070 event type; state = `{steps, toolCalls, hypotheses, report, verification, budget, badges, proposal, completed}`.

- [ ] **Step 1: TST-UI-001** — replay the fixture through the reducer and the rendered page (MSW streaming response): after all events, the timeline lists every step and tool call in order with durations; the hypothesis board shows the final hypotheses with confidences; the report panel shows summary, root-cause entity (monospace), category, confidence and claims; clicking an evidence chip opens the drawer (640 px) with the tool name and the JSON pointer target highlighted (`aria-current="true"` on the node); budget meter shows tool calls / LLM calls / tokens / cost against AGT-020 caps; "System" badge (fixture is system mode); `aria-live="polite"` region announces "Step rca completed". Reducer unit tests for each event type; reconnect test: stream drops after event 10 → reconnect sends `Last-Event-ID: 10`.
- [ ] **Step 2: Implement** the three-column layout (28/44/28 % at ≥ 1280 px; at 1024–1279 px the right column moves below the centre without horizontal scrolling, NG7); confidence bars animate width over 300 ms unless `prefers-reduced-motion: reduce`; topology via `@xyflow/react` from `GET /v1/topology?investigation_id=`, node fill interpolated from neutral (0 %) to `--crit` (≥ 20 %) on `error_ratio`, suspected nodes outlined 2 px `--accent`; timeline virtualised (`@tanstack/react-virtual`) above 100 items; after completion fetch `GET /v1/investigations/{id}` for the final state. Measure render time per event with React Profiler in a test harness (target ≤ 16 ms, UI-020 SHOULD; record the measurement in `wiki/components/console.md`).
- [ ] **Step 3: Commit** `feat(console): add live investigation screen`.

---

### Task W6-T04: Proposal screen with step-up approval

**Requirement IDs:** UI-030, SEC-023a, POL-032, POL-060 (client side).
**Depends on:** W6-T02 (runs in parallel with W6-T03, stage W6-P2). **Branch:** `feat/w6-proposal-ui`.

- [ ] **Step 1: Tests** — header shows action summary and tier badge (T0 green, T1 amber, T2 red, DENIED grey strike-through, each with icon + text); stepper with timestamps, failure states red; policy panel lists reasons, deny reasons and requirements text exactly `1 approver · passkey step-up · not the initiator · comment ≥ 20 chars` for T2 (`1 approver · passkey step-up` for T1); diff rendered side-by-side via `diff2html`; `resync_app` shows an out-of-sync table instead; Approve visible only to approvers while `awaiting_approval`; T2 dialog requires ≥ 20 chars (button disabled below); on 401 `insufficient_user_authentication` the client navigates to `/auth/step-up?returnTo=/proposals/<id>?resume=approve` and, on return with `resume=approve`, re-opens the dialog with the stored comment (sessionStorage key `rootline:pending-approval:<id>`, cleared after success) and retries with the **same** `Idempotency-Key`; server errors shown inline with `detail` and `request_id`; PR and ArgoCD links (`https://argocd.<D>/applications/argocd/workload`).
- [ ] **Step 2: Implement; commit** `feat(console): add proposal screen with passkey step-up approvals`.

---

### Task W6-T05: Lab and eval pages with charts

**Requirement IDs:** UI-010 (`/lab`, `/lab/runs/[id]`, `/eval`, `/eval/runs/[id]`, `/eval/compare`), UI-040, §12.3 (lab endpoints).
**Depends on:** W6-T02, W6-T07 (eval API). **Branch:** `feat/w6-lab-eval-ui`.

- [ ] **Step 1: API lab endpoints** (in `api`, if not yet present): `GET /v1/lab/scenarios` (from `lab.scenarios` joined with the latest run), `POST /v1/lab/runs` (admin; proxies to faultlab `POST /internal/v1/runs` with the `rootline-api` service-account token; 409 `lab_busy` passthrough), `GET /v1/lab/runs/{id}`, `POST /v1/lab/runs/{id}/restore`; tests with a respx-mocked faultlab.
- [ ] **Step 2: Pages** — `/lab` scenario browser with filters (split, channel, category, fault type) in the URL; admin "Run demo" per scenario opens a dialog naming the fault type, target and channel; active-run banner with "Restore baseline"; `/lab/runs/[id]` timeline of LAB-052 timestamps and links to incidents with `lab_run_id`. `/eval` runs table; `/eval/runs/[id]` metrics panel, Pareto chart (x log-scale cost, y top-1 %, CI error bars, frontier line connecting non-dominated points: a point is dominated if another has ≤ cost and ≥ top-1 with one strict), per-category bar chart with CI whiskers, reliability diagram (10 bins, bars = accuracy, diagonal, counts, ECE in title), category confusion matrix, results table with filters, Langfuse dataset-run link; `/eval/compare?a=&b=` side-by-side metrics, McNemar p-values (from the report JSON), disagreeing scenarios. Every chart has a "Show data table" toggle (UI-040). Follow the `dataviz` skill (palette, marks, accessibility).
- [ ] **Step 3: Tests** — Pareto frontier selection unit test; each chart renders its table alternative; filters round-trip through the URL.
- [ ] **Step 4: Commit** `feat(console): add lab and eval pages`.

---

### Task W6-T06: Audit page, banners and remaining states

**Requirement IDs:** UI-010 (`/audit`), SEC-132 (UI), CST-010 (banner), OBS-021 (banner), UI-052.
**Depends on:** W6-T02. **Branch:** `feat/w6-audit-ui`.

- [ ] **Steps:** `/audit` (admin) table with action/target filters and cursor pagination; "Verify chain" button calls `GET /v1/audit/verify?check_approvals=true` and shows `chain_ok`, rows, first bad ID and violations; global banners from `/v1/me.banners` (`llm_budget_exhausted` → "The in-cluster LLM budget is exhausted; auto-investigation is paused.", `langfuse_disabled` → "Tracing is disabled for the rest of the month (Langfuse free-tier limit)."); add `langfuse_disabled` to `/v1/me` banners in `api` (reads `core.langfuse_usage.disabled` for the current month). Tests for role hiding (non-admin never sees the nav item or page), verify result rendering, banners. Commit `feat(console): add audit page and system banners`.

---

### Task W6-T07: Eval API endpoints, export and import

**Requirement IDs:** §12.3 (`/v1/eval/*`), EVL-001 (`export`), EVL-002.
**Depends on:** W4-T12. **Parallel-safe** with W6-T01…T04. **Branch:** `feat/w6-eval-api`.

- [ ] **Step 1: `rootline-eval export <run_id>`** — writes `eval/exports/<run_id>.tar.zst` containing `run.json`, `results.jsonl` with `raw` included, `metrics.json`, `report.md` (if any); ≤ 50 MB (fail otherwise).
- [ ] **Step 2: `POST /v1/eval/runs/import`** (admin, idempotent, multipart `bundle` ≤ 50 MB): validate archive members (only those four names, no paths), parse, insert `eval.runs` and `eval.results` in one transaction (existing `run_id` → 409 `conflict`); `GET /v1/eval/runs` (headline computed from `metrics`), `GET /v1/eval/runs/{id}` (`metrics`, `report_md`), `GET /v1/eval/runs/{id}/results` (filters `category`, `correct`; without `raw`).
- [ ] **Step 3: Tests** — import round-trip of a fixture export; oversize and unexpected members rejected (422); pagination order newest first. **Commit** `feat(api): add eval run export and import endpoints`.

---

### Task W6-T08: Accessibility suite and console deployment

**Requirement IDs:** UI-051, TST-UI-010, ARC-001 (console), CI-020 (console image), SEC-120 (console rows), INF-040 (HTTPRoute local).
**Depends on:** W6-T02…T06. **Branch:** `feat/w6-console-deploy`.

**Smoke registration (overview §7.7):** this task also creates `tests/smoke/console.yaml` with an `http` check per Service (`console`: namespace `rootline`, Service port `80`, path `/auth/login`, `expect_status: 307`) and an `argocd_app` check `rootline` → `Synced/Healthy`; the coordinator's G12 run (`task smoke:cluster`) must pass.

- [ ] **Step 1: Dockerfile** — multi-stage `node:24-bookworm-slim@<digest>`: `npm ci`, `npm run gen:api` check, `npm run build`; runtime copies `.next/standalone`, `.next/static`, `public`; `USER 10001`; `ENTRYPOINT ["node", "server.js"]`; port 3000.
- [ ] **Step 2: Chart** — Deployment `console` (1 replica, 192Mi/384Mi, env `KEYCLOAK_ISSUER`, `CONSOLE_BASE_URL`, `API_BASE=http://api.rootline.svc.cluster.local`, `BFF_CLIENT_SECRET` from `bff-client-secret`, `BFF_SESSION_KEY` from `bff-session-key` (generator `password-43`), `DATABASE_URL` from `pg-rootline-console`, `NODE_EXTRA_CA_CERTS=/etc/rootline/ca/ca.crt`), Service port 80 → 3000, `HTTPRoute console` (host `console.<D>`, Gateway `rootline`; Traefik flush interval 100 ms for SSE via a `Middleware`/route annotation per the Traefik version), NetworkPolicy rows from SEC-120.
- [ ] **Step 3: TST-UI-010** — `apps/console/e2e/a11y.spec.ts` (Playwright): against the running local console with a seeded session (log in as `owner` via the virtual authenticator helper from W6-T10), visit every UI-010 page (using IDs from the API), run `new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21aa","wcag22aa"]).analyze()`, and assert no violation with impact `serious` or `critical`; also keyboard checks: Tab reaches every interactive element on `/incidents` and `/proposals/[id]` with a visible focus ring (`:focus-visible` outline ≥ 2 px), dialogs trap focus and close on Esc.
- [ ] **Step 4: Deploy locally, run the suite, commit** `feat(deploy): deploy console; add accessibility tests`.

---

### Task W6-T09: End-to-end environment (`rootline-env-e2e`, ci values, `e2e.yml`)

**Requirement IDs:** TST-070 (environment), CI-001 (`e2e.yml`), CI-010 (secrets), GEN-060 (`e2e:up`, `e2e`), O-11.
**Depends on:** W6-T08. **Branch:** `feat/w6-e2e-env`.

- [ ] **Step 1 [CONFIRM] (O-11):** create private repo `arkhash0309/rootline-env-e2e`; push `workload/quote.yaml`, `workload/flagd-config.yaml`, `workload/networkpolicies.yaml` copied from `rootline-env` baseline, and `.rootline/baseline.json`; tag `baseline-v1`; install the three GitHub Apps on it (owner); create ruleset `protect-main` identical to SEC-081; add Actions secrets `E2E_GH_APP_AGENT_ID`, `E2E_GH_APP_AGENT_INSTALLATION_ID`, `E2E_GH_APP_AGENT_PRIVATE_KEY` (and `_GATE_`, `_FAULTLAB_` equivalents; installation IDs differ per repo), `E2E_SEED_PASSWORDS` (JSON `{"owner": "...", "interviewer": "...", "viewer1": "...", "breakglass": "...", "breakglass_otp_seed": "..."}`), `E2E_DEPLOY_KEY_ROOTLINE`, `E2E_DEPLOY_KEY_ROOTLINE_ENV_E2E`.
- [ ] **Step 2: `deploy/values/ci.yaml`** (root chart values for env `ci`): `envRepoURL` = the e2e repo; `chaos-mesh` disabled; kind has no bundled Traefik, so the `traefik` Application's `envs` becomes `[gke, ci]` (upstream chart, values `deploy/upstream/traefik/values-ci.yaml` with `providers.kubernetesGateway.enabled: true`, `ports.websecure.http.tls.enabled: true`, `gateway.enabled: false` and NodePorts mapped to kind ports 80/443; Gateway `rootline` keeps listeners 8000 and 8443, the entry point ports; PG-27, ADR 0046 T9); `observability` with Loki/Tempo/collector off (W1-T11 `values-ci.yaml`); Kyverno policies `Audit`; resources reduced to ≈ 60% of ARC-030 requests (each component's `values-ci.yaml`); `AUTO_INVESTIGATE=true`; agent `ROOTLINE_LLM_BACKEND=scripted`, `LLM_SCRIPT_DIR=/fixtures` with fixtures from `tests/e2e/llm-fixtures/` baked into a ConfigMap; faultlab `ENV_REPO=arkhash0309/rootline-env-e2e`, `ROOTLINE_SCENARIOS_FILE=/app/tests/e2e/scenarios.yaml` (file `tests/e2e/scenarios.yaml` with `scn-v1-git-bad-image-tag-00` re-targeted to `quote`, copied into the faultlab image only for the `ci` tag).
- [ ] **Step 3: `task e2e:up` / `task e2e`** — `scripts/e2e.py up`: kind cluster `rootline-e2e` with extra port mappings 80/443 and a CoreDNS rewrite for `auth|console|argocd.127.0.0.1.sslip.io` → the Traefik Service (SEC-011 kind variant), `build_images.py --tag ci --load-kind rootline-e2e`, after `kind create cluster` and before ArgoCD is installed call `scripts.up.fix_node_dns("rootline-e2e-control-plane", "kind-rootline-e2e")` (PG-28, ADR 0047 E1; verify with the three E1 commands of W1-T12 Step 5 using context `kind-rootline-e2e` and node `rootline-e2e-control-plane`, and record the three outputs in `wiki/components/argocd.md` section "Defects found by W1-T12"), Helm-install ArgoCD, create secrets from env (CI) or `.env.local` (local), apply the root Application with `env=ci` and with `spec.ignoreDifferences = scripts.up.ROOT_IGNORE_DIFFERENCES`, `spec.syncPolicy = {"automated": {"prune": True, "selfHeal": True}, "syncOptions": ["RespectIgnoreDifferences=true"], "retry": scripts.up.SYNC_RETRY}` (spec INF-021, PG-28, ADR 0047 D2 and D3), wait ≤ 15 min; `scripts/e2e.py test` runs Playwright (W6-T10); `scripts/e2e.py down`. Taskfile tasks `e2e:up`, `e2e`, `e2e:down`.
- [ ] **Step 4: `.github/workflows/e2e.yml`** — triggers `pull_request` → `main` and `workflow_dispatch`; `concurrency: {group: e2e, cancel-in-progress: false}`; one job on `ubuntu-24.04` (timeout 60 min): checkout, setup uv/node/helm/kind, `uv run python scripts/e2e.py up`, `uv run python scripts/e2e.py test`, upload the Playwright report and `kubectl get events -A` / pod logs as artifacts on failure, `scripts/e2e.py down`.
- [ ] **Step 5: Commit** `ci: add end-to-end environment and e2e workflow`.

---

### Task W6-T10: End-to-end test TST-E2E-001

**Requirement IDs:** TST-070, TST-071, S5, S7.
**Depends on:** W6-T09. **Branch:** `feat/w6-e2e-test`.

**Files:** `tests/e2e/{playwright.config.ts,e2e.spec.ts,helpers/webauthn.ts,helpers/api.ts}`, `tests/e2e/llm-fixtures/<investigation-agnostic prompt dirs>`, `tests/e2e/scenarios.yaml`.

- [ ] **Step 1: Scripted fixtures** — two fixture sets selected by trigger: (a) for the `ContainerWaiting` incident on `quote`: triage → hypothesize (plan: `list_workloads`, `get_recent_changes`, `describe_workload Deployment quote`) → update (conclude) → rca (`diagnosed`, `Deployment/shop/quote`, `config_change`, confidence 0.92, claims citing the gathered tool calls by **position** — the scripted backend substitutes `{{tool_call_id:N}}` placeholders with the Nth recorded tool call ID of the investigation; add this substitution to `ScriptedBackend`) → verify critique (none unsupported) → plan_fix (`revert_commit {{commit:fault}}` — placeholder resolved to the newest commit SHA from the `get_recent_changes` result); (b) for the second scenario: plan_fix `scale quote 2` with confidence 0.95 → T1 (not a T0 type).
- [ ] **Step 2: Playwright spec** — exactly TST-070 steps 2–7: virtual authenticator via CDP (`helpers/webauthn.ts`: `WebAuthn.enable`, `WebAuthn.addVirtualAuthenticator({options: {protocol: "ctap2", transport: "internal", hasResidentKey: true, hasUserVerification: true, isUserVerified: true}})`); owner first login with password then passkey registration; start the Fault Lab demo run from `/lab` (admin); poll the API with timeouts 4 min (incident), 3 min (report `diagnosed` with `Deployment/shop/quote`), 2 min (proposal T0 merged), 6 min (`verified`); `GET /v1/audit/verify?check_approvals=true` → `chain_ok` and 0 violations; second scenario: wait for the T1 proposal, approve in the UI with step-up through the virtual authenticator, assert `verified`; teardown restores the demo run.
- [ ] **Step 3: Run locally** (`task e2e:up && task e2e`) then in CI on the release PR; if CI fails twice with OOMKilled/evicted pods (TST-071), run locally, attach the Playwright HTML report to the release PR, switch `e2e.yml` to `workflow_dispatch` only, and write an ADR.
- [ ] **Step 4: Week 6 acceptance and release** — TST-UI-001/010, TST-SEC-025, TST-E2E-001 evidence; `release: milestone 6`.
