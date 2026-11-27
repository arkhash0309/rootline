"""Pure transforms for rendered OTel Demo manifests (WKL-010, PG-11, PG-12)."""

from __future__ import annotations

import copy
import json
from typing import Any

import yaml

COLLECTOR_FQDN = "otel-collector.observability.svc.cluster.local"
KEPT_COMPONENTS = [
    "frontend",
    "frontend-proxy",
    "load-generator",
    "flagd",
    "ad",
    "cart",
    "valkey-cart",
    "checkout",
    "currency",
    "email",
    "payment",
    "product-catalog",
    "astronomy-db",
    "quote",
    "recommendation",
    "shipping",
    "kafka",
    "fraud-detection",
    "image-provider",
]
WORKLOAD_KINDS = ("Deployment", "StatefulSet")
KIND_ORDER = ["ServiceAccount", "ConfigMap", "Service", "Deployment", "StatefulSet"]


def component_of(obj: dict[str, Any]) -> str:
    labels = obj.get("metadata", {}).get("labels", {}) or {}
    return str(labels.get("app.kubernetes.io/component") or obj["metadata"]["name"])


def _set_env(container: dict[str, Any], name: str, value: str) -> None:
    for e in container.setdefault("env", []):
        if e["name"] == name:
            e.pop("valueFrom", None)
            e["value"] = value
            return
    container["env"].append({"name": name, "value": value})


def _fix_otel(container: dict[str, Any]) -> None:
    for e in container.get("env", []):
        if e["name"] == "OTEL_COLLECTOR_NAME":
            e.pop("valueFrom", None)
            e["value"] = COLLECTOR_FQDN
        elif e["name"] == "OTEL_EXPORTER_OTLP_ENDPOINT" and "$(OTEL_COLLECTOR_NAME)" not in e.get(
            "value", ""
        ):
            scheme, _, rest = e["value"].partition("://")
            port = rest.rsplit(":", 1)[1] if ":" in rest else "4317"
            e["value"] = f"{scheme}://{COLLECTOR_FQDN}:{port}"


def _add_readiness(container: dict[str, Any]) -> None:
    ports = container.get("ports") or []
    if ports and "readinessProbe" not in container:
        container["readinessProbe"] = {
            "tcpSocket": {"port": ports[0]["containerPort"]},
            "initialDelaySeconds": 5,
            "periodSeconds": 10,
            "failureThreshold": 3,
        }


def _fix_flagd(spec: dict[str, Any]) -> None:
    spec.pop("initContainers", None)
    spec["containers"] = [c for c in spec["containers"] if c["name"] == "flagd"]
    vols = [v for v in spec.get("volumes", []) if v["name"] != "config-ro"]
    for v in vols:
        if v["name"] == "config-rw":
            v.clear()
            v.update({"name": "config-rw", "configMap": {"name": "flagd-config"}})
    spec["volumes"] = vols


def _flags_off(cm: dict[str, Any]) -> None:
    data = json.loads(cm["data"]["demo.flagd.json"])
    for flag in data["flags"].values():
        flag["defaultVariant"] = "off"
    cm["data"]["demo.flagd.json"] = json.dumps(data, indent=2, sort_keys=True) + "\n"


def network_policies() -> list[dict[str, Any]]:
    base = {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy"}
    return [
        {
            **base,
            "metadata": {"name": "allow-observability-scrape", "namespace": "shop"},
            "spec": {
                "podSelector": {},
                "policyTypes": ["Ingress"],
                "ingress": [
                    {
                        "from": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {"kubernetes.io/metadata.name": "observability"}
                                }
                            }
                        ]
                    }
                ],
            },
        },
        {
            **base,
            "metadata": {"name": "allow-same-namespace", "namespace": "shop"},
            "spec": {
                "podSelector": {},
                "policyTypes": ["Ingress"],
                "ingress": [{"from": [{"podSelector": {}}]}],
            },
        },
    ]


def transform(docs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for original in docs:
        obj = copy.deepcopy(original)
        if obj["kind"] == "Secret":
            continue
        obj["metadata"]["namespace"] = "shop"
        obj["metadata"].pop("managedFields", None)
        if obj["kind"] == "ConfigMap" and obj["metadata"]["name"] == "flagd-config":
            _flags_off(obj)
            out.setdefault("flagd-config", []).append(obj)
            continue
        comp = component_of(obj)
        if comp not in KEPT_COMPONENTS:
            continue
        if obj["kind"] in WORKLOAD_KINDS:
            obj["metadata"].setdefault("labels", {})["app.kubernetes.io/part-of"] = "rootline-workload"
            tmpl = obj["spec"]["template"]
            tmpl.setdefault("metadata", {}).setdefault("labels", {})["rootline.dev/workload"] = comp
            spec = tmpl["spec"]
            if comp == "flagd":
                _fix_flagd(spec)
            for c in spec["containers"] + spec.get("initContainers", []):
                _fix_otel(c)
            for c in spec["containers"]:
                _add_readiness(c)
            if comp == "load-generator":
                for name, value in (
                    ("LOCUST_USERS", "10"),
                    ("LOCUST_SPAWN_RATE", "2"),
                    ("LOCUST_AUTOSTART", "true"),
                ):
                    _set_env(spec["containers"][0], name, value)
        out.setdefault(comp, []).append(obj)
    for objs in out.values():
        objs.sort(
            key=lambda o: (
                KIND_ORDER.index(o["kind"]) if o["kind"] in KIND_ORDER else 99,
                o["metadata"]["name"],
            )
        )
    out["networkpolicies"] = sorted(network_policies(), key=lambda o: o["metadata"]["name"])
    return out


def dump(objs: list[dict[str, Any]]) -> str:
    return "---\n".join(yaml.safe_dump(o, sort_keys=True, default_flow_style=False) for o in objs)
