"""`task secrets:local` (GEN-060, SEC-100, PG-9): create the local bootstrap secrets from `.env.local`.

Usage: uv run python scripts/secrets_local.py [--context k3d-rootline]

Creates, with `kubectl --context <ctx> apply -f -`:
  1. Namespaces `rootline-secrets` and `argocd` (when missing).
  2. Secret `rootline-secrets/rootline-bootstrap` holding every non-empty `.env.local` key except
     `DEPLOY_KEY_*`, `ROOTLINE_ENV_DIR`, `ROOTLINE_HOST_ANTHROPIC_API_KEY` and `HF_USER`.
  3. ArgoCD repository secrets `argocd/deploy-key-rootline` and `argocd/deploy-key-rootline-env`
     (label `argocd.argoproj.io/secret-type: repository`, SSH deploy keys from `DEPLOY_KEY_ROOTLINE`
     and `DEPLOY_KEY_ROOTLINE_ENV`).

Exit codes: 0 all applied; 1 a deploy key is missing from `.env.local` or `kubectl apply` failed.
Secret values are never printed.
"""

from __future__ import annotations

import argparse
import base64
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXT = "k3d-rootline"
BOOTSTRAP_NAMESPACE = "rootline-secrets"
BOOTSTRAP_NAME = "rootline-bootstrap"
EXCLUDED_KEYS = frozenset({"ROOTLINE_ENV_DIR", "ROOTLINE_HOST_ANTHROPIC_API_KEY", "HF_USER"})
EXCLUDED_PREFIX = "DEPLOY_KEY_"
REPO_KEYS = (  # (secret name, `.env.local` key, key of deploy/root/values.yaml holding the URL)
    ("deploy-key-rootline", "DEPLOY_KEY_ROOTLINE", "repoURL"),
    ("deploy-key-rootline-env", "DEPLOY_KEY_ROOTLINE_ENV", "envRepoURL"),
)


def build_bootstrap_secret(env: Mapping[str, str | None]) -> dict[str, Any]:
    """Secret manifest with every non-empty key of `env` except the host-only keys (GEN-060)."""
    data = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in sorted(env.items())
        if value and key not in EXCLUDED_KEYS and not key.startswith(EXCLUDED_PREFIX)
    }
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": BOOTSTRAP_NAME, "namespace": BOOTSTRAP_NAMESPACE},
        "type": "Opaque",
        "data": data,
    }


def repo_secret(name: str, url: str, key_pem: str) -> dict[str, Any]:
    """ArgoCD repository Secret for an SSH deploy key (PG-9)."""
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": name,
            "namespace": "argocd",
            "labels": {"argocd.argoproj.io/secret-type": "repository"},
        },
        "stringData": {"type": "git", "url": url, "sshPrivateKey": key_pem},
    }


def namespace_manifest(name: str) -> dict[str, Any]:
    return {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": name}}


def normalise_pem(pem: str) -> str:
    """Exactly one final newline: OpenSSH rejects a private key file without it."""
    return pem.rstrip("\n") + "\n"


def apply(context: str, manifest: dict[str, Any]) -> bool:
    result = run(
        ["kubectl", "--context", context, "apply", "-f", "-"],
        check=False,
        input_text=yaml.safe_dump(manifest),
    )
    kind_name = f"{manifest['kind']}/{manifest['metadata']['name']}"
    if result.returncode != 0:
        print(f"FAIL {kind_name}: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"OK   {kind_name}")
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--context", default=DEFAULT_CONTEXT)
    args = parser.parse_args(argv)
    env_file = REPO / ".env.local"
    if not env_file.exists():
        print(f"FAIL {env_file} does not exist", file=sys.stderr)
        return 1
    env = dict(dotenv_values(env_file))
    root_values = yaml.safe_load((REPO / "deploy/root/values.yaml").read_text(encoding="utf-8"))
    missing = [key for _, key, _ in REPO_KEYS if not env.get(key)]
    if missing:
        print(f"FAIL .env.local has no value for: {', '.join(missing)}", file=sys.stderr)
        return 1
    manifests: list[dict[str, Any]] = [namespace_manifest(BOOTSTRAP_NAMESPACE), namespace_manifest("argocd")]
    manifests.append(build_bootstrap_secret(env))
    for name, key, url_key in REPO_KEYS:
        manifests.append(repo_secret(name, root_values[url_key], normalise_pem(env[key] or "")))
    ok = all([apply(args.context, m) for m in manifests])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
