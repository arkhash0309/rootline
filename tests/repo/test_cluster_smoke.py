"""Verifies PG-16 (overview §7.7 gate check G12, `tests/smoke/<component>.yaml` format), ARC-030 (memory)."""

import http.server
import json
import os
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

from scripts import cluster_smoke as cs
from scripts.integration_gate import CmdResult

SMOKE_API = """component: api
checks:
  - {name: readyz, kind: http, namespace: rootline, service: api, port: 80, path: /readyz, expect_status: 200}
  - name: db-ping
    kind: exec
    namespace: rootline
    pod_selector: "app.kubernetes.io/name=api"
    container: api
    command: [python, -c, "print(1)"]
    expect_exit: 0
  - {name: workload-synced, kind: argocd_app, app: workload, expect: Synced/Healthy}
"""


class FakeBackend:
    """Replaces kubectl, port-forward, HTTP and the clock."""

    def __init__(self, responses: dict[str, CmdResult] | None = None, status: int = 200) -> None:
        self.responses = responses or {}
        self.commands: list[list[str]] = []
        self.forwards: list[list[str]] = []
        self.requests: list[tuple[int, str]] = []
        self.status = status
        self.now = 0.0
        self.sleeps: list[float] = []

    def run(self, cmd: list[str], timeout: int = 120) -> CmdResult:
        self.commands.append(cmd)
        for needle, result in self.responses.items():
            if needle in " ".join(cmd):
                return result
        return CmdResult(0, "")

    @contextmanager
    def port_forward(self, cmd: list[str]) -> Iterator[None]:
        self.forwards.append(cmd)
        yield

    def free_port(self) -> int:
        return 45678

    def http_get(self, port: int, path: str, timeout: float = 10.0) -> int:
        self.requests.append((port, path))
        return self.status

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def write_smoke(tmp_path: Path, name: str, text: str) -> Path:
    directory = tmp_path / "smoke"
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")
    return directory


def test_smoke_file_parses_and_validates(tmp_path: Path) -> None:
    directory = write_smoke(tmp_path, "api.yaml", SMOKE_API)
    files = cs.load_smoke_files(directory)
    assert [f.component for f in files] == ["api"]
    assert [c["kind"] for c in files[0].checks] == ["http", "exec", "argocd_app"]


HTTP_OK = {
    "name": "x", "kind": "http", "namespace": "rootline", "service": "api", "port": 80,
    "path": "/readyz", "expect_status": 200,
}  # fmt: skip
EXEC_OK = {
    "name": "x", "kind": "exec", "namespace": "rootline", "pod_selector": "app=api", "container": "api",
    "command": ["true"], "expect_exit": 0,
}  # fmt: skip
ARGO_OK = {"name": "x", "kind": "argocd_app", "app": "workload", "expect": "Synced/Healthy"}


def smoke_text(component: object, checks: object) -> str:
    document = {"checks": checks} if component is None else {"component": component, "checks": checks}
    return yaml.safe_dump(document)


@pytest.mark.parametrize(
    "text",
    [
        smoke_text("api", [HTTP_OK, EXEC_OK, ARGO_OK]) + "extra: 1\n",
        smoke_text("api", []),
        smoke_text("api", [{"name": "x", "kind": "ping"}]),
        smoke_text("api", [{**HTTP_OK, "path": "readyz"}]),
        smoke_text("api", [{k: v for k, v in HTTP_OK.items() if k != "expect_status"}]),
        smoke_text("api", [{**HTTP_OK, "port": 0}]),
        smoke_text("api", [{**ARGO_OK, "expect": "Synced"}]),
        smoke_text("api", [{**EXEC_OK, "command": []}]),
        smoke_text("api", [{**EXEC_OK, "unknown": 1}]),
        smoke_text(None, [ARGO_OK]),
        smoke_text("Api", [ARGO_OK]),
    ],
)
def test_invalid_smoke_file_is_rejected_by_the_schema(tmp_path: Path, text: str) -> None:
    directory = write_smoke(tmp_path, "api.yaml", text)
    with pytest.raises(cs.SmokeError) as excinfo:
        cs.load_smoke_files(directory)
    assert "api.yaml" in str(excinfo.value)


def test_file_name_must_equal_the_component(tmp_path: Path) -> None:
    directory = write_smoke(tmp_path, "other.yaml", SMOKE_API)
    with pytest.raises(cs.SmokeError, match=r"other\.yaml: file name must be api\.yaml"):
        cs.load_smoke_files(directory)


def test_duplicate_check_names_in_one_file_are_rejected(tmp_path: Path) -> None:
    text = smoke_text("api", [HTTP_OK, {**EXEC_OK, "name": HTTP_OK["name"]}])
    directory = write_smoke(tmp_path, "api.yaml", text)
    with pytest.raises(cs.SmokeError, match=r"api\.yaml: duplicate check name: " + str(HTTP_OK["name"])):
        cs.load_smoke_files(directory)


def test_http_check_builds_the_port_forward_and_requests_the_forwarded_port(tmp_path: Path) -> None:
    check = cs.load_smoke_files(write_smoke(tmp_path, "api.yaml", SMOKE_API))[0].checks[0]
    backend = FakeBackend(status=200)
    outcome = cs.run_check("api", check, backend, "k3d-rootline")
    assert backend.forwards == [
        ["kubectl", "--context", "k3d-rootline", "-n", "rootline", "port-forward", "svc/api", "45678:80"]
    ]
    assert backend.requests == [(45678, "/readyz")]
    assert outcome.line() == "PASS api/readyz: HTTP 200"


def test_http_check_fails_on_a_different_status_and_accepts_a_redirect_status(tmp_path: Path) -> None:
    check = cs.load_smoke_files(write_smoke(tmp_path, "api.yaml", SMOKE_API))[0].checks[0]
    assert (
        cs.run_check("api", check, FakeBackend(status=503), "c").line()
        == "FAIL api/readyz: expected HTTP 200, got 503"
    )
    redirect = {**check, "expect_status": 302}
    assert cs.run_check("api", redirect, FakeBackend(status=302), "c").status == "PASS"


def test_http_get_never_follows_redirects() -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(302)
            self.send_header("Location", "/elsewhere")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert cs.http_get(server.server_address[1], "/start", timeout=5.0) == 302
    finally:
        server.shutdown()
        server.server_close()


def test_exec_check_resolves_the_pod_and_runs_the_command(tmp_path: Path) -> None:
    check = cs.load_smoke_files(write_smoke(tmp_path, "api.yaml", SMOKE_API))[0].checks[1]
    backend = FakeBackend({"get pods": CmdResult(0, "api-7d9f-abcde")})
    outcome = cs.run_check("api", check, backend, "k3d-rootline")
    assert backend.commands == [
        [
            "kubectl",
            "--context",
            "k3d-rootline",
            "-n",
            "rootline",
            "get",
            "pods",
            "-l",
            "app.kubernetes.io/name=api",
            "-o",
            "jsonpath={.items[0].metadata.name}",
        ],
        [
            "kubectl",
            "--context",
            "k3d-rootline",
            "-n",
            "rootline",
            "exec",
            "api-7d9f-abcde",
            "-c",
            "api",
            "--",
            "python",
            "-c",
            "print(1)",
        ],
    ]
    assert outcome.line() == "PASS api/db-ping: exit 0"


def test_exec_check_fails_when_no_pod_matches_or_the_exit_code_differs(tmp_path: Path) -> None:
    check = cs.load_smoke_files(write_smoke(tmp_path, "api.yaml", SMOKE_API))[0].checks[1]
    no_pod = cs.run_check("api", check, FakeBackend({"get pods": CmdResult(0, "")}), "c")
    assert no_pod.line() == "FAIL api/db-ping: no pod matches app.kubernetes.io/name=api in rootline"
    bad_exit = cs.run_check(
        "api", check, FakeBackend({"get pods": CmdResult(0, "p1"), "exec": CmdResult(3, "")}), "c"
    )
    assert bad_exit.line() == "FAIL api/db-ping: expected exit 0, got 3"


def test_argocd_app_check_reads_sync_and_health_status(tmp_path: Path) -> None:
    check = cs.load_smoke_files(write_smoke(tmp_path, "api.yaml", SMOKE_API))[0].checks[2]
    backend = FakeBackend({"get application": CmdResult(0, "Synced/Healthy")})
    outcome = cs.run_check("api", check, backend, "k3d-rootline")
    assert backend.commands == [
        [
            "kubectl",
            "--context",
            "k3d-rootline",
            "-n",
            "argocd",
            "get",
            "application",
            "workload",
            "-o",
            "jsonpath={.status.sync.status}/{.status.health.status}",
        ]
    ]
    assert outcome.line() == "PASS api/workload-synced: Synced/Healthy"
    degraded = cs.run_check(
        "api", check, FakeBackend({"get application": CmdResult(0, "OutOfSync/Degraded")}), "c"
    )
    assert degraded.line() == "FAIL api/workload-synced: expected Synced/Healthy, got OutOfSync/Degraded"


def apps(*pairs: tuple[str, str, str]) -> CmdResult:
    items = [
        {"metadata": {"name": n}, "status": {"sync": {"status": s}, "health": {"status": h}}}
        for n, s, h in pairs
    ]
    return CmdResult(0, json.dumps({"items": items}))


def test_wait_for_argocd_polls_every_15_seconds_until_all_apps_are_ready() -> None:
    class Flaky(FakeBackend):
        def run(self, cmd: list[str], timeout: int = 120) -> CmdResult:
            super().run(cmd, timeout)
            ready = len(self.commands) >= 3
            return apps(
                ("root", "Synced", "Healthy"), ("loki", "Synced" if ready else "OutOfSync", "Healthy")
            )

    backend = Flaky()
    outcome = cs.wait_for_argocd(backend, "k3d-rootline", timeout_s=1200)
    assert outcome.line() == "PASS argocd/apps: 2 applications Synced/Healthy"
    assert backend.sleeps == [15, 15]
    assert backend.commands[0] == [
        "kubectl",
        "--context",
        "k3d-rootline",
        "-n",
        "argocd",
        "get",
        "applications.argoproj.io",
        "-o",
        "json",
    ]


def test_wait_for_argocd_fails_after_the_timeout_and_names_the_apps() -> None:
    backend = FakeBackend(
        {
            "applications.argoproj.io": apps(
                ("root", "Synced", "Healthy"), ("loki", "OutOfSync", "Progressing")
            )
        }
    )
    outcome = cs.wait_for_argocd(backend, "c", timeout_s=45)
    assert outcome.status == "FAIL"
    assert outcome.line() == "FAIL argocd/apps: not Synced/Healthy after 45 s: loki (OutOfSync/Progressing)"
    assert sum(backend.sleeps) <= 45


def test_wait_for_argocd_fails_when_no_application_exists() -> None:
    outcome = cs.wait_for_argocd(FakeBackend({"applications.argoproj.io": apps()}), "c", timeout_s=30)
    assert outcome.line() == "FAIL argocd/apps: not Synced/Healthy after 30 s: no Application found"


def test_wait_for_argocd_treats_non_json_output_as_a_pending_poll() -> None:
    class Garbled(FakeBackend):
        def run(self, cmd: list[str], timeout: int = 120) -> CmdResult:
            super().run(cmd, timeout)
            if len(self.commands) < 3:
                return CmdResult(0, "error: <html>proxy</html>")
            return apps(("root", "Synced", "Healthy"))

    backend = Garbled()
    assert cs.wait_for_argocd(backend, "c", timeout_s=1200).line() == (
        "PASS argocd/apps: 1 applications Synced/Healthy"
    )
    assert backend.sleeps == [15, 15]
    always = FakeBackend({"applications.argoproj.io": CmdResult(0, "not json")})
    outcome = cs.wait_for_argocd(always, "c", timeout_s=30)
    assert outcome.status == "FAIL"
    assert "kubectl output is not a JSON object" in outcome.detail


class SilentProcess:
    """A `kubectl port-forward` stand-in whose stdout is an open pipe that never receives a byte."""

    def __init__(self, text: str = "") -> None:
        read_fd, self.write_fd = os.pipe()
        self.stdout = os.fdopen(read_fd, "r")
        if text:
            os.write(self.write_fd, text.encode())
        self.terminated = False

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self.terminated = True
        os.close(self.write_fd)

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        self.terminate()


HTTP_CHECK = {"name": "readyz", "kind": "http", "namespace": "n", "service": "s", "port": 80, "path": "/"}


def test_port_forward_that_prints_nothing_times_out_and_fails_the_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PG-16: the 30 s readiness deadline holds even when kubectl prints nothing (shortened to 0.3 s)."""
    process = SilentProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(cs, "PORT_FORWARD_READY_TIMEOUT_S", 0.3)
    started = time.monotonic()
    outcome = cs.run_check("api", {**HTTP_CHECK, "expect_status": 200}, cs.RealBackend(), "c")
    assert time.monotonic() - started < 5
    assert outcome.status == "FAIL"
    assert outcome.detail.startswith("request failed: port-forward not ready after 0 s")
    assert process.terminated


def test_wait_for_forwarding_returns_true_on_the_forwarding_line() -> None:
    process = SilentProcess("Handling x\nForwarding from 127.0.0.1:45678 -> 80\n")
    try:
        assert cs.wait_for_forwarding(process.stdout, 5.0) is True
    finally:
        process.terminate()


def test_wait_for_forwarding_returns_false_when_the_process_exits() -> None:
    process = SilentProcess("error: unable to listen\n")
    process.terminate()
    assert cs.wait_for_forwarding(process.stdout, 5.0) is False


def pods_json(*memory: str) -> CmdResult:
    containers = [{"resources": {"requests": {"memory": m}}} for m in memory]
    return CmdResult(
        0, json.dumps({"items": [{"status": {"phase": "Running"}, "spec": {"containers": containers}}]})
    )


def test_memory_check_is_skipped_when_doctor_is_missing() -> None:
    outcome = cs.memory_outcome(FakeBackend(), "c", doctor_module=None)
    assert outcome.line() == "SKIP cluster/memory-requests: scripts/doctor.py missing"


def test_memory_check_compares_against_9_5_gib() -> None:
    class Doctor:
        @staticmethod
        def memory_requests_gib(pods: dict[str, object]) -> float:
            return 9.0 if len(pods["items"]) == 1 else 0.0  # type: ignore[arg-type]

    ok = cs.memory_outcome(FakeBackend({"get pods": pods_json("1Gi")}), "c", doctor_module=Doctor)
    assert ok.line() == "PASS cluster/memory-requests: 9.00 GiB <= 9.5 GiB"

    class Big:
        @staticmethod
        def memory_requests_gib(pods: dict[str, object]) -> float:
            return 9.6

    bad = cs.memory_outcome(FakeBackend({"get pods": pods_json("1Gi")}), "c", doctor_module=Big)
    assert bad.line() == "FAIL cluster/memory-requests: 9.60 GiB > 9.5 GiB"


def test_main_prints_one_line_per_check_and_exits_1_on_any_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = write_smoke(tmp_path, "api.yaml", SMOKE_API)
    backend = FakeBackend(
        {
            "applications.argoproj.io": apps(("root", "Synced", "Healthy")),
            "get application workload": CmdResult(0, "Synced/Healthy"),
            "get pods -l": CmdResult(0, "p1"),
            "get pods -A": pods_json("1Gi"),
        },
        status=500,
    )
    code = cs.main(["--timeout", "30"], backend=backend, smoke_dir=directory, doctor_module=None)
    lines = capsys.readouterr().out.splitlines()
    assert code == 1
    assert lines == [
        "PASS argocd/apps: 1 applications Synced/Healthy",
        "SKIP cluster/memory-requests: scripts/doctor.py missing",
        "FAIL api/readyz: expected HTTP 200, got 500",
        "PASS api/db-ping: exit 0",
        "PASS api/workload-synced: Synced/Healthy",
    ]


def test_main_exits_1_on_an_invalid_smoke_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    directory = write_smoke(tmp_path, "api.yaml", "component: api\nchecks: []\n")
    backend = FakeBackend({"applications.argoproj.io": apps(("root", "Synced", "Healthy"))})
    assert cs.main(["--timeout", "30"], backend=backend, smoke_dir=directory, doctor_module=None) == 1
    assert "FAIL smoke/api.yaml:" in capsys.readouterr().out
