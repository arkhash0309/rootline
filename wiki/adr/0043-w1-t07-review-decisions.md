# 0043 — `rootline_common` decisions from the W1-T07 review (spec-gap)

Status: accepted
Date: 2026-11-27
Label: spec-gap
Plan gap: PG-24 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

The review of W1-T07 (`rootline_common` foundation modules, plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T07", branch `feat/w1-py-common` at `c91ea10`) found seven defects in the plan text. In each case the implementer followed the plan, so the fix belongs in the plan. The defects are lettered A to G, and decision D<n> answers letter n (D1 answers A, D7 answers G).

- **A. Version bounds.** W1-T02 Step 6 says every Python dependency gets `>=<resolved>,<<next major>>`, and a 0.x package gets `>=<resolved>,<0.<minor+1>>`. On `c91ea10`, `libs/py-common/pyproject.toml` has `fastapi>=0.165.0,<1`, `prometheus-client>=0.26.0,<1` and `httpx>=0.29.0,<1`. The W1-T07 "Files" line only said "constraints per W1-T02" and did not list the lines.
- **B. Request ID on a 500.** Starlette sends handlers registered for `Exception` (or status 500) to `ServerErrorMiddleware`, the outermost layer, which sits outside every `app.add_middleware` layer and so outside `RequestIdMiddleware`. When `_internal` runs, `RequestIdMiddleware` has already reset `request_id_var` in its `finally`, and the 500 response goes straight to the server's `send`, not through the middleware's `send_with_id`. Checked on 2026-11-27 with `fastapi` `0.165.0` and `starlette` `1.10.0`: a route that raises `RuntimeError` returns a 500 with no `X-Request-Id` header. Its body `request_id` is a new ULID, not the incoming ID, and the log line has `request_id: null`. This breaks API-004: "Every response carries `X-Request-Id`", and the ID appears in all logs.
- **C. HTTP exceptions.** `install_problem_handlers` registered no handler for `starlette.exceptions.HTTPException`. Starlette raises it for an unknown path (404, detail `Not Found`) and a wrong method (405, detail `Method Not Allowed`, header `Allow`), and FastAPI's security helpers raise it for 401 and 403. All of these came back in Starlette's default `application/json` shape `{"detail": ...}`, which breaks API-002 ("All errors use RFC 9457 `application/problem+json`"). The API-002 code table (spec §12.1) and `PROBLEM_CODES` are closed lists with no code for 405, and they say nothing about any status outside the table.
- **D. Non-UTF-8 request ID.** `dict(scope["headers"]).get(b"x-request-id", b"").decode()` decodes as UTF-8. An `X-Request-Id` of raw bytes such as `b"\xff\xfe"` therefore raises `UnicodeDecodeError` before the app runs. HTTP header values are bytes, and Starlette decodes them with latin-1. The `dict(...)` call also keeps the last of several `x-request-id` headers, while Starlette's `Headers.get` returns the first.
- **E. Reserved `extra` keys.** `_body` ends with `**(extra or {})`, so `Problem(..., extra={"status": 200, "code": "x"})` overwrites the body's `status` and `code`. The HTTP status of the response still comes from `body["status"]`, so the response status changes too. No document said what happens to such keys.
- **F. Naive datetimes.** `to_rfc3339` and `parse_rfc3339` call `datetime.astimezone(UTC)`, which treats a naive datetime as local time. On a host whose zone is not UTC, a naive input silently shifts by the host's offset. API-006 and MCP-002 require UTC with `Z`, and no document said whether naive input is allowed.
- **G. Health router and `/metrics`.** Overview §3.1 says `make_health_router` serves `/healthz` and `/readyz` and that `make_metrics_route()` serves `/metrics`. The W1-T07 Step 3 code and the Step 1 test (`assert c.get("/metrics").status_code == 200` on an app that includes only the health router) mount `/metrics` inside the health router. No document said whether an app may add both. If it does, Starlette registers two `GET /metrics` routes, and the first one registered answers.

## Decision

Each decision follows spec §0.3 (simplest, cheapest, safest, in that order). None of them changes cost, security posture or scope. D3 adds one row to the spec API-002 table and one paragraph below it; both are additions that fill the gap, and no existing row changes. The final code and tests are the W1-T07 Step 1 and Step 3 blocks of `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md`, amended in the same PR as this ADR. The planner ran them on 2026-11-27 (Python `3.12.16`, `fastapi` `0.165.0`, `starlette` `1.10.0`, `httpx` `0.29.0`, `prometheus-client` `0.26.0`, `python-ulid` `3.2.1`): every test passes, `mypy` with `strict = true` reports no issue, and the new and changed tests in `test_problem.py`, `test_requestid.py` and `test_timeutil.py` fail on the `c91ea10` modules.

### D1 — Version bounds (A)

No new rule. The W1-T02 Step 6 rule applies:

| Package kind | Constraint |
|---|---|
| Major version ≥ 1 | `>=<resolved>,<<major+1>>` |
| 0.x (including pre-releases such as `0.66b0`) | `>=<resolved>,<0.<minor+1>>` |

`libs/py-common/pyproject.toml` `[project] dependencies` has exactly these eleven lines, in this order. The resolved versions come from `versions.yaml` on the pin date `2026-11-27`; the three `opentelemetry-instrumentation-*` lines keep their values from `c91ea10`.

| # | Line | Changed from `c91ea10` |
|---|---|---|
| 1 | `fastapi>=0.165.0,<0.166` | yes (was `<1`) |
| 2 | `pydantic>=2.14.4,<3` | no |
| 3 | `pydantic-settings>=2.16.3,<3` | no |
| 4 | `python-ulid>=3.2.1,<4` | no |
| 5 | `prometheus-client>=0.26.0,<0.27` | yes (was `<1`) |
| 6 | `opentelemetry-sdk>=1.45.2,<2` | no |
| 7 | `opentelemetry-exporter-otlp-proto-grpc>=1.45.2,<2` | no |
| 8 | `opentelemetry-instrumentation-fastapi>=0.66b0,<0.67` | no |
| 9 | `opentelemetry-instrumentation-httpx>=0.66b0,<0.67` | no |
| 10 | `opentelemetry-instrumentation-psycopg>=0.66b0,<0.67` | no |
| 11 | `httpx>=0.29.0,<0.30` | yes (was `<1`) |

After the edit the implementer runs `uv lock`. The resolved versions do not change, because each one already lies inside its new bound. If `uv lock` changes any `rootline-common` dependency version in `uv.lock`, the implementer stops and reports `STATUS: BLOCKED`.

### D2 — Request ID on a 500 (B)

1. `RequestIdMiddleware.__call__`, for `scope["type"] == "http"`, resolves `rid` (D4). Before it calls the inner app, it runs `scope.setdefault("state", {})["request_id"] = rid`. So the key path is `scope["state"]["request_id"]`, and `scope["state"]` is created as an empty `dict` when it is absent. The middleware also sets `request_id_var` (reset in `finally`) and appends the header `x-request-id: <rid>` to every `http.response.start` message it forwards, both unchanged. Inside a route, `request.state.request_id` returns the same value, because Starlette's `Request.state` wraps `scope["state"]`.
2. `rootline_common.problem._request_id(request: Request) -> str` returns the first of these that applies:
   1. `request.scope["state"]["request_id"]`, when `scope["state"]` is a `dict` and the value is a non-empty `str`;
   2. `request_id_var.get()`, when it is not `None` or empty;
   3. `new_ulid()`.
   So a new ULID is generated only when neither the scope nor the context variable holds an ID. That happens when `RequestIdMiddleware` is not installed. The body helper `_body(request, code, status, title, detail, extra=None, request_id=None)` sets body `request_id` to its `request_id` argument when that is given, and to `_request_id(request)` otherwise.
3. The `Exception` handler `_internal`:
   1. `rid = _request_id(request)`;
   2. sets `request_id_var` to `rid`, calls `log.error("unhandled error", exc_info=exc)` on logger `rootline.problem`, and resets `request_id_var` in a `finally`. The JSON log line (OBS-001) therefore carries `"request_id": rid`;
   3. returns status `500`, media type `application/problem+json`, body `{"type": "https://rootline.dev/problems/internal", "title": "Internal error", "status": 500, "detail": "unexpected error", "instance": <path>, "code": "internal", "request_id": rid}` and header `X-Request-Id: rid`.

   The header appears exactly once, because the `ServerErrorMiddleware` response never passes through `send_with_id`.
4. The handlers for `Problem`, `HTTPException` and `RequestValidationError` run in `ExceptionMiddleware`, inside `RequestIdMiddleware`. They do not add `X-Request-Id` themselves; the middleware adds it, so it is not duplicated.
5. Test (`libs/py-common/tests/test_problem.py::test_internal_error_carries_incoming_request_id`): an app with `install_problem_handlers` and `RequestIdMiddleware`, and a route `/crash` that raises `RuntimeError("secret detail")`. The test calls `configure_logging("test", "INFO")`, then `TestClient(app, raise_server_exceptions=False).get("/crash", headers={"X-Request-Id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"})`. It asserts status `500`, `r.headers.get_list("x-request-id") == ["01ARZ3NDEKTSV4RRFFQ69G5FAV"]` and `r.json()["request_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"`, and that the `request_id` values of the captured stdout log lines whose `logger` is `rootline.problem` equal `["01ARZ3NDEKTSV4RRFFQ69G5FAV"]`. A second test, `test_internal_error_generated_request_id_matches`, sends no header and asserts that the single `x-request-id` header equals the body `request_id` and is a ULID.

Failure behaviour: if the response has already started when the exception is raised, Starlette cannot send a second response and re-raises. That behaviour is Starlette's and is unchanged.

### D3 — HTTP exceptions (C)

1. `install_problem_handlers(app)` registers `@app.exception_handler(starlette.exceptions.HTTPException)`. Starlette looks handlers up along the exception's MRO, so this handler also covers `fastapi.HTTPException`, which subclasses it. The handler keeps the exception's headers (`dict(exc.headers)` when `exc.headers` is set): `Allow` on 405, `WWW-Authenticate` on 401.
2. `rootline_common.problem.HTTP_STATUS_PROBLEMS: dict[int, tuple[str, str]]` is the closed status mapping:

   | HTTP status | `code` | `title` | `detail` |
   |---|---|---|---|
   | 401 | `unauthenticated` | `Unauthenticated` | `exc.detail[:500]` when `exc.detail` is a `str`, else `""` |
   | 403 | `forbidden` | `Forbidden` | `exc.detail[:500]` when `exc.detail` is a `str`, else `""` |
   | 404 | `not_found` | `Not found` | `exc.detail[:500]` when `exc.detail` is a `str`, else `""` |
   | 405 | `method_not_allowed` | `Method not allowed` | `exc.detail[:500]` when `exc.detail` is a `str`, else `""` |
   | any other status except 204 and 304 | `internal` | `Internal error` | `unexpected error` (the exception's detail is not echoed) |
   | 204, 304 | — | — | empty body: `Response(status_code=exc.status_code, headers=<kept headers>)`, because these statuses carry no body (RFC 9110 §15.3.5, §15.4.5) |

   In every row except 204 and 304, the response status is `exc.status_code` (preserved, never rewritten to 500), the media type is `application/problem+json`, and the body has the seven API-002 keys. An unmapped status also writes one log line on logger `rootline.problem` at level `WARNING`, with message `unmapped HTTPException status <status>`.
3. `PROBLEM_CODES` gains exactly one entry, `"method_not_allowed": 405`, so it has twelve entries: `unauthenticated` 401, `insufficient_user_authentication` 401, `forbidden` 403, `not_found` 404, `method_not_allowed` 405, `validation_error` 422, `invalid_transition` 409, `conflict` 409, `separation_of_duties` 403, `rate_limited` 429, `lab_busy` 409, `internal` 500. For every row of `HTTP_STATUS_PROBLEMS`, `PROBLEM_CODES[code] == status` (asserted by `test_codes_table`). `PROBLEM_CODES["internal"]` stays `500`; the fallback row of point 2 is the only place where code `internal` appears with another status.
4. Spec change (spec-gap addition, recorded here and in spec §26 PG-24): the API-002 table in `docs/superpowers/specs/2026-11-25-rootline-design.md` §12.1 gains the row with code `method_not_allowed`, HTTP `405` and "When" text "The path exists but not for the request method (`Allow` header kept); row added by PG-24 (ADR 0043)", between `not_found` and `validation_error`. A paragraph "Framework HTTP errors" below the table states the mapping of point 2 and the rule that service code MUST signal errors by raising `rootline_common.problem.Problem` and MUST NOT raise `HTTPException` itself. No existing row of the table changes.
5. Why only 405 is added: Starlette's routing raises exactly two statuses, 404 (`Router.not_found`) and 405 (`Route.handle` on a method mismatch), both checked on 2026-11-27 with `starlette` `1.10.0`. 404, 401 and 403 already have codes. Rootline code never raises `HTTPException`, so every other status can come only from a framework internal, and FastAPI's body-parse failure (400) is the one known case. Giving each such status its own code would add table rows that no Rootline requirement uses. Keeping the status (instead of rewriting it to 500) keeps the client-error signal for retry logic, which is safer. Hiding the detail matches the `internal` row's "details only in logs".
6. Tests in `libs/py-common/tests/test_problem.py`:

   | Test | Request | Asserts |
   |---|---|---|
   | `test_not_found_is_problem` | `GET /nope`, `X-Request-Id: 01ARZ3NDEKTSV4RRFFQ69G5FAV`, middleware installed | status 404, media type `application/problem+json`, full body `{"type": "https://rootline.dev/problems/not_found", "title": "Not found", "status": 404, "detail": "Not Found", "instance": "/nope", "code": "not_found", "request_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"}`, one `x-request-id` header |
   | `test_method_not_allowed_keeps_allow_header` | `POST /boom` (route is GET only) | status 405, header `allow` = `GET`, code `method_not_allowed`, title `Method not allowed` |
   | `test_http_401_maps_to_unauthenticated_and_keeps_headers` | `GET /auth` raising `HTTPException(401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})` | status 401, header `www-authenticate` = `Bearer`, code `unauthenticated`, title `Unauthenticated`, detail `Not authenticated` |
   | `test_unmapped_http_status_is_internal_with_status_kept` | `GET /teapot` raising `HTTPException(418, detail="teapot detail")` | status 418, problem+json, body `status` 418, code `internal`, title `Internal error`, detail `unexpected error`, `teapot detail` absent from the response text |
   | `test_codes_table` | none | `PROBLEM_CODES` equals the twelve entries of point 3; `HTTP_STATUS_PROBLEMS` equals the four rows of point 2; each row agrees with `PROBLEM_CODES` |

### D4 — Non-UTF-8 request ID (D)

1. `RequestIdMiddleware` reads the incoming ID with `raw = next((v for k, v in scope["headers"] if k == b"x-request-id"), b"")`. ASGI header names are lowercase bytes, so this is the first `x-request-id` header, the same one Starlette's `Headers.get` returns. It then decodes with `incoming = raw.decode("latin-1")`. Latin-1 maps every byte to a code point, so decoding never raises.
2. `rid = incoming if is_ulid(incoming) else new_ulid()` (API-004, unchanged). A latin-1 string with a byte ≥ `0x80` never matches `^[0-9A-HJKMNP-TV-Z]{26}$`, so such a value is always replaced. An absent header gives `""`, which is also replaced.
3. Tests in `libs/py-common/tests/test_requestid.py` drive the middleware with a raw ASGI scope through `asyncio.run`, because `TestClient` re-encodes header bytes:

   | Test | Scope headers | Asserts |
   |---|---|---|
   | `test_non_utf8_incoming_id_is_replaced` | `[(b"x-request-id", b"\xff\xfe01ARZ3NDEKTSV4RRFFQ69G5F")]` | no exception; the response header is a ULID and equals `scope["state"]["request_id"]` |
   | `test_first_incoming_header_wins` | `[(b"x-request-id", b"01ARZ3NDEKTSV4RRFFQ69G5FAV"), (b"x-request-id", b"01BX5ZZKBKACTAV9WEVGEMMVRZ")]` | response header and `scope["state"]["request_id"]` are `01ARZ3NDEKTSV4RRFFQ69G5FAV` |

   The `TestClient` tests `test_valid_incoming_id_is_kept` and `test_invalid_incoming_id_is_replaced` also assert that `request.state.request_id` equals the response header.

### D5 — Reserved `extra` keys (E)

1. `rootline_common.problem.RESERVED_PROBLEM_KEYS: frozenset[str] = frozenset({"type", "title", "status", "detail", "instance", "code", "request_id"})`.
2. `Problem.__init__` stores `self.extra` without these keys, and `_body` drops them again from its `extra` argument before it merges `extra` after the seven API-002 keys. A reserved key is dropped silently: no exception and no log line. Every other key (for example `errors` from the validation handler, `hint`) is kept unchanged.
3. Test (`test_reserved_extra_keys_are_dropped`): `GET /extra` raising `Problem("conflict", 409, "Conflict", "key reused", extra={"status": 200, "code": "x", "request_id": "y", "hint": "h"})` returns HTTP 409 with body `status` 409, `code` `conflict`, `hint` `h`, and `request_id` not equal to `y`. `Problem("conflict", 409, "Conflict", extra={"title": "x", "hint": "h"}).extra == {"hint": "h"}`.

### D6 — Naive datetimes (F)

| Function | Rejected input | Exception |
|---|---|---|
| `to_rfc3339(dt, *, ms=True)` | `dt.utcoffset() is None` (no `tzinfo`, or a `tzinfo` that returns `None`) | `ValueError(f"naive datetime not allowed: {dt.isoformat()}")`, for example `naive datetime not allowed: 2026-11-30T09:05:07` |
| `parse_rfc3339(text)` | `datetime.fromisoformat(text.replace("Z", "+00:00"))` returns a datetime whose `utcoffset()` is `None` (a string with no `Z` and no `±HH:MM` offset) | `ValueError(f"naive datetime not allowed: {text}")`, with `text` exactly as passed, for example `naive datetime not allowed: 2026-11-30T09:05:07` |

A string that `fromisoformat` cannot parse still raises that function's own `ValueError`, unchanged. Aware inputs in any zone are converted to UTC as before. Tests: `test_timeutil.py::test_to_rfc3339_rejects_naive` and `test_parse_rejects_missing_offset` (`pytest.raises(ValueError, match=r"^naive datetime not allowed: 2026-11-30T09:05:07$")`).

### D7 — Health router and `/metrics` (G)

1. `make_health_router(checks)` returns an `APIRouter` with exactly three routes: `GET /healthz`, `GET /readyz` and `GET /metrics`. `/metrics` is added with `router.routes.append(make_metrics_route())` and serves `prometheus_client.generate_latest()` with media type `prometheus_client.CONTENT_TYPE_LATEST`. All three routes have `include_in_schema=False`.
2. `make_metrics_route() -> APIRoute` returns the `GET /metrics` route alone. It exists for an app that serves `/metrics` without the health router. An app MUST NOT include both `make_health_router(...)` and `make_metrics_route()`, because that registers `GET /metrics` twice. The rule is enforced by review; no runtime check is made.
3. The overview §3.1 row `rootline_common.health` now lists `/metrics` for `make_health_router` and states the MUST NOT rule.
4. Test (`test_health.py::test_health_router_serves_metrics_once`): the sorted paths of `make_health_router({}).routes` are exactly `["/healthz", "/metrics", "/readyz"]`. `test_metrics_route_standalone` checks that an app with only `make_metrics_route()` answers `GET /metrics` with status 200 and a `text/plain` content type.

## Consequences

- W1-T07 in `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` changed on 2026-11-27 on branch `docs/w1-t07-review-decisions`: an amendment note under the task header, the "Files" `pyproject.toml` line (eleven exact lines), the Step 1 test blocks `test_timeutil.py`, `test_problem.py`, `test_health.py` and `test_requestid.py`, and the Step 3 blocks `timeutil.py`, `problem.py`, `health.py` and `requestid.py`. Steps 2, 4 and 5 are unchanged.
- Overview §3.1 rows `rootline_common.timeutil`, `rootline_common.problem` (now including `headers` in `Problem.__init__`, plus `HTTP_STATUS_PROBLEMS` and `RESERVED_PROBLEM_KEYS`), `rootline_common.health` and `rootline_common.requestid` changed; overview §5 gains PG-24 and §6 gains the PG-24 traceability row. The next free ADR number is 0044.
- Spec §12.1 API-002 gains the `method_not_allowed` row and the "Framework HTTP errors" paragraph; spec §26 gains row PG-24.
- The W1-T07 implementer replaces `timeutil.py`, `problem.py`, `health.py` and `requestid.py` and their tests on `feat/w1-py-common` with the amended blocks. Extra tests already on `c91ea10` (`test_health.py::test_ready_when_all_checks_pass`, `test_settings_otel.py`) stay. The implementer fixes the three `pyproject.toml` lines (D1), runs `uv lock`, `uv run ruff format`, `uv run ruff check`, `uv run pytest libs/py-common/tests -v --cov=rootline_common` (coverage ≥ 80 %) and `uv run mypy libs/py-common`, and commits on `feat/w1-py-common`. The schedule YAML (`docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`) and the wave-file "Execution schedule" table do not change, because no owned path changes.
- Every service built after W1-T07 (W2 to W8) that includes `RequestIdMiddleware` and `install_problem_handlers` gets `X-Request-Id` on 500 responses and problem+json for 404 and 405 without further code. Services that need `/metrics` include `make_health_router` and do not add `make_metrics_route()`.
- `services/api/openapi.json` (API-001) is not affected: the new handler adds no route.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| (D1) Keep `<1` for 0.x packages | Contradicts W1-T02 Step 6; a 0.x minor release may break the API under semantic versioning, and GEN-051 requires an ADR for that kind of change |
| (D2) Make `RequestIdMiddleware` catch exceptions and build the 500 itself | Moves problem+json logic into the middleware, and `install_problem_handlers` would then depend on middleware order; one value in the scope is simpler |
| (D2) Read only `request_id_var` in `_internal` | The variable is already reset when `ServerErrorMiddleware` runs the handler (checked on 2026-11-27), so it gives a new ULID |
| (D2) Generate a new ULID in `_internal` and log it | The body and log ID would then differ from the incoming `X-Request-Id`, which breaks API-004 propagation |
| (D3) Add codes `bad_request` (400) and `not_acceptable` (406) as well | No Rootline requirement raises them, and Starlette routing never raises 406; extra rows would widen the closed table with no user. 400 from FastAPI body parsing is covered by the fallback row |
| (D3) Map every unmapped status to 500 `internal` | Turns client errors (4xx) into server errors, so clients retry requests that cannot succeed |
| (D3) A generic code such as `http_error` for unmapped statuses | Adds a code to the closed table for a case that Rootline code never triggers; `internal` with the status kept already says "unexpected" |
| (D3) Echo `exc.detail` for unmapped statuses | The `internal` row says "details only in logs"; framework details are not designed for display |
| (D4) Decode as UTF-8 with `errors="replace"` | Gives the same outcome (not a ULID, so replaced), but differs from Starlette's own latin-1 header decoding, which Rootline code reading `request.headers` sees |
| (D4) Keep the last header (`dict(...)`) | Disagrees with `request.headers.get("x-request-id")`, which returns the first, so middleware and route code could see different IDs |
| (D5) Raise `ValueError` for reserved keys | A mistake in an error path would turn a 4xx into a 500; dropping them silently is safer and keeps the API-002 shape |
| (D6) Assume UTC for naive input | Hides bugs; API-006 requires explicit UTC, and failing loudly is safer |
| (D7) Remove `/metrics` from `make_health_router` and require `make_metrics_route()` everywhere | Every service needs `/metrics` (ARC-020), so one call that mounts all three paths is simpler; the Step 1 test already expects `/metrics` from the router |
| (D7) Delete `make_metrics_route()` | It is in overview §3.1 and on `c91ea10` with a test; keeping it costs nothing and covers an app without readiness checks |

## Spec references

API-001, API-002, API-004, API-006, ARC-020, OBS-001, GEN-050, GEN-051, MCP-002, PG-19, PG-21, PG-24, spec §0.3, §12.1, §26, overview §3.1, §5, §6, W1-T02 Step 6, W1-T07.
