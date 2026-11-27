"""`task up` (GEN-060, INF-030, INF-020): create the local k3d cluster and deploy everything through ArgoCD.

Usage: uv run python scripts/up.py [--revision develop] [--timeout 1200]

Steps, in order, each printing `==> <step>`:
  1. k3d cluster `rootline`: when `k3d cluster list -o json` has no such cluster, write
     `infra/k3d/rootline.generated.yaml` from `infra/k3d/rootline.yaml` (`<versions.k3s>` -> the `k3s` row of
     `versions.yaml` with `+` replaced by `-`; `<repo>` -> the absolute repository path) and run
     `k3d cluster create --config infra/k3d/rootline.generated.yaml`.
  2. Node DNS search list (PG-28, ADR 0047 E1), on every run: `fix_node_dns()` removes the `search` and
     `domain` lines from `/etc/resolv.conf` of the k3d node container, so pods do not resolve `github.com`
     through a workstation DNS suffix with a wildcard record.
  3. `scripts/build_images.py --tag dev --import-k3d rootline`.
  4. Helm release `argocd` (chart `argo/argo-cd` at the `chart` of the `argo-cd` row of `versions.yaml`) in
     namespace `argocd` with `deploy/upstream/argo-cd/values-local.yaml`, `--wait --timeout 10m`.
  5. `scripts/secrets_local.py`.
  6. Application `root` (project `default`, source `deploy/root` at `--revision`, parameters `env=local`,
     `domain=127.0.0.1.sslip.io`, `targetRevision=<--revision>`, `ignoreDifferences` for the finalizers of
     child Applications, automated sync with prune and selfHeal, `RespectIgnoreDifferences=true`, retry
     `SYNC_RETRY`; ADR 0047 D2 and D3).
  7. `scripts/wait_apps.py --timeout <--timeout>`; on timeout the unhealthy names and
     `kubectl -n argocd get applications` are printed.
  8. Print the ArgoCD admin password and URL.
  9. Print `memory_requests_total` (the `scripts/doctor.py` memory check).

Exit codes: 0 every step succeeded; 1 a step failed (message on stderr) or an Application is not
Synced/Healthy.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import wait_apps
from scripts.doctor import cluster_memory_check
from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
CLUSTER = "rootline"
CONTEXT = "k3d-rootline"
DOMAIN = "127.0.0.1.sslip.io"
TEMPLATE = REPO / "infra/k3d/rootline.yaml"
GENERATED = REPO / "infra/k3d/rootline.generated.yaml"
NODE = "k3d-rootline-server-0"  # the only kubelet node of INF-030 (servers: 1, agents: 0)
CMD_TIMEOUT_S = 60
# ADR 0047 D2: equal to the `retry` block of deploy/root/templates/apps.yaml (tests/repo/test_root_chart.py).
SYNC_RETRY: dict[str, Any] = {"limit": 10, "backoff": {"duration": "10s", "factor": 2, "maxDuration": "3m"}}
# ADR 0047 D3: ArgoCD adds PreDelete finalizers to child Applications; `root` must not report them as drift.
ROOT_IGNORE_DIFFERENCES: list[dict[str, Any]] = [
    {"group": "argoproj.io", "kind": "Application", "jsonPointers": ["/metadata/finalizers"]}
]


class StepError(Exception):
    """A bring-up step failed."""


def render_k3d_config(template: str, k3s: str, repo: str) -> str:
    """Substitute the two INF-030 placeholders."""
    return template.replace("<versions.k3s>", k3s.replace("+", "-")).replace("<repo>", repo)


def cluster_exists(k3d_list_json: str, name: str) -> bool:
    return any(c.get("name") == name for c in json.loads(k3d_list_json or "[]"))


def root_application(*, repo_url: str, revision: str, domain: str) -> dict[str, Any]:
    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {"name": "root", "namespace": "argocd"},
        "spec": {
            "project": "default",
            "destination": {"server": "https://kubernetes.default.svc", "namespace": "argocd"},
            "source": {
                "repoURL": repo_url,
                "targetRevision": revision,
                "path": "deploy/root",
                "helm": {
                    "parameters": [
                        {"name": "env", "value": "local"},
                        {"name": "domain", "value": domain},
                        {"name": "targetRevision", "value": revision},
                    ]
                },
            },
            "ignoreDifferences": ROOT_IGNORE_DIFFERENCES,
            "syncPolicy": {
                "automated": {"prune": True, "selfHeal": True},
                "syncOptions": ["RespectIgnoreDifferences=true"],
                "retry": SYNC_RETRY,
            },
        },
    }


def application_names(rendered: str) -> list[str]:
    return [
        d["metadata"]["name"] for d in yaml.safe_load_all(rendered) if d and d.get("kind") == "Application"
    ]


def strip_search_lines(text: str) -> str:
    """Drop every `search` and `domain` line of a resolv.conf; keep every other line and line ending."""
    kept = [
        line for line in text.splitlines(keepends=True) if line.split()[:1] not in (["search"], ["domain"])
    ]
    return "".join(kept)


def _node_run(cmd: list[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return run(cmd, check=False, timeout=CMD_TIMEOUT_S, input_text=input_text)
    except subprocess.TimeoutExpired as error:
        raise StepError(f"{' '.join(cmd)} timed out after {CMD_TIMEOUT_S} s") from error


def _node_run_ok(cmd: list[str], input_text: str | None = None) -> str:
    result = _node_run(cmd, input_text)
    if result.returncode != 0:
        raise StepError(f"{' '.join(cmd)} exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def fix_node_dns(node: str = NODE, context: str = CONTEXT) -> bool:
    """ADR 0047 E1: remove `search` and `domain` lines from the node's /etc/resolv.conf; True when changed.

    On a changed file, ArgoCD workloads of an already existing cluster are restarted so they get a clean
    list; a new cluster has no namespace `argocd` yet and its pods are created after this step.
    """
    read = ["docker", "exec", node, "cat", "/etc/resolv.conf"]
    text = _node_run_ok(read)
    cleaned = strip_search_lines(text)
    if cleaned == text:
        print(f"node DNS: {node} has no search or domain line")
        return False
    _node_run_ok(["docker", "exec", "-i", node, "sh", "-c", "cat > /etc/resolv.conf"], input_text=cleaned)
    reread = _node_run_ok(read)
    if strip_search_lines(reread) != reread:
        raise StepError(f"node DNS: search or domain line still present in {node}:/etc/resolv.conf")
    print(f"node DNS: removed search and domain lines from {node}:/etc/resolv.conf")
    exists = _node_run(["kubectl", "--context", context, "get", "namespace", "argocd", "-o", "name"])
    if exists.returncode == 0:
        for kind in ("deployment", "statefulset"):
            _node_run_ok(["kubectl", "--context", context, "-n", "argocd", "rollout", "restart", kind])
        print("node DNS: restarted deployments and statefulsets in namespace argocd")
    return True


def sh(cmd: list[str], *, input_text: str | None = None, timeout: int = 900) -> str:
    result = run(cmd, check=False, input_text=input_text, timeout=timeout)
    if result.returncode != 0:
        raise StepError(f"{' '.join(cmd)} exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def stream(cmd: list[str], timeout: int) -> None:
    try:
        failed = run(cmd, check=False, capture=False, timeout=timeout).returncode != 0
    except subprocess.TimeoutExpired as error:
        raise StepError(f"{' '.join(cmd)} timed out after {timeout} s") from error
    if failed:
        raise StepError(f"{' '.join(cmd)} failed")


def step_cluster(versions: dict[str, Any]) -> None:
    print("==> k3d cluster", flush=True)
    if cluster_exists(sh(["k3d", "cluster", "list", "-o", "json"]), CLUSTER):
        print(f"cluster {CLUSTER} exists")
        return
    GENERATED.write_text(
        render_k3d_config(TEMPLATE.read_text(encoding="utf-8"), versions["k3s"], str(REPO)), encoding="utf-8"
    )
    stream(["k3d", "cluster", "create", "--config", str(GENERATED)], timeout=900)


def step_node_dns() -> None:
    print("==> node DNS search list", flush=True)
    fix_node_dns()


def step_images() -> None:
    print("==> build and import images", flush=True)
    stream(
        [sys.executable, str(REPO / "scripts/build_images.py"), "--tag", "dev", "--import-k3d", CLUSTER],
        timeout=3600,
    )


def step_argocd(versions: dict[str, Any]) -> None:
    print("==> install ArgoCD", flush=True)
    row = versions["argo-cd"]
    stream(["helm", "repo", "add", "argo", row["repo"], "--force-update"], timeout=600)
    stream(
        [
            "helm", "--kube-context", CONTEXT, "upgrade", "--install", "argocd", "argo/argo-cd",
            "--version", row["chart"], "-n", "argocd", "--create-namespace",
            "-f", str(REPO / "deploy/upstream/argo-cd/values-local.yaml"), "--wait", "--timeout", "10m",
        ],
        timeout=900,
    )  # fmt: skip


def step_secrets() -> None:
    print("==> secrets:local", flush=True)
    stream([sys.executable, str(REPO / "scripts/secrets_local.py"), "--context", CONTEXT], timeout=120)


def step_root(revision: str) -> list[str]:
    print("==> apply root Application", flush=True)
    root_values = yaml.safe_load((REPO / "deploy/root/values.yaml").read_text(encoding="utf-8"))
    rendered = sh(
        ["helm", "template", "root", str(REPO / "deploy/root"), "--set", "env=local",
         "--set", f"domain={DOMAIN}", "--set", f"targetRevision={revision}"]
    )  # fmt: skip
    names = application_names(rendered)
    app = root_application(repo_url=root_values["repoURL"], revision=revision, domain=DOMAIN)
    sh(["kubectl", "--context", CONTEXT, "apply", "-f", "-"], input_text=yaml.safe_dump(app))
    return ["root", *names]


def step_wait(expected: list[str], timeout: int) -> None:
    print("==> wait for applications", flush=True)
    code = wait_apps.main(["--context", CONTEXT, "--timeout", str(timeout), "--expect", *expected])
    if code != 0:
        raise StepError("applications not Synced/Healthy")


def step_report() -> None:
    print("==> ArgoCD login", flush=True)
    encoded = sh(
        ["kubectl", "--context", CONTEXT, "-n", "argocd", "get", "secret", "argocd-initial-admin-secret",
         "-o", "jsonpath={.data.password}"]
    )  # fmt: skip
    print(f"ArgoCD user: admin\nArgoCD password: {base64.b64decode(encoded).decode()}")
    print(f"ArgoCD URL: https://argocd.{DOMAIN}")
    print("==> memory check", flush=True)
    print(cluster_memory_check().line())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--revision", default="develop")
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args(argv)
    versions = yaml.safe_load((REPO / "versions.yaml").read_text(encoding="utf-8"))
    try:
        step_cluster(versions)
        step_node_dns()
        step_images()
        step_argocd(versions)
        step_secrets()
        expected = step_root(args.revision)
        step_wait(expected, args.timeout)
        step_report()
    except StepError as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
