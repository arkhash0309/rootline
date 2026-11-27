"""task doctor (GEN-060): prerequisites, Docker memory, .env.local keys, cluster memory requests."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
MEMORY_CAP_GIB = 9.5
UNITS = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "K": 10**3, "M": 10**6, "G": 10**9}


@dataclass(frozen=True)
class Check:
    name: str
    status: Literal["OK", "WARN", "FAIL"]
    detail: str

    def line(self) -> str:
        return f"{self.status:<4} {self.name}: {self.detail}"


def parse_bytes(q: str) -> int:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([KMGT]i?)?", q)
    if not m:
        raise ValueError(q)
    return int(float(m.group(1)) * UNITS.get(m.group(2) or "", 1))


def memory_requests_gib(pods: dict[str, Any]) -> float:
    total = 0
    for pod in pods["items"]:
        if pod["status"].get("phase") in ("Succeeded", "Failed"):
            continue
        for c in pod["spec"].get("containers", []):
            req = c.get("resources", {}).get("requests", {}).get("memory")
            if req:
                total += parse_bytes(req)
    return round(total / 2**30, 3)


def current_week(status_text: str) -> int:
    m = re.search(r"Current milestone: Week (\d+)", status_text)
    return int(m.group(1)) if m else 1


def env_key_checks(example: str, local: dict[str, str | None], week: int) -> list[Check]:
    checks, key_week = [], 1
    for line in example.splitlines():
        if m := re.match(r"# week: (\d+)", line):
            key_week = int(m.group(1))
        elif m := re.match(r"([A-Z0-9_]+)=", line):
            key = m.group(1)
            present = bool(local.get(key))
            if present:
                checks.append(Check(f"env:{key}", "OK", "set"))
            else:
                status: Literal["WARN", "FAIL"] = "FAIL" if key_week <= week else "WARN"
                checks.append(Check(f"env:{key}", status, f"missing (required from week {key_week})"))
    return checks


TOOLS = {  # name -> (version command, regex extracting the version)
    "docker": (["docker", "version", "--format", "{{.Server.Version}}"], r"(\S+)"),
    "k3d": (["k3d", "version"], r"k3d version v(\S+)"),
    "kubectl": (["kubectl", "version", "--client", "-o", "json"], r'"gitVersion":\s*"v(\S+?)"'),
    "helm": (["helm", "version", "--short"], r"v(\S+?)\+"),
    "task": (["task", "--version"], r"(\d+\.\d+\.\d+)"),
    "uv": (["uv", "--version"], r"uv (\S+)"),
    "node": (["node", "--version"], r"v(\S+)"),
    "terraform": (["terraform", "version", "-json"], r'"terraform_version":\s*"(\S+?)"'),
    "gcloud": (["gcloud", "version", "--format=json"], r'"Google Cloud SDK":\s*"(\S+?)"'),
    "gh": (["gh", "--version"], r"gh version (\S+)"),
    "ollama": (["ollama", "--version"], r"(\d+\.\d+\.\d+)"),
    "opa": (["opa", "version"], r"Version: (\S+)"),
    "git": (["git", "--version"], r"git version (\d+\.\d+\.\d+)"),
}


def tool_checks() -> list[Check]:
    out = []
    for name, (cmd, rx) in TOOLS.items():
        if shutil.which(cmd[0]) is None:
            out.append(Check(name, "FAIL", "not on PATH"))
            continue
        r = run(cmd, check=False)
        m = re.search(rx, r.stdout + r.stderr)
        out.append(Check(name, "OK" if m else "WARN", m.group(1) if m else "version not parsed"))
    git = next(c for c in out if c.name == "git")
    if git.status == "OK" and tuple(int(x) for x in git.detail.split(".")[:2]) < (2, 45):
        out[out.index(git)] = Check("git", "FAIL", f"{git.detail} < 2.45")
    login = ""
    if shutil.which("gh") is not None:
        login = run(["gh", "api", "user", "--jq", ".login"], check=False).stdout.strip()
    out.append(Check("gh-account", "OK" if login == "arkhash0309" else "FAIL", login or "not authenticated"))
    return out


def docker_memory_check() -> Check:
    if shutil.which("docker") is None:
        return Check("docker-memory", "FAIL", "docker not running")
    r = run(["docker", "info", "--format", "{{.MemTotal}}"], check=False)
    try:
        gib = int(r.stdout.strip()) / 2**30
    except ValueError:
        return Check("docker-memory", "FAIL", "docker not running")
    return Check(
        "docker-memory",
        "OK" if gib >= 11.5 else "FAIL",
        f"{gib:.1f} GiB (need ≥ 11.5; native Docker Engine sees the WSL VM memory set by .wslconfig)",
    )


def cluster_memory_check() -> Check:
    if shutil.which("kubectl") is None:
        return Check("memory_requests_total", "WARN", "cluster k3d-rootline not reachable")
    r = run(["kubectl", "--context", "k3d-rootline", "get", "pods", "-A", "-o", "json"], check=False)
    if r.returncode != 0:
        return Check("memory_requests_total", "WARN", "cluster k3d-rootline not reachable")
    gib = memory_requests_gib(json.loads(r.stdout))
    print(f"memory_requests_total={gib} GiB")
    return Check(
        "memory_requests_total",
        "OK" if gib <= MEMORY_CAP_GIB else "FAIL",
        f"{gib} GiB (cap {MEMORY_CAP_GIB})",
    )


def wsl_checks(proc_version: str, repo: Path, env: dict[str, str]) -> list[Check]:
    """GEN-040/041 (PG-17): run inside WSL 2, repo on the WSL filesystem, systemd Docker."""
    out = [
        Check(
            "wsl",
            "OK" if "microsoft" in proc_version.lower() and env.get("WSL_DISTRO_NAME") else "FAIL",
            env.get("WSL_DISTRO_NAME", "not running inside WSL"),
        )
    ]
    on_windows_fs = str(repo).startswith("/mnt/")
    location = "WSL filesystem"
    if on_windows_fs:
        location = "Windows filesystem: move to /home/arkhash0309/projects"
    out.append(Check("repo-location", "FAIL" if on_windows_fs else "OK", f"{repo} ({location})"))
    cpus = os.cpu_count() or 0
    out.append(Check("wsl-cpus", "OK" if cpus >= 16 else "WARN", f"{cpus} (.wslconfig processors=16)"))
    return out


def main() -> int:
    week = current_week((REPO / "wiki/status.md").read_text(encoding="utf-8"))
    local = dotenv_values(REPO / ".env.local") if (REPO / ".env.local").exists() else {}
    checks = (
        wsl_checks(Path("/proc/version").read_text(encoding="utf-8"), REPO, dict(os.environ))
        + tool_checks()
        + [docker_memory_check()]
    )
    checks += env_key_checks((REPO / ".env.example").read_text(encoding="utf-8"), dict(local), week)
    checks.append(cluster_memory_check())
    for c in checks:
        print(c.line())
    return 1 if any(c.status == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
