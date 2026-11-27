"""Verifies GEN-060 (up, secrets:local, trust-ca, images), PG-9, INF-030 (ADR 0046 T6), ARC-030."""

import base64
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import build_images, trust_ca, up, wait_apps
from scripts.secrets_local import (
    build_bootstrap_secret,
    namespace_manifest,
    normalise_pem,
    repo_secret,
)

REPO = Path(__file__).resolve().parents[2]


def test_bootstrap_secret_excludes_host_only_keys() -> None:
    """GEN-060, PG-9: host-only and deploy-key variables never reach the cluster secret."""
    s = build_bootstrap_secret(
        {
            "ANTHROPIC_API_KEY": "k",
            "DEPLOY_KEY_ROOTLINE": "p",
            "ROOTLINE_HOST_ANTHROPIC_API_KEY": "h",
            "HF_USER": "u",
            "EMPTY": "",
        }
    )
    assert s["metadata"] == {"name": "rootline-bootstrap", "namespace": "rootline-secrets"}
    assert set(s["data"]) == {"ANTHROPIC_API_KEY"}
    assert base64.b64decode(s["data"]["ANTHROPIC_API_KEY"]) == b"k"


def test_bootstrap_secret_excludes_every_deploy_key_and_env_dir() -> None:
    """GEN-060: DEPLOY_KEY_* prefix and ROOTLINE_ENV_DIR are excluded; None values count as empty."""
    s = build_bootstrap_secret(
        {
            "DEPLOY_KEY_ROOTLINE_ENV": "p",
            "ROOTLINE_ENV_DIR": "/x",
            "LANGFUSE_HOST": "https://cloud.langfuse.com",
            "SEED_OWNER": None,
        }
    )
    assert s["kind"] == "Secret"
    assert s["apiVersion"] == "v1"
    assert s["type"] == "Opaque"
    assert set(s["data"]) == {"LANGFUSE_HOST"}


def test_bootstrap_secret_may_be_empty_in_week_one() -> None:
    """GEN-060: in week 1 `.env.local` has no secret value; the Secret is still created with no data."""
    s = build_bootstrap_secret({"DEPLOY_KEY_ROOTLINE": "p", "ROOTLINE_ENV_DIR": "/x"})
    assert s["data"] == {}


def test_repo_secret_shape() -> None:
    """GEN-060, PG-9: ArgoCD repository secret with the label ArgoCD selects on."""
    s = repo_secret("deploy-key-rootline", "git@github.com:arkhash0309/rootline.git", "PEM")
    assert s["metadata"]["labels"] == {"argocd.argoproj.io/secret-type": "repository"}
    assert s["metadata"]["namespace"] == "argocd"
    assert s["stringData"] == {
        "type": "git",
        "url": "git@github.com:arkhash0309/rootline.git",
        "sshPrivateKey": "PEM",
    }


def test_normalise_pem_adds_final_newline() -> None:
    """OpenSSH rejects a private key without a final newline."""
    assert normalise_pem("A\nB") == "A\nB\n"
    assert normalise_pem("A\nB\n\n") == "A\nB\n"


def test_namespace_manifest() -> None:
    assert namespace_manifest("argocd") == {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {"name": "argocd"},
    }


def test_k3d_config_substitutes_both_placeholders() -> None:
    """INF-030, ADR 0046 T6: `+` becomes `-` in the k3s tag; `<repo>` becomes the absolute path."""
    template = (REPO / "infra/k3d/rootline.yaml").read_text(encoding="utf-8")
    out = up.render_k3d_config(template, "v1.36.6+k3s1", "/home/arkhash0309/projects/rootline")
    assert "<versions.k3s>" not in out
    assert "<repo>" not in out
    config = yaml.safe_load(out)
    assert config["image"] == "rancher/k3s:v1.36.6-k3s1"
    assert config["volumes"][0]["volume"].startswith(
        "/home/arkhash0309/projects/rootline/infra/k3d/manifests:"
    )


def test_k3d_template_keeps_placeholders() -> None:
    """INF-030: the committed template keeps both placeholders."""
    template = (REPO / "infra/k3d/rootline.yaml").read_text(encoding="utf-8")
    assert "<versions.k3s>" in template
    assert "<repo>" in template


def test_generated_k3d_config_is_gitignored() -> None:
    """ADR 0046 T6: the generated file is ignored and the two lines end `.gitignore` exactly."""
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert lines[-2:] == [
        "# Generated k3d config (W1-T12, ADR 0046 T6)",
        "infra/k3d/rootline.generated.yaml",
    ]


def test_cluster_exists_parses_k3d_json() -> None:
    assert up.cluster_exists(json.dumps([{"name": "rootline"}]), "rootline")
    assert not up.cluster_exists(json.dumps([{"name": "other"}]), "rootline")
    assert not up.cluster_exists("[]", "rootline")


def test_root_application_manifest() -> None:
    """INF-020: Application `root` in project default with automated prune and selfHeal."""
    app = up.root_application(
        repo_url="git@github.com:arkhash0309/rootline.git", revision="develop", domain="127.0.0.1.sslip.io"
    )
    assert app["metadata"] == {"name": "root", "namespace": "argocd"}
    spec = app["spec"]
    assert spec["project"] == "default"
    assert spec["source"]["path"] == "deploy/root"
    assert spec["source"]["targetRevision"] == "develop"
    assert spec["source"]["helm"]["parameters"] == [
        {"name": "env", "value": "local"},
        {"name": "domain", "value": "127.0.0.1.sslip.io"},
        {"name": "targetRevision", "value": "develop"},
    ]
    assert spec["syncPolicy"]["automated"] == {"prune": True, "selfHeal": True}
    assert spec["destination"] == {"server": "https://kubernetes.default.svc", "namespace": "argocd"}


def test_expected_app_names_are_the_local_applications() -> None:
    """INF-020: names come from `helm template`; gke-only and disabled apps are absent for `local`."""
    rendered = """
---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: {name: namespaces, namespace: argocd}
---
apiVersion: v1
kind: ConfigMap
metadata: {name: not-an-app}
---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: {name: workload, namespace: argocd}
"""
    assert up.application_names(rendered) == ["namespaces", "workload"]


def _app_json(*pairs: tuple[str, str, str]) -> str:
    return json.dumps(
        {
            "items": [
                {
                    "metadata": {"name": name},
                    "status": {"sync": {"status": sync}, "health": {"status": health}},
                }
                for name, sync, health in pairs
            ]
        }
    )


def test_unhealthy_names() -> None:
    """GEN-060: wait_apps reports every Application that is not Synced and Healthy."""
    doc = _app_json(("a", "Synced", "Healthy"), ("b", "OutOfSync", "Healthy"), ("c", "Synced", "Progressing"))
    assert wait_apps.unhealthy(doc, expected=[]) == ["b", "c"]


def test_unhealthy_reports_missing_expected_and_empty_status() -> None:
    doc = json.dumps({"items": [{"metadata": {"name": "a"}}]})
    assert wait_apps.unhealthy(doc, expected=["a", "z"]) == ["a", "z"]
    assert wait_apps.unhealthy(_app_json(), expected=[]) == ["(no Application found)"]


def test_unhealthy_invalid_json_is_pending() -> None:
    assert wait_apps.unhealthy("not json", expected=[]) == ["(kubectl output is not JSON)"]


def test_wait_all_returns_empty_when_all_healthy() -> None:
    outputs = iter([_app_json(("a", "Synced", "Progressing")), _app_json(("a", "Synced", "Healthy"))])
    clock = {"now": 0.0}

    def fake_get(_context: str) -> str:
        return next(outputs)

    def fake_sleep(s: float) -> None:
        clock["now"] += s

    assert (
        wait_apps.wait_all("ctx", 100, get_apps=fake_get, sleep=fake_sleep, monotonic=lambda: clock["now"])
        == []
    )
    assert clock["now"] == 15.0


def test_wait_all_returns_names_on_timeout() -> None:
    clock = {"now": 0.0}

    def fake_sleep(s: float) -> None:
        clock["now"] += s

    left = wait_apps.wait_all(
        "ctx",
        40,
        get_apps=lambda _c: _app_json(("a", "Synced", "Healthy"), ("b", "Synced", "Degraded")),
        sleep=fake_sleep,
        monotonic=lambda: clock["now"],
    )
    assert left == ["b"]
    assert clock["now"] <= 40


def test_services_are_directories_with_a_dockerfile() -> None:
    """GEN-060: image name = directory name of every services/*/Dockerfile, plus console."""
    expected = sorted(p.parent.name for p in REPO.glob("services/*/Dockerfile"))
    if (REPO / "apps/console/Dockerfile").exists():
        expected.append("console")
    assert build_images.SERVICES == expected


def test_build_args_use_repo_at_digest() -> None:
    """GEN-050: base images are referenced as repo@digest."""
    args = build_images.build_args(
        {"python-image": {"repo": "r/python", "digest": "sha256:aa", "version": "1"}},
        {"PYTHON_IMAGE": "python-image"},
    )
    assert args == ["--build-arg", "PYTHON_IMAGE=r/python@sha256:aa"]


def test_build_command() -> None:
    cmd = build_images.build_command("api", "dev", Path("/r"), ["--build-arg", "A=b"])
    assert cmd == [
        "docker",
        "buildx",
        "build",
        "--load",
        "-f",
        "/r/services/api/Dockerfile",
        "-t",
        "rootline/api:dev",
        "--build-arg",
        "A=b",
        "/r",
    ]
    console = build_images.build_command("console", "dev", Path("/r"), [])
    assert console[console.index("-f") + 1] == "/r/apps/console/Dockerfile"


def test_build_images_without_dockerfile_skips(monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    monkeypatch.setattr(build_images, "SERVICES", [])
    assert build_images.main(["--tag", "dev", "--import-k3d", "rootline"]) == 0
    assert "no image has a Dockerfile" in capsys.readouterr().out


def test_trust_ca_refuses_outside_wsl(monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    """GEN-060, PG-17: no WSL_DISTRO_NAME and no --linux-only is an error."""
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    assert trust_ca.main([]) == 1
    assert "WSL" in capsys.readouterr().err


def test_trust_ca_command_lists() -> None:
    """GEN-060, PG-17, INF-031: the three trust steps use the documented commands."""
    ca = Path("/r/data/rootline-ca.crt")
    assert trust_ca.system_store_commands(ca) == [
        ["sudo", "install", "-m", "0644", str(ca), "/usr/local/share/ca-certificates/rootline-ca.crt"],
        ["sudo", "update-ca-certificates"],
    ]
    nss = trust_ca.nss_commands(ca, Path("/home/u/.pki/nssdb"), db_exists=False)
    assert nss[0] == ["certutil", "-d", "sql:/home/u/.pki/nssdb", "-N", "--empty-password"]
    assert nss[1] == [
        "certutil",
        "-d",
        "sql:/home/u/.pki/nssdb",
        "-A",
        "-t",
        "C,,",
        "-n",
        "rootline-local-ca",
        "-i",
        str(ca),
    ]
    assert len(trust_ca.nss_commands(ca, Path("/home/u/.pki/nssdb"), db_exists=True)) == 1
    assert trust_ca.windows_command("C:\\r\\ca.crt") == [
        "/mnt/c/Windows/System32/certutil.exe",
        "-user",
        "-addstore",
        "Root",
        "C:\\r\\ca.crt",
    ]
