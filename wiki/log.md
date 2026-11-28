# Log

Append-only (WIK-013). Format: `- [agent|owner] <what happened> (PR #n / commit sha7)` under a date heading.

## 2026-11-27
- [agent] Created rootline-env repository (W1-T08, deferred log append from docs/w1-env-repo)
- [agent] Created wiki skeleton (W1-T03)
- [agent] Added ADRs 0001-0036 (W1-T04)
- [agent] Added rootline-wiki agent skill (W1-T05)
- [agent] Added rootline_common foundation modules (W1-T07)
- [agent] Added k3d config, ArgoCD root chart, namespaces and platform-config charts, upstream values and render_manifests (W1-T10)
- [agent] Added workload render script, transforms and tests (W1-T09 steps 1-5; real render in W1-S3)
- [agent] Applied ADR 0044 (PG-25) to the workload render: keep referenced ServiceAccount and ConfigMaps (W1-T09 review fix)
- [agent] Added observability and postgres charts and the render_versions Chart.yaml step (W1-T11)
- [agent] Added ci.yml, scripts/ci_changed_files.py, ruleset JSON files and the Rulesets runbook section (W1-T14; ruleset creation O-3 and the first CI run are deferred)
- [agent] Planner recorded ADR 0045 / PG-26: W1-T14 CI and ruleset decisions (docs/w1-t14-ci-decisions)
- [agent] Planner recorded ADR 0046 / PG-27: W1-T10 and W1-T11 review decisions; observability PSS privileged awaits owner confirmation (docs/w1-t10-t11-review-decisions)
- [agent] Added task up, secrets:local, trust-ca, build_images and wait_apps scripts; first local k3d bring-up on 2026-11-27 verified pgvector 0.8.6, collector log permissions, Prometheus pod labels, Gateway acceptance and the memory total (3.684 GiB); recorded root-chart defects D1 to D4 and DNS problem E1 in wiki/components/argocd.md; Step 7 (trust-ca, browser) not run (W1-T12, branch feat/w1-task-up)
- 2026-11-28 [agent] W1-T12 Step 5 and Step 8 re-check after task up exit 0 (smoke: 15 PASS)
- [agent] Planner recorded ADR 0047 / PG-28: W1-T12 bring-up decisions (explicit Application namespaces, sync retry, root ignores child finalizers, node DNS search list stripped by task up) (docs/w1-t12-bringup-decisions)
- [agent] Recorded W1-T09 step 6 real-render findings (22 files; astronomy-db, valkey-cart, kafka are Deployments; LOCUST_USERS container index 0) in wiki/components/workload.md
- [agent] rootline-env commit 1acc350 (1acc3501b1163ed2e21192a63810b8e7f9898089) renders workload from opentelemetry-demo 0.42.8; tag baseline-v1 on it; pushed to origin main (W1-T09 step 7, made by the coordinator)

## 2026-11-28
- [agent] Planner recorded ADR 0048 / PG-29: Deployment kafka never Ready because the KRaft voter 1@kafka:9093 goes through Service kafka; WKL-010 step 7 sets KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093, re-render as rootline-env tag baseline-v2, baseline-v1 unchanged (docs/w1-kafka-readiness-decision)
- [agent] Added the kafka KRaft voter rule (KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093) and BASELINE_TAG baseline-v2 to the workload render (ADR 0048, PG-29); rootline-env re-render pending
- [agent] W1-T13: baseline health gate passed on 2026-11-28 (30 min, 13 of 13 services PASS, 0 restarts, baseline-v2 workload); recorded telemetry names and findings F1 to F10 in wiki/components/telemetry.md; wrote metric-map.yaml, thresholds, PrometheusRule rootline-workload (89 rules, healthy and inactive in the live cluster) and AlertmanagerConfig; ADR 0049 / PG-30 (feat/w1-baseline-gate 77560ca)
- [agent] W1-T13 review fix round 1: baseline_gate exits 2 on every precondition failure (kubectl missing, timeout, malformed JSON, port-forward start); derive_thresholds writes both outputs through temporary files and exits 2 on OSError; tests for PromClient and main(); ADR 0049 D6 to D8 corrected (error_ratio never no-data, fraud-detection rules cannot fire, live Alertmanager configuration facts); open HighCPU defect (no CPU request or limit on 19 shop containers, verified 2026-11-28) handed to the planner as PENDING; Tempo restarts measured 23 in 11 h 49 min (feat/w1-baseline-gate)
