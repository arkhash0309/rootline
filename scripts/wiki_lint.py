"""Wiki lint (WIK-020, WIK-021). Usage:
uv run python scripts/wiki_lint.py                          # static checks
uv run python scripts/wiki_lint.py --changed-files f.txt --pr-body body.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.proc import run

REPO = Path(__file__).resolve().parents[1]
COMPONENT_PAGES = [
    "console",
    "api",
    "agent",
    "gate",
    "faultlab",
    "mcp-telemetry",
    "mcp-k8s",
    "mcp-gitops",
    "migrate",
    "demo-seed",
    "postgres",
    "keycloak",
    "keycloak-config",
    "otel-collector",
    "kube-prometheus-stack",
    "loki",
    "tempo",
    "argocd",
    "chaos-mesh",
    "kyverno",
    "external-secrets",
    "cert-manager",
    "traefik",
    "workload",
    "telemetry",
    "capacity",
]
CODE_PREFIXES = ("services/", "libs/", "deploy/", "infra/", "policies/", "eval/")
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
FORBIDDEN = ("TODO", "TBD")
STATUS_RE = re.compile(r"^Last updated: (\d{4}-\d{2}-\d{2})", re.M)


def check_static(wiki: Path, today: date) -> list[str]:
    problems: list[str] = []
    for slug in COMPONENT_PAGES:
        if not (wiki / "components" / f"{slug}.md").is_file():
            problems.append(f"missing-component: {slug}")
    for n in range(1, 26):
        if not list((wiki / "adr").glob(f"{n:04d}-*.md")):
            problems.append(f"missing-adr: {n:04d}")
    index_text = (wiki / "index.md").read_text(encoding="utf-8") if (wiki / "index.md").exists() else ""
    for page in sorted(wiki.rglob("*.md")):
        rel = page.relative_to(wiki).as_posix()
        text = page.read_text(encoding="utf-8")
        for word in FORBIDDEN:
            if re.search(rf"\b{word}\b", text):
                problems.append(f"forbidden-word: {rel}: {word}")
        for target in LINK_RE.findall(text):
            if re.match(r"^[a-z]+:", target):
                continue  # absolute URL
            if not (page.parent / target).resolve().exists():
                problems.append(f"broken-link: {rel} -> {target}")
        if rel != "index.md" and f"({rel})" not in index_text:
            problems.append(f"index-missing: {rel}")
    return problems


def status_is_stale(status_date: date, latest_code_commit: date) -> bool:
    return (latest_code_commit - status_date).days > 7


def check_status(wiki: Path) -> list[str]:
    m = STATUS_RE.search((wiki / "status.md").read_text(encoding="utf-8"))
    if not m:
        return ["status-format: missing 'Last updated: YYYY-MM-DD'"]
    out = run(
        ["git", "-C", str(REPO), "log", "-1", "--format=%cs", "--", *CODE_PREFIXES],
        check=False,
    ).stdout.strip()
    if not out:
        return []
    if status_is_stale(
        datetime.strptime(m.group(1), "%Y-%m-%d").date(),
        datetime.strptime(out, "%Y-%m-%d").date(),
    ):
        return [f"status-stale: status.md {m.group(1)} vs last code commit {out}"]
    return []


def check_changed(changed: list[str], pr_body: str) -> list[str]:
    if re.search(r"^wiki-skip: \S.*$", pr_body, re.M):
        return []
    code = [f for f in changed if f.startswith(CODE_PREFIXES)]
    if code and not any(f.startswith("wiki/") for f in changed):
        return [f"wiki-not-updated: {f}" for f in code]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed-files")
    ap.add_argument("--pr-body")
    args = ap.parse_args()
    wiki = REPO / "wiki"
    problems = check_static(wiki, today=date.today()) + check_status(wiki)
    if args.changed_files:
        changed = Path(args.changed_files).read_text(encoding="utf-8").split()
        body = Path(args.pr_body).read_text(encoding="utf-8") if args.pr_body else ""
        problems += check_changed(changed, body)
    for p in problems:
        print(f"wiki-lint: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
