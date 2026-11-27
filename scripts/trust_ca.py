"""`task trust-ca` (GEN-060, INF-031, PG-17): trust the cluster's local CA in WSL and in Windows.

Usage: uv run python scripts/trust_ca.py [--env local|gke] [--context <ctx>] [--linux-only]

Reads Secret `cert-manager/rootline-local-ca` key `ca.crt` (on `--env gke` this is the in-cluster fallback CA
of INF-041, which uses the same Secret name) and writes it to `data/rootline-ca.crt`. Then:
  1. `sudo install -m 0644 data/rootline-ca.crt /usr/local/share/ca-certificates/rootline-ca.crt` and
     `sudo update-ca-certificates` (prompts for the sudo password in the terminal);
  2. `certutil -d sql:$HOME/.pki/nssdb -A -t C,, -n rootline-local-ca -i data/rootline-ca.crt`, after
     `certutil -d sql:$HOME/.pki/nssdb -N --empty-password` when the database does not exist;
  3. `/mnt/c/Windows/System32/certutil.exe -user -addstore Root <wslpath -w data/rootline-ca.crt>` through WSL
     interop (Windows shows a confirmation dialog). Skipped with `--linux-only` (used by CI).
Each step prints `OK` or `FAIL`.

Exit codes: 0 every step OK; 1 a step failed, the secret could not be read, or the script runs outside WSL
(no `WSL_DISTRO_NAME`) without `--linux-only`.
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
CA_FILE = REPO / "data/rootline-ca.crt"
SYSTEM_CA_PATH = "/usr/local/share/ca-certificates/rootline-ca.crt"
WINDOWS_CERTUTIL = "/mnt/c/Windows/System32/certutil.exe"
NSS_NICKNAME = "rootline-local-ca"


def system_store_commands(ca: Path) -> list[list[str]]:
    return [["sudo", "install", "-m", "0644", str(ca), SYSTEM_CA_PATH], ["sudo", "update-ca-certificates"]]


def nss_commands(ca: Path, db: Path, *, db_exists: bool) -> list[list[str]]:
    url = f"sql:{db}"
    commands = [] if db_exists else [["certutil", "-d", url, "-N", "--empty-password"]]
    commands.append(["certutil", "-d", url, "-A", "-t", "C,,", "-n", NSS_NICKNAME, "-i", str(ca)])
    return commands


def windows_command(windows_path: str) -> list[str]:
    return [WINDOWS_CERTUTIL, "-user", "-addstore", "Root", windows_path]


def _run_all(label: str, commands: list[list[str]]) -> bool:
    for command in commands:
        if run(command, check=False, capture=False).returncode != 0:
            print(f"FAIL {label}: {' '.join(command)}")
            return False
    print(f"OK   {label}")
    return True


def fetch_ca(context: str | None) -> bytes | None:
    cmd = ["kubectl"] + (["--context", context] if context else [])
    cmd += ["-n", "cert-manager", "get", "secret", "rootline-local-ca", "-o", r"jsonpath={.data.ca\.crt}"]
    result = run(cmd, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        print(f"FAIL read secret cert-manager/rootline-local-ca: {result.stderr.strip()}", file=sys.stderr)
        return None
    return base64.b64decode(result.stdout.strip())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--env", choices=["local", "gke"], default="local")
    parser.add_argument("--context", default=None)
    parser.add_argument("--linux-only", action="store_true")
    args = parser.parse_args(argv)
    if not os.environ.get("WSL_DISTRO_NAME") and not args.linux_only:
        print(
            "FAIL not running inside WSL (WSL_DISTRO_NAME unset); pass --linux-only to skip Windows",
            file=sys.stderr,
        )
        return 1
    context = args.context or ("k3d-rootline" if args.env == "local" else None)
    ca = fetch_ca(context)
    if ca is None:
        return 1
    CA_FILE.parent.mkdir(parents=True, exist_ok=True)
    CA_FILE.write_bytes(ca)
    nss_db = Path.home() / ".pki/nssdb"
    results = [
        _run_all("WSL system store", system_store_commands(CA_FILE)),
        _run_all("WSL NSS database", nss_commands(CA_FILE, nss_db, db_exists=(nss_db / "cert9.db").exists())),
    ]
    if not args.linux_only:
        windows_path = run(["wslpath", "-w", str(CA_FILE)], check=False).stdout.strip()
        results.append(_run_all("Windows Root store", [windows_command(windows_path)]))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
