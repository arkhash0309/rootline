"""Load and validate versions.yaml (GEN-050)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]

# key -> regex the resolved version must fully match (spec GEN-050 table)
CONSTRAINTS: dict[str, str] = {
    "python": r"^3\.12\.\d+$",
    "node": r"^24\.\d+\.\d+$",
    "uv": r"^\d+\.\d+\.\d+$",
    "fastapi": r"^\d+\.\d+\.\d+$",
    "sqlalchemy": r"^2\.0\.\d+$",
    "alembic": r"^1\.\d+\.\d+$",
    "pydantic": r"^2\.\d+\.\d+$",
    "psycopg": r"^3\.\d+\.\d+$",
    "httpx": r"^\d+\.\d+\.\d+$",
    "anthropic": r"^1\.\d+\.\d+$",
    "langgraph": r"^1\.\d+\.\d+$",
    "langgraph-checkpoint-postgres": r"^\d+\.\d+\.\d+$",
    "mcp": r"^\d+\.\d+\.\d+$",
    "langfuse": r"^3\.\d+\.\d+$",
    "drain3": r"^0\.9\.\d+$",
    "ruptures": r"^1\.1\.\d+$",
    "fastembed": r"^\d+\.\d+\.\d+$",
    "pgvector": r"^0\.8\.\d+$",
    "next": r"^16\.\d+\.\d+$",
    "react": r"^19\.\d+\.\d+$",
    "typescript": r"^5\.\d+\.\d+$",
    "tailwindcss": r"^4\.\d+\.\d+$",
    "keycloak": r"^26\.8\.\d+$",
    "keycloak-config-cli": r"^\d+\.\d+\.\d+.*$",
    "argo-cd": r"^3\.\d+\.\d+$",
    "k3d": r"^5\.(8|9|\d{2,})\.\d+$",
    "k3s": r"^v1\.\d+\.\d+\+k3s\d+$",
    "gke": r"^REGULAR$",
    "kube-prometheus-stack": r"^\d+\.\d+\.\d+$",
    "loki": r"^6\.\d+\.\d+$",
    "tempo": r"^\d+\.\d+\.\d+$",
    "opentelemetry-collector": r"^\d+\.\d+\.\d+$",
    "chaos-mesh": r"^2\.(7|8|9|\d{2,})\.\d+$",
    "kyverno": r"^3\.\d+\.\d+$",
    "external-secrets": r"^\d+\.\d+\.\d+$",
    "cert-manager": r"^v?1\.\d+\.\d+$",
    "cloudnative-pg": r"^\d+\.\d+\.\d+$",
    "traefik": r"^3\.\d+\.\d+$",
    "opa": r"^1\.\d+\.\d+$",
    "opentelemetry-demo": r"^0\.42\.8$",
    "terraform": r"^1\.(1[3-9]|[2-9]\d)\.\d+$",
    "google": r"^7\.\d+\.\d+$",
    "ollama": r"^\d+\.\d+\.\d+$",
    "playwright": r"^1\.\d+\.\d+$",
}


def load_versions(path: Path = REPO / "versions.yaml") -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError("versions.yaml must be a mapping")
    return data


def version_of(key: str, data: dict[str, Any] | None = None) -> str:
    data = data if data is not None else load_versions()
    value = data[key]
    if isinstance(value, dict):
        return str(value["version"])
    return str(value)


def validate(data: dict[str, Any], keys: list[str] | None = None) -> list[str]:
    errors: list[str] = []
    for key in keys if keys is not None else list(CONSTRAINTS):
        if key not in data:
            errors.append(f"{key}: missing")
            continue
        v = version_of(key, data)
        pattern = CONSTRAINTS[key]
        if not re.fullmatch(pattern, v):
            errors.append(f"{key}: {v!r} does not match {pattern}")
    for key, value in data.items():
        if isinstance(value, dict) and "digest" in value:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(value["digest"])):
                errors.append(f"{key}: bad digest {value['digest']!r}")
    return errors
