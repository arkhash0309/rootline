# Workstation setup

Requirement IDs: GEN-040, GEN-041, GEN-050, PG-17 (ADR 0036), PG-13 (ADR 0032), O-8 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §2).
Source: `docs/superpowers/specs/2026-11-25-rootline-design.md` §4.5.
Last verified: not re-run. The commands follow the install methods recorded in GEN-040 for 2026-11-26; this page was written on 2026-11-27 from that table and has not been executed again.

This runbook installs everything the project needs on the owner workstation: a Windows 11 PC (15.6 GB RAM, 20 logical CPUs) on which all development runs inside WSL 2. Run every command in a WSL `Ubuntu` bash shell unless a heading says Windows. Never use PowerShell, cmd or Git Bash for project commands (GEN-041).

## Windows side

Run these steps once, from a Windows PowerShell window opened by the owner. This is the only place where PowerShell is used, and only for WSL administration.

1. Install WSL 2 with the distribution `Ubuntu` (Ubuntu 26.04 LTS): `wsl --install -d Ubuntu`. Create the Linux user `arkhash0309` when the distribution asks for it.
2. Create the file `%UserProfile%\.wslconfig` with exactly this content (GEN-040; 16 of the 20 logical CPUs go to WSL, 4 stay with Windows):

   ```ini
   [wsl2]
   memory=12GB
   processors=16
   swap=8GB
   localhostForwarding=true
   ```

3. Apply it by running `wsl --shutdown` once, then start `Ubuntu` again.
4. Install a web browser, Edge or Chrome, with Windows Hello enabled for passkeys. The browser opens the console, Keycloak and ArgoCD at `https://*.127.0.0.1.sslip.io` through WSL localhost forwarding.

Windows runs nothing else for the project. From WSL, a URL is opened in the Windows browser with `/mnt/c/Windows/explorer.exe "<url>"`.

## WSL basics

1. Create or replace `/etc/wsl.conf` with exactly this content (`sudo tee /etc/wsl.conf`), then run `wsl --shutdown` from Windows and start `Ubuntu` again:

   ```ini
   [boot]
   systemd=true

   [user]
   default=arkhash0309

   [interop]
   appendWindowsPath=false
   ```

   With `appendWindowsPath=false`, Windows programs are not on the WSL `PATH`. Call them by absolute path. The only Windows programs automation may call are `/mnt/c/Windows/System32/certutil.exe` (`task trust-ca`) and `/mnt/c/Windows/explorer.exe` (GEN-041).
2. Update the system: `sudo apt update && sudo apt upgrade -y`.
3. Install the support packages of GEN-040: `sudo apt install -y unzip jq zstd libnss3-tools build-essential ca-certificates git`. Git must be version 2.45 or newer; check with `git --version`.
4. Put `~/.local/bin` and `fnm` first on `PATH` for interactive and non-interactive shells. Append to both `~/.profile` and `~/.bashrc`:

   ```bash
   export PATH="$HOME/.local/bin:$HOME/.local/share/fnm:$PATH"
   if command -v fnm >/dev/null 2>&1; then eval "$(fnm env --shell bash)"; fi
   ```

5. Create the directories used below: `mkdir -p ~/.local/bin ~/.local/opt ~/projects`.

## Tools

Versions marked "from `versions.yaml`" are the values of the keys of the same name in `versions.yaml` (GEN-050, resolved by W1-T02). Set the shell variable named in the command to that value before running it. All user-level binaries go to `~/.local/bin`.

### Root part: script `~/rootline-root-setup.sh`

The commands that need `sudo` are collected in the script `~/rootline-root-setup.sh` in the home directory (not in the repository). The script contains exactly:

```bash
#!/usr/bin/env bash
set -euo pipefail
apt-get update
apt-get install -y docker.io containerd docker-buildx docker-compose-v2
systemctl enable --now docker
usermod -aG docker arkhash0309
# Windows programs are not on the PATH (GEN-040)
if ! grep -q '^\[interop\]' /etc/wsl.conf; then
  printf '\n[interop]\nappendWindowsPath=false\n' >> /etc/wsl.conf
fi
# Ollama: install, then keep the service disabled (started only for pilots)
curl -fsSL https://ollama.com/install.sh | sh
systemctl disable --now ollama
```

Run it with `sudo bash ~/rootline-root-setup.sh`, then log out of the WSL shell and back in so that the group `docker` applies. Verify with `docker run --rm hello-world`.

### Docker Engine

Installed by the root script: Ubuntu packages `docker.io`, `containerd`, `docker-buildx`, `docker-compose-v2`; systemd service `docker` enabled; user `arkhash0309` in group `docker`. Docker Desktop is not used.

### Ollama

Installed by the root script with the Linux installer (systemd service `ollama`, CPU-only). The service is disabled by default; start it only for pilots with `sudo systemctl start ollama` and stop it afterwards with `sudo systemctl stop ollama`. Ollama is not in the cluster (spec §9.5.4).

### k3d

```bash
K3D_VERSION=<value of key k3d in versions.yaml, written with a leading v>
curl -fsSL -o ~/.local/bin/k3d "https://github.com/k3d-io/k3d/releases/download/${K3D_VERSION}/k3d-linux-amd64"
chmod +x ~/.local/bin/k3d
```

### kubectl

```bash
KUBECTL_VERSION=<value of key kubectl in versions.yaml, written with a leading v>
curl -fsSL -o ~/.local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
chmod +x ~/.local/bin/kubectl
```

The kubectl minor version must match the cluster minor version plus or minus 1. W1-T02 re-pins it once the `k3s` minor is resolved.

### Helm

```bash
HELM_VERSION=<value of key helm in versions.yaml, written with a leading v>
curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" | tar -xz -C /tmp linux-amd64/helm
install -m 0755 /tmp/linux-amd64/helm ~/.local/bin/helm
```

### go-task

```bash
TASK_VERSION=<value of key go-task in versions.yaml, without a leading v>
curl -fsSL "https://github.com/go-task/task/releases/download/v${TASK_VERSION}/task_linux_amd64.tar.gz" | tar -xz -C ~/.local/bin task
```

### uv and Python 3.12

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
```

The installer places `uv` in `~/.local/bin`. The system Python 3.14 is not used.

### Node.js 24 with fnm

```bash
curl -fsSL https://fnm.vercel.app/install | bash -s -- --install-dir ~/.local/share/fnm --skip-shell
fnm install 24
fnm default 24
```

### Playwright browsers

Installed in week 6 for the end-to-end and accessibility tests: `npx playwright install --with-deps chromium`.

### Terraform

```bash
TERRAFORM_VERSION=<value of key terraform in versions.yaml, without a leading v>
curl -fsSL -o /tmp/terraform.zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
unzip -o /tmp/terraform.zip terraform -d ~/.local/bin
```

### gcloud CLI

```bash
curl -fsSL -o /tmp/gcloud.tar.gz https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xzf /tmp/gcloud.tar.gz -C ~/.local/opt
~/.local/opt/google-cloud-sdk/install.sh --quiet --path-update false --command-completion false
ln -sf ~/.local/opt/google-cloud-sdk/bin/gcloud ~/.local/bin/gcloud
~/.local/opt/google-cloud-sdk/bin/gcloud components install gke-gcloud-auth-plugin --quiet
ln -sf ~/.local/opt/google-cloud-sdk/bin/gke-gcloud-auth-plugin ~/.local/bin/gke-gcloud-auth-plugin
```

### GitHub CLI

```bash
GH_VERSION=<release number shown at https://github.com/cli/cli/releases/latest, without a leading v>
curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" | tar -xz -C /tmp
install -m 0755 "/tmp/gh_${GH_VERSION}_linux_amd64/bin/gh" ~/.local/bin/gh
gh auth login
gh auth setup-git
```

Log in as `arkhash0309` only. Never use any other account configured in `gh`. `gh auth setup-git` makes `gh` the git credential helper.

### OPA CLI

```bash
OPA_VERSION=<value of key opa in versions.yaml, without a leading v>
curl -fsSL -o ~/.local/bin/opa "https://github.com/open-policy-agent/opa/releases/download/v${OPA_VERSION}/opa_linux_amd64_static"
chmod +x ~/.local/bin/opa
```

### Claude Code

Install the native Linux build into `~/.local/bin` (`curl -fsSL https://claude.ai/install.sh | bash`). Start every coordinator and agent session from a WSL shell in `/home/arkhash0309/projects/rootline`. The Windows copy of Claude Code, and any other Windows binary under `/mnt/c` (for example `node` or `gh`), is never used from WSL.

## Repositories

Clone both repositories on the WSL filesystem, never under `/mnt/c` (cross-filesystem I/O is several times slower):

```bash
gh repo clone arkhash0309/rootline /home/arkhash0309/projects/rootline
gh repo clone arkhash0309/rootline-env /home/arkhash0309/projects/rootline-env
```

VS Code users open both directories with the Remote - WSL extension. The `rootline-env` repository is created by W1-T08; see [local-up](local-up.md).

## Anthropic

Owner step O-8 (week 4, task W4-T01): buy Anthropic prepaid credits with a total of at most USD 75 and auto-reload off (CST-001), then create the API keys `rootline-dev`, `rootline-cluster` and `rootline-ci` in the Anthropic Console. Key placement (PG-13, ADR 0032):

| Key name in the console | Where it is stored | Variable name |
|---|---|---|
| `rootline-cluster` | `.env.local` (git-ignored) | `ANTHROPIC_API_KEY` (the in-cluster key) |
| `rootline-dev` | `.env.local` (git-ignored) | `ROOTLINE_HOST_ANTHROPIC_API_KEY` (the host key for the eval runner and pilots) |
| `rootline-ci` | GitHub Actions repository secret | `ANTHROPIC_API_KEY_CI` |

Never write a key into Git, Helm values, Terraform variables or the wiki (SEC-101).

## Verify

Run `task doctor` from `/home/arkhash0309/projects/rootline`. It checks every tool above and exits 0 when all checks pass. `task doctor` is created by W1-T06.
