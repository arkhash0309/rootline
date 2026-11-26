"""Cluster smoke test: gate check G12 of overview §7.7. PG-16.

Usage:
  uv run python scripts/cluster_smoke.py [--context k3d-rootline] [--timeout 1200]

Steps, in order:
  1. Wait until every ArgoCD `Application` in namespace `argocd` is `Synced` and `Healthy`
     (poll every 15 s, give up after `--timeout` seconds; at least one Application must exist).
  2. Memory check: `scripts/doctor.py` function `memory_requests_gib(pods_json)` over
     `kubectl get pods -A -o json` must be <= 9.5 GiB. Reported `SKIP` when `scripts/doctor.py` does
     not exist yet (it is created by W1-T06).
  3. Every check of every `tests/smoke/<component>.yaml`, validated against `tests/smoke/schema.json`.
     `http` checks run `kubectl port-forward svc/<service> <free local port>:<port>`, send
     `GET http://127.0.0.1:<local><path>` and never follow redirects, so `expect_status` may be a 3xx
     code. `exec` checks resolve the first pod of `pod_selector` and run `kubectl exec`. `argocd_app`
     checks read `.status.sync.status/.status.health.status` of the Application.

Output: one line per check, `PASS|FAIL|SKIP <component>/<name>: <detail>`.
Exit codes: 0 no FAIL; 1 at least one FAIL (including an invalid smoke file or a timeout in step 1).
"""

from __future__ import annotations

import argparse
import http.client
import importlib
import json
import queue
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import jsonschema
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.integration_gate import CmdResult
from scripts.proc import run
from scripts.swarm_lib import REPO

SMOKE_DIR = REPO / "tests/smoke"
SCHEMA_PATH = SMOKE_DIR / "schema.json"
DEFAULT_CONTEXT = "k3d-rootline"
DEFAULT_TIMEOUT_S = 1200
POLL_S = 15
MEMORY_LIMIT_GIB = 9.5
PORT_FORWARD_READY_TIMEOUT_S = 30.0
HTTP_TIMEOUT_S = 10.0


class SmokeError(ValueError):
    """A smoke file is not valid YAML, violates `tests/smoke/schema.json`, or is misnamed."""


@dataclass
class SmokeFile:
    component: str
    checks: list[dict[str, Any]]
    path: Path


@dataclass
class Outcome:
    status: str
    component: str
    name: str
    detail: str

    def line(self) -> str:
        return f"{self.status} {self.component}/{self.name}: {self.detail}"


class Backend(Protocol):
    def run(self, cmd: list[str], timeout: int = 120) -> CmdResult: ...

    def port_forward(self, cmd: list[str]) -> Any: ...

    def free_port(self) -> int: ...

    def http_get(self, port: int, path: str, timeout: float = HTTP_TIMEOUT_S) -> int: ...

    def monotonic(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...


def http_get(port: int, path: str, timeout: float = HTTP_TIMEOUT_S) -> int:
    """GET `http://127.0.0.1:<port><path>` and return the status code; redirects are not followed."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        connection.request("GET", path)
        return connection.getresponse().status
    finally:
        connection.close()


def wait_for_forwarding(stdout: Any, timeout_s: float) -> bool:
    """True when a line containing `Forwarding from` is read from `stdout` within `timeout_s` seconds.

    A reader thread calls the blocking `readline`, so the deadline holds even when the process prints
    nothing. False on timeout or end of output (the process exited). After the first `Forwarding from`
    line the thread keeps draining the pipe and discards the lines, so `kubectl` never blocks on a full pipe.
    """
    lines: queue.Queue[str] = queue.Queue()
    ready = threading.Event()

    def pump() -> None:
        for line in iter(stdout.readline, ""):
            if not ready.is_set():
                lines.put(line)
        lines.put("")

    threading.Thread(target=pump, daemon=True).start()
    deadline = time.monotonic() + timeout_s
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            line = lines.get(timeout=remaining)
        except queue.Empty:
            return False
        if "Forwarding from" in line:
            ready.set()
            return True
        if line == "":
            return False


class RealBackend:
    """kubectl through `scripts.proc.run`, real sockets, real clock."""

    def run(self, cmd: list[str], timeout: int = 120) -> CmdResult:
        try:
            done = run(cmd, check=False, timeout=timeout)
        except subprocess.TimeoutExpired:
            return CmdResult(124, "", f"timeout after {timeout} s: {' '.join(cmd)}\n")
        except FileNotFoundError as error:
            return CmdResult(127, "", f"{error}\n")
        return CmdResult(done.returncode, done.stdout or "", done.stderr or "")

    @contextmanager
    def port_forward(self, cmd: list[str]) -> Iterator[None]:
        # S603: `cmd` is the kubectl argument list built by build_port_forward_cmd, no shell is involved.
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)  # noqa: S603
        try:
            ready = process.stdout is not None and wait_for_forwarding(
                process.stdout, PORT_FORWARD_READY_TIMEOUT_S
            )
            if not ready:
                raise RuntimeError(
                    f"port-forward not ready after {PORT_FORWARD_READY_TIMEOUT_S:.0f} s: {cmd}"
                )
            yield
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    def free_port(self) -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def http_get(self, port: int, path: str, timeout: float = HTTP_TIMEOUT_S) -> int:
        return http_get(port, path, timeout)

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


# ---- kubectl command builders ---------------------------------------------------------------------


def kubectl(context: str, namespace: str | None, *args: str) -> list[str]:
    base = ["kubectl", "--context", context]
    return base + (["-n", namespace] if namespace else []) + list(args)


def build_port_forward_cmd(
    context: str, namespace: str, service: str, local_port: int, port: int
) -> list[str]:
    return kubectl(context, namespace, "port-forward", f"svc/{service}", f"{local_port}:{port}")


def build_pod_lookup_cmd(context: str, namespace: str, selector: str) -> list[str]:
    return kubectl(
        context, namespace, "get", "pods", "-l", selector, "-o", "jsonpath={.items[0].metadata.name}"
    )


def build_exec_cmd(context: str, namespace: str, pod: str, container: str, command: list[str]) -> list[str]:
    return kubectl(context, namespace, "exec", pod, "-c", container, "--", *command)


def build_argocd_app_cmd(context: str, app: str) -> list[str]:
    return kubectl(
        context,
        "argocd",
        "get",
        "application",
        app,
        "-o",
        "jsonpath={.status.sync.status}/{.status.health.status}",
    )


# ---- smoke files ----------------------------------------------------------------------------------


def load_smoke_files(directory: Path = SMOKE_DIR, schema_path: Path = SCHEMA_PATH) -> list[SmokeFile]:
    """Load `<directory>/*.yaml` in name order and validate each against `schema_path`.

    Raises SmokeError on the first invalid file (invalid YAML, schema violation, a file name different from
    `<component>.yaml`, or a check `name` used twice in one file).
    """
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    files: list[SmokeFile] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise SmokeError(f"{path.name}: invalid YAML: {error}") from error
        errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
        if errors:
            location = "/".join(str(p) for p in errors[0].absolute_path) or "(root)"
            raise SmokeError(f"{path.name}: {location}: {errors[0].message}")
        if path.name != f"{document['component']}.yaml":
            raise SmokeError(f"{path.name}: file name must be {document['component']}.yaml")
        names = [check["name"] for check in document["checks"]]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise SmokeError(f"{path.name}: duplicate check name: {', '.join(duplicates)}")
        files.append(SmokeFile(component=document["component"], checks=document["checks"], path=path))
    return files


# ---- checks ---------------------------------------------------------------------------------------


def run_check(component: str, check: dict[str, Any], backend: Backend, context: str) -> Outcome:
    name, kind = check["name"], check["kind"]
    if kind == "http":
        local = backend.free_port()
        cmd = build_port_forward_cmd(context, check["namespace"], check["service"], local, check["port"])
        try:
            with backend.port_forward(cmd):
                status = backend.http_get(local, check["path"])
        except (OSError, RuntimeError) as error:
            return Outcome("FAIL", component, name, f"request failed: {error}")
        if status == check["expect_status"]:
            return Outcome("PASS", component, name, f"HTTP {status}")
        return Outcome("FAIL", component, name, f"expected HTTP {check['expect_status']}, got {status}")
    if kind == "exec":
        namespace, selector = check["namespace"], check["pod_selector"]
        pod = backend.run(build_pod_lookup_cmd(context, namespace, selector)).stdout.strip()
        if not pod:
            return Outcome("FAIL", component, name, f"no pod matches {selector} in {namespace}")
        result = backend.run(build_exec_cmd(context, namespace, pod, check["container"], check["command"]))
        if result.returncode == check["expect_exit"]:
            return Outcome("PASS", component, name, f"exit {result.returncode}")
        return Outcome(
            "FAIL", component, name, f"expected exit {check['expect_exit']}, got {result.returncode}"
        )
    result = backend.run(build_argocd_app_cmd(context, check["app"]))
    seen = result.stdout.strip()
    if result.returncode == 0 and seen == check["expect"]:
        return Outcome("PASS", component, name, seen)
    detail = seen if result.returncode == 0 else f"kubectl exit {result.returncode}"
    return Outcome("FAIL", component, name, f"expected {check['expect']}, got {detail}")


def wait_for_argocd(backend: Backend, context: str, timeout_s: int, poll_s: int = POLL_S) -> Outcome:
    """Poll every `poll_s` seconds until every Application is Synced/Healthy or `timeout_s` has passed."""
    cmd = kubectl(context, "argocd", "get", "applications.argoproj.io", "-o", "json")
    deadline = backend.monotonic() + timeout_s
    while True:
        result = backend.run(cmd)
        pending: list[str] = []
        total = 0
        if result.returncode != 0:
            pending = [f"kubectl exit {result.returncode}"]
        else:
            try:
                document = json.loads(result.stdout)
            except json.JSONDecodeError:
                document = None
            if not isinstance(document, dict):
                pending = ["kubectl output is not a JSON object"]
            else:
                items = document.get("items", [])
                total = len(items)
                for item in items:
                    sync = item.get("status", {}).get("sync", {}).get("status", "Unknown")
                    health = item.get("status", {}).get("health", {}).get("status", "Unknown")
                    if (sync, health) != ("Synced", "Healthy"):
                        pending.append(f"{item['metadata']['name']} ({sync}/{health})")
                if total == 0:
                    pending = ["no Application found"]
        if not pending:
            return Outcome("PASS", "argocd", "apps", f"{total} applications Synced/Healthy")
        if backend.monotonic() + poll_s > deadline:
            return Outcome(
                "FAIL", "argocd", "apps", f"not Synced/Healthy after {timeout_s} s: {', '.join(pending)}"
            )
        backend.sleep(poll_s)


def memory_outcome(backend: Backend, context: str, doctor_module: Any = ...) -> Outcome:
    """`doctor_module` defaults to importing `scripts.doctor`; pass None to force the SKIP outcome."""
    name = "memory-requests"
    if doctor_module is ...:
        try:
            doctor_module = importlib.import_module("scripts.doctor")
        except ModuleNotFoundError:
            doctor_module = None
    if doctor_module is None:
        return Outcome("SKIP", "cluster", name, "scripts/doctor.py missing")
    result = backend.run(kubectl(context, None, "get", "pods", "-A", "-o", "json"))
    if result.returncode != 0:
        return Outcome("FAIL", "cluster", name, f"kubectl get pods exit {result.returncode}")
    gib = float(doctor_module.memory_requests_gib(json.loads(result.stdout)))
    if gib <= MEMORY_LIMIT_GIB:
        return Outcome("PASS", "cluster", name, f"{gib:.2f} GiB <= {MEMORY_LIMIT_GIB} GiB")
    return Outcome("FAIL", "cluster", name, f"{gib:.2f} GiB > {MEMORY_LIMIT_GIB} GiB")


def main(
    argv: Sequence[str] | None = None,
    *,
    backend: Backend | None = None,
    smoke_dir: Path | None = None,
    doctor_module: Any = ...,
) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--context", default=DEFAULT_CONTEXT)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    args = parser.parse_args(argv)
    be: Backend = backend or RealBackend()
    outcomes = [
        wait_for_argocd(be, args.context, args.timeout),
        memory_outcome(be, args.context, doctor_module),
    ]
    try:
        for smoke in load_smoke_files(smoke_dir or SMOKE_DIR):
            outcomes.extend(run_check(smoke.component, check, be, args.context) for check in smoke.checks)
    except SmokeError as error:
        file_name, _, detail = str(error).partition(": ")
        outcomes.append(Outcome("FAIL", "smoke", file_name, detail))
    for outcome in outcomes:
        print(outcome.line())
    return 1 if any(o.status == "FAIL" for o in outcomes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
