"""Pure transforms for rendered OTel Demo manifests (WKL-010, PG-11, PG-12, PG-25, PG-29)."""

from __future__ import annotations

import copy
import json
from typing import Any

import yaml

COLLECTOR_FQDN = "otel-collector.observability.svc.cluster.local"
# WKL-010 step 7, PG-29 (ADR 0048 D1): the single KRaft voter is the kafka pod itself, not Service kafka.
KAFKA_QUORUM_VOTERS = "1@localhost:9093"
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
# Kinds that the reference rule can keep, and the shared file of each (PG-25 D1, D2).
REFERENCED_KINDS = ("ServiceAccount", "ConfigMap")
SHARED_STEMS = {"ServiceAccount": "serviceaccount", "ConfigMap": "configmaps"}
# Objects Kubernetes creates in every namespace; a reference to one is never an error (PG-25 D3).
AUTO_CREATED = frozenset({("ServiceAccount", "default"), ("ConfigMap", "kube-root-ca.crt")})


class UnresolvedReferenceError(ValueError):
    """A kept workload references an object that is not in the output (PG-25 D3)."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


def component_of(obj: dict[str, Any]) -> str:
    labels = obj.get("metadata", {}).get("labels", {}) or {}
    return str(labels.get("app.kubernetes.io/component") or obj["metadata"]["name"])


def pod_references(spec: dict[str, Any]) -> set[tuple[str, str, bool]]:
    """(kind, name, optional) of every object a pod spec references by name (PG-25 D1)."""
    refs: set[tuple[str, str, bool]] = set()
    account = spec.get("serviceAccountName") or spec.get("serviceAccount")
    if account:
        refs.add(("ServiceAccount", account, False))
    for pull in spec.get("imagePullSecrets") or []:
        refs.add(("Secret", pull["name"], False))
    for vol in spec.get("volumes") or []:
        if "configMap" in vol:
            refs.add(("ConfigMap", vol["configMap"]["name"], bool(vol["configMap"].get("optional"))))
        if "secret" in vol:
            refs.add(("Secret", vol["secret"]["secretName"], bool(vol["secret"].get("optional"))))
        for src in (vol.get("projected") or {}).get("sources") or []:
            if "configMap" in src:
                refs.add(("ConfigMap", src["configMap"]["name"], bool(src["configMap"].get("optional"))))
            if "secret" in src:
                refs.add(("Secret", src["secret"]["name"], bool(src["secret"].get("optional"))))
    for c in (spec.get("containers") or []) + (spec.get("initContainers") or []):
        for src in c.get("envFrom") or []:
            if "configMapRef" in src:
                refs.add(
                    ("ConfigMap", src["configMapRef"]["name"], bool(src["configMapRef"].get("optional")))
                )
            if "secretRef" in src:
                refs.add(("Secret", src["secretRef"]["name"], bool(src["secretRef"].get("optional"))))
        for e in c.get("env") or []:
            value_from = e.get("valueFrom") or {}
            if "configMapKeyRef" in value_from:
                ref = value_from["configMapKeyRef"]
                refs.add(("ConfigMap", ref["name"], bool(ref.get("optional"))))
            if "secretKeyRef" in value_from:
                ref = value_from["secretKeyRef"]
                refs.add(("Secret", ref["name"], bool(ref.get("optional"))))
    return refs


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
    placed: set[tuple[str, str]] = set()  # (kind, name) of every object already in `out`
    candidates: dict[tuple[str, str], dict[str, Any]] = {}  # unplaced ServiceAccounts and ConfigMaps
    # (kind, name) -> {(component, workload kind, workload name)} of the kept workloads referencing it
    referrers: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    required: set[tuple[str, str]] = set()  # referenced at least once without optional: true
    for original in docs:
        obj = copy.deepcopy(original)
        if obj["kind"] == "Secret":
            continue
        obj["metadata"]["namespace"] = "shop"
        obj["metadata"].pop("managedFields", None)
        key = (obj["kind"], obj["metadata"]["name"])
        if obj["kind"] == "ConfigMap" and obj["metadata"]["name"] == "flagd-config":
            _flags_off(obj)
            out.setdefault("flagd-config", []).append(obj)
            placed.add(key)
            continue
        comp = component_of(obj)
        if comp not in KEPT_COMPONENTS:
            if obj["kind"] in REFERENCED_KINDS:
                candidates[key] = obj
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
            if comp == "kafka":
                _set_env(spec["containers"][0], "KAFKA_CONTROLLER_QUORUM_VOTERS", KAFKA_QUORUM_VOTERS)
            for kind, name, optional in pod_references(spec):
                referrers.setdefault((kind, name), set()).add((comp, obj["kind"], obj["metadata"]["name"]))
                if not optional:
                    required.add((kind, name))
        out.setdefault(comp, []).append(obj)
        placed.add(key)
    errors: set[str] = set()
    for key in sorted(referrers):
        kind, name = key
        if key in placed or key in AUTO_CREATED:
            continue
        if kind in REFERENCED_KINDS and key in candidates:
            comps = sorted({comp for comp, _, _ in referrers[key]})
            stem = comps[0] if len(comps) == 1 else SHARED_STEMS[kind]
            out.setdefault(stem, []).append(candidates[key])
            placed.add(key)
            continue
        if key not in required:
            continue
        reason = (
            "Secrets are removed by WKL-010 step 2" if kind == "Secret" else "not in the helm template output"
        )
        for _, wkind, wname in referrers[key]:
            errors.add(f"unresolved reference {wkind}/{wname} -> {kind}/{name} ({reason})")
    if errors:
        raise UnresolvedReferenceError(sorted(errors))
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
