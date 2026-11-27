"""Verifies INF-020 to INF-022, INF-030, INF-031, GEN-012, ARC-010, SEC-011, SEC-033, SEC-100, PG-22."""

import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest
import yaml

from scripts.proc import run

REPO = Path(__file__).resolve().parents[2]
ENVS = ["local", "gke", "ci"]


def render(env: str) -> list[dict]:
    out = run(["helm", "template", "root", str(REPO / "deploy/root"), "--set", f"env={env}"]).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def tmpl(chart: str, env: str, *extra: str) -> list[dict]:
    """helm template of deploy/charts/<chart> with values.yaml, values-<env>.yaml and global.env=<env>."""
    path = REPO / "deploy/charts" / chart
    args = ["helm", "template", "x", str(path), "-f", str(path / "values.yaml")]
    env_file = path / f"values-{env}.yaml"
    if env_file.exists():
        args += ["-f", str(env_file)]
    args += ["--set", f"global.env={env}", *extra]
    return [d for d in yaml.safe_load_all(run(args).stdout) if d]


def by_kind_name(docs: list[dict]) -> dict[tuple[str, str], dict]:
    return {(d["kind"], d["metadata"]["name"]): d for d in docs}


@pytest.mark.parametrize("env", ENVS)
def test_waves_and_sync_policy(env: str) -> None:
    apps = {a["metadata"]["name"]: a for a in render(env)}
    assert apps["namespaces"]["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-4"
    assert apps["rootline"]["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "1"
    for name, a in apps.items():
        sp = a["spec"]["syncPolicy"]
        if name == "workload":
            assert sp["automated"] == {"prune": True, "selfHeal": False}
            # W2-T08 tightens this to == "rootline-workload" when the AppProject exists.
            assert a["spec"]["project"] in {"default", "rootline-workload"}
        else:
            assert sp["automated"] == {"prune": True, "selfHeal": True}
            assert sp["syncOptions"] == ["CreateNamespace=false", "ServerSideApply=true"]


def test_env_filters() -> None:
    assert "chaos-mesh" in {a["metadata"]["name"] for a in render("local")}
    assert "chaos-mesh" not in {a["metadata"]["name"] for a in render("gke")}
    assert "traefik" in {a["metadata"]["name"] for a in render("gke")}
    assert "traefik" not in {a["metadata"]["name"] for a in render("local")}


def test_workload_ignores_load_generator_env() -> None:
    wl = next(a for a in render("local") if a["metadata"]["name"] == "workload")
    assert {
        "group": "apps",
        "kind": "Deployment",
        "name": "load-generator",
        "jsonPointers": ["/spec/template/spec/containers/0/env"],
    } in wl["spec"]["ignoreDifferences"]


def test_namespaces_pss() -> None:
    out = run(["helm", "template", "ns", str(REPO / "deploy/charts/namespaces")]).stdout
    ns = {
        d["metadata"]["name"]: d["metadata"]["labels"]
        for d in yaml.safe_load_all(out)
        if d and d["kind"] == "Namespace"
    }
    expected = {
        "rootline": "restricted",
        "rootline-data": "restricted",
        "rootline-lab": "restricted",
        "rootline-secrets": "restricted",
        "keycloak": "restricted",
        "observability": "baseline",
        "shop": "baseline",
        "argocd": "baseline",
        "chaos-mesh": "privileged",
        "kyverno": "baseline",
        "external-secrets": "baseline",
        "cert-manager": "baseline",
        "cnpg-system": "baseline",
        "traefik": "baseline",
    }
    assert set(ns) == set(expected)
    for name, level in expected.items():
        assert ns[name]["pod-security.kubernetes.io/enforce"] == level, name
        assert ns[name]["pod-security.kubernetes.io/enforce-version"] == "latest", name
        assert ns[name]["rootline.dev/managed"] == "true", name


def test_namespaces_default_deny_and_dns() -> None:
    """ARC-010: default-deny plus allow-dns exactly in the six namespaces marked yes."""
    out = run(["helm", "template", "ns", str(REPO / "deploy/charts/namespaces")]).stdout
    pols = [d for d in yaml.safe_load_all(out) if d and d["kind"] == "NetworkPolicy"]
    denied = {"rootline", "rootline-data", "rootline-lab", "rootline-secrets", "keycloak", "observability"}
    deny = {p["metadata"]["namespace"]: p for p in pols if p["metadata"]["name"] == "default-deny"}
    dns = {p["metadata"]["namespace"]: p for p in pols if p["metadata"]["name"] == "allow-dns"}
    assert set(deny) == denied
    assert set(dns) == denied
    assert len(pols) == 2 * len(denied)
    for p in deny.values():
        assert p["spec"] == {"podSelector": {}, "policyTypes": ["Ingress", "Egress"]}
    for p in dns.values():
        assert p["spec"]["podSelector"] == {}
        assert p["spec"]["policyTypes"] == ["Egress"]
        egress = p["spec"]["egress"]
        assert len(egress) == 1
        assert egress[0]["to"] == [
            {"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "kube-system"}}}
        ]
        assert egress[0]["ports"] == [{"protocol": "UDP", "port": 53}, {"protocol": "TCP", "port": 53}]


def test_apps_contract_matches_plan() -> None:
    """INF-020: the values contract of the root chart (every later wave edits `apps`)."""
    values = yaml.safe_load((REPO / "deploy/root/values.yaml").read_text())
    top = {k: v for k, v in values.items() if k != "apps"}
    assert top == {
        "env": "local",
        "domain": "127.0.0.1.sslip.io",
        "targetRevision": "develop",
        "repoURL": "git@github.com:arkhash0309/rootline.git",
        "envRepoURL": "git@github.com:arkhash0309/rootline-env.git",
        "envRepoRevision": "main",
        "gcpProject": "",
        "k8sIssuer": "https://kubernetes.default.svc.cluster.local",
        "artifactsBucket": "",
        "ingressIP": "",
    }
    waves = {name: (a["enabled"], a["wave"]) for name, a in values["apps"].items()}
    assert waves == {
        "namespaces": (True, -4),
        "gateway-api-crds": (True, -4),
        "cert-manager": (True, -3),
        "external-secrets": (True, -3),
        "cnpg-operator": (True, -3),
        "kyverno": (True, -3),
        "chaos-mesh": (True, -3),
        "prometheus-crds": (True, -3),
        "traefik": (True, -3),
        "platform-config": (True, -2),
        "postgres": (True, -1),
        "observability": (True, -1),
        "keycloak": (False, 0),
        "argocd-accounts": (False, 0),
        "rootline": (True, 1),
        "workload": (True, 2),
        "demo-seed": (False, 2),
    }


@pytest.mark.parametrize("env", ENVS)
def test_application_sources(env: str) -> None:
    versions = yaml.safe_load((REPO / "versions.yaml").read_text())
    apps = {a["metadata"]["name"]: a for a in render(env)}
    # upstream chart: pinned chart version from versions.yaml, values file in this repository
    cm = apps["cert-manager"]["spec"]["sources"]
    assert cm[0]["repoURL"] == versions["cert-manager"]["repo"]
    assert cm[0]["chart"] == "cert-manager"
    assert cm[0]["targetRevision"] == versions["cert-manager"]["chart"]
    assert cm[0]["helm"]["valueFiles"] == [f"$values/deploy/upstream/cert-manager/values-{env}.yaml"]
    assert cm[0]["helm"]["ignoreMissingValueFiles"] is True
    assert cm[1]["ref"] == "values"
    assert cm[1]["repoURL"] == "git@github.com:arkhash0309/rootline.git"
    assert apps["cert-manager"]["spec"]["destination"]["namespace"] == "cert-manager"
    # the application name `cnpg-operator` differs from the values directory `cloudnative-pg`
    cnpg = apps["cnpg-operator"]["spec"]["sources"]
    assert cnpg[0]["chart"] == "cloudnative-pg"
    assert cnpg[0]["helm"]["valueFiles"] == [f"$values/deploy/upstream/cloudnative-pg/values-{env}.yaml"]
    # CRD-only chart is resolved through key prometheus-operator-crds (W1-T02)
    prom = apps["prometheus-crds"]["spec"]["sources"][0]
    assert prom["chart"] == "prometheus-operator-crds"
    assert prom["targetRevision"] == versions["prometheus-operator-crds"]["chart"]
    assert prom["repoURL"] == versions["prometheus-operator-crds"]["repo"]
    # Gateway API CRDs from the pinned release tag
    gw = apps["gateway-api-crds"]["spec"]["source"]
    assert gw["repoURL"] == "https://github.com/kubernetes-sigs/gateway-api"
    assert gw["targetRevision"] == f"v{versions['gateway-api']}"
    assert gw["path"] == "config/crd/standard"
    # local chart: global parameters and values files (INF-020)
    pc = apps["platform-config"]["spec"]["source"]
    assert pc["path"] == "deploy/charts/platform-config"
    assert pc["helm"]["valueFiles"] == ["values.yaml", f"values-{env}.yaml"]
    assert pc["helm"]["ignoreMissingValueFiles"] is True
    assert {p["name"]: p["value"] for p in pc["helm"]["parameters"]} == {
        "global.env": env,
        "global.domain": "127.0.0.1.sslip.io",
        "global.gcpProject": "",
        "global.k8sIssuer": "https://kubernetes.default.svc.cluster.local",
        "global.artifactsBucket": "",
        "global.ingressIP": "",
    }
    # workload: env repository, branch main, path workload, destination namespace shop (GEN-012)
    wl = apps["workload"]["spec"]
    assert wl["source"] == {
        "repoURL": "git@github.com:arkhash0309/rootline-env.git",
        "targetRevision": "main",
        "path": "workload",
    }
    assert wl["destination"] == {"server": "https://kubernetes.default.svc", "namespace": "shop"}
    assert apps["rootline"]["metadata"]["finalizers"] == ["resources-finalizer.argocd.argoproj.io"]


def test_disabled_apps_not_rendered() -> None:
    names = {a["metadata"]["name"] for a in render("local")}
    assert not names & {"keycloak", "argocd-accounts", "demo-seed"}


def test_workload_project_follows_argocd_accounts() -> None:
    out = run(
        [
            "helm",
            "template",
            "root",
            str(REPO / "deploy/root"),
            "--set",
            "apps.argocd-accounts.enabled=true",
        ]
    ).stdout
    apps = {d["metadata"]["name"]: d for d in yaml.safe_load_all(out) if d}
    assert apps["workload"]["spec"]["project"] == "rootline-workload"


def test_k3d_config() -> None:
    """INF-030: the committed k3d Simple config keeps two documented placeholders."""
    text = (REPO / "infra/k3d/rootline.yaml").read_text()
    cfg = yaml.safe_load(text)
    assert cfg["apiVersion"] == "k3d.io/v1alpha5"
    assert cfg["kind"] == "Simple"
    assert cfg["metadata"] == {"name": "rootline"}
    assert cfg["servers"] == 1 and cfg["agents"] == 0
    assert cfg["image"] == "rancher/k3s:<versions.k3s>"
    assert cfg["ports"] == [
        {"port": "80:80", "nodeFilters": ["loadbalancer"]},
        {"port": "443:443", "nodeFilters": ["loadbalancer"]},
    ]
    assert cfg["volumes"] == [
        {
            "volume": "<repo>/infra/k3d/manifests:/var/lib/rancher/k3s/server/manifests/rootline",
            "nodeFilters": ["server:0"],
        }
    ]
    assert cfg["options"]["k3s"]["extraArgs"] == [
        {"arg": "--kubelet-arg=max-pods=150", "nodeFilters": ["server:0"]}
    ]
    # the substituted tag form of versions.k3s must be a valid image tag (no `+`)
    k3s = yaml.safe_load((REPO / "versions.yaml").read_text())["k3s"]
    assert "+" not in k3s.replace("+", "-")


def test_traefik_helmchartconfig() -> None:
    cfg = yaml.safe_load((REPO / "infra/k3d/manifests/traefik-config.yaml").read_text())
    assert cfg["apiVersion"] == "helm.cattle.io/v1"
    assert cfg["kind"] == "HelmChartConfig"
    assert cfg["metadata"] == {"name": "traefik", "namespace": "kube-system"}
    values = yaml.safe_load(cfg["spec"]["valuesContent"])
    assert values == {
        "deployment": {"replicas": 1},
        "providers": {"kubernetesGateway": {"enabled": True}},
        "ports": {"websecure": {"tls": {"enabled": True}}},
    }


@pytest.mark.parametrize("env", ["local", "ci"])
def test_platform_config_tls_and_dns(env: str) -> None:
    docs = by_kind_name(tmpl("platform-config", env, "--set", "global.domain=127.0.0.1.sslip.io"))
    assert docs[("ClusterIssuer", "selfsigned")]["spec"] == {"selfSigned": {}}
    ca = docs[("Certificate", "rootline-local-ca")]
    assert ca["metadata"]["namespace"] == "cert-manager"
    assert ca["spec"]["isCA"] is True
    assert ca["spec"]["duration"] == "87600h"
    assert ca["spec"]["privateKey"] == {"algorithm": "ECDSA", "size": 256}
    assert ca["spec"]["secretName"] == "rootline-local-ca"
    assert ca["spec"]["issuerRef"]["name"] == "selfsigned"
    assert docs[("ClusterIssuer", "rootline-ca")]["spec"] == {"ca": {"secretName": "rootline-local-ca"}}
    wild = docs[("Certificate", "rootline-wildcard")]
    assert wild["metadata"]["namespace"] == "kube-system"
    assert wild["spec"]["dnsNames"] == ["*.127.0.0.1.sslip.io", "127.0.0.1.sslip.io"]
    assert wild["spec"]["issuerRef"]["name"] == "rootline-ca"
    assert wild["spec"]["secretName"] == "rootline-wildcard-tls"
    gw = docs[("Gateway", "rootline")]
    assert gw["metadata"]["namespace"] == "kube-system"
    assert gw["spec"]["gatewayClassName"] == "traefik"
    listeners = {entry["name"]: entry for entry in gw["spec"]["listeners"]}
    assert listeners["http"]["port"] == 80
    assert listeners["https"]["port"] == 443
    assert listeners["https"]["tls"] == {
        "mode": "Terminate",
        "certificateRefs": [{"name": "rootline-wildcard-tls"}],
    }
    for entry in listeners.values():
        assert entry["allowedRoutes"] == {"namespaces": {"from": "All"}}
    cm = docs[("ConfigMap", "coredns-custom")]
    assert cm["metadata"]["namespace"] == "kube-system"
    lines = cm["data"]["rootline.override"].splitlines()
    assert lines == [
        f"rewrite name {host}.127.0.0.1.sslip.io traefik.kube-system.svc.cluster.local"
        for host in ("auth", "console", "argocd")
    ]


def test_platform_config_gke_differences() -> None:
    docs = by_kind_name(tmpl("platform-config", "gke", "--set", "global.domain=1-2-3-4.sslip.io"))
    assert ("ClusterIssuer", "selfsigned") not in docs
    assert ("Certificate", "rootline-local-ca") not in docs
    assert ("ConfigMap", "coredns-custom") not in docs
    assert ("ClusterSecretStore", "bootstrap") not in docs
    assert docs[("Gateway", "rootline")]["metadata"]["namespace"] == "traefik"
    # the pg-roles store and the generators exist in every environment (PG-10)
    assert ("ClusterSecretStore", "pg-roles") in docs
    assert ("Password", "password-48") in docs


@pytest.mark.parametrize("env", ["local", "ci"])
def test_copy_ca_job(env: str) -> None:
    """PG-22, ADR 0041: shell-less kubectl image, `kubectl apply -k /work` over a projected volume."""
    docs = by_kind_name(tmpl("platform-config", env))
    versions = yaml.safe_load((REPO / "versions.yaml").read_text())["kubectl-image"]
    image = f"{versions['repo']}:v{versions['version']}@{versions['digest']}"
    job = docs[("Job", "copy-ca")]
    assert job["metadata"]["namespace"] == "cert-manager"
    assert job["metadata"]["annotations"] == {
        "argocd.argoproj.io/hook": "PostSync",
        "argocd.argoproj.io/hook-delete-policy": "BeforeHookCreation",
    }
    assert job["spec"]["backoffLimit"] == 6
    assert job["spec"]["activeDeadlineSeconds"] == 600
    pod = job["spec"]["template"]["spec"]
    assert pod["restartPolicy"] == "Never"
    assert pod["serviceAccountName"] == "copy-ca"
    (container,) = pod["containers"]
    assert container["name"] == "copy-ca"
    assert container["image"] == image
    assert container["command"] == ["/bin/kubectl", "apply", "-k", "/work"]
    tmp_mount_path = {m["name"]: m for m in container["volumeMounts"]}["tmp"]["mountPath"]
    assert PurePosixPath(tmp_mount_path).parts == ("/", "tmp")
    assert container["env"] == [{"name": "HOME", "value": tmp_mount_path}]
    assert container["securityContext"] == {
        "runAsNonRoot": True,
        "runAsUser": 1000,
        "runAsGroup": 1000,
        "readOnlyRootFilesystem": True,
        "allowPrivilegeEscalation": False,
        "capabilities": {"drop": ["ALL"]},
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    mounts = {m["name"]: m for m in container["volumeMounts"]}
    assert mounts["work"]["mountPath"] == "/work" and mounts["work"]["readOnly"] is True
    assert mounts["tmp"]["mountPath"] == tmp_mount_path
    volumes = {v["name"]: v for v in pod["volumes"]}
    assert volumes["tmp"] == {"name": "tmp", "emptyDir": {}}
    assert volumes["work"]["projected"]["sources"] == [
        {
            "configMap": {
                "name": "copy-ca-kustomization",
                "items": [{"key": "kustomization.yaml", "path": "kustomization.yaml"}],
            }
        },
        {"secret": {"name": "rootline-local-ca", "items": [{"key": "ca.crt", "path": "ca.crt"}]}},
    ]
    kust = yaml.safe_load(docs[("ConfigMap", "copy-ca-kustomization")]["data"]["kustomization.yaml"])
    assert kust == {
        "apiVersion": "kustomize.config.k8s.io/v1beta1",
        "kind": "Kustomization",
        "generatorOptions": {"disableNameSuffixHash": True},
        "configMapGenerator": [
            {"name": "rootline-ca", "namespace": "rootline", "files": ["ca.crt"]},
            {"name": "rootline-ca", "namespace": "keycloak", "files": ["ca.crt"]},
        ],
    }


@pytest.mark.parametrize("env", ["local", "ci"])
def test_copy_ca_rbac(env: str) -> None:
    docs = tmpl("platform-config", env)
    roles = [d for d in docs if d["kind"] == "Role" and d["metadata"]["name"] == "copy-ca"]
    assert {r["metadata"]["namespace"] for r in roles} == {"rootline", "keycloak"}
    for role in roles:
        assert role["rules"] == [
            {"apiGroups": [""], "resources": ["configmaps"], "verbs": ["create"]},
            {
                "apiGroups": [""],
                "resources": ["configmaps"],
                "resourceNames": ["rootline-ca"],
                "verbs": ["get", "patch"],
            },
        ]
    bindings = [d for d in docs if d["kind"] == "RoleBinding" and d["metadata"]["name"] == "copy-ca"]
    assert {b["metadata"]["namespace"] for b in bindings} == {"rootline", "keycloak"}
    for b in bindings:
        assert b["roleRef"] == {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "copy-ca"}
        assert b["subjects"] == [{"kind": "ServiceAccount", "name": "copy-ca", "namespace": "cert-manager"}]
    sa = next(d for d in docs if d["kind"] == "ServiceAccount" and d["metadata"]["name"] == "copy-ca")
    assert sa["metadata"]["namespace"] == "cert-manager"
    # ADR 0041: no Role in cert-manager (the kubelet reads the secret for the projected volume)
    assert not [
        d
        for d in docs
        if d["kind"] in {"Role", "RoleBinding"} and d["metadata"]["namespace"] == "cert-manager"
    ]


def test_copy_ca_image_matches_versions_yaml() -> None:
    values = yaml.safe_load((REPO / "deploy/charts/platform-config/values.yaml").read_text())
    v = yaml.safe_load((REPO / "versions.yaml").read_text())["kubectl-image"]
    assert values["copyCa"]["image"] == f"{v['repo']}:v{v['version']}@{v['digest']}"


def test_eso_stores_and_generators() -> None:
    """SEC-100, PG-10."""
    docs = by_kind_name(tmpl("platform-config", "local"))
    boot = docs[("ClusterSecretStore", "bootstrap")]["spec"]["provider"]["kubernetes"]
    assert boot["remoteNamespace"] == "rootline-secrets"
    assert boot["auth"] == {
        "serviceAccount": {"name": "eso-bootstrap-reader", "namespace": "rootline-secrets"}
    }
    assert boot["server"]["caProvider"] == {
        "type": "ConfigMap",
        "name": "kube-root-ca.crt",
        "key": "ca.crt",
        "namespace": "rootline-secrets",
    }
    boot_role = docs[("Role", "eso-bootstrap-reader")]
    assert boot_role["metadata"]["namespace"] == "rootline-secrets"
    assert boot_role["rules"] == [
        {
            "apiGroups": [""],
            "resources": ["secrets"],
            "resourceNames": ["rootline-bootstrap"],
            "verbs": ["get", "list", "watch"],
        }
    ]
    pg = docs[("ClusterSecretStore", "pg-roles")]["spec"]["provider"]["kubernetes"]
    assert pg["remoteNamespace"] == "rootline-data"
    assert pg["auth"]["serviceAccount"] == {"name": "eso-pg-reader", "namespace": "rootline-data"}
    pg_role = docs[("Role", "eso-pg-reader")]
    assert pg_role["metadata"]["namespace"] == "rootline-data"
    assert pg_role["rules"][0]["resourceNames"] == [
        "pg-rootline-migrator",
        "pg-rootline-api",
        "pg-rootline-agent",
        "pg-rootline-faultlab",
        "pg-rootline-console",
        "pg-keycloak",
    ]
    assert pg_role["rules"][0]["verbs"] == ["get", "list", "watch"]
    gens = [d for d in tmpl("platform-config", "local") if d["kind"] == "Password"]
    assert {d["metadata"]["namespace"] for d in gens} == {
        "rootline-data",
        "rootline",
        "keycloak",
        "observability",
    }
    assert len(gens) == 8
    for d in gens:
        assert d["apiVersion"] == "generators.external-secrets.io/v1alpha1"
        if d["metadata"]["name"] == "password-48":
            assert d["spec"] == {
                "length": 48,
                "digits": 8,
                "symbols": 0,
                "noUpper": False,
                "allowRepeat": True,
            }
        else:
            assert d["metadata"]["name"] == "password-43"
            assert d["spec"] == {
                "length": 43,
                "digits": 8,
                "symbols": 0,
                "noUpper": False,
                "allowRepeat": True,
            }


def test_pg_role_external_secrets() -> None:
    docs = tmpl("platform-config", "local")
    ess = {d["metadata"]["name"]: d for d in docs if d["kind"] == "ExternalSecret"}
    roles = [
        "rootline_migrator",
        "rootline_api",
        "rootline_agent",
        "rootline_faultlab",
        "rootline_console",
        "keycloak",
    ]
    assert set(ess) == {f"pg-{r.replace('_', '-')}" for r in roles}
    for role in roles:
        es = ess[f"pg-{role.replace('_', '-')}"]
        assert es["metadata"]["namespace"] == "rootline-data"
        assert es["spec"]["refreshInterval"] == "0"
        assert es["spec"]["dataFrom"] == [
            {
                "sourceRef": {
                    "generatorRef": {
                        "apiVersion": "generators.external-secrets.io/v1alpha1",
                        "kind": "Password",
                        "name": "password-48",
                    }
                }
            }
        ]
        tpl = es["spec"]["target"]["template"]
        assert tpl["type"] == "kubernetes.io/basic-auth"
        assert tpl["data"] == {"username": role, "password": "{{ .password }}"}


def test_rootline_umbrella_defaults() -> None:
    """INF-022: empty umbrella chart; no template renders an object yet."""
    chart = yaml.safe_load((REPO / "deploy/charts/rootline/Chart.yaml").read_text())
    assert chart["apiVersion"] == "v2" and chart["name"] == "rootline"
    values = yaml.safe_load((REPO / "deploy/charts/rootline/values.yaml").read_text())
    assert values["image"] == {"registry": "rootline", "tag": "dev", "pullPolicy": "IfNotPresent"}
    assert values["security"] == {"delegationMode": "act"}
    assert values["llm"] == {"clusterBudgetUsd": 6}
    assert set(values["resources"]) == {
        "console",
        "api",
        "agent",
        "gate",
        "opa",
        "faultlab",
        "mcp-telemetry",
        "mcp-k8s",
        "mcp-gitops",
    }
    assert values["resources"]["agent"] == {"requests": {"memory": "256Mi"}, "limits": {"memory": "512Mi"}}
    assert tmpl("rootline", "local") == []


def test_rootline_helpers_render(tmp_path: Path) -> None:
    """INF-022, SEC-033: shared helpers, rendered through a throw-away template in a copy of the chart."""
    copy = tmp_path / "rootline"
    shutil.copytree(REPO / "deploy/charts/rootline", copy)
    (copy / "templates/probe.yaml").write_text(
        'psc: {{ include "rootline.podSecurityContext" . | fromYaml | toJson }}\n'
        'csc: {{ include "rootline.containerSecurityContext" . | fromYaml | toJson }}\n'
        'image: {{ include "rootline.image" (dict "Values" .Values "component" "api") }}\n'
        'probes: {{ include "rootline.probes" . | fromYaml | toJson }}\n'
        'otel: {{ include "rootline.otelEnv" (dict "component" "api") | fromYamlArray | toJson }}\n'
        'volume: {{ include "rootline.keycloakTokenVolume" . | fromYaml | toJson }}\n'
        'mount: {{ include "rootline.keycloakTokenVolumeMount" . | fromYaml | toJson }}\n'
    )

    def probe(*extra: str) -> dict:
        out = run(
            ["helm", "template", "x", str(copy), "--set", "global.domain=127.0.0.1.sslip.io", *extra]
        ).stdout
        return yaml.safe_load(out)

    local = probe()
    assert local["psc"] == {
        "runAsNonRoot": True,
        "runAsUser": 10001,
        "runAsGroup": 10001,
        "fsGroup": 10001,
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    assert local["csc"] == {
        "readOnlyRootFilesystem": True,
        "allowPrivilegeEscalation": False,
        "capabilities": {"drop": ["ALL"]},
    }
    assert local["image"] == "rootline/api:dev"
    assert local["probes"]["livenessProbe"]["httpGet"] == {"path": "/healthz", "port": "http"}
    assert local["probes"]["livenessProbe"]["periodSeconds"] == 10
    assert local["probes"]["readinessProbe"]["httpGet"] == {"path": "/readyz", "port": "http"}
    assert local["probes"]["readinessProbe"]["periodSeconds"] == 5
    assert local["otel"] == [
        {
            "name": "OTEL_EXPORTER_OTLP_ENDPOINT",
            "value": "http://otel-collector.observability.svc.cluster.local:4317",
        },
        {"name": "OTEL_SERVICE_NAME", "value": "rootline-api"},
    ]
    assert local["volume"]["name"] == "keycloak-token"
    token = local["volume"]["projected"]["sources"][0]["serviceAccountToken"]
    assert token == {
        "audience": "https://auth.127.0.0.1.sslip.io/realms/rootline",
        "expirationSeconds": 600,
        "path": "keycloak-token",
    }
    assert local["mount"] == {
        "name": "keycloak-token",
        "mountPath": "/var/run/secrets/rootline/keycloak-token",
        "readOnly": True,
    }
    # values-gke.yaml: the registry is templated with the GCP project (INF-022)
    gke = run(
        [
            "helm",
            "template",
            "x",
            str(copy),
            "-f",
            str(copy / "values-gke.yaml"),
            "--set",
            "global.gcpProject=demo-proj",
            "--set",
            "global.domain=1-2-3-4.sslip.io",
        ]
    ).stdout
    assert "image: us-central1-docker.pkg.dev/demo-proj/rootline/api:dev" in gke


def test_upstream_values_files() -> None:
    """Week-1 upstream values (W1-T10 Step 7) for the three environments."""
    base = REPO / "deploy/upstream"
    names = ["argo-cd", "cert-manager", "external-secrets", "cloudnative-pg", "kyverno", "chaos-mesh"]
    for name in names:
        envs = ["local"] if name == "chaos-mesh" else ["local", "ci", "gke"]
        for env in envs:
            assert (base / name / f"values-{env}.yaml").is_file(), f"{name} {env}"
    local = {n: yaml.safe_load((base / n / "values-local.yaml").read_text()) for n in names}
    argo = local["argo-cd"]
    assert argo["dex"] == {"enabled": False}
    assert argo["notifications"] == {"enabled": False}
    assert argo["applicationSet"]["replicas"] == 0
    assert argo["configs"]["params"]["server.insecure"] is True
    assert argo["configs"]["cm"]["admin.enabled"] is True
    assert argo["configs"]["cm"]["accounts.rootline-gate"] == "apiKey"
    assert argo["configs"]["cm"]["accounts.rootline-faultlab"] == "apiKey"
    assert argo["server"]["resources"]["requests"]["memory"] == "160Mi"
    assert argo["repoServer"]["resources"]["requests"]["memory"] == "192Mi"
    assert argo["controller"]["resources"]["requests"]["memory"] == "224Mi"
    assert argo["redis"]["resources"]["requests"]["memory"] == "64Mi"
    assert local["cert-manager"]["crds"]["enabled"] is True
    assert local["external-secrets"]["installCRDs"] is True
    assert local["cloudnative-pg"]["resources"] == {
        "requests": {"memory": "96Mi"},
        "limits": {"memory": "256Mi"},
    }
    kyv = local["kyverno"]
    assert kyv["admissionController"]["replicas"] == 1
    assert kyv["backgroundController"]["replicas"] == 1
    assert kyv["cleanupController"]["enabled"] is False
    assert kyv["reportsController"]["enabled"] is False
    chaos = local["chaos-mesh"]
    assert chaos["chaosDaemon"]["runtime"] == "containerd"
    assert chaos["chaosDaemon"]["socketPath"] == "/run/k3s/containerd/containerd.sock"
    assert chaos["dnsServer"]["create"] is True
    assert chaos["dashboard"]["create"] is False
    assert (base / "gateway-api/README.md").is_file()


def test_upstream_readme_lists_every_chart_repo() -> None:
    """SEC-110: deploy/upstream/README.md lists every chart repository (rootline-platform sources)."""
    readme = (REPO / "deploy/upstream/README.md").read_text()
    versions = yaml.safe_load((REPO / "versions.yaml").read_text())
    for key in [
        "argo-cd",
        "cert-manager",
        "external-secrets",
        "cloudnative-pg",
        "kyverno",
        "chaos-mesh",
        "traefik",
        "kube-prometheus-stack",
        "loki",
        "tempo",
        "opentelemetry-collector",
        "prometheus-operator-crds",
    ]:
        assert versions[key]["repo"] in readme, key
    assert "https://github.com/kubernetes-sigs/gateway-api" in readme
    assert "git@github.com:arkhash0309/rootline.git" in readme


def test_render_manifests_script() -> None:
    """The script renders every environment as one YAML stream and fails on a broken chart."""
    result = subprocess.run(  # noqa: S603 - fixed argument list, no shell (GEN-041)
        [sys.executable, str(REPO / "scripts/render_manifests.py"), "--allow-missing"],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stderr
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    kinds = {d["kind"] for d in docs}
    assert {"Application", "Namespace", "ClusterIssuer", "Gateway", "Job"} <= kinds
    envs = {
        d["spec"]["source"]["helm"]["parameters"][0]["value"]
        for d in docs
        if d["kind"] == "Application" and d["metadata"]["name"] == "platform-config"
    }
    assert envs == set(ENVS)


def test_render_manifests_missing_chart_fails(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO))
    from scripts import render_manifests

    with pytest.raises(render_manifests.RenderError):
        render_manifests.render_local_chart(tmp_path / "no-such-chart", "local")
