# 0048 — Kafka KRaft controller quorum voter on `localhost` in the workload render (spec-gap)

Status: accepted
Date: 2026-11-28
Label: spec-gap
Plan gap: PG-29 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

This ADR holds five decisions, D1 to D5. They answer the defect that the W1-T12 bring-up (`task up` on `feat/w1-task-up`, PR #30) found on 2026-11-28 in the live k3d cluster `rootline` (context `k3d-rootline`): Deployment `kafka` in namespace `shop` crash-loops, so Deployments `checkout` and `fraud-detection` never leave their init container and Application `workload` stays `Degraded`. The workload is the render of W1-T09 (chart `opentelemetry-demo` `0.42.8`, app `3.1.0`) in `rootline-env` commit `1acc3501b1163ed2e21192a63810b8e7f9898089`, tag `baseline-v1`.

## Context

The Kafka container of chart `0.42.8` runs in KRaft combined mode: one process is both broker and controller (image environment `KAFKA_PROCESS_ROLES=controller,broker`, `KAFKA_NODE_ID=1`). The chart sets the controller quorum voter to the Service name, `KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093`. So the broker part of the process registers with its own controller through Service `kafka` port `9093`.

WKL-010 step 4 adds a readiness probe `tcpSocket.port: 9092` to every container that exposes a Service port and has no probe; the upstream chart has no probe on `kafka`, so the transform adds it. Kafka opens the client port `9092` only after the broker has registered with the controller. Service `kafka` (ClusterIP, ports `9092` and `9093`, `publishNotReadyAddresses` unset) gets an endpoint only when the pod is Ready. The result is a cycle:

1. The broker connects to `kafka:9093` (the ClusterIP). The Service has no endpoint, so the connection times out.
2. The broker cannot register, so port `9092` stays closed, so the readiness probe fails, so the pod is not Ready, so the Service gets no endpoint (back to 1).
3. After `initial.broker.registration.timeout.ms` (`60000` ms) plus start-up, the process exits with code `1`, and the kubelet restarts it (`CrashLoopBackOff`).

Without the WKL-010 step 4 probe, a pod with no readiness probe is Ready as soon as it runs, the Service gets the endpoint at once, and the cycle does not form. That is why the upstream demo works and why the spec gap is ours: neither WKL-010 nor WKL-002 says how the probe and the chart's KRaft voter address work together.

Downstream effect: Deployments `checkout` and `fraud-detection` have an init container that runs `until nc -z -v -w30 kafka 9092; do echo waiting for kafka; sleep 2; done;`, so their pods stay in `Init:0/1` and Application `workload` is `Degraded`.

## Verification performed on 2026-11-28

All commands ran in WSL Ubuntu 26.04 with helm `v3.22.1`, Docker Engine on the WSL host, and the live cluster created by `task up` on `feat/w1-task-up`.

| Fact | How it was verified |
|---|---|
| Chart `0.42.8` with `deploy/upstream/otel-demo/values.yaml` renders Service `kafka` with `type: ClusterIP`, ports `9092` (`plaintext`) and `9093` (`controller`), selector `opentelemetry.io/name: kafka`, and no `publishNotReadyAddresses` | `helm template shop open-telemetry/opentelemetry-demo --version 0.42.8 --namespace shop -f deploy/upstream/otel-demo/values.yaml` (2541 lines), object `Service/kafka` |
| The same render gives Deployment `kafka` one container `kafka`, image `ghcr.io/open-telemetry/demo:3.1.0-kafka`, ports `9092` and `9093`, no readiness probe, and the env values `KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092`, `KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093`, `KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER`, `KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093`, `KAFKA_HEAP_OPTS=-Xmx400M -Xms400M` | same render, object `Deployment/kafka` |
| The image sets `KAFKA_PROCESS_ROLES=controller,broker`, `KAFKA_NODE_ID=1`, `KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT`, `CLUSTER_ID=ckjPoprWQzOf0-FuNkGfFQ`; it runs Kafka `4.3.1` | `docker inspect ghcr.io/open-telemetry/demo:3.1.0-kafka --format '{{json .Config.Env}}'`; log line `Kafka version: 4.3.1` |
| `rootline-env` `workload/kafka.yaml` at tag `baseline-v1` has `value: 1@kafka:9093` at line 80 and the step 4 probe `tcpSocket.port: 9092` | `git -C /home/arkhash0309/projects/rootline-env show baseline-v1:workload/kafka.yaml`; the working tree equals the tag |
| Live pod `kafka-65bbccddb7-65fc4`: `0/1`, `Error`, 5 restarts; last state `Terminated`, exit code `1`, 95 s after start; events `Readiness probe failed: dial tcp 10.42.0.171:9092: connect: connection refused`; Endpoints `kafka` empty | `kubectl --context k3d-rootline -n shop get pods`; `kubectl --context k3d-rootline -n shop describe pod kafka-65bbccddb7-65fc4`; `kubectl --context k3d-rootline -n shop get endpoints kafka` |
| The live broker cannot reach its controller: repeated `Unable to register the broker because the RPC got timed out before it could be sent`, `RegistrationResponseHandler: channel manager timed out before sending the request`, and `Disconnecting from node 1 due to socket connection setup timeout` | `kubectl --context k3d-rootline -n shop logs kafka-65bbccddb7-65fc4` |
| `checkout` and `fraud-detection` pods are `Init:0/1`; the `checkout` init container command is `["sh","-c","until nc -z -v -w30 kafka 9092; do echo waiting for kafka; sleep 2; done;"]` | `kubectl --context k3d-rootline -n shop get pods`; `kubectl --context k3d-rootline -n shop get pod <checkout pod> -o jsonpath='{.spec.initContainers[0].command}'` |
| With the same image, `--user 1000:1000` (the chart's `securityContext`), the chart's Kafka env and `KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093`, in a container whose hostname is `kafka-verify` (so the name `kafka` does not resolve to it), the process logs `Successfully registered broker 1 with broker epoch 11` and `Kafka Server started` about 1 s after the controller started and within 15 s of `docker run`; port `127.0.0.1:9092` accepts a TCP connection; `kafka-metadata-quorum.sh --bootstrap-controller localhost:9093 describe --status` prints `LeaderId: 1` and `CurrentVoters: [{"id": 1, "endpoints": ["CONTROLLER://localhost:9093"]}]` | `docker run -d --name kafka-verify-localhost --hostname kafka-verify --user 1000:1000 -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092 -e "KAFKA_HEAP_OPTS=-Xmx400M -Xms400M" -e KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093 -e KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER -e KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093 -e OTEL_SDK_DISABLED=true -e OTEL_SERVICE_NAME=kafka ghcr.io/open-telemetry/demo:3.1.0-kafka`, then `docker logs`, `docker exec kafka-verify-localhost bash -c 'exec 3<>/dev/tcp/127.0.0.1/9092'`, and the quorum command; container removed afterwards |
| The D1 rule, applied to the real chart output, changes exactly one line of the 22 files: `workload/kafka.yaml` line 80, `value: 1@kafka:9093` becomes `value: 1@localhost:9093` | planner prototype of D1 in a scratch copy of `scripts/workload_transforms.py`, run on the render above; `diff -r /home/arkhash0309/projects/rootline-env/workload <prototype output>` |
| The D2 tests fail on `develop` (`3a299a0`) and pass with D1 and D3 applied; `ruff format --check` and `ruff check` pass | planner prototype in the worktree of this PR, reverted before the commit: `uv run pytest tests/repo/test_workload_render.py` reported `3 failed, 23 passed` without D1 and D3 (`test_kafka_controller_quorum_voter_is_localhost`, `test_kafka_controller_quorum_voter_added_when_absent`, `test_render_workload_writes_files_and_baseline`) and `26 passed` with them |

Not verified: the D1 render on the live cluster (that is D4, after D3), and option (a) below (not tried on the cluster, so its behaviour is not a verified fact).

## Decision

Each decision follows spec §0.3 (simplest, cheapest, safest, in that order). None changes cost, security level or scope: D1 changes one environment value of one container in namespace `shop`, D2 adds tests, D3 is the re-render that WKL-001 already prescribes, D4 is a check, D5 states a non-change.

### D1 — WKL-010 step 7 sets the KRaft voter to `localhost`

Transform rule (spec WKL-010 step 7, PG-29):

| Field | Value |
|---|---|
| Object kind | `Deployment` or `StatefulSet` (`WORKLOAD_KINDS`); chart `0.42.8` renders a `Deployment` |
| Object selection | component `kafka` (label `app.kubernetes.io/component`, else `metadata.name`; `component_of`) |
| Container | `spec.template.spec.containers[0]` (chart `0.42.8`: the only container, name `kafka`) |
| Field | `env[]` entry with `name: KAFKA_CONTROLLER_QUORUM_VOTERS` |
| Value | `1@localhost:9093` (plain `value`; a `valueFrom` on that entry is removed) |
| When the entry exists | its `value` is replaced in place; its position in `env` is kept |
| When the entry is absent | `{"name": "KAFKA_CONTROLLER_QUORUM_VOTERS", "value": "1@localhost:9093"}` is appended at the end of `env` (`env` is created when absent) |
| Order | after step 4 (readiness probe) and in the same place as the `load-generator` env overrides of step 7; before the reference collection of step 8 (the value holds no reference, so step 8 is not affected) |
| Unchanged | Service `kafka` (no `publishNotReadyAddresses`), `KAFKA_LISTENERS`, `KAFKA_ADVERTISED_LISTENERS`, `KAFKA_CONTROLLER_LISTENER_NAMES`, the step 4 readiness probe `tcpSocket.port: 9092` |

Implementation in `scripts/workload_transforms.py`, with the existing helper `_set_env` (which already has exactly the "exists" and "absent" behaviour above):

```python
COLLECTOR_FQDN = "otel-collector.observability.svc.cluster.local"
# WKL-010 step 7, PG-29 (ADR 0048 D1): the single KRaft voter is the kafka pod itself, not Service kafka.
KAFKA_QUORUM_VOTERS = "1@localhost:9093"
```

and in `transform`, directly after the `load-generator` block inside `if obj["kind"] in WORKLOAD_KINDS:`:

```python
            if comp == "kafka":
                _set_env(spec["containers"][0], "KAFKA_CONTROLLER_QUORUM_VOTERS", KAFKA_QUORUM_VOTERS)
```

The module docstring becomes `"""Pure transforms for rendered OTel Demo manifests (WKL-010, PG-11, PG-12, PG-25, PG-29)."""`.

Failure behaviour: `transform` stays pure (it works on a deep copy). A `kafka` workload with an empty or missing `containers` list raises `IndexError` or `KeyError` (the same behaviour as the `load-generator` rule); `scripts/render_workload.py` does not catch it, exits `1` with a Python traceback, and writes nothing, because `transform` runs before the first write. The rule adds no other error case.

Why `localhost` is correct: the controller listener is `CONTROLLER://:9093`, which binds every interface of the container, `127.0.0.1` included. Clients never use the voter address: they bootstrap with `kafka:9092` and receive the advertised listener `PLAINTEXT://kafka:9092`, both unchanged. The voter address is used only by the process to reach its own controller, and with D1 that path no longer depends on Service `kafka`, CoreDNS, kube-proxy or the pod's readiness.

Invariant: D1 is correct only while `kafka` runs exactly one replica (spec ARC-001 row "Workload", "1 each"; chart `default.replicas: 1` in `deploy/upstream/otel-demo/values.yaml`). A change to more than one `kafka` replica, or to a separate controller, MUST get a new ADR that replaces D1.

### D2 — Fixture and tests

`tests/repo/fixtures/otel-demo-mini.yaml` gets two documents appended at the end of the file (each preceded by a `---` line), with the real-render shape of chart `0.42.8` (only the fields the tests read, plus the ports and env that the transform touches):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kafka
  namespace: default
  labels:
    app.kubernetes.io/component: kafka
    app.kubernetes.io/name: kafka
spec:
  type: ClusterIP
  ports:
    - port: 9092
      name: plaintext
      targetPort: 9092
    - port: 9093
      name: controller
      targetPort: 9093
  selector:
    opentelemetry.io/name: kafka
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka
  namespace: default
  labels:
    app.kubernetes.io/component: kafka
    app.kubernetes.io/name: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      opentelemetry.io/name: kafka
  template:
    metadata:
      labels:
        opentelemetry.io/name: kafka
        app.kubernetes.io/component: kafka
        app.kubernetes.io/name: kafka
    spec:
      serviceAccountName: shop
      containers:
        - name: kafka
          image: ghcr.io/open-telemetry/demo:3.1.0-kafka
          ports:
            - containerPort: 9092
              name: plaintext
            - containerPort: 9093
              name: controller
          env:
            - name: OTEL_COLLECTOR_NAME
              value: otel-collector
            - name: KAFKA_ADVERTISED_LISTENERS
              value: PLAINTEXT://kafka:9092
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: http://$(OTEL_COLLECTOR_NAME):4318
            - name: KAFKA_LISTENERS
              value: PLAINTEXT://:9092,CONTROLLER://:9093
            - name: KAFKA_CONTROLLER_LISTENER_NAMES
              value: CONTROLLER
            - name: KAFKA_CONTROLLER_QUORUM_VOTERS
              value: 1@kafka:9093
```

`tests/repo/test_workload_render.py` gets two new tests, placed directly before `def where(`, and two changed assertions:

```python
def test_kafka_controller_quorum_voter_is_localhost() -> None:
    """WKL-010 step 7, PG-29 (ADR 0048): the KRaft voter is the kafka pod itself, not Service kafka."""
    out = transform(docs())
    assert [o["kind"] for o in out["kafka"]] == ["Service", "Deployment"]
    dep = next(o for o in out["kafka"] if o["kind"] == "Deployment")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    names = [e["name"] for e in container["env"]]
    env = {e["name"]: e.get("value") for e in container["env"]}
    assert names.count("KAFKA_CONTROLLER_QUORUM_VOTERS") == 1
    assert env["KAFKA_CONTROLLER_QUORUM_VOTERS"] == "1@localhost:9093"
    assert env["KAFKA_LISTENERS"] == "PLAINTEXT://:9092,CONTROLLER://:9093"
    assert env["KAFKA_ADVERTISED_LISTENERS"] == "PLAINTEXT://kafka:9092"
    assert container["readinessProbe"] == {
        "tcpSocket": {"port": 9092},
        "initialDelaySeconds": 5,
        "periodSeconds": 10,
        "failureThreshold": 3,
    }
    svc = next(o for o in out["kafka"] if o["kind"] == "Service")
    assert "publishNotReadyAddresses" not in svc["spec"]


def test_kafka_controller_quorum_voter_added_when_absent() -> None:
    """WKL-010 step 7, PG-29 (ADR 0048): a chart output without the variable gets it appended."""
    ds = docs()
    dep = next(d for d in ds if d["kind"] == "Deployment" and d["metadata"]["name"] == "kafka")
    container = dep["spec"]["template"]["spec"]["containers"][0]
    container["env"] = [e for e in container["env"] if e["name"] != "KAFKA_CONTROLLER_QUORUM_VOTERS"]
    out = next(o for o in transform(ds)["kafka"] if o["kind"] == "Deployment")
    env = out["spec"]["template"]["spec"]["containers"][0]["env"]
    assert env[-1] == {"name": "KAFKA_CONTROLLER_QUORUM_VOTERS", "value": "1@localhost:9093"}
```

Changed assertions in `test_render_workload_writes_files_and_baseline`: the expected file list gains `"kafka.yaml"` between `"flagd.yaml"` and `"load-generator.yaml"` (nine names), and the baseline assertion becomes `assert baseline == {"baseline_tag": "baseline-v2", "rendered_from": "0.42.8"}` (D3). The module docstring becomes `"""Verifies WKL-010, WKL-011 (TST-WKL-001), PG-11, PG-12, PG-25, PG-29."""`. No other test changes: `test_every_reference_of_kept_workload_resolves` still expects exactly `ServiceAccount/shop`, `ConfigMap/flagd-config`, `ConfigMap/postgresql-init` and `ConfigMap/shop-shared-env`, because the fixture `kafka` references only `ServiceAccount/shop`.

The first test is the regression guard for the defect: it fails when the rule is missing (voter `1@kafka:9093`), when the rule is moved to the Service (option (a)), or when the step 4 probe is dropped for `kafka` (alternative (d)).

### D3 — Baseline tag constant and the `baseline-v2` re-render

`scripts/render_workload.py` gets a module constant directly after the `from scripts.workload_transforms import ...` line:

```python
# WKL-001, GEN-011, PG-29 (ADR 0048 D3): the rootline-env tag of this render; +1 on every re-render.
BASELINE_TAG = "baseline-v2"
```

and writes `{"baseline_tag": BASELINE_TAG, "rendered_from": demo["chart"]}` (sorted keys, LF) instead of the literal `"baseline-v1"`. Rule for every re-render after this one (spec WKL-001 "Re-rendering"): the PR that changes the render output raises N in `BASELINE_TAG` by exactly 1 (`baseline-v3` next), and the `rootline-env` squash commit that results gets that tag. An existing `baseline-v*` tag MUST NOT be moved, deleted or force-pushed: `baseline-v1` stays on `1acc3501b1163ed2e21192a63810b8e7f9898089`.

The re-render is a PR in `rootline-env` (spec WKL-001 "Re-rendering is only allowed via a PR to `rootline-env` that bumps `baseline-vN`"). The PR branch is short-lived and deleted when the PR merges, so `main` stays the only long-lived branch (GEN-024), exactly as for the agent's `rootline/fix/...` branches. Until ruleset `protect-main` exists (week 3, SEC-081) the PR needs no approval and no status check. The coordinator runs these commands in WSL bash after the W1-T12 fix round (Consequences) has passed review, from `/home/arkhash0309/projects/rootline` checked out at the reviewed commit of `feat/w1-task-up`:

```bash
set -euo pipefail
cd /home/arkhash0309/projects/rootline
E=/home/arkhash0309/projects/rootline-env
SRC=$(git rev-parse --short=7 HEAD)
git -C "$E" switch main
git -C "$E" pull --ff-only origin main
test -z "$(git -C "$E" status --porcelain)"
test "$(git -C "$E" rev-parse HEAD)" = 1acc3501b1163ed2e21192a63810b8e7f9898089
git -C "$E" switch -c fix/baseline-v2
uv run python scripts/render_workload.py --out "$E/workload"
git -C "$E" diff --numstat
git -C "$E" status --porcelain
uv run python scripts/render_workload.py --out "$E/workload"
git -C "$E" diff --numstat
```

Expected: both renders exit `0`. Each `git diff --numstat` prints exactly these two lines (tab-separated), in this order: `1	1	.rootline/baseline.json` and `1	1	workload/kafka.yaml`. `git status --porcelain` prints exactly ` M .rootline/baseline.json` and ` M workload/kafka.yaml`. `git -C "$E" diff workload/kafka.yaml` shows the one removed line `          value: 1@kafka:9093` and the one added line `          value: 1@localhost:9093`; `cat "$E/.rootline/baseline.json"` prints `{"baseline_tag": "baseline-v2", "rendered_from": "0.42.8"}`. If any command fails or any output differs, run `git -C "$E" switch -f main && git -C "$E" branch -D fix/baseline-v2`, push nothing, and report `STATUS: BLOCKED` with the outputs; do not edit the rendered files by hand.

Then commit, open the PR, squash-merge it, and tag the squash commit:

```bash
MSG_SUBJECT="fix: run the kafka KRaft voter on localhost (baseline-v2)"
MSG_BODY="Re-render of opentelemetry-demo 0.42.8 by rootline commit ${SRC} (WKL-010 step 7, ADR 0048, PG-29): KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093 on Deployment kafka.

Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
git -C "$E" add .rootline/baseline.json workload/kafka.yaml
git -C "$E" commit -m "$MSG_SUBJECT" -m "$MSG_BODY"
git -C "$E" push -u origin fix/baseline-v2
gh pr create -R arkhash0309/rootline-env --base main --head fix/baseline-v2 --title "$MSG_SUBJECT" --body "Re-render for baseline-v2: ADR 0048 (PG-29) in arkhash0309/rootline. Changes workload/kafka.yaml (one line) and .rootline/baseline.json."
gh pr merge -R arkhash0309/rootline-env fix/baseline-v2 --squash --delete-branch --subject "$MSG_SUBJECT" --body "$MSG_BODY"
git -C "$E" switch main
git -C "$E" pull --ff-only origin main
git -C "$E" branch -D fix/baseline-v2
git -C "$E" log -1 --format=%s
git -C "$E" tag baseline-v2
git -C "$E" push origin baseline-v2
git -C "$E" rev-parse baseline-v1 baseline-v2
```

Commit message format of the `rootline-env` commit on `main` (the squash commit): subject exactly `fix: run the kafka KRaft voter on localhost (baseline-v2)`; one blank line; the body line `Re-render of opentelemetry-demo 0.42.8 by rootline commit <sha7> (WKL-010 step 7, ADR 0048, PG-29): KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093 on Deployment kafka.`, where `<sha7>` is the 7-character SHA of the `rootline` commit that rendered it; one blank line; the trailer `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>` (the coordinator writes it; plan overview §7.1 "Commit attribution trailers"). Expected outputs: `git log -1 --format=%s` prints the subject exactly; the last command prints `1acc3501b1163ed2e21192a63810b8e7f9898089` and then the SHA of the new `main` commit. The tag is lightweight, as `baseline-v1` is. `git push origin baseline-v2` pushes only the new tag; `--tags`, `--force` and `git tag -f` MUST NOT be used.

Failure behaviour: a failed `git push` or `gh pr create` leaves `main` unchanged; fix the cause (network, `gh auth status`) and rerun from that command. A failed `gh pr merge` leaves the PR open; rerun it. A failed `git push origin baseline-v2` leaves the tag local only; rerun it. If `main` moved between the render and the merge (`gh pr merge` reports a conflict), close the PR, delete the branch, and rerun D3 from the top, which then fails at the `rev-parse HEAD` check and reports `STATUS: BLOCKED`.

The coordinator then appends to `wiki/log.md` on `feat/w1-task-up`: `- [agent] rootline-env commit <sha7> (<full sha>) re-renders workload with the kafka KRaft voter on localhost (ADR 0048, PG-29); tag baseline-v2 on it; baseline-v1 unchanged on 1acc350 (made by the coordinator)`.

### D4 — Live check after the re-render

ArgoCD Application `workload` has automated sync (GEN-012), so it syncs the new `main` commit without a manual sync. The coordinator runs, in WSL bash, after D3:

```bash
SHA=$(git -C /home/arkhash0309/projects/rootline-env rev-parse baseline-v2)
kubectl --context k3d-rootline -n argocd annotate application workload argocd.argoproj.io/refresh=normal --overwrite
timeout 600 bash -c "until [ \"\$(kubectl --context k3d-rootline -n argocd get application workload -o jsonpath='{.status.sync.revision}')\" = $SHA ]; do sleep 10; done"
kubectl --context k3d-rootline -n shop get deployment kafka -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="KAFKA_CONTROLLER_QUORUM_VOTERS")].value}{"\n"}'
kubectl --context k3d-rootline -n shop rollout status deployment/kafka --timeout=300s
kubectl --context k3d-rootline -n shop get endpoints kafka -o jsonpath='{range .subsets[*].addresses[*]}{.ip}{"\n"}{end}'
kubectl --context k3d-rootline -n shop rollout status deployment/checkout --timeout=300s
kubectl --context k3d-rootline -n shop rollout status deployment/fraud-detection --timeout=300s
timeout 600 bash -c "until [ \"\$(kubectl --context k3d-rootline -n argocd get application workload -o jsonpath='{.status.sync.status} {.status.health.status}')\" = 'Synced Healthy' ]; do sleep 10; done"
kubectl --context k3d-rootline -n argocd get application workload -o jsonpath='{.status.sync.status} {.status.health.status}{"\n"}'
```

Expected, in order: the `timeout 600` loops exit `0`; the env query prints exactly `1@localhost:9093`; `rollout status` for `kafka` prints `deployment "kafka" successfully rolled out`; the Endpoints query prints exactly one line, an IPv4 address in the k3s pod network `10.42.0.0/16` (only Ready pods are listed under `addresses`; kubectl also prints the warning `v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice` on stderr, which is expected); `rollout status` prints `successfully rolled out` for `checkout` and for `fraud-detection` (their running pods leave `Init:0/1` once `kafka:9092` answers; they are not restarted); the last command prints `Synced Healthy`. The pods of `checkout` and `fraud-detection` are not deleted by hand. On any timeout or different output: collect `kubectl --context k3d-rootline -n shop logs deployment/kafka --tail=200`, `kubectl --context k3d-rootline -n shop get pods` and `kubectl --context k3d-rootline -n shop describe pod -l opentelemetry.io/name=kafka`, report `STATUS: BLOCKED` with them, and do not change D1 without a new planner decision. The outputs are recorded in `wiki/components/workload.md` section "Render findings" (a new paragraph "baseline-v2 (ADR 0048)" with the date, the `rootline-env` SHA and the outputs) by the coordinator on `feat/w1-task-up`, and W1-T12 Step 5 then expects `workload` `Synced/Healthy` as before.

### D5 — ADR 0047 D4 (the `workload` path) is not affected

ADR 0047 D4 was "Application `workload` has no `workload/` path because W1-T09 steps 6 and 7 have not run". It closed when `rootline-env` commit `1acc350` (tag `baseline-v1`) created `workload/` on `main`. ADR 0048 changes the content of one file under that path. It does not change Application `workload` (`repoURL`, `targetRevision: main`, `path: workload`, destination namespace `shop`, `syncPolicy`, `ignoreDifferences`), its namespace entry of ADR 0047 D1 (`workload: shop`), or its retry of ADR 0047 D2. ADR 0047 is not amended.

## Consequences

- The fix is applied in a W1-T12 fix round on `feat/w1-task-up` (PR #30), because the defect blocks W1-T12 Step 5 (`workload` is Healthy) and W1-S3 is a sequential stage, so no `owns` list applies (plan overview §7.4); this is the same route as ADR 0047. The implementer edits `scripts/workload_transforms.py` (D1), `scripts/render_workload.py` (D3 constant), `tests/repo/fixtures/otel-demo-mini.yaml` and `tests/repo/test_workload_render.py` (D2), runs `uv run pytest tests/repo/test_workload_render.py -v` (expected: 26 passed), `uv run ruff format --check scripts tests/repo` and `uv run ruff check scripts tests/repo`, and records the D1 rule in `wiki/components/workload.md` (a new row of the "Transform decisions" table: `kafka` container 0, `KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093`, WKL-010 step 7, PG-29; and `baseline-v2` in the `.rootline/baseline.json` example of section "Interfaces"). Commit message: `fix(scripts): run the kafka KRaft voter on localhost in the workload render (PG-29)`.
- After review the coordinator performs D3 and D4, then reruns W1-T12 Step 5 and Step 8.
- Spec WKL-001 "Re-rendering", WKL-010 step 7, the GEN-010 tree comment for `.rootline/baseline.json`, and §26 (row PG-29) are amended in this PR.
- Plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md`: W1-T09 (amendment note, "Files" fixture line, "Interfaces", Step 2 tests and "Fixture additions" items 6 and 7, Step 3 rule, Step 4 constant, Step 6 expected checks, Step 7 note); W1-T12 (amendment note; Step 6 re-render tag); W1-T13 Step 5 (re-render tag). Plan `docs/superpowers/plans/2026-11-26-rootline-w6-console-e2e.md` W6-T09 Step 1: the e2e repository is tagged with the `baseline_tag` value of the copied `.rootline/baseline.json`. No schedule change: W1-T12 stays in W1-S3, and `docs/superpowers/plans/2026-11-26-rootline-schedule.yaml` is unchanged.
- The next re-render (W1-T12 Step 6 memory requests, W1-T13 Step 5 baseline gate) uses `baseline-v3`.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| (a) `publishNotReadyAddresses: true` on Service `kafka` in the transform | Breaks the cycle, but makes Service `kafka` route client traffic (`checkout`, `fraud-detection`, and their `nc -z kafka 9092` init check) to a broker that is not Ready, unlike every other `shop` Service, so readiness stops being evidence for Kafka (the agent reads endpoints and readiness). The controller path still depends on CoreDNS, kube-proxy and hairpin traffic from the pod to its own ClusterIP. It adds a transform of a Service object, which WKL-010 does not have today. Not tried on the cluster. D1 is one env value with the existing `_set_env` helper and was verified with the exact image |
| (b) `KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093` | chosen (D1) |
| (c) disable the combined-mode controller listener and run a separate controller | A second Deployment and Service, more memory against ARC-030 (3.2 GiB for `shop`), a second fault surface, and a change of WKL-002 (one `kafka` component). Not simple, not cheap |
| (d) exempt `kafka` from the WKL-010 step 4 readiness probe | Removes the cycle the same way the upstream chart avoids it, but `kafka` would be Ready before it accepts clients, and step 4 would get an exception list. D1 keeps step 4 uniform |
| (e) `components.kafka.envOverrides` in `deploy/upstream/otel-demo/values.yaml` (chart `0.42.8` has `envOverrides`) | Same result as D1, but `tests/repo/test_workload_render.py` works on the fixture without `helm`, so no offline test could guard the value, and the chart's override merge would be a second place where the render changes env values. WKL-010 is the spec's single list of render changes |
| Re-render as a direct push to `main` (as W1-T09 Step 7 did for the first render) | WKL-001 requires a PR for a re-render. The PR costs two `gh` commands and leaves the same single commit on `main` |
| Move tag `baseline-v1` to the new commit | GEN-011 makes `baseline-vN` the known-good state that the Fault Lab restores to; a moved tag rewrites that history. A new tag is the WKL-001 rule |

## Spec references

WKL-001 ("Re-rendering"), WKL-002, WKL-010 steps 4, 7 and 8, WKL-011, GEN-010 (tree), GEN-011, GEN-012, GEN-024, ARC-001 row "Workload", ARC-030, SEC-081, §0.3, §26 PG-29; ADR 0044 (PG-25), ADR 0047 D4; plan `docs/superpowers/plans/2026-11-26-rootline-w1-foundations.md` "Task W1-T09" (amendment note of 2026-11-28, Steps 2, 3, 4, 6, 7), "Task W1-T12" (amendment note of 2026-11-28, Steps 5, 6), "Task W1-T13" Step 5; `docs/superpowers/plans/2026-11-26-rootline-w6-console-e2e.md` W6-T09 Step 1; plan overview §5 PG-29 and §7.1 "Commit attribution trailers".
