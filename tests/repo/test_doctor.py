"""Verifies GEN-060 (doctor), SEC-101, S2."""

from pathlib import Path

from scripts import doctor

EXAMPLE = """# week: 1 — a
A=
# week: 4 — b
B=
"""


def test_env_keys_required_by_week() -> None:
    checks = doctor.env_key_checks(EXAMPLE, {"A": "x"}, week=1)
    assert [(c.name, c.status) for c in checks] == [("env:A", "OK"), ("env:B", "WARN")]
    checks = doctor.env_key_checks(EXAMPLE, {"A": "x"}, week=4)
    assert ("env:B", "FAIL") in [(c.name, c.status) for c in checks]


def test_empty_value_counts_as_missing() -> None:
    checks = doctor.env_key_checks(EXAMPLE, {"A": ""}, week=1)
    assert checks[0].status == "FAIL"


def test_memory_requests_sum() -> None:
    pods = {
        "items": [
            {
                "status": {"phase": "Running"},
                "spec": {
                    "containers": [
                        {"resources": {"requests": {"memory": "512Mi"}}},
                        {"resources": {"requests": {"memory": "1Gi"}}},
                    ],
                    "initContainers": [{"resources": {"requests": {"memory": "4Gi"}}}],
                },
            },
            {
                "status": {"phase": "Succeeded"},
                "spec": {"containers": [{"resources": {"requests": {"memory": "8Gi"}}}]},
            },
        ]
    }
    assert doctor.memory_requests_gib(pods) == 1.5  # init containers and finished pods excluded


def test_parse_week_from_status() -> None:
    assert doctor.current_week("## Current milestone: Week 3 — Identity and MCP\n") == 3


def test_check_line_format() -> None:
    assert doctor.Check("git", "OK", "2.47.1").line() == "OK   git: 2.47.1"


def test_wsl_checks() -> None:
    """Verifies GEN-040, GEN-041 (PG-17)."""
    ok = doctor.wsl_checks(
        "Linux version 6.6.114.1-microsoft-standard-WSL2",
        Path("/home/arkhash0309/projects/rootline"),
        {"WSL_DISTRO_NAME": "Ubuntu"},
    )
    assert [(c.name, c.status) for c in ok][:2] == [("wsl", "OK"), ("repo-location", "OK")]
    bad = doctor.wsl_checks("Linux version 6.8.0-generic", Path("/mnt/c/Users/arkha/rootline"), {})
    assert [(c.name, c.status) for c in bad][:2] == [("wsl", "FAIL"), ("repo-location", "FAIL")]
