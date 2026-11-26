# Rootline Implementation Plan — Week 3: Identity and MCP

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keycloak with passkeys, LoA step-up, federated client authentication and RFC 8693 token exchange; three MCP servers (`rootline-telemetry`, `rootline-k8s`, `rootline-gitops` read tools) that are OAuth resource servers, run live against the cluster and in replay against snapshots with proven parity; GitHub Apps and rulesets; RBAC, NetworkPolicies and Kyverno; ≥ 150 scenarios captured.

**Architecture:** `rootline_common.auth` holds all token logic (validation, client credentials with projected service-account tokens, token exchange). `rootline_mcpkit` turns a list of `ToolDef`s into a Starlette app with bearer auth, RFC 9728 metadata, scope checks, rate limits, redaction and size limits. Each MCP server implements tools once on top of a backend interface with a live and a replay implementation, so parity is structural.

**Tech Stack:** Keycloak 26.8 + keycloak-config-cli, PyJWT, `mcp` Python SDK (streamable HTTP), Starlette, DuckDB, `kubernetes` client, testcontainers (Postgres, Keycloak), kind, Kyverno CLI.

## Global Constraints

All constraints in `2026-11-26-rootline-00-overview.md` → "Global Constraints" apply. Week-specific additions:

- MCP revision and SDK fallback per `versions.yaml` (`mcp`, optional `mcp_protocol_revision`) and ADR 0012.
- Tokens are never logged; only `sub`, `azp`, `act.client_id`, `jti` (SEC-050 step 4).
- Week 3 acceptance (MS-001): TST-SEC-005, TST-SEC-010–016, TST-SEC-020, TST-SEC-030 pass; TST-MCP-001/005/010/020 pass; ADR 0010 final mode recorded; ≥ 150 scenarios captured (≥ 20 with `parity: true`, PG-5).

**Before starting:** read the Keycloak pages listed in spec §27 (token exchange, federated client authentication) and the Keycloak 26.8 release notes; record in `wiki/components/keycloak.md` the exact names of: the delegation preview feature flag, the client attribute enabling standard token exchange, the federated-JWT client authenticator ID and its attributes, and the Kubernetes identity-provider type. Every place below that names one of these uses the recorded value.

---

### Task W3-T01: Keycloak deployment and the `rootline` realm

**Requirement IDs:** SEC-010, SEC-011, SEC-012, SEC-020, SEC-021, SEC-022, SEC-030, SEC-031, SEC-032, SEC-033, SEC-100 (keycloak secrets), ARC-030.
**Depends on:** W2 complete. **Branch:** `feat/w3-keycloak`.

**Files:**
- Create: `deploy/charts/keycloak/{Chart.yaml,values.yaml,values-gke.yaml,values-ci.yaml}`, `templates/{deployment,service,httproute,serviceaccount,clusterrolebinding,externalsecrets,networkpolicy,config-job,realm-configmap}.yaml`
- Create: `deploy/charts/keycloak/files/realm/rootline.yaml` (spec says `deploy/charts/rootline/files/realm/rootline.yaml`; the realm belongs to the keycloak chart that applies it — record this path change in spec §26 and ADR 0028)
- Modify: `deploy/root/values.yaml` (`apps.keycloak.enabled: true`), `deploy/charts/platform-config` (ExternalSecrets `keycloak-admin`, `seed-users`, `bff-client-secret` in `keycloak` and `rootline` from generator `password-48` / store `bootstrap`)
- Test: `tests/repo/test_realm.py`

- [ ] **Step 1: Failing realm test** — parses `files/realm/rootline.yaml` after rendering the chart with `global.domain=127.0.0.1.sslip.io`, and asserts:

```python
"""Verifies SEC-012, SEC-020, SEC-021, SEC-022, SEC-030, SEC-031."""
def test_realm_settings(realm):
    assert realm["accessTokenLifespan"] == 300
    assert (realm["ssoSessionIdleTimeout"], realm["ssoSessionMaxLifespan"]) == (1800, 36000)
    assert realm["revokeRefreshToken"] is True and realm["refreshTokenMaxReuse"] == 0
    assert realm["bruteForceProtected"] is True and realm["failureFactor"] == 5
    assert realm["waitIncrementSeconds"] == 60 and realm["maxFailureWaitSeconds"] == 900
    assert realm["loginWithEmailAllowed"] is False and realm["registrationAllowed"] is False
    assert realm["defaultSignatureAlgorithm"] == "RS256"
    assert realm["eventsEnabled"] is True and realm["adminEventsEnabled"] is True
    assert realm["eventsExpiration"] == 604800
    assert realm["browserFlow"] == "rootline-browser"
    assert realm["attributes"]["acr.loa.map"] == '{"normal":1,"step-up":2}'

def test_roles_and_composites(realm):
    roles = {r["name"]: r for r in realm["roles"]["realm"]}
    assert set(roles) >= {"viewer", "responder", "approver", "admin"}
    assert roles["responder"]["composites"]["realm"] == ["viewer"]
    assert roles["approver"]["composites"]["realm"] == ["responder"]
    assert sorted(roles["admin"]["composites"]["realm"]) == ["responder", "viewer"]

def test_passkey_policy(realm):
    assert realm["webAuthnPolicyPasswordlessRpEntityName"] == "Rootline"
    assert realm["webAuthnPolicyPasswordlessRpId"] == "127.0.0.1.sslip.io"
    assert realm["webAuthnPolicyPasswordlessSignatureAlgorithms"] == ["ES256", "RS256"]
    assert realm["webAuthnPolicyPasswordlessAttestationConveyancePreference"] == "none"
    assert realm["webAuthnPolicyPasswordlessRequireResidentKey"] == "Yes"
    assert realm["webAuthnPolicyPasswordlessUserVerificationRequirement"] == "required"
    assert realm["webAuthnPolicyPasswordlessCreateTimeout"] == 120
    assert realm["webAuthnPolicyPasswordlessAvoidSameAuthenticatorRegister"] is False

def test_clients(realm):
    c = {x["clientId"]: x for x in realm["clients"]}
    assert set(c) == {"rootline-console", "rootline-api", "rootline-agent", "mcp-telemetry", "mcp-k8s",
                      "mcp-gitops", "rootline-gate", "rootline-faultlab"}
    console = c["rootline-console"]
    assert console["redirectUris"] == ["https://console.127.0.0.1.sslip.io/auth/callback"]
    assert console["attributes"]["pkce.code.challenge.method"] == "S256"
    assert console["consentRequired"] is False
    assert set(console["defaultClientScopes"]) == {"openid", "profile", "roles", "rootline-api-audience"}
    assert "delegation:client:rootline-agent" in console["optionalClientScopes"]
    agent = c["rootline-agent"]
    assert agent["serviceAccountsEnabled"] is True
    assert agent["attributes"]["access.token.lifespan"] == "600"
    assert set(agent["optionalClientScopes"]) >= {"k8s:read", "telemetry:read", "gitops:read", "gitops:propose"}

def test_users(realm):
    u = {x["username"]: x for x in realm["users"]}
    assert set(u["owner"]["realmRoles"]) == {"admin", "approver"}
    assert u["interviewer"]["realmRoles"] == ["approver"]
    assert u["viewer1"]["realmRoles"] == ["viewer"]
    assert u["breakglass"]["realmRoles"] == ["admin"] and u["breakglass"]["groups"] == ["/break-glass"]
    for name in ("owner", "interviewer", "viewer1"):
        assert u[name]["requiredActions"] == ["webauthn-register-passwordless"]
```

The test file provides a `realm` fixture that runs `helm template` on the keycloak chart, finds the realm ConfigMap and parses its `rootline.yaml` key with PyYAML (keycloak-config-cli variable substitution placeholders `$(env:SEED_OWNER)` are left as strings).

- [ ] **Step 2: Write the realm file** — keycloak-config-cli YAML (top-level realm representation) implementing the test plus:
  - **Client scopes:** `k8s:read`, `telemetry:read`, `gitops:read`, `gitops:propose`, `api:internal` (protocol `openid-connect`, `include.in.token.scope: "true"`, no mappers); `rootline-api-audience` with an `oidc-audience-mapper` (`included.client.audience: rootline-api`, `access.token.claim: "true"`); `roles` with `oidc-usermodel-realm-role-mapper` (`claim.name: realm_access.roles`, `multivalued: "true"`); the delegation scope `delegation:client:rootline-agent` exactly as the Keycloak 26.8 delegation docs require (recorded in `wiki/components/keycloak.md`).
  - **Clients:** per SEC-030. Service-account clients (`rootline-api`, `rootline-agent`, `mcp-gitops`, `rootline-gate`, `rootline-faultlab`) use the federated-JWT authenticator with `jwt.credential.issuer: k8s` (IdP alias) and `jwt.credential.sub: system:serviceaccount:rootline:<sa>` (attribute names as recorded). Audience mappers: on `rootline-api`'s service account add audiences `rootline-gate`, `rootline-faultlab`; on `mcp-gitops`, `rootline-gate`, `rootline-faultlab`, `rootline-agent` add `rootline-api` where they call it. Resource clients `mcp-telemetry`, `mcp-k8s` are bearer-only (`publicClient: false`, `standardFlowEnabled: false`, `serviceAccountsEnabled: false`, `directAccessGrantsEnabled: false`). `rootline-agent` has standard token exchange enabled (attribute as recorded). `rootline-console` client secret = `$(env:BFF_CLIENT_SECRET)`.
  - **Identity provider** alias `k8s`, type Kubernetes (as recorded), issuer `{{ .Values.global.k8sIssuer }}` (local/ci `https://kubernetes.default.svc.cluster.local`; gke per SEC-032).
  - **Flow `rootline-browser`** exactly the SEC-022 tree; the `first-login-password` subflow contains `Condition - credential` (configured to "WebAuthn Passwordless not configured") OR group condition for `break-glass`; break-glass branch requires `OTP Form`. Top-level `rootline-browser` is bound as `browserFlow`.
  - **Users:** `owner`, `interviewer`, `viewer1`, `breakglass` with credentials `{type: password, value: $(env:SEED_<USER>), temporary: false}`; `breakglass` also an OTP credential from `SEED_BREAKGLASS_OTP_SEED` (algorithm `HmacSHA1`, digits 6, period 30); group `break-glass`.

- [ ] **Step 3: Chart templates**
  - Deployment `keycloak` (image `quay.io/keycloak/keycloak:<versions.keycloak>`, args `["start", "--optimized"]` is **not** used because features are set at runtime; use `["start"]`), env `KC_DB=postgres`, `KC_DB_URL=jdbc:postgresql://rootline-pg-rw.rootline-data.svc:5432/keycloak`, `KC_DB_USERNAME`/`KC_DB_PASSWORD` from `pg-keycloak`, `KC_HOSTNAME=https://auth.{{D}}`, `KC_HTTP_ENABLED=true`, `KC_PROXY_HEADERS=xforwarded`, `KC_HEALTH_ENABLED=true`, `KC_METRICS_ENABLED=true`, `KC_FEATURES=<delegation feature>`, `KC_BOOTSTRAP_ADMIN_USERNAME`/`KC_BOOTSTRAP_ADMIN_PASSWORD` from `keycloak-admin`, `JAVA_OPTS_KC_HEAP=-Xms256m -Xmx512m`; ports 8080 and 9000; probes on `:9000/health/ready` and `/health/live`; resources 640Mi/900Mi; security context `runAsNonRoot` (uid 1000 from the image), `readOnlyRootFilesystem: false` (Keycloak writes to `/opt/keycloak/data`; mount an `emptyDir` there and set `readOnlyRootFilesystem: true` if Keycloak starts with it — test it and record the result in `wiki/components/keycloak.md`).
  - ServiceAccount `keycloak` with ClusterRoleBinding to `system:service-account-issuer-discovery` (local, ci only — SEC-070).
  - HTTPRoute `auth` → Service `keycloak:8080`, parentRef Gateway `rootline`, hostname `auth.{{D}}`.
  - Job `keycloak-config` (PostSync hook, image `adorsys/keycloak-config-cli:<version>`): env `KEYCLOAK_URL=http://keycloak.keycloak.svc:8080`, `KEYCLOAK_USER`/`KEYCLOAK_PASSWORD` from `keycloak-admin`, `IMPORT_FILES_LOCATIONS=/config/rootline.yaml`, `IMPORT_VARSUBSTITUTION_ENABLED=true`, `IMPORT_MANAGED_CLIENT=full`, `IMPORT_MANAGED_ROLE=full`, `IMPORT_MANAGED_CLIENT_SCOPE=full`, `IMPORT_MANAGED_AUTHENTICATION_FLOW=full`, `IMPORT_MANAGED_IDENTITY_PROVIDER=full`, `SEED_*` and `BFF_CLIENT_SECRET` from secrets; mounts the realm ConfigMap at `/config`.
  - NetworkPolicy in `keycloak`: ingress 8080 from `kube-system`/`traefik` (Traefik) and `rootline`; 9000 from `observability`; egress Postgres 5432, kube-apiserver (issuer discovery/JWKS, local), DNS, and 443 to the internet (gke issuer JWKS).
  - `coredns-custom` already maps `auth.D` (W1-T10). Pods calling `https://auth.D` mount ConfigMap `rootline-ca` at `/etc/rootline/ca` and set `SSL_CERT_FILE=/etc/rootline/ca/ca.crt` (SEC-011).

- [ ] **Step 4: Deploy and smoke-check** — enable the app, `task up REVISION=feat/w3-keycloak`; `curl --cacert data/rootline-ca.crt https://auth.127.0.0.1.sslip.io/realms/rootline/.well-known/openid-configuration` returns issuer `https://auth.127.0.0.1.sslip.io/realms/rootline`; log in to the account console as `owner` in the browser and register a passkey (Windows Hello). Record both in `wiki/components/keycloak.md` and fill `wiki/runbooks/recovery.md#keycloak-lockout-break-glass` (log in as `breakglass` with password + TOTP; it has `admin` but not `approver`).
- [ ] **Step 5: Run tests, update `capacity.md`, commit** `feat(deploy): add Keycloak with the rootline realm`.

---

### Task W3-T02: `rootline_common.auth` (validation, client credentials, exchange, static-test)

**Requirement IDs:** SEC-033, SEC-040, SEC-042, SEC-043, SEC-050, SEC-053, TST-SEC-011, TST-SEC-012, TST-SEC-013, TST-SEC-015, TST-SEC-020.
**Depends on:** W1-T07. **Parallel-safe** with W3-T01. **Branch:** `feat/w3-auth-lib`.

**Files:**
- Create: `libs/py-common/rootline_common/auth/{__init__,principal,validator,client,static_test,jwks}.py`
- Test: `libs/py-common/tests/auth/{test_validator,test_client,test_static_test}.py`

**Interfaces:** overview §3.1 auth rows.

- [ ] **Step 1: Failing tests** (keys from `tests/fixtures/keys.py`; a second key `OTHER_RSA_PEM` is added there; JWKS served via `respx`)

```python
"""Verifies SEC-043, SEC-050 (TST-SEC-011, TST-SEC-012, TST-SEC-013, TST-SEC-015)."""
import time

import jwt
import pytest

from rootline_common.auth.validator import AuthError, TokenValidator
from tests.fixtures.jwks import ISS, issue, jwks_mock   # helpers: issue(claims, key=TEST, alg="RS256", kid="k1")

AGENT_SUB = "11111111-agent-sa"


def v(mode: str = "act") -> TokenValidator:
    return TokenValidator(issuer=ISS, audience="mcp-k8s", jwks_url=f"{ISS}/protocol/openid-connect/certs",
                          delegation_mode=mode, agent_actor_sub=AGENT_SUB)


def claims(**kw) -> dict:
    now = int(time.time())
    base = {"iss": ISS, "aud": ["mcp-k8s"], "sub": "user-1", "azp": "rootline-agent",
            "act": {"client_id": "rootline-agent"}, "scope": "openid k8s:read", "iat": now, "exp": now + 300,
            "jti": "j1"}
    base.update(kw)
    return {k: val for k, val in base.items() if val is not None}


async def test_delegated_token_accepted(jwks_mock) -> None:
    p = await v().validate(issue(claims()))
    assert (p.kind, p.sub, p.act_client_id, "k8s:read" in p.scopes) == ("delegated", "user-1", "rootline-agent", True)


async def test_tst_sec_011_wrong_audience(jwks_mock) -> None:
    with pytest.raises(AuthError, match="audience"):
        await v().validate(issue(claims(aud=["mcp-telemetry"])))


@pytest.mark.parametrize("kw,reason", [
    ({"exp": int(time.time()) - 60}, "expired"),
    ({"iss": "https://evil/realms/rootline"}, "issuer"),
    ({"nbf": int(time.time()) + 120}, "not yet valid"),
    ({"iat": int(time.time()) - 900, "exp": int(time.time()) + 300}, "lifetime"),
])
async def test_tst_sec_012_rejections(jwks_mock, kw, reason) -> None:
    with pytest.raises(AuthError, match=reason):
        await v().validate(issue(claims(**kw)))


async def test_tst_sec_012_alg_none_and_hs256(jwks_mock) -> None:
    for token in (jwt.encode(claims(), key=None, algorithm="none"),
                  jwt.encode(claims(), key="secret", algorithm="HS256", headers={"kid": "k1"})):
        with pytest.raises(AuthError):
            await v().validate(token)


async def test_tst_sec_013_act_mode_rejects_delegated_without_act(jwks_mock) -> None:
    """Keycloak #52691 class: a user-subject token minted for the agent but lacking act."""
    with pytest.raises(AuthError, match="principal"):
        await v("act").validate(issue(claims(act=None)))


async def test_azp_mode_accepts_without_act(jwks_mock) -> None:
    p = await v("azp").validate(issue(claims(act=None)))
    assert p.kind == "delegated"


async def test_tst_sec_015_system_token_accepted_and_plain_user_rejected(jwks_mock) -> None:
    p = await v().validate(issue(claims(sub=AGENT_SUB, act=None)))
    assert p.kind == "system"
    with pytest.raises(AuthError, match="principal"):
        await v().validate(issue(claims(azp="rootline-console", act=None)))


async def test_unknown_kid_triggers_refetch(jwks_mock) -> None:
    token = issue(claims(), kid="k2")          # jwks_mock serves k1 first, then k1+k2
    assert (await v().validate(token)).sub == "user-1"
    assert jwks_mock.calls == 2
```

`test_client.py`: `ClientCredentials` posts `grant_type=client_credentials`, `client_id`, `client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer`, `client_assertion=<file content>` and `scope`; re-reads the assertion file on every call (write a new value between two calls and assert the second request body has it); caches nothing (callers cache). `TokenExchanger.exchange` in `act` mode sends exactly the SEC-042 `act` column (including `actor_token` and `actor_token_type`); in `azp` mode omits `actor_*`; returns `AccessToken` with `expires_at = time.time() + expires_in` and decoded (unverified) claims.

`test_static_test.py` (TST-SEC-020): `assert_static_test_allowed("eval")` and `("test")` pass; `("local")`, `("gke")`, `("ci-e2e")`, `("ci")` raise `RuntimeError("static-test auth is not allowed in ROOTLINE_ENV=<env>")`; `StaticTestIssuer().mint(sub="u", aud=["mcp-k8s"], scope="k8s:read")` produces a token that a `TokenValidator` configured with `issuer="https://test.rootline.invalid/realms/rootline"` and the issuer's in-memory JWKS accepts.

- [ ] **Step 2: Implement `validator.py`**

```python
"""Bearer token validation (SEC-050) with the delegation principal rules (SEC-043)."""
from __future__ import annotations

import time
from typing import Any, Literal

import jwt

from rootline_common.auth.jwks import JwksCache
from rootline_common.auth.principal import Principal


class AuthError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class TokenValidator:
    def __init__(self, *, issuer: str, audience: str, jwks_url: str, delegation_mode: Literal["act", "azp"],
                 agent_client_id: str = "rootline-agent", agent_actor_sub: str | None = None,
                 leeway_s: int = 30, allow_user_tokens: bool = False, max_lifetime_s: int = 600,
                 jwks: JwksCache | None = None) -> None:
        self.issuer, self.audience, self.mode = issuer, audience, delegation_mode
        self.agent_client_id, self.agent_actor_sub = agent_client_id, agent_actor_sub
        self.leeway, self.allow_user_tokens, self.max_lifetime = leeway_s, allow_user_tokens, max_lifetime_s
        self.jwks = jwks or JwksCache(jwks_url, ttl_s=600)

    async def validate(self, token: str) -> Principal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise AuthError("malformed token") from e
        if header.get("alg") != "RS256":
            raise AuthError("algorithm not allowed")
        key = await self.jwks.key(header.get("kid", ""))
        if key is None:
            raise AuthError("unknown signing key")
        try:
            c: dict[str, Any] = jwt.decode(token, key=key, algorithms=["RS256"], audience=self.audience,
                                           issuer=self.issuer, leeway=self.leeway,
                                           options={"require": ["exp", "iat", "iss", "sub"]})
        except jwt.ExpiredSignatureError as e:
            raise AuthError("expired") from e
        except jwt.InvalidAudienceError as e:
            raise AuthError("audience mismatch") from e
        except jwt.InvalidIssuerError as e:
            raise AuthError("issuer mismatch") from e
        except jwt.ImmatureSignatureError as e:
            raise AuthError("not yet valid") from e
        except jwt.PyJWTError as e:
            raise AuthError("invalid token") from e
        if c["exp"] - c["iat"] > self.max_lifetime:
            raise AuthError("lifetime exceeds 600 s")
        return Principal(sub=c["sub"], azp=c.get("azp", ""), act_client_id=(c.get("act") or {}).get("client_id"),
                         scopes=frozenset(str(c.get("scope", "")).split()),
                         roles=frozenset((c.get("realm_access") or {}).get("roles", [])),
                         acr=c.get("acr"), auth_time=c.get("auth_time"), jti=c.get("jti"),
                         kind=self._kind(c), claims=c)

    def _kind(self, c: dict[str, Any]) -> Literal["delegated", "system", "user"]:
        azp, act, sub = c.get("azp"), c.get("act"), c["sub"]
        if azp == self.agent_client_id and act is None and self.agent_actor_sub and sub == self.agent_actor_sub:
            return "system"
        if azp == self.agent_client_id and self.mode == "act" and isinstance(act, dict) and (
                act.get("client_id") == self.agent_client_id or act.get("sub") == self.agent_actor_sub):
            return "delegated"
        if azp == self.agent_client_id and self.mode == "azp" and act is None:
            return "delegated"
        if self.allow_user_tokens:
            return "user"
        raise AuthError("principal rule not satisfied")
```

`allow_user_tokens=True` is used only by `api` (console user tokens) and internal endpoints that check `azp` separately. `jwks.py`: `JwksCache(url, ttl_s)` with `async key(kid)`: fetch via httpx (timeout 5 s) when the cache is older than `ttl_s` or the kid is unknown (at most one refetch per 30 s to resist kid-flooding); returns `jwt.PyJWK(jwk).key` for RSA keys only. `principal.py` per overview.

- [ ] **Step 3: Implement `client.py` and `static_test.py`** per the tests. `static_test.py` generates a 2048-bit key per process when no PEM is given, exposes `jwks() -> dict` and a `JwksCache` subclass `StaticJwks` that serves it without HTTP.
- [ ] **Step 4: Run** with branch coverage (`rootline_common.auth` counts toward the `rootline_api.auth` ≥ 70% branch target via api's reuse) → PASS. Commit `feat(py-common): add token validation, client credentials and token exchange`.

---

### Task W3-T03: Keycloak integration tests and the delegation-mode decision

**Requirement IDs:** SEC-022, SEC-023, SEC-040, SEC-041, SEC-042, SEC-043, TST-SEC-005, TST-SEC-010, TST-SEC-014, ADR 0010.
**Depends on:** W3-T01, W3-T02. **Branch:** `feat/w3-keycloak-tests`.

**Files:**
- Create: `tests/integration/keycloak/{conftest.py,test_step_up.py,test_exchange.py}` (root `tests/` per PG-8; marker `integration`)
- Modify: `wiki/adr/0010-agent-delegation.md`, `deploy/charts/rootline/values.yaml` (`security.delegationMode`)

- [ ] **Step 1: Fixture** — testcontainers `GenericContainer("quay.io/keycloak/keycloak:<v>")` with `start-dev`, `KC_FEATURES=<delegation feature>`, bootstrap admin env; then a second container `adorsys/keycloak-config-cli:<v>` on the same Docker network importing the rendered realm (rendered with `global.domain=localhost` and test seed passwords). Because federated client authentication needs a Kubernetes issuer, the fixture **additionally** imports a test-only overlay `tests/integration/keycloak/overlay.yaml` that gives `rootline-agent` a client secret (`clientAuthenticatorType: client-secret`) — the federated path is tested separately in W3-T04 (TST-SEC-016).
- [ ] **Step 2: TST-SEC-010 / TST-SEC-014 / exchange shape** — using `httpx`: (a) password grant is disabled in the realm, so obtain a user token for `owner` via a scripted authorization-code flow with `acr_values=normal` against the test container (helper `login_code_flow(username, password)` that follows the HTML forms with `httpx` and a temporary test-only `Password Form` flow binding — overlay sets the browser flow to `browser` for the test realm because WebAuthn cannot be automated without a browser); (b) agent client-credentials token; (c) exchange per SEC-042 `act` mode for audience `mcp-k8s`, scope `k8s:read`. Assert decoded claims per SEC-043 `act` column: `aud` contains `mcp-k8s`, `sub` = owner's ID, `azp == "rootline-agent"`, `act.client_id == "rootline-agent"` (or `act.sub` = agent SA user), `scope ⊇ {k8s:read}`, `exp − iat ≤ 600`. TST-SEC-014: exchange for audience `mcp-k8s` with `scope=gitops:propose` → HTTP 400 `invalid_scope`, or a token whose `scope` lacks `gitops:propose`.
- [ ] **Step 3: TST-SEC-005 (step-up)** — Playwright (Python, `playwright` package in the dev group) with Chromium and a CDP virtual authenticator (`WebAuthn.enable`, `WebAuthn.addVirtualAuthenticator` with `protocol: ctap2, transport: internal, hasResidentKey: true, hasUserVerification: true, isUserVerified: true`), against the realm with the **real** `rootline-browser` flow: register a passkey for `interviewer` (first login with password → required action), log in with `acr_values=normal` → token `acr == "normal"` (or absent per mapping) ; request `acr_values=step-up&prompt=login` → passkey assertion → token `acr == "step-up"` and `auth_time` within 5 s of now; wait 301 s (use `max_age` override in the test realm: overlay sets LoA 2 max age to 5 s and the test waits 6 s) → a new `acr_values=step-up` request requires re-authentication. If any assertion fails on the pinned Keycloak, implement SEC-023 fallback: flow with `prompt=login&max_age=0`, API checks `now − auth_time ≤ 300`; write an ADR and set `security.stepUpMode: auth_time` (default `acr`) consumed by `api` in W5.
- [ ] **Step 4: Decide delegation mode (SEC-040)** — run TST-SEC-010 … TST-SEC-016 (016 from W3-T04). All pass → `security.delegationMode: act`; any fails → `azp`. Update ADR 0010 with the pinned Keycloak version, the test results table and the final mode; record the trade-off of SEC-041.
- [ ] **Step 5: Commit** `test: add Keycloak step-up and token-exchange integration tests`.

---

### Task W3-T04: Federated client authentication test on kind (TST-SEC-016)

**Requirement IDs:** SEC-032, SEC-033, TST-SEC-016, TST-020.
**Depends on:** W3-T01, W3-T02. **Branch:** `feat/w3-federated-auth-test`.

**Files:**
- Create: `tests/k8s/test_federated_client_auth.py` (marker `k8s`), `scripts/test_k8s.py`
- Modify: `Taskfile.yml` (task `test:k8s`)

- [ ] **Step 1: `task test:k8s`** → `uv run python scripts/test_k8s.py`: creates kind cluster `rootline-k8stest` (image from `versions.yaml` `kind` node image matching `k3s` minor), installs Keycloak with the keycloak chart in a minimal values profile (`values-ci.yaml`, dev DB `KC_DB=dev-file`), applies the realm, creates ServiceAccount `rootline/agent` and a Pod `token-probe` (image `python-image`) that mounts a projected token with `audience: http://keycloak.keycloak.svc:8080/realms/rootline` (issuer set accordingly in the test overlay), runs `pytest -m k8s`, deletes the cluster.
- [ ] **Step 2: Test** — inside the probe pod (via `kubectl exec`), call `ClientCredentials(token_url, "rootline-agent", "/var/run/secrets/rootline/keycloak-token").token("k8s:read")` and assert a 200 with an access token whose `azp == "rootline-agent"`; then use the token of a **different** ServiceAccount (`rootline/api`) as assertion for `rootline-agent` → `invalid_client`.
- [ ] **Step 3: Commit** `test: add kind-based federated client authentication test`.

---

### Task W3-T05: `rootline_mcpkit` server framework

**Requirement IDs:** MCP-001 … MCP-009, MCP-050, MCP-051 (in-process support), MCP-052, MCP-062, SEC-050, SEC-051, SEC-052, SEC-053, OBS-002 (`rootline_tool_calls_total`, `rootline_tool_call_duration_seconds`, `rootline_auth_failures_total`).
**Depends on:** W3-T02, W2-T04. **Branch:** `feat/w3-mcpkit`.

**Files:**
- Create: `libs/py-mcpkit/rootline_mcpkit/{windows,errors,limits,tooldef,server,auth,ratelimit,snapshot,migrations,metrics}.py`
- Test: `libs/py-mcpkit/tests/{test_windows,test_limits,test_server,test_auth_http,test_snapshot}.py`

**Interfaces:** overview §3.3.

- [ ] **Step 1: Verify the SDK surface** — in the pinned `mcp` package, read `mcp/server/lowlevel/server.py` and `mcp/server/streamable_http_manager.py`; confirm: `Server(name, version=...)`, decorators `@server.list_tools()` and `@server.call_tool()`, that `call_tool` handlers may return a `types.CallToolResult` (or the tuple form `(content, structured)`), and `StreamableHTTPSessionManager(app=server, json_response=True, stateless=True)` with `handle_request(scope, receive, send)` and `run()` context manager. Write the confirmed signatures into `wiki/components/mcp-telemetry.md` § "SDK surface". If they differ, adapt `server.py` below and keep the public `build_app` signature unchanged.

- [ ] **Step 2: Failing tests**

`test_windows.py` (MCP-003):

```python
from datetime import UTC, datetime, timedelta

import pytest

from rootline_mcpkit.errors import ToolError
from rootline_mcpkit.windows import resolve_window

NOW = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)


def test_default_15m() -> None:
    w = resolve_window(None, None, None, now=NOW)
    assert (w.start, w.end, w.clipped) == (NOW - timedelta(minutes=15), NOW, False)


@pytest.mark.parametrize("bad", ["0m", "61m", "2h", "15", "1d", "015m"])
def test_bad_window(bad: str) -> None:
    with pytest.raises(ToolError) as e:
        resolve_window(bad, None, None, now=NOW)
    assert e.value.code == "invalid_argument"


def test_explicit_range_overrides_and_max_60() -> None:
    w = resolve_window("5m", "2026-12-01T11:00:00Z", "2026-12-01T11:30:00Z", now=NOW)
    assert w.end - w.start == timedelta(minutes=30)
    with pytest.raises(ToolError):
        resolve_window(None, "2026-12-01T10:00:00Z", "2026-12-01T11:30:00Z", now=NOW)


def test_replay_clipping_and_outside() -> None:
    cap = (NOW - timedelta(minutes=10), NOW + timedelta(minutes=3))
    w = resolve_window("15m", None, None, now=NOW, capture=cap)
    assert w.start == cap[0] and w.clipped
    with pytest.raises(ToolError) as e:
        resolve_window(None, "2026-12-01T09:00:00Z", "2026-12-01T09:30:00Z", now=NOW, capture=cap)
    assert e.value.code == "outside_window"
```

Notes: `1h` is allowed (= 60 min); `max_minutes` for gitops tools is 1440 (`get_recent_changes` max `24h`), passed by the caller.

`test_limits.py` (MCP-004): an output with a 500-element list is trimmed from the end until the canonical JSON (`json.dumps(sort_keys=True, separators=(",",":"))`) ≤ 12,000 chars; `truncated: true`, `omitted_count` correct; `truncate_str("x"*301) == "x"*300 + "…[truncated]"`.

`test_server.py` (MCP-002, MCP-005, MCP-006, MCP-007, MCP-062) — builds an app with two fake tools (`echo` returning `{"items":[...]}`, `slow` sleeping 3 s) with `StaticTestAuthenticator`, mounts it with `httpx.ASGITransport`, and uses the MCP SDK client (`mcp.client.streamable_http.streamablehttp_client` over the ASGI transport, or raw JSON-RPC POSTs if the client cannot use an ASGI transport — then send `initialize`, `notifications/initialized`, `tools/list`, `tools/call` by hand with header `MCP-Protocol-Version`) and asserts:
  1. `tools/list` returns both tools; each `inputSchema` has `"additionalProperties": false`.
  2. `tools/call echo` returns `structuredContent` and one text block equal to `json.dumps(structured, sort_keys=True)`.
  3. Unknown argument → `isError: true`, `structuredContent.error.code == "invalid_argument"`, `retryable == false`.
  4. `slow` in replay mode (2 s limit) → `timeout`, `retryable: true`.
  5. 121 calls within a minute from the same `sub`+`act` → the 121st returns `rate_limited`.
  6. A tool returning `"password=x"` in a string → output contains `[REDACTED:password_kv]`.

`test_auth_http.py` (SEC-050, SEC-051):
  1. No `Authorization` → 401 with `WWW-Authenticate: Bearer resource_metadata="http://testserver/.well-known/oauth-protected-resource", scope="k8s:read"`.
  2. Valid token without the tool's scope, `tools/call` → HTTP 403 with `WWW-Authenticate: Bearer error="insufficient_scope", scope="k8s:read"`; `tools/list` with the same token succeeds.
  3. `GET /.well-known/oauth-protected-resource` and `/.well-known/oauth-protected-resource/mcp` → the SEC-051 JSON.
  4. `rootline_auth_failures_total{component="mcp-k8s",reason="audience mismatch"}` increments.

`test_snapshot.py` (MCP-050, MCP-052): a snapshot written by `SnapshotWriter` (W2-T09) opens; a corrupted file → `SnapshotError("sha256 mismatch: metrics.parquet")`; `tool_layer_version: "2"` → `SnapshotError("incompatible tool_layer_version 2")`; `duck().execute("select count(*) from metrics").fetchone()` works.

- [ ] **Step 3: Implement**
  - `errors.py`: `ERROR_RETRYABLE = {"invalid_argument": False, "not_found": False, "forbidden": False, "upstream_unavailable": True, "timeout": True, "outside_window": False, "rate_limited": True}`; `ToolError.envelope()` → `{"error": {"code", "message"[:200], "retryable"}}`.
  - `windows.py`: regex `^([1-9][0-9]?)(m|h)$`; minutes = n or 60n; > `max_minutes` → `invalid_argument`; explicit `start`/`end` parsed with `parse_rfc3339`, `end > start`, span ≤ `max_minutes`; with `capture`: if `end <= cap.start or start >= cap.end` → `outside_window`; else clip to the capture window and set `clipped` when either bound moved.
  - `limits.py`: as specified; `fit_output` removes items from the end of `obj[list_field]` one at a time (binary search acceptable) and finally sets `truncated`/`omitted_count` only when something was removed.
  - `tooldef.py`: per overview; `input_schema(model)` = `model.model_json_schema()` with `additionalProperties: false` enforced on the root (models use `ConfigDict(extra="forbid")`, which already yields it — assert in a test).
  - `server.py`:

```python
"""Starlette app for one MCP server (MCP-001 - MCP-007, SEC-050/051)."""
from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from rootline_common.ids import new_ulid
from rootline_mcpkit.auth import Authenticator, AuthMiddleware, current_principal, protected_resource_metadata
from rootline_mcpkit.errors import ToolError
from rootline_mcpkit.limits import MAX_OUTPUT_CHARS, fit_output
from rootline_mcpkit.metrics import TOOL_CALLS, TOOL_DURATION
from rootline_mcpkit.ratelimit import TokenBucket
from rootline_mcpkit.redact import redact_obj
from rootline_mcpkit.tooldef import ToolContext, ToolDef


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


async def dispatch(tool: ToolDef, args: dict[str, Any], ctx: ToolContext, server_name: str,
                   bucket: TokenBucket | None = None) -> types.CallToolResult:
    start = time.perf_counter()
    status = "ok"
    try:
        if bucket and not bucket.allow(f"{ctx.principal.sub}|{ctx.principal.act_client_id}"):
            raise ToolError("rate_limited", "per-token rate limit exceeded")
        try:
            parsed = tool.input_model.model_validate(args)
        except ValidationError as e:
            raise ToolError("invalid_argument", str(e.errors()[0]["msg"])) from e
        limit = tool.live_timeout_s if ctx.mode == "live" else 2.0
        try:
            out = await asyncio.wait_for(tool.handler(parsed, ctx), timeout=limit)
        except TimeoutError as e:
            raise ToolError("timeout", f"tool exceeded {limit:g}s") from e
        out, _ = redact_obj(out)
        if tool.list_field:
            out = fit_output(out, tool.list_field)
        if len(canonical(out)) > MAX_OUTPUT_CHARS:
            raise ToolError("upstream_unavailable", "output too large after truncation")
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(out, sort_keys=True))],
                                    structuredContent=out, isError=False)
    except ToolError as e:
        status = "error"
        env = e.envelope()
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(env, sort_keys=True))],
                                    structuredContent=env, isError=True)
    finally:
        TOOL_CALLS.labels(server=server_name, tool=tool.name, status=status).inc()
        TOOL_DURATION.labels(server=server_name, tool=tool.name).observe(time.perf_counter() - start)


def build_mcp_server(name: str, version: str, tools: Sequence[ToolDef], mode: Literal["live", "replay"],
                     now_fn: Callable[[], datetime], bucket: TokenBucket | None) -> Server:
    server = Server(name, version=version)
    by_name = {t.name: t for t in tools}

    @server.list_tools()
    async def _list() -> list[types.Tool]:
        return [types.Tool(name=t.name, description=t.description, inputSchema=t.input_schema()) for t in tools]

    @server.call_tool()
    async def _call(tool_name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        tool = by_name.get(tool_name)
        if tool is None:
            env = ToolError("invalid_argument", f"unknown tool {tool_name}").envelope()
            return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(env))],
                                        structuredContent=env, isError=True)
        ctx = ToolContext(principal=current_principal(), now=now_fn(), mode=mode, request_id=new_ulid())
        return await dispatch(tool, arguments or {}, ctx, name, bucket)

    return server


def build_app(*, name: str, version: str, tools: Sequence[ToolDef], scopes_supported: list[str],
              auth: Authenticator, mode: Literal["live", "replay"], now_fn: Callable[[], datetime],
              resource_url: str, issuer: str, extra_routes: list[Route] | None = None) -> Starlette:
    server = build_mcp_server(name, version, tools, mode, now_fn, TokenBucket(120))
    manager = StreamableHTTPSessionManager(app=server, json_response=True, stateless=True)
    meta = protected_resource_metadata(name, resource_url, issuer, scopes_supported)

    async def metadata(_req) -> JSONResponse:
        return JSONResponse(meta)

    async def handle(scope, receive, send) -> None:
        await manager.handle_request(scope, receive, send)

    @asynccontextmanager
    async def lifespan(_app):
        async with manager.run():
            yield

    scope_of = {t.name: t.scope for t in tools}
    app = Starlette(routes=[
        Route("/.well-known/oauth-protected-resource", metadata),
        Route("/.well-known/oauth-protected-resource/mcp", metadata),
        Mount("/mcp", app=AuthMiddleware(handle, auth=auth, scope_of=scope_of, resource_metadata_url=None,
                                         component=name.removeprefix("rootline-"))),
        *(extra_routes or []),
    ], lifespan=lifespan)
    return app
```

  - `auth.py`: `current_principal()` reads a `ContextVar[Principal]`; `AuthMiddleware` (ASGI) — reads `Authorization`; missing/invalid → 401 with `WWW-Authenticate: Bearer resource_metadata="<scheme>://<host>/.well-known/oauth-protected-resource", scope="<space-joined scopes of all tools>"`; on success, buffers the request body; if it is a JSON-RPC (single or batch) `tools/call` for a tool whose scope is not in `principal.scopes`, responds 403 `insufficient_scope` with that scope; otherwise sets the context var and replays the buffered body to the inner app; logs `{"msg":"mcp request","sub","azp","act_client_id","jti","tool"}` and sets the same as OTel span attributes; increments `rootline_auth_failures_total{component, reason}` on failures. `JwtAuthenticator(validator)` and `StaticTestAuthenticator(issuer)` (which calls `assert_static_test_allowed(os.environ["ROOTLINE_ENV"])` in `__init__`). `protected_resource_metadata` returns exactly SEC-051.
  - `ratelimit.py`: token bucket refilled continuously at `rate/60` tokens per second, capacity `rate`.
  - `snapshot.py`: `SnapshotStore(root)` → reads `manifest.json` into `SnapshotManifest`, calls `migrations.check_compatible`, verifies each file's sha256; `duck()` creates an in-memory DuckDB connection with views `CREATE VIEW metrics AS SELECT * FROM read_parquet('<root>/metrics.parquet')` (same for `service_graph`, `logs`, `traces`); `json(path)` loads JSON files (cached).
  - `migrations.py`: `check_compatible(m)`: major of `m.tool_layer_version` must equal `"1"` unless `MIGRATIONS` (empty dict for now) has an entry.
  - `metrics.py`: the three Prometheus metrics with OBS-002 names and labels.
- [ ] **Step 4: Run tests** → PASS; commit `feat(py-mcpkit): add MCP server framework with OAuth resource-server auth`.

---
### Task W3-T06: `rootline-telemetry` MCP server (live and replay)

**Requirement IDs:** §8.2.1, MCP-003, MCP-008, MCP-020–023, MCP-050, ARC-011, TST-MCP-001, TST-MCP-005.
**Depends on:** W3-T05, W2-T03, W1-T13 (metric map). **Branch:** `feat/w3-mcp-telemetry`.

**Files:**
- Create: `services/mcp-telemetry/rootline_mcp_telemetry/{backend,live,replay,tools,models,app}.py`
- Test: `services/mcp-telemetry/tests/{test_tools_replay.py,test_scoping.py,test_live_queries.py}`, fixture snapshot `services/mcp-telemetry/tests/fixtures/snap/` (a small synthetic snapshot produced by `tests/fixtures/make_snapshot.py` using `SnapshotWriter`: 3 services, 20 min of metrics with a spike on `payment`, 300 log lines, 20 traces with 2 errors, 1 alert)

**Interfaces:**
- Produces: `TelemetryBackend` Protocol —

```python
class TelemetryBackend(Protocol):
    def services(self) -> list[tuple[str, str]]: ...                       # (service, workload), sorted
    async def metric_frame(self, start: datetime, end: datetime, services: list[str] | None = None,
                           metrics: list[str] | None = None) -> pd.DataFrame: ...   # metric_key, service, ts, value
    async def service_graph(self, start: datetime, end: datetime) -> pd.DataFrame: ...  # client, server, ts, request_rate, error_ratio, latency_p95
    async def logs(self, service: str, start: datetime, end: datetime, min_severity: str,
                   contains: str | None) -> list[LogLine]: ...
    async def spans(self, start: datetime, end: datetime, service: str | None = None,
                    trace_id: str | None = None) -> pd.DataFrame: ...       # LAB-060 traces columns
    async def alerts(self, start: datetime, end: datetime) -> list[dict]: ...  # LAB-060 alerts.json rows
```

`LiveTelemetry(prom, loki, tempo, alertmanager, metric_map)` and `ReplayTelemetry(store: SnapshotStore)`; `tools.build_tools(backend) -> list[ToolDef]`; `app.create_app() -> Starlette` reading env `ROOTLINE_MCP_MODE` (`live`|`replay`), `ROOTLINE_SNAPSHOT_DIR`, `AUTH_MODE` (`jwt`|`static-test`), `KEYCLOAK_ISSUER`, `ROOTLINE_DELEGATION_MODE`, `ROOTLINE_AGENT_ACTOR_SUB`; console script `rootline-mcp-telemetry` (uvicorn on `0.0.0.0:8080`).

**Tool semantics (exact; shared by both backends):**

| Tool | Logic |
|---|---|
| `list_services` | window via `resolve_window`; `metric_frame(metrics=[request_rate,error_ratio,latency_p95])`; mean per (service, metric) ignoring NaN (NaN mean → `null`); `has_alert` = any alert from `alerts(window)` with that `service`; `workload` from `services()`; sort `error_ratio` desc (nulls last), then `service`. `list_field="services"` |
| `get_service_graph` | `service_graph(window)` mean per (client, server); sort `error_ratio` desc, `client`, `server`; `list_field="edges"` |
| `get_metric_series` | validate `service ∈ services()` else `invalid_argument "unknown service"`; metric not available (`jvm_only`/`services` restriction in the metric map, or no data at all for the service in the snapshot) → `invalid_argument "metric not available for service"`; baseline `[start − 10 min, start − 1 min]`, falling back to the first 25% of in-window points when < 8 baseline points (note `"baseline: first 25% of window"`); `baseline` = `{start, end, median, mad, p95}`; `summary` over in-window non-NaN values; `anomalies` = `find_runs` over in-window points with `robust_z` vs baseline; `change_points` over in-window values; `series` = in-window points averaged into `min(30, n)` equal-width buckets keyed by bucket start ts; `unit` from the metric map |
| `find_anomalies` | `scan_anomalies(metric_frame(window − 10 min … window end, services), window)`; `services` input max 20 names; `list_field="anomalies"` |
| `search_logs` | `logs(service, window, min_severity, contains)`; `contains` matched case-insensitive substring (≤ 100 chars, validated by the input model); `total_lines`; `mine_templates`; each template's samples truncated to 300 chars; `list_field="templates"` |
| `get_error_traces` | spans with `status_code == STATUS_CODE_ERROR` and `service` in window → distinct trace IDs, newest `start_unix_nano` first, first `limit`; for each: root span (no parent) `service`/`name`, `start`, `duration_ms`, the first error span (`service`, `name`, `status_message`, attributes), `path` = service names from root to the error span following `parent_span_id` |
| `get_trace` | `spans(trace_id=…)`; empty → `not_found`; `start_offset_ms` relative to the earliest span; order error spans first, then `duration_ms` desc; max 50 |
| `get_alerts` | `alerts(window)` rows overlapping the window, `rootline="true"` only, `state = firing` if `ends_at` is null or after `now`, else `resolved`; sort `starts_at` asc |

Every input model has `ConfigDict(extra="forbid")`; no field accepts a namespace. Live queries always include `namespace="shop"` (Prometheus kube-state/cAdvisor metrics), `k8s_namespace_name="shop"` (Loki), `k8s.namespace.name=shop` (Tempo), injected in `LiveTelemetry` (MCP-008, ARC-011). Required scope for all tools: `telemetry:read`; signal types from `rootline_schemas.tools.SIGNAL_TYPES`.

- [ ] **Step 1: Failing replay tests (TST-MCP-001)** — for each of the 8 tools, call it through `dispatch()` against `ReplayTelemetry(SnapshotStore(fixture))` with `now = manifest.replay_now`, and assert: output validates against the tool's Pydantic **output** model in `models.py` (one model per tool, field names exactly §8.2.1); canonical JSON ≤ 12,000 chars; timestamps match `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z`; list order per the table. Specific expectations from the fixture: `find_anomalies` returns `payment error_ratio` first with `direction == "up"`; `get_metric_series(payment, error_ratio)` has `len(series) == 30`; `get_metric_series(cart, gc_pause)` → `invalid_argument`; `get_trace("0"*32)` → `not_found`; a 2-hour `start/end` range → `invalid_argument`; a range before the capture window → `outside_window`.
- [ ] **Step 2: Failing scoping test (TST-MCP-005)** — (a) every input model rejects an extra field `namespace` (`invalid_argument`); (b) `LiveTelemetry` with a recording fake HTTP transport: every PromQL query string sent contains `namespace="shop"` or a `service=` matcher restricted to kept services, every Loki query contains `k8s_namespace_name="shop"`, every Tempo search contains `k8s.namespace.name=shop`; (c) `search_logs(service="faultlab")` → `invalid_argument "unknown service"`.
- [ ] **Step 3: Implement** `models.py`, `backend.py`, `replay.py` (DuckDB SQL over the views with `WHERE ts BETWEEN ? AND ?`), `live.py` (reuses the faultlab `queries.py` adapters — move `Prom`, `Loki`, `Tempo` from `rootline_faultlab.capture.queries` to `rootline_mcp_telemetry.upstreams` and import them from faultlab; one implementation for capture and live tools), `tools.py`, `app.py`.
- [ ] **Step 4: Live smoke** — with the cluster up and a flag fault injected by the new debug subcommand `rootline-faultlab inject --scenario scn-v1-flag-payment-failure-01` (injects without capture or restore; refuses unless `ROOTLINE_ENV=local`), run `uv run python -m rootline_mcp_telemetry.smoke --live` which calls every tool once via in-process dispatch with live backends and prints sizes; then restore with `rootline-faultlab restore --run <id>`.
- [ ] **Step 5: Commit** `feat(mcp-telemetry): add telemetry MCP server with live and replay backends`.

---

### Task W3-T07: `rootline-k8s` MCP server

**Requirement IDs:** §8.3, MCP-030, MCP-031, MCP-008, MCP-050, TST-MCP-001, TST-MCP-005, SEC-070 (mcp-k8s).
**Depends on:** W3-T05. **Parallel-safe** with W3-T06. **Branch:** `feat/w3-mcp-k8s`.

**Files:** `services/mcp-k8s/rootline_mcp_k8s/{backend,live,replay,tools,models,app}.py`; tests `test_tools_replay.py`, `test_scoping.py`, `test_redaction_env.py`.

**Interfaces:** `K8sBackend` Protocol — `async objects(kind: str) -> list[dict]` (kinds `Deployment`, `StatefulSet`, `ReplicaSet`, `Pod`, `Service`, `ConfigMap`, `NetworkPolicy`, `Node`, `Application`), `async events() -> list[dict]`, `async pod_log(pod, container, previous, tail) -> list[str] | None`. `LiveK8s` lists with namespace `shop` hard-coded (Application: namespace `argocd`, name `workload` only); `ReplayK8s` reads `k8s/objects.json`, `k8s/events.json`, `k8s/pod_logs/*`.

**Tool semantics:** exactly the §8.3 table. Additional rules:
- `list_workloads`: Deployments and StatefulSets; `desired = spec.replicas`, `ready = status.readyReplicas or 0`, `available = status.availableReplicas or 0`; `images` = container images; `last_rollout_at` = newest owned ReplicaSet `creationTimestamp` (Deployments) or `status.updateRevision`'s ControllerRevision time if present (StatefulSets: `null` when unknown); sort by `ready/desired` asc (desired 0 → ratio 1.0), then name.
- `describe_workload`: env per MCP-030 (`secretKeyRef` → `{"name": n, "value_from": "secret:<name>/<key>"}`; `configMapKeyRef` resolved from the ConfigMap and redacted; `fieldRef` → `{"value_from": "field:<path>"}`); `replica_sets` last 5 by revision annotation `deployment.kubernetes.io/revision`.
- `get_pods`: pods whose `ownerReferences` chain leads to the named workload (ReplicaSet → Deployment, or StatefulSet); `ready` = all containers ready.
- `get_events`: `since` window default `15m` relative to `now`; filter by `involvedObject.kind/name` when given; `types` default both; sort `last_ts` desc; max 50; messages ≤ 300 chars.
- `get_pod_logs`: pod must exist in `shop` objects (else `not_found`, MCP-031); container default = first container; replay serves only captured log files and returns `not_found` with message `"logs not captured for this pod"` otherwise; each line ≤ 300 chars, total ≤ 8,000 chars (drop oldest lines first).
- `get_configmap`: JSON-looking values (`{` or `[` first char) pretty-printed with `indent=2, sort_keys=True`; each value ≤ 2,000 chars.
- `get_argocd_app`: from the Application object: `sync_status`, `health_status`, `revision` (`status.sync.revision`), `history` (last 10, newest first), `out_of_sync` = resources with `status != "Synced"`, `degraded` = resources with `health.status == "Degraded"` (with `health.message`).
- Scope `k8s:read` for all eight tools.

- [ ] **Step 1: Failing tests** — fixture snapshot from W3-T06 extended with `k8s/objects.json` (2 Deployments `payment`, `cart`; 1 StatefulSet `valkey-cart`; ReplicaSets; 3 Pods with one CrashLoopBackOff; Services; ConfigMap `flagd-config`; NetworkPolicies; Application `workload` OutOfSync on `ConfigMap/flagd-config`), `events.json` (5 events), `pod_logs/payment-abc-123__payment.log`. Assertions: schemas and sort orders; `describe_workload(Deployment, payment)` shows `{"name": "API_TOKEN", "value_from": "secret:payment-secrets/token"}` and redacts a literal `password=hunter2`; `get_pod_logs("faultlab-xyz")` → `not_found`; `describe_workload(kind="Secret", …)` → `invalid_argument`; an extra `namespace` field → `invalid_argument`; `LiveK8s` with a fake API client records only calls with namespace `shop` (or `argocd`/`workload` for the Application, and cluster-scoped Nodes).
- [ ] **Step 2: Implement; live smoke** against the cluster; **commit** `feat(mcp-k8s): add Kubernetes MCP server`.

---

### Task W3-T08: `rootline-gitops` MCP server (read tools)

**Requirement IDs:** §8.4 (`get_recent_changes`, `get_commit_diff`, `get_proposal_status` stub), MCP-050, TST-MCP-001.
**Depends on:** W3-T05, W2-T07. **Parallel-safe** with W3-T06/T07. **Branch:** `feat/w3-mcp-gitops-read`.

**Files:** `services/mcp-gitops/rootline_mcp_gitops/{backend,live,replay,tools,models,app}.py`; tests.

**Tool semantics:**
- `get_recent_changes`: window `Nm|Nh` up to `24h` (`max_minutes=1440`), default `60m`; commits newest first, max 30; `short_sha` = first 7; `files[].workload` = `<component>` for paths `workload/<component>.yaml`, `null` otherwise; author = `author_name`; message ≤ 300 chars. Live via `EnvRepo.list_commits` using the `rootline-agent` App installation token (W3-T10) — until O-7 is done, live mode uses the `rootline-faultlab` App credentials read-only and logs a warning; this fallback is removed in W3-T10.
- `get_commit_diff`: `sha` 7–40 hex; prefix-resolved against known commits (ambiguous prefix → `invalid_argument "ambiguous sha"`); unknown → `not_found`; diff ≤ 300 lines with the truncation marker.
- `get_proposal_status`: returns `not_found` until W5-T03 wires it to `api`.
- Scopes: `gitops:read` for these three; `propose_fix` (scope `gitops:propose`) is added in W5-T03.

- [ ] **Steps:** failing replay tests against fixture `git/commits.json` + `git/diffs/*.diff` (3 commits: baseline, fault, revert) → implement → live smoke → commit `feat(mcp-gitops): add read-only GitOps MCP tools`.

---

### Task W3-T09: Live/replay parity (MCP-053, TST-MCP-010)

**Requirement IDs:** MCP-053, TST-MCP-010, LAB-041 step 4, PG-5, R6.
**Depends on:** W3-T06, W3-T07, W3-T08. **Branch:** `feat/w3-parity`.

**Files:**
- Create: `services/faultlab/rootline_faultlab/capture/parity.py`, `libs/py-mcpkit/rootline_mcpkit/parity.py` (comparison rules)
- Modify: `services/faultlab/rootline_faultlab/orchestrator.py` (step 4 runs parity; manifest `parity: true`), `services/faultlab/pyproject.toml` (runtime deps on the three MCP server packages)
- Test: `libs/py-mcpkit/tests/test_parity_compare.py`, `tests/parity/test_tst_mcp_010.py`

**Interfaces:** `rootline_faultlab.capture.parity.run_parity(target: str, live: LiveBackends, now: datetime) -> list[dict]` (lines `{tool, args, output}`); `rootline_mcpkit.parity.compare(tool: str, live: dict, replay: dict) -> list[str]` (empty = equal).

- [ ] **Step 1: Parity calls (MCP-053)** — `run_parity` calls, through `dispatch()` with live backends and a synthetic system principal, in this order: `get_alerts(15m)`, `list_services(15m)`, `get_service_graph(15m)`, `find_anomalies(15m)`, `get_metric_series(<target svc>, m)` for `m ∈ {error_ratio, latency_p95, request_rate}`, `search_logs(<target>, 15m)`, `get_error_traces(<target>, 15m)`, `get_trace(<first trace id from get_error_traces>)` (skipped if none), `list_workloads()`, `describe_workload(<kind of target>, <target>)`, `get_pods(<target>)`, `get_events()`, `get_configmap("flagd-config")`, `get_network_policies()`, `get_argocd_app()`, `get_recent_changes(60m)`, `get_commit_diff(<newest sha>)`. Output written to `parity/live_outputs.jsonl` with `json.dumps(line, sort_keys=True)`.
- [ ] **Step 2: Comparison rules (`compare`)** — recursively walk both outputs:
  - set equality (order-insensitive) for: alert identities `(alertname, service, starts_at)`; workloads names; pod names; event identities `(reason, involved, first_ts)`; commit SHAs; log template strings; error trace IDs;
  - numbers: equal within 2% relative or 1e-6 absolute;
  - anomaly onsets (`onset_ts`, `start`) within ±15 s;
  - `series` arrays: compared point-wise by value tolerance (replay is computed from Parquet at 15 s; live from PromQL range at 15 s);
  - other strings: equal, except `notes`, `truncated`, `omitted_count` which are ignored.
  Unit tests cover each rule with crafted pairs.
- [ ] **Step 3: TST-MCP-010** — `tests/parity/test_tst_mcp_010.py` iterates every snapshot in `data/snapshots/v1/*/*` whose manifest has `parity: true` (skip the test with a clear message when none exist; CI has none), replays each line of `parity/live_outputs.jsonl` against `ReplayTelemetry/ReplayK8s/ReplayGitops` at `now = replay_now`, and asserts `compare(...) == []`, collecting all failures before failing. Run it with `uv run pytest tests/parity -v`.
- [ ] **Step 4: Wire into capture** — orchestrator step 4 calls `run_parity` and sets `parity: true`; a parity exception logs and sets `parity: false` without failing the run.
- [ ] **Step 5: Verify on a fresh capture** of 3 scenarios (one per channel) → TST-MCP-010 passes on them. If it fails, fix the tool or backend before any further capture (R6). **Commit** `feat(faultlab): record live tool outputs at capture and test replay parity`.

---

### Task W3-T10: GitHub Apps `rootline-agent` and `rootline-gate`, rulesets, App secrets

**Requirement IDs:** SEC-080, SEC-081, SEC-082 (verify), GEN-024, O-7.
**Depends on:** W3-T08. **Branch:** `feat/w3-github-apps`.

- [ ] **Step 1 [OWNER] (O-7): Create the two Apps** (same procedure as O-5, documented in `wiki/runbooks/github-apps.md`):
  - `rootline-agent`: Contents RW, Pull requests RW, Metadata R.
  - `rootline-gate`: Contents RW, Pull requests RW, Checks RW, Commit statuses R, Metadata R.
  Install both only on `rootline-env`. Put `GH_APP_AGENT_*`, `GH_APP_GATE_*` in `.env.local`; record the bot logins (`<slug>[bot]`) in `wiki/components/mcp-gitops.md` and `gate.md`. Spec text `rootline-agent[bot]` means the actual agent App bot login; the gate compares against the configured value `GITOPS_AGENT_BOT_LOGIN`.
- [ ] **Step 2 [CONFIRM]: Ruleset `protect-main` on `rootline-env`** (SEC-081) — `.github/rulesets/env-protect-main.json` in `rootline` (documentation copy) and applied with `gh api -X POST repos/arkhash0309/rootline-env/rulesets --input .github/rulesets/env-protect-main.json`: rules `deletion`, `non_fast_forward`, `required_linear_history`, `pull_request` (0 approvals), `required_status_checks` with `{"context": "rootline-gate/policy", "integration_id": <gate App ID>}`; `bypass_actors`: `{actor_id: <faultlab App ID>, actor_type: Integration, bypass_mode: always}`, `{actor_id: <gate App ID>, actor_type: Integration, bypass_mode: always}`, `{actor_id: 5, actor_type: RepositoryRole, bypass_mode: always}`. Verify: with the `rootline-agent` installation token (not a bypass actor), create a commit object and call `PATCH /repos/arkhash0309/rootline-env/git/refs/heads/main` → the API rejects it with HTTP 422 and a "Repository rule violations" message. Record the response in `wiki/runbooks/github-apps.md`.
- [ ] **Step 3: ExternalSecrets** `github-app-agent` (consumer `mcp-gitops`) and `github-app-gate` (consumer `gate`) from store `bootstrap`; `mcp-gitops` live mode switches to the agent App (remove the W3-T08 fallback).
- [ ] **Step 4: Verify deploy keys are read-only** (SEC-082): `gh api repos/arkhash0309/rootline/keys` and `.../rootline-env/keys` show `read_only: true`.
- [ ] **Step 5: Commit** `feat(deploy): add agent and gate GitHub App secrets and env-repo ruleset`.

---

### Task W3-T11: `faultlab` internal API (LAB-046) and demo mode server

**Requirement IDs:** LAB-046, LAB-040 (demo), LAB-042, SEC-050, SEC-060 (pattern).
**Depends on:** W3-T02, W2-T10. **Branch:** `feat/w3-faultlab-api`.

**Files:** `services/faultlab/rootline_faultlab/api.py` (FastAPI), `serve` subcommand; tests `test_api.py`.

- [ ] **Step 1: Failing tests** — FastAPI `TestClient` with `TokenValidator` over static-test JWKS (`ROOTLINE_ENV=test`): `POST /internal/v1/runs` with a token `aud=rootline-faultlab, azp=rootline-api, scope=api:internal` → 202 `{run_id}`; same with `azp=rootline-agent` → 403 problem `forbidden`; without token → 401 problem `unauthenticated`; second POST while a demo run is active → 409 problem `lab_busy`; `mode: "capture"` → 422; `POST /internal/v1/runs/{id}/restore` → 202 and the run transitions to `demo_restored` (orchestrator fake); `GET /internal/v1/runs/{id}` → the run record; unknown id → 404. Auto-restore: with a fake clock, a demo run is restored 15 min after `injected_at`.
- [ ] **Step 2: Implement** — app factory with `RequestIdMiddleware`, problem handlers, health router (`db`), a dependency `require_internal(azp_allow={"rootline-api"})` that validates `Authorization: Bearer` with `TokenValidator(audience="rootline-faultlab", allow_user_tokens=True)` (service-account tokens of `rootline-api` are classified `user` because their `azp` is not the agent; the dependency then checks `azp` and `api:internal` scope itself), the three endpoints, and a background task (started in lifespan) that every 30 s restores demo runs older than 15 min. `serve` runs uvicorn on 8080. The Deployment command changes from `idle` to `serve`.
- [ ] **Step 3: Commit** `feat(faultlab): add internal run API with demo auto-restore`.

---

### Task W3-T12: RBAC, NetworkPolicies and Kyverno policies

**Requirement IDs:** SEC-070, SEC-090, SEC-120, ARC-010, ARC-011, T5, T10.
**Depends on:** W3-T06 … W3-T08. **Branch:** `feat/w3-policies`.

**Files:**
- Create: `deploy/charts/rootline/templates/{mcp-k8s/rbac.yaml,netpol/*.yaml}`; `policies/kyverno/{verify-rootline-images,restrict-rootline-registries,disallow-privileged,require-resources,workload-confinement}.yaml`, `policies/kyverno/allowed-upstream.yaml`, `policies/kyverno/tests/<policy>/{kyverno-test.yaml,resources.yaml}`
- Modify: `deploy/charts/platform-config/templates/kyverno.yaml` (installs the ClusterPolicies with `validationFailureAction` per env: SEC-090 table; `verify-rootline-images` rendered only on gke)

- [ ] **Step 1: mcp-k8s RBAC** exactly SEC-070 (Role in `shop` with the listed groups/resources/verbs; Role in `argocd` `get` on `applications` `resourceNames: [workload]`; ClusterRole `get,list` on `nodes`). A chart unit test asserts the rendered rules equal the SEC-070 row; step 4 checks them live.
- [ ] **Step 2: NetworkPolicies (SEC-120)** — one policy per row, in namespace `rootline`, selecting pods by `app.kubernetes.io/name: <component>`. Egress to the internet on 443 is `ipBlock: {cidr: 0.0.0.0/0, except: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]}` only for the pods listed (agent; mcp-gitops, gate, faultlab). Calls to `https://auth.D` go through Traefik: egress to namespace `kube-system` (local/ci) or `traefik` (gke) pods `app.kubernetes.io/name: traefik` on ports 8443 and 443 (container port of websecure) — verify the Traefik container port in the cluster and record it. kube-apiserver egress: `ipBlock` with the API server endpoint IP from `kubectl get endpoints kubernetes -n default` on 6443 (local) / 443 (gke), templated from values `network.apiServerCIDR` (`task up` reads it and passes it as a root parameter).
- [ ] **Step 3: Kyverno policies (SEC-090)** — write the five ClusterPolicies; `restrict-rootline-registries` allows `rootline/*:dev`, `rootline/*:ci`, the Artifact Registry prefix (gke), and the exact digests listed in `allowed-upstream.yaml` (OPA image, busybox, kubectl-image, python-image used by Jobs); `disallow-privileged` excludes `otel-collector` in `observability` for read-only `hostPath: /var/log/pods`; `workload-confinement` matches resources with label `argocd.argoproj.io/instance: workload`. For each policy, a `kyverno test` case with one passing and one failing resource. Run `kyverno test policies/kyverno` (CI `policy` job now active).
- [ ] **Step 4: Live verification** — sync; `kubectl auth can-i list secrets -n shop --as system:serviceaccount:rootline:mcp-k8s` → `no`; `kubectl auth can-i get pods -n rootline --as system:serviceaccount:rootline:mcp-k8s` → `no`; `kubectl run probe -n rootline --image=busybox --restart=Never -- sleep 1` → denied by `restrict-rootline-registries`; from a debug pod labelled as `api`, `wget` to `mcp-k8s:80` fails (only `agent` may reach MCP servers). Record outputs in `wiki/security/threat-model.md` under T4, T5, T10 evidence.
- [ ] **Step 5: Commit** `feat(policies): add RBAC, network policies and Kyverno admission policies`.

---

### Task W3-T13: Deploy the MCP servers; in-process replay sessions

**Requirement IDs:** ARC-001 (mcp-*), ARC-030, SEC-033, SEC-051, MCP-051, OBS-002.
**Depends on:** W3-T06 … W3-T12. **Branch:** `feat/w3-mcp-deploy`.

**Files:**
- Create: `services/mcp-{telemetry,k8s,gitops}/Dockerfile` (W2-T11 pattern), `deploy/charts/rootline/templates/mcp-{telemetry,k8s,gitops}/{deployment,service,serviceaccount}.yaml`
- Create: `libs/py-mcpkit/rootline_mcpkit/inprocess.py`; test `libs/py-mcpkit/tests/test_inprocess.py`

- [ ] **Step 1: Chart** — each Deployment: 1 replica, port 8080 named `http`, probes, resources per ARC-030, env `ROOTLINE_MCP_MODE=live`, `AUTH_MODE=jwt`, `KEYCLOAK_ISSUER=https://auth.{{D}}/realms/rootline`, `ROOTLINE_DELEGATION_MODE={{ .Values.security.delegationMode }}`, `ROOTLINE_AGENT_ACTOR_SUB` (the agent service-account user ID: looked up once by the keycloak-config Job and written to ConfigMap `rootline-agent-identity` key `actor_sub`; add that step to the W3-T01 Job), `SSL_CERT_FILE`, mounts `rootline-ca`. `mcp-k8s` uses its own ServiceAccount token (automount true); `mcp-gitops` mounts the projected Keycloak token (it calls `api` later) and Secret `github-app-agent`; `mcp-telemetry` needs no Kubernetes API access (automount false).
- [ ] **Step 2: In-process sessions (MCP-051)** — `open_inprocess_sessions(snapshot_dir, issuer)` builds the three servers in replay mode (`build_mcp_server`), connects each with the SDK's in-memory transport (`mcp.shared.memory.create_connected_server_and_client_session` — verify the name in the pinned SDK; if absent, start each `build_app` with uvicorn on `127.0.0.1:0` and connect with `streamablehttp_client`), sets the principal context var to a `Principal` minted by `issuer` with all read scopes (validated once through `StaticTestAuthenticator`, so SEC-053 still applies), and yields `{"telemetry": session, "k8s": session, "gitops": session}`. Test: opening sessions on the fixture snapshot and calling `list_services` through the client returns the same structured content as `dispatch()`.
- [ ] **Step 3: Deploy and verify** — `task images`, sync; `kubectl -n rootline get pods` all Ready; from a debug pod with the agent's labels and its projected token, perform a system-mode token request and a `tools/list` against each server (script `scripts/mcp_probe.py`, run inside the agent pod in W4; for now inside a temporary pod using the agent ServiceAccount) → 200 with tool lists; record in `wiki/components/mcp-*.md`.
- [ ] **Step 4: Commit** `feat(deploy): deploy MCP servers; add in-process replay sessions`.

---

### Task W3-T14: Capture continuation and week 3 acceptance

**Requirement IDs:** S3 (progress), MS-001 week 3, PG-5, O-6.

- [ ] **Step 1:** Batches `capture-<date>-b/c.yaml` covering remaining base scenarios in catalogue order until ≥ 150 total `captured`, of which ≥ 20 have `parity: true` (all captures from now on have parity). Run overnight (O-6), `task lab:pull`.
- [ ] **Step 2:** `uv run pytest tests/parity -v` → PASS on every parity snapshot.
- [ ] **Step 3: Acceptance** — TST-SEC-005, 010–016, 020, 030 and TST-MCP-001/005/010/020 pass (list each with the command and result in the release PR); ADR 0010 has the final mode; `task doctor` memory ≤ 9.5 GiB (update `capacity.md`; apply ARC-031 if needed).
- [ ] **Step 4: Release** `release: milestone 3` with wiki updates (`status.md` → Week 4 — Minimal end-to-end version).
