# 0036 — Development in WSL 2 Ubuntu 26.04

Status: accepted
Date: 2026-11-26
Label: spec-gap
Plan gap: PG-17 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5)

## Context

PG-17 (spec reference GEN-040, GEN-041, GEN-060, AGT-053, CST-011, INF-031): Owner instruction (2026-11-26): all development moves from Windows-native shells into WSL 2 to use the CPU cores better.

The owner instruction of 2026-11-26 moves all development into WSL 2.

The spec does not answer these questions, so spec §0.3 applies: the simplest, cheapest and safest option is chosen. Each question is a row of the spec gap log in spec §26.

## Decision

PG-17: WSL 2 Ubuntu 26.04 LTS with systemd and native Docker Engine (no Docker Desktop); repositories at `/home/arkhash0309/projects/{rootline,rootline-env}`; `.wslconfig` `memory=12GB`, `processors=16`, `swap=8GB`, `localhostForwarding=true`; Windows keeps only the browser; `task trust-ca` installs the CA into the WSL system store, the WSL NSS database and the Windows user Root store; Ollama runs in WSL; the LLM ledger is `~/.local/share/rootline/llm-ledger.json`; Taskfile sets `SSL_CERT_FILE` and `NODE_EXTRA_CA_CERTS` so Python and Node in WSL trust the local CA.

## Consequences

- All development, every Claude Code session and every project command runs in WSL 2 Ubuntu 26.04 with the native Docker Engine; the repositories live on the WSL filesystem.
- Windows keeps the browser and `%UserProfile%\.wslconfig`; the local CA is trusted in the WSL system store, the WSL NSS database and the Windows user Root store.

## Alternatives considered

- Windows-native development with PowerShell or Git Bash and Docker Desktop: not chosen because of the owner instruction of 2026-11-26 (WSL 2 uses the CPU cores better).

## Spec references

PG-17, GEN-040, GEN-041, GEN-060, AGT-053, CST-011, INF-031; spec §26 rows PG-17; `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §5.
