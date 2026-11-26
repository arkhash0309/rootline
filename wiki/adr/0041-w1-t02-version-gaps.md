# 0041 — Version pinning gaps found in W1-T02 (spec-gap)

Status: accepted
Date: 2026-11-27
Label: spec-gap
Plan gap: PG-22 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

The implementation of W1-T02 (branch `feat/w1-versions`, commit `bef5406`, plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T02") resolved every GEN-050 line on 2026-11-27 and found seven questions that the spec (GEN-050, GEN-051), the plan and the schedule (`docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`) do not answer. They are lettered A to G; each Decision item names the letter it answers.

- **A. Ownership of `wiki/versions.md`.** W1-T02 "Files" says "Create: `wiki/versions.md`", and W1-T03 "Files" excludes it, but the schedule YAML lists it in no task's `owns`. W1-T03's `owns` is `wiki/**`, with only `wiki/runbooks/local-up.md` in `excludes`, so W1-T03 owned the page. The W1-T03 Step 5 table also told W1-T03 to create the stub, which contradicts its "Files" list. `check_ownership.py --task W1-T02` therefore fails on the committed stub. Adding the path only to W1-T02's `owns` makes `validate` report `W1-P1: W1-T02 and W1-T03 both own wiki/versions.md` (checked on 2026-11-27).
- **B. `scripts/check_versions.py` has no interface.** W1-T02 "Files" creates it, but no step and no "Interfaces" entry defines its arguments, output or exit codes.
- **C. Chart rows.** W1-T02 Steps 3 and 5 say chart entries are `{version: <app version>, chart: <chart version>, repo}`, while the `CONSTRAINTS` regex applies to `version`. For most chart keys the GEN-050 line is on the chart (`loki` chart 6.x, `kyverno` chart 3.x, `chaos-mesh` chart 2.x at 2.7.0 or above, `cert-manager` chart 1.x, `opentelemetry-demo` chart exactly 0.42.8). Storing the app version in `version` checks the wrong number: Loki app `3.6.7` fails `^6\.\d+\.\d+$` although chart `6.55.0` is inside the line. Only `argo-cd` ("`argo-cd` (app) 3.x") and `traefik` (Traefik 3.x; the chart `traefik/traefik` is at `43.0.0`) have their line on the application.
- **D. `pathspec`.** The version table says "latest 0.x" with no pinned value. `pathspec` 1.x exists (1.1.1 on 2026-11-27). `mypy` 1.20 requires `pathspec` 1.x, so with `pathspec` on 0.x uv resolves an older `mypy` inside the dev constraint `mypy>=1.18,<2`.
- **E. `kubectl-image`.** The table says `{version, repo: bitnami/kubectl, digest}` "matching the cluster minor". On 2026-11-27 `docker.io/bitnami/kubectl` publishes only the tag `latest` (kubectl 1.37.3, image label `org.opencontainers.image.version`); no 1.36 tag exists. The cluster minor is 1.36 (`k3s` `v1.36.6+k3s1`). The W1-T02 implementer pinned `latest` (1.37.3), one minor ahead.
- **F. Image `repo` spelling.** The schema says `repo` is a "Helm repo URL or image repo" without saying whether the registry host is included. The implementer wrote fully qualified repositories (`docker.io/library/python`, `docker.io/openpolicyagent/opa`, `ghcr.io/cloudnative-pg/postgresql`).
- **G. Pin date.** GEN-050 says versions are resolved "on the pin date" and recorded in `wiki/versions.md`, but no document states which date W1-T02 used.

## Decision

Each decision follows spec §0.3 (simplest, cheapest, safest, in that order). None changes cost, security posture or scope; the owner's standing instruction for this work is to take the recommended option.

1. **(A)** `wiki/versions.md` is owned by W1-T02. The schedule YAML adds `wiki/versions.md` to W1-T02 `owns` and to W1-T03 `excludes`, so the two W1-P1 tasks stay disjoint; `uv run python scripts/swarm_schedule.py validate` prints `schedule OK: 8 weeks, 39 stages, 94 tasks`. W1-T02 creates the stub in stage W1-P1 with exactly three lines: `# Versions`, an empty line, `Status: not implemented yet — planned in W1-T02 step 8.` Its deferred Step 8 (stage W1-S3) replaces the stub. W1-T03 does not create the page, but its `wiki/index.md` lists it (`- [versions.md](versions.md) — pin date and resolved versions (GEN-050)`). On `feat/w1-wiki` alone `scripts/wiki_lint.py` therefore prints exactly `wiki-lint: broken-link: index.md -> versions.md` (W1-T03 Step 6 and W1-T04 Step 2 expect this line); on `integration/w1-p1`, where both branches are merged and gate check G11 runs the lint, it prints nothing and exits 0.
2. **(A, base)** The W1-P1 stage base moves from `f85bb63` to the first `origin/develop` commit that contains this ADR (the squash merge of `docs/w1-t02-gaps`). The coordinator records that commit in `.swarm/stages/W1-P1.json` before it dispatches W1-T03 and before it creates `integration/w1-p1`. Reason: W1-T03's `wiki/index.md` must list `adr/0041-w1-t02-version-gaps.md`, and that link resolves only when the ADR is on the branch. `feat/w1-versions` is not rebased: `git diff <base>...feat/w1-versions` uses the merge base `f85bb63`, so the paths that `check_ownership.py` checks do not change. If `feat/w1-wiki` already exists on an older base, its implementer rebases it onto the new base before W1-T03 Step 5.
3. **(B)** `scripts/check_versions.py` is a CLI run as `uv run python scripts/check_versions.py`, with no arguments. It runs `validate()` over `versions.yaml` and prints one line per error to stderr. Exit codes:

   | Case | Output (stderr) | Exit |
   |---|---|---|
   | No validation error | nothing | 0 |
   | One or more validation errors | one line per error, the `validate()` string (`<key>: <problem>`), in `validate()` order | 1 |
   | `versions.yaml` missing or unreadable, or its top level is not a mapping | one line `versions.yaml: <exception text>` | 2 |

   It writes no file and makes no network call. The final text of the script is in W1-T02 Step 4; the interface is in W1-T02 "Interfaces".
4. **(C)** In a chart row, `version` holds the value that the key's GEN-050 line constrains, and `CONSTRAINTS` applies to `version`: the chart version for `kube-prometheus-stack`, `loki`, `tempo`, `opentelemetry-collector`, `chaos-mesh`, `kyverno`, `external-secrets`, `cert-manager`, `cloudnative-pg`, `opentelemetry-demo` and the extra key `prometheus-operator-crds`; the application version for `argo-cd` and `traefik`. `chart` holds the chart version. `app` holds the application version; it MUST be written when it differs from `version` and MAY be written when the two are equal. `repo` is the Helm repository URL. The `opentelemetry-demo` row stays exactly `{version: "0.42.8", chart: "0.42.8", app: "3.1.0", repo: "https://open-telemetry.github.io/opentelemetry-helm-charts"}`. Examples on 2026-11-27: `argo-cd` `{version: "3.6.3", chart: "10.20.0"}`, `traefik` `{version: "3.8.0", chart: "43.0.0"}`, `loki` `{version: "6.55.0", chart: "6.55.0", app: "3.6.7"}`.
5. **(D)** `pathspec` is pinned to `0.12.1`, the latest 0.x release on 2026-11-27, with the root `dev` constraint `pathspec>=0.12.1,<0.13`. The `mypy` constraint stays `mypy>=1.18,<2`, inside which uv resolves `mypy` `1.19.1`, because `mypy` 1.20 requires `pathspec` 1.x. This is expected. Moving to `pathspec` 1.x is a major-version change that needs its own ADR under GEN-051.
6. **(E)** `kubectl-image` is `{version: "1.36.<patch>", repo: "docker.io/rancher/kubectl", digest: "sha256:<64 hex>"}`: the highest Docker Hub tag `v1.36.<patch>` of `docker.io/rancher/kubectl`, `version` without the leading `v`, `digest` the multi-arch index digest of that tag. The image reference used in manifests is `<repo>:v<version>@<digest>`. On 2026-11-27 the highest tag is `v1.36.2`, digest `sha256:06c7a7a9772737494ae1e0c3af90f1b5385630c147e47c1c7cea92f4bed55fbe` (Docker Hub tag listing and `docker buildx imagetools inspect`). The repository changed from `bitnami/kubectl` because `bitnami/kubectl` has no 1.36 tag; an exact minor match is the safest option and costs nothing. The W1-T02 implementer replaces the `kubectl-image` row of `versions.yaml` on `feat/w1-versions`.
7. **(E, consequence)** `docker.io/rancher/kubectl:v1.36.2` contains only `/bin/kubectl` (entrypoint `/bin/kubectl`, user `kubectl`, UID 1000; no `/bin/sh`, checked on 2026-11-27 with `docker export`). The `copy-ca` Job of W1-T10 Step 5 therefore cannot run a shell pipeline. It runs `["/bin/kubectl", "apply", "-k", "/work"]`, where `/work` is a read-only `projected` volume with ConfigMap `copy-ca-kustomization` (key `kustomization.yaml`, a `configMapGenerator` producing ConfigMap `rootline-ca` key `ca.crt` in `rootline` and in `keycloak`, `disableNameSuffixHash: true`) and secret `rootline-local-ca` (item `ca.crt`). The kubelet, not the ServiceAccount, reads the secret, so the `cert-manager` Role with `get` on that secret is dropped; the Roles in `rootline` and `keycloak` (`get,create,patch` on configmaps) stay. The full Job specification is in W1-T10 Step 5.
8. **(F)** For every image row (`postgres-image`, `kubectl-image`, `busybox`, `uv-image`, `python-image`, `node-image`, `opa-image`, and the `keycloak` and `keycloak-config-cli` mappings), `repo` is the fully qualified image repository: registry host included, tag excluded. Docker Hub official images are `docker.io/library/<name>`, other Docker Hub images `docker.io/<namespace>/<name>`, other registries use their own host (`ghcr.io/…`, `quay.io/…`). This is how the W1-T02 implementer wrote them.
9. **(G)** The W1-T02 pin date is `2026-11-27`, the date of the lookup: `versions.yaml` has `pin_date: "2026-11-27"`, and every value in it was looked up that day. Step 8 writes the same date into `wiki/versions.md`.

## Consequences

- W1-T02 "Files", "Interfaces", the version table (`pathspec`, `kubectl-image`, the image-row note), Steps 3 to 9 and the schedule YAML (W1-T02 `owns`, W1-T03 `excludes`) were amended on 2026-11-27 on branch `docs/w1-t02-gaps`. The wave-file "Execution schedule" table is unchanged, because it shows no `owns` or `excludes`.
- The W1-T02 implementer changes `kubectl-image` in `versions.yaml` to `docker.io/rancher/kubectl` `v1.36.2` with its digest; every other value on `feat/w1-versions` (`bef5406`) already follows decisions 3 to 9.
- W1-T03 lists `adr/0041-w1-t02-version-gaps.md` and `versions.md` in `wiki/index.md`, and does not create either file. W1-T04 does not create, edit or renumber ADR 0041 or its spec §26 row; the next free ADR number after W1-T04 is 0042.
- W1-T10 implements the shell-less `copy-ca` Job (decision 7). W3-T12 Step 3 (`docs/superpowers/plans/2026-11-26-rootline-w3-identity-mcp.md`) lists the `kubectl-image` digest in `allowed-upstream.yaml` for the Kyverno policy `restrict-rootline-registries`; it takes the digest from `versions.yaml`, which now holds the `docker.io/rancher/kubectl` digest, so W3-T12's text needs no change.
- The coordinator moves the W1-P1 stage base (decision 2) before it dispatches W1-T03.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| (A) W1-T03 keeps owning `wiki/versions.md` and W1-T02 drops the stub | W1-T02's Step 8 then edits a page owned by another task, and the committed stub on `feat/w1-versions` would have to be removed; one owner for the page the task fills is simpler |
| (A) W1-T03's index omits `versions.md` until W1-S3 | `wiki_lint.py` reports `index-missing: versions.md` on `integration/w1-p1`, so G11 fails there |
| (A, base) The W1-T03 implementer merges `origin/develop` into `feat/w1-wiki` | The merge brings plan and schedule files that W1-T03 does not own, so `check_ownership.py --task W1-T03` fails |
| (C) Keep `version` = application version and add a second regex for charts | Two constraint fields per key for no gain; GEN-050 names one line per key |
| (D) Move to `pathspec` 1.x to get `mypy` 1.20 | The W1-T16 table fixed the 0.x line; a major change after the line is set needs a GEN-051 ADR and a re-test of `swarm_lib.matches` |
| (E) Keep `bitnami/kubectl:latest` (1.37.3) | One minor ahead of the cluster; the plan asks for the cluster minor, and `latest` moves, so the next lookup would silently change the minor |
| (E) `registry.k8s.io/kubectl` or `alpine/k8s` | Not named by any document; `docker.io/rancher/kubectl` is published by the k3s vendor, has a tag for every 1.36 patch, and gives an exact minor match |
| (E) A busybox container that calls the API with `wget` | Needs TLS and JSON handling by hand; `kubectl apply -k` over a projected volume needs no shell and no extra image |
| (F) Short names (`python`, `bitnami/kubectl`) | Kyverno digest allow-lists and `docker buildx imagetools inspect` need the full reference; short names depend on the runtime's default registry |

## Spec references

GEN-050, GEN-051, PG-16, PG-22, WIK-002, WIK-011, overview §5, §7.2, §7.4, §7.5, §7.6, §7.7 (G1, G11), W1-T02, W1-T03, W1-T04, W1-T10, W1-T16, ADR 0040, spec §0.3, spec §26.
