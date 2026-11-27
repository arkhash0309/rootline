# 0044 — Workload render keeps the objects its kept workloads reference (spec-gap)

Status: accepted
Date: 2026-11-27
Label: spec-gap
Plan gap: PG-25 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

The review of W1-T09 (workload render script, plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T09", branch `feat/w1-workload-render` at `e5a43f1`) ran the plan's Step 3 transform on the real chart output. The transform keeps an object only when its component is in `KEPT_COMPONENTS`. The component is the `app.kubernetes.io/component` label, or `metadata.name` when the label is absent. The rule drops objects that a kept workload needs.

The planner checked the facts again on 2026-11-27. It ran `helm template shop <cache>/opentelemetry-demo-0.42.8.tgz --namespace shop -f deploy/upstream/otel-demo/values.yaml`, with helm `v3.22.1` and the `values.yaml` from `e5a43f1`:

| Fact | Value |
|---|---|
| Objects in the render | 19 Deployments, 18 Services (every kept component except `fraud-detection`), 3 ConfigMaps, 1 ServiceAccount; no Secret, no Namespace, no StatefulSet |
| ServiceAccount | `shop`. Labels `helm.sh/chart`, `app.kubernetes.io/version`, `app.kubernetes.io/part-of`, `app.kubernetes.io/managed-by`; no `app.kubernetes.io/component` |
| References to `shop` | `spec.template.spec.serviceAccountName: shop` in all 19 Deployments |
| ConfigMap `postgresql-init` | No component label, key `init.sql`. Deployment `astronomy-db` mounts it as volume `postgresql-init` (`configMap.name: postgresql-init`) at `/docker-entrypoint-initdb.d` |
| ConfigMap `flagd-config` | No component label. Kept by the existing special case (WKL-010 step 6) in `workload/flagd-config.yaml` |
| ConfigMap `product-catalog-product-catalog-otel-config` | Label `app.kubernetes.io/component: product-catalog`. Kept by the component rule in `workload/product-catalog.yaml` |
| Other pod-spec references | None. No Deployment has `envFrom`, `env[].valueFrom.configMapKeyRef`, `secretKeyRef`, `secret` or `projected` volumes, or `imagePullSecrets` |
| `spec.template.spec.volumes` | `null` (not absent) in 14 of the 19 Deployments |

Two defects follow:

- **A. ServiceAccount dropped.** `component_of(ServiceAccount/shop)` is `shop`, which is not a kept component, so the object is dropped. The ServiceAccount admission plugin then rejects the pods of all 19 Deployments, because they name a ServiceAccount that does not exist.
- **B. ConfigMap dropped.** `component_of(ConfigMap/postgresql-init)` is `postgresql-init`, so the object is dropped. The `astronomy-db` pod stays in `ContainerCreating`, because its `configMap` volume cannot be mounted.

WKL-010 step 8 lists "ConfigMaps, ServiceAccount" among "each component's objects". It does not say how an object with no component is assigned, or what happens to a shared one. The test fixture `tests/repo/fixtures/otel-demo-mini.yaml` hid both defects: its only ServiceAccount carried the label `app.kubernetes.io/component: payment`.

## Decision

Each decision follows spec §0.3 (simplest, cheapest, safest, in that order). None of them changes cost, security posture or scope. The output keeps exactly the objects the kept workloads need to start. No Secret enters `rootline-env`, as before. The final code and tests are the W1-T09 Step 2, 3 and 4 blocks of `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md`, amended in the same PR as this ADR. The planner ran them on 2026-11-27 (Python `3.13.13`, PyYAML `6.0.4`, pytest `9.2.0`) against the amended fixture (15 tests passed; the 5 new tests that need the new code failed on `e5a43f1`) and against the real render above (22 files, below). After `ruff format`, ruff `0.17.6` gave `All checks passed!` for all three files, with the root `[tool.ruff]` settings.

### Terms

| Term | Meaning |
|---|---|
| component of an object | `metadata.labels["app.kubernetes.io/component"]` when present and non-empty, else `metadata.name` (function `component_of`, unchanged) |
| kept workload | A `Deployment` or `StatefulSet` whose component is in `KEPT_COMPONENTS` (the 19 WKL-002 names) |
| reference | A `(kind, name, optional)` triple read from the pod spec `spec.template.spec` of a kept workload, after WKL-010 steps 3 to 7 have changed it, by `pod_references` (D1) |
| required reference | A reference whose source has no `optional: true`. `serviceAccountName` and `imagePullSecrets` cannot be optional |
| placed object | An object put into the output by rule R1 (`flagd-config`) or R2 (component rule) of D1 |
| candidate | A `ServiceAccount` or `ConfigMap` that is not a Secret and not placed by R1 or R2 |

### D1 — Keep rule (A, B)

An object other than a `Secret` is kept when it is placed by R1 or R2, or when it is a candidate named by a reference of a kept workload (R3). Every other object is dropped. A `Namespace` object can only be kept by R2: no pod-spec field names a Namespace, so R3 never keeps one. The chart `0.42.8` render contains none.

References read by `pod_references(spec)` (missing fields and `null` values are treated as empty lists):

| Source in `spec.template.spec` | Reference kind | `optional` from |
|---|---|---|
| `serviceAccountName`, or the deprecated `serviceAccount` when `serviceAccountName` is empty | `ServiceAccount` | always `false` |
| `imagePullSecrets[].name` | `Secret` | always `false` |
| `volumes[].configMap.name` | `ConfigMap` | `volumes[].configMap.optional` |
| `volumes[].secret.secretName` | `Secret` | `volumes[].secret.optional` |
| `volumes[].projected.sources[].configMap.name` | `ConfigMap` | `…configMap.optional` |
| `volumes[].projected.sources[].secret.name` | `Secret` | `…secret.optional` |
| `containers[]` and `initContainers[]`: `envFrom[].configMapRef.name` | `ConfigMap` | `…configMapRef.optional` |
| `containers[]` and `initContainers[]`: `envFrom[].secretRef.name` | `Secret` | `…secretRef.optional` |
| `containers[]` and `initContainers[]`: `env[].valueFrom.configMapKeyRef.name` | `ConfigMap` | `…configMapKeyRef.optional` |
| `containers[]` and `initContainers[]`: `env[].valueFrom.secretKeyRef.name` | `Secret` | `…secretKeyRef.optional` |

An `optional` field that is absent counts as `false`. References are read after WKL-010 steps 3 to 7. For `flagd` this means after `_fix_flagd` (PG-11), so the removed `config-ro` volume and the removed init container `init-config` add no reference.

Pseudocode of `transform(docs)` (Python form: W1-T09 Step 3):

```
out        = {}            # file stem -> list of objects
placed     = {}            # set of (kind, name) already in out
candidates = {}            # (kind, name) -> object; kind in {ServiceAccount, ConfigMap}
referrers  = {}            # (kind, name) -> set of (component, workload kind, workload name)
required   = {}            # set of (kind, name) referenced at least once without optional: true

for obj in deep copies of docs, in input order:
    if obj.kind == "Secret": drop; continue                                    # WKL-010 step 2
    obj.metadata.namespace = "shop"; remove obj.metadata.managedFields         # WKL-010 step 1
    if obj.kind == "ConfigMap" and obj.metadata.name == "flagd-config":        # R1
        set every flag's defaultVariant to "off"; out["flagd-config"] += obj; placed += (kind, name); continue
    comp = component_of(obj)
    if comp not in KEPT_COMPONENTS:
        if obj.kind in {"ServiceAccount", "ConfigMap"}: candidates[(kind, name)] = obj
        continue                                                               # dropped unless R3 keeps it
    if obj.kind in {"Deployment", "StatefulSet"}:                              # kept workload
        apply WKL-010 steps 3, 4, 5, 6 (flagd), 7 (load-generator) to obj
        for (rkind, rname, optional) in pod_references(obj.spec.template.spec):
            referrers[(rkind, rname)] += (comp, obj.kind, obj.metadata.name)
            if not optional: required += (rkind, rname)
    out[comp] += obj; placed += (obj.kind, obj.metadata.name)                  # R2

errors = {}
for key = (kind, name) in sorted(referrers):
    if key in placed or key in AUTO_CREATED: continue
    if kind in {"ServiceAccount", "ConfigMap"} and key in candidates:          # R3
        comps = sorted distinct component of referrers[key]
        stem  = comps[0] if len(comps) == 1 else SHARED_STEMS[kind]            # D2
        out[stem] += candidates[key]; placed += key; continue
    if key not in required: continue                                           # optional and absent: ignored
    reason = "Secrets are removed by WKL-010 step 2" if kind == "Secret" else "not in the helm template output"
    for (comp, wkind, wname) in referrers[key]:
        errors += "unresolved reference {wkind}/{wname} -> {kind}/{name} ({reason})"
if errors: raise UnresolvedReferenceError(sorted(errors))                      # D3
sort each out[stem] by (index in KIND_ORDER, else 99; metadata.name)
out["networkpolicies"] = the two NetworkPolicies sorted by name                # WKL-010 step 9
return out
```

Constants:

| Name | Value |
|---|---|
| `REFERENCED_KINDS` | `("ServiceAccount", "ConfigMap")` |
| `SHARED_STEMS` | `{"ServiceAccount": "serviceaccount", "ConfigMap": "configmaps"}` |
| `AUTO_CREATED` | `frozenset({("ServiceAccount", "default"), ("ConfigMap", "kube-root-ca.crt")})`. Kubernetes creates both objects in every namespace, so a reference to one is never an error and the object is never written |
| `KIND_ORDER` | unchanged: `["ServiceAccount", "ConfigMap", "Service", "Deployment", "StatefulSet"]`; other kinds sort after them (key `99`), then by name |

Placement precedence: R1, then R2, then R3. So an object that R1 or R2 places stays in that file even when other components reference it. The labelled ConfigMap `product-catalog-product-catalog-otel-config` stays in `workload/product-catalog.yaml`, and `flagd-config` stays in `workload/flagd-config.yaml`.

### D2 — File placement

| Object | File |
|---|---|
| ConfigMap `flagd-config` (R1) | `workload/flagd-config.yaml` (WKL-010 step 6, unchanged) |
| Object whose component is a kept component (R2) | `workload/<component>.yaml` (unchanged) |
| Candidate (R3) referenced by the kept workloads of exactly one component `<c>` | `workload/<c>.yaml`. Its own name does not matter |
| Candidate (R3) `ServiceAccount` referenced by the kept workloads of two or more components | `workload/serviceaccount.yaml` |
| Candidate (R3) `ConfigMap` referenced by the kept workloads of two or more components | `workload/configmaps.yaml` |
| The two baseline NetworkPolicies | `workload/networkpolicies.yaml` (WKL-010 step 9, unchanged) |

"Components" counts distinct components, not workloads. A file is written only when it holds at least one object. `networkpolicies` always holds two, so `workload/networkpolicies.yaml` is always written, and `workload/configmaps.yaml` is not written when no shared candidate ConfigMap exists. The stems `flagd-config`, `serviceaccount`, `configmaps` and `networkpolicies` are reserved. None of them is a WKL-002 component name, so they cannot collide with `<component>`. Inside a shared file, objects are sorted by `KIND_ORDER` index, then `metadata.name`, like every other file.

Result for the real chart `0.42.8` (planner run, 2026-11-27): exactly 22 files.

| File | Objects |
|---|---|
| `workload/serviceaccount.yaml` | `ServiceAccount/shop` (referenced by all 19 components) |
| `workload/astronomy-db.yaml` | `ConfigMap/postgresql-init`, `Service/astronomy-db`, `Deployment/astronomy-db` |
| `workload/product-catalog.yaml` | `ConfigMap/product-catalog-product-catalog-otel-config`, `Service/product-catalog`, `Deployment/product-catalog` |
| `workload/flagd-config.yaml` | `ConfigMap/flagd-config` |
| `workload/fraud-detection.yaml` | `Deployment/fraud-detection` (the chart renders no Service for it) |
| `workload/<c>.yaml` for each of the other 16 components (`ad`, `cart`, `checkout`, `currency`, `email`, `flagd`, `frontend`, `frontend-proxy`, `image-provider`, `kafka`, `load-generator`, `payment`, `quote`, `recommendation`, `shipping`, `valkey-cart`) | `Service/<c>`, `Deployment/<c>` |
| `workload/networkpolicies.yaml` | `NetworkPolicy/allow-observability-scrape`, `NetworkPolicy/allow-same-namespace` |

`workload/configmaps.yaml` is not produced for chart `0.42.8`. Totals: 19 Deployments, 18 Services, 3 ConfigMaps, 1 ServiceAccount, 2 NetworkPolicies, 43 objects. Two runs gave identical output (WKL-011).

### D3 — Secrets, Namespace and unresolved references

1. Secrets: unchanged. Every `Secret` is removed (WKL-010 step 2), including one that a kept workload references. No task in `docs/superpowers/plans/` creates an ExternalSecret or Secret in namespace `shop` (searched 2026-11-27). So a required Secret reference from a kept workload is always unresolved, and it is an error. The chart `0.42.8` render has no such reference.
2. Namespace: unchanged. Step 1 sets `metadata.namespace: shop` on every kept object, and D1 decides whether a Namespace object is kept (only through R2).
3. Unresolved reference: a required reference `(kind, name)` is unresolved when it is not placed, is not in `AUTO_CREATED`, and is not a candidate that R3 keeps. That covers every Secret kind, and any ServiceAccount or ConfigMap missing from the `helm template` output. For each pair of unresolved reference and referring kept workload, `transform` collects one message:

   | Referenced kind | Message |
   |---|---|
   | `Secret` | `unresolved reference <WorkloadKind>/<workload name> -> Secret/<name> (Secrets are removed by WKL-010 step 2)` |
   | `ServiceAccount`, `ConfigMap` | `unresolved reference <WorkloadKind>/<workload name> -> <Kind>/<name> (not in the helm template output)` |

   After all objects are processed, `transform` raises `scripts.workload_transforms.UnresolvedReferenceError(errors)` when there is at least one message. The class subclasses `ValueError`, its attribute `errors: list[str]` holds the messages de-duplicated and sorted by Python string order, and `str(exc)` is the messages joined with `\n`. A reference with `optional: true` whose object is absent is not an error, and nothing is written for it.
4. `scripts/render_workload.py` catches `UnresolvedReferenceError`. It prints each message as one stderr line `render_workload: <message>`, for example `render_workload: unresolved reference Deployment/astronomy-db -> ConfigMap/postgresql-init (not in the helm template output)`, and exits with code `3`. The exception is raised before the script creates `--out`, deletes stale `*.yaml` files or writes `.rootline/baseline.json`, so the output directory is left unchanged. Other exit codes are unchanged: `0` success, and `1` with a Python traceback when `helm` fails (`subprocess.CalledProcessError` from `scripts.proc.run`) or `versions.yaml` cannot be loaded.

### D4 — Interfaces, WKL-010 step 8 and the fixture

1. W1-T09 "Interfaces" lists `pod_references(spec: dict) -> set[tuple[str, str, bool]]`, `UnresolvedReferenceError(ValueError)` with `errors: list[str]`, the constants `REFERENCED_KINDS`, `SHARED_STEMS` and `AUTO_CREATED`, and the CLI exit codes `0`, `1` and `3`. `transform` keeps its signature and returns stems `<component>`, `flagd-config`, `networkpolicies`, `serviceaccount` and `configmaps` (the last two only when non-empty). W1-T09 "Output" lists `workload/serviceaccount.yaml` and `workload/configmaps.yaml` (written only when non-empty).
2. Spec WKL-010 step 8 is reworded to state R1 to R3, the D2 placement and the D3 error. Spec WKL-001 "Output" and the GEN-010 tree (§4.2) name the two shared files. These are spec-gap additions: no existing rule is reversed. Step 8 already listed ConfigMaps and ServiceAccounts among the objects written.
3. The fixture `tests/repo/fixtures/otel-demo-mini.yaml` MUST contain the real-shape ServiceAccount: name `shop`, the four labels from the Context table, and no `app.kubernetes.io/component`. It replaces the labelled `shop-opentelemetry-demo`. Every Deployment in the fixture sets `serviceAccountName: shop`. The fixture MUST also contain:
   - ConfigMap `postgresql-init` (no component label), mounted by a new kept Deployment `astronomy-db`;
   - ConfigMap `shop-shared-env` (no component label), referenced by `payment` through `envFrom[].configMapRef` and by `load-generator` through `env[].valueFrom.configMapKeyRef`, so it goes to `configmaps`;
   - ConfigMap `orphan-config` (no component label, referenced by nothing);
   - ConfigMap `jaeger-sampling` (no component label, referenced only by the dropped Deployment `jaeger`).

   The exact YAML is in W1-T09 Step 2.

### D5 — Tests

`tests/repo/test_workload_render.py` gains six tests. The four that the review required:

| Test | Asserts |
|---|---|
| `test_referenced_serviceaccount_kept` | `ServiceAccount/shop` is in stem `serviceaccount`, is the only object there, and has namespace `shop` |
| `test_referenced_configmap_kept_in_workload_file` | `ConfigMap/postgresql-init` is in stem `astronomy-db` (kinds `["ConfigMap", "Deployment"]`); `ConfigMap/shop-shared-env` is in `configmaps`; `ConfigMap/flagd-config` is in `flagd-config` |
| `test_unreferenced_unlabelled_object_dropped` | `ConfigMap/orphan-config`, `ConfigMap/jaeger-sampling` and `Deployment/jaeger` are in no stem |
| `test_every_reference_of_kept_workload_resolves` | The test reads them with its own code, not `pod_references`: every `serviceAccountName`, `volumes[].configMap.name`, `envFrom[].configMapRef.name` and `env[].valueFrom.configMapKeyRef.name` of every Deployment and StatefulSet in the output. That set equals `{ServiceAccount/shop, ConfigMap/flagd-config, ConfigMap/postgresql-init, ConfigMap/shop-shared-env}` and is a subset of the output's `(kind, name)` pairs |

Two more for D3: `test_missing_reference_rejected` (fixture without `ConfigMap/postgresql-init` → `errors` equals the one `ConfigMap` message) and `test_secret_reference_rejected` (`payment` gains `envFrom: [{secretRef: {name: shop-registry-credentials}}]` → `errors` equals the one `Secret` message). Step 6 also checks the real render: 22 files, exactly the list in D2.

## Consequences

- W1-T09 in `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` changed on 2026-11-27 on branch `docs/w1-t09-referenced-objects`. It gained an amendment note under the task header, a new fixture description in "Files", the "Output" and "Interfaces" lines, the Step 2 test block with its fixture YAML, the Step 3 `workload_transforms.py` block, the Step 4 `render_workload.py` block, and the expected file list in Step 6.
- The W1-T09 implementer applies these blocks on `feat/w1-workload-render` as a review fix. It changes `scripts/workload_transforms.py`, `scripts/render_workload.py`, `tests/repo/test_workload_render.py` and `tests/repo/fixtures/otel-demo-mini.yaml`, and replaces the "Unverified (2026-11-27): the ServiceAccount name …" paragraph of `wiki/components/workload.md` with the facts of D2. All of these paths are in W1-T09 `owns` in `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`, so the schedule does not change.
- Spec WKL-001 "Output", the GEN-010 tree (§4.2) and WKL-010 steps 2 and 8 changed. Spec §26 gains row PG-25. Overview §5 gains PG-25 and §6 gains the PG-25 traceability row. The next free ADR number is 0045.
- W3-T08 `get_recent_changes` (`docs/superpowers/plans/2026-11-26-rootline-w3-identity-mcp.md`) sets `files[].workload` from paths `workload/<component>.yaml`. The plan now states that `workload/serviceaccount.yaml` and `workload/configmaps.yaml` give `null`, because their stems are not WKL-002 component names.
- The Fault Lab git injector (W2, `workload/<target>.yaml`) and the W5 `inventory.load()` (`workload/*.yaml`) read workload files by component name or by object kind. The new `workload/serviceaccount.yaml` holds no Deployment or StatefulSet, so neither sees a new workload.
- The pods of all 19 kept Deployments pass ServiceAccount admission, and `astronomy-db` mounts `postgresql-init`. Both are checked when W1-T12 (`task up`) runs the workload.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Add `shop` and `postgresql-init` to a hard-coded keep list | Breaks again when a chart bump renames or adds an object. The reference rule follows the render and needs no list |
| Keep every unlabelled ServiceAccount and ConfigMap | Would also keep objects of disabled components (WKL-003), such as `jaeger-sampling` in the fixture |
| Put a shared ServiceAccount into the file of the alphabetically first referrer (`ad.yaml`) | A git fault on `ad` (W2) that rewrites `workload/ad.yaml` could then break all 19 workloads, and the file name would hide the object's scope |
| One file per referenced object (`workload/<name>.yaml`) | `<name>` could equal a component name and collide; two fixed stems are simpler |
| Always put referenced-only objects in shared files, even with one referrer | `postgresql-init` belongs only to `astronomy-db`. Keeping it in `astronomy-db.yaml` keeps one component's state in one file, as WKL-010 step 8 intends |
| Set `automountServiceAccountToken`, or remove `serviceAccountName` so pods use `default` | Changes the chart's pod specs beyond WKL-010 and drops the chart's own ServiceAccount; ARC-010 and SEC-033 hardening belongs to the platform charts, not the workload render |
| Keep a referenced Secret in `rootline-env` | Violates WKL-010 step 2 and GEN-010 (no secrets in the env repository) |
| Warn and continue on an unresolved reference | Commits a workload that cannot start; failing the render before anything is written is safer and is noticed at render time |
| Skip `optional: true` references entirely, even when the object exists | The object then disappears from a pod that would have used it; keeping an existing optional reference matches what the chart deploys |

## Spec references

WKL-001, WKL-002, WKL-003, WKL-010 (steps 1, 2, 6, 8, 9), WKL-011, TST-WKL-001, GEN-010, GEN-011, PG-11, PG-21, PG-25, spec §0.3, §4.2, §6.1, §6.3, §26, overview §5, §6, W1-T09, W3-T08.
