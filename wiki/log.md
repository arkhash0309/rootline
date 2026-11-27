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
