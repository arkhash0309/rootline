# GitHub Apps

Status: the `## Rulesets` section is written (W1-T14, 2026-11-27) and has not been executed: the owner runs it as step O-3. The GitHub Apps sections are not implemented yet; they are planned in W2-T07 and W3-T10.

Purpose: Create and install the GitHub Apps `rootline-faultlab`, `rootline-agent` and `rootline-gate`, and create the branch rulesets of the repository `arkhash0309/rootline`.

## Rulesets

Requirement IDs: GEN-020 (branch protection table), GEN-021 (merge strategy), SEC-083, CI-001 (`ci.yml`, job `required`). Plan step: O-3 (`docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §2), task W1-T14 Step 3.

Status of this section: unverified (2026-11-27). The two JSON files were written by W1-T14 and validated only as JSON; no ruleset exists on GitHub until the owner performs the steps below.

### What is created

| Ruleset name | File | Branch | Rules | Bypass |
|---|---|---|---|---|
| `protect-main` | `.github/rulesets/main.json` | `refs/heads/main` | `deletion`, `non_fast_forward`, `pull_request` (0 required approvals, no stale-review dismissal, no code-owner review, no last-push approval, no thread-resolution requirement), `required_status_checks` with the single context `ci / required` and `strict_required_status_checks_policy: false` | Actor `5` (`RepositoryRole`, the repository admin role) with `bypass_mode: always` |
| `protect-develop` | `.github/rulesets/develop.json` | `refs/heads/develop` | the same four rules as `protect-main` | none |

Both rulesets have `enforcement: active` and `target: branch`.

Decision, recorded under GEN-021: `protect-main` omits the `required_linear_history` rule that the GEN-020 table lists for `main`. The release PR `develop → main` is merged with a merge commit titled `release: milestone <N>` (GEN-021), and `required_linear_history` rejects merge commits, so both rules cannot hold. GEN-021 wins because it is the more specific rule. The planner records this in spec §26 and ADR 0025 (outside the ownership of W1-T14; reported to the coordinator in the W1-T14 report).

Decision, status check name: the `required` job in `.github/workflows/ci.yml` has `name: ci / required`. GitHub matches a ruleset status check against the check-run name, which is the job `name`, so the ruleset context `ci / required` (GEN-020) is satisfied by exactly that job and by no other. Verify after the first CI run on a pull request that the check list shows a check named `ci / required` (the web page shows `ci / ci / required` because it prefixes the workflow name `ci`); if the check list shows another name, edit the `context` value in both JSON files to that name before the next import.

### Prerequisites

| # | Prerequisite | How to check | If it is not met |
|---|---|---|---|
| 1 | The files `.github/workflows/ci.yml`, `.github/rulesets/main.json` and `.github/rulesets/develop.json` exist on `develop` | `git -C /home/arkhash0309/projects/rootline ls-tree -r --name-only develop .github` lists the three files | Wait until the stage W1-P3 integration PR is merged into `develop` |
| 2 | The repository exists and is private: `arkhash0309/rootline` | `gh repo view arkhash0309/rootline --json nameWithOwner,isPrivate` prints `"nameWithOwner":"arkhash0309/rootline"` | Stop and ask the owner |
| 3 | `gh` is logged in as `arkhash0309` and as no other account | `gh auth status` shows `Logged in to github.com account arkhash0309` and marks it `Active account: true` | `gh auth switch --user arkhash0309`; never use any other account (overview Global Constraints "GitHub account") |
| 4 | The GitHub plan of `arkhash0309` supports rulesets on private repositories | Step 1 of the procedure below returns HTTP 201 | See the failure table |

### Procedure (chosen method: `gh api`)

Run in WSL bash from `/home/arkhash0309/projects/rootline` with `develop` checked out and up to date. This step is **[OWNER]**: an agent runs it only after the owner confirms in the session (overview Global Constraints "Outward-facing actions").

1. Create the `main` ruleset:

   ```bash
   gh api -X POST repos/arkhash0309/rootline/rulesets --input .github/rulesets/main.json
   ```

   Expected: HTTP 201 and a JSON body whose `name` is `protect-main` and whose `enforcement` is `active`. Write down the `id`.
2. Create the `develop` ruleset:

   ```bash
   gh api -X POST repos/arkhash0309/rootline/rulesets --input .github/rulesets/develop.json
   ```

   Expected: HTTP 201 and a JSON body whose `name` is `protect-develop`. Write down the `id`.
3. Verify:

   ```bash
   gh api repos/arkhash0309/rootline/rulesets --jq '.[] | "\(.name) \(.enforcement) \(.target)"'
   ```

   Expected output, in any order:

   ```text
   protect-main active branch
   protect-develop active branch
   ```
4. Verify the rules of one ruleset: `gh api repos/arkhash0309/rootline/rulesets/<id of protect-main> --jq '[.rules[].type] | sort'` prints `["deletion","non_fast_forward","pull_request","required_status_checks"]`.
5. Append one line to `wiki/log.md` under the current date: `- [owner] Created rulesets protect-main and protect-develop on rootline (O-3)`.

### Fallback method: web page

Use it only when step 1 or 2 of the procedure fails with HTTP 422 for a reason other than a duplicate name.

1. Open `https://github.com/arkhash0309/rootline/settings/rules` in the Windows browser (from WSL: `/mnt/c/Windows/explorer.exe "https://github.com/arkhash0309/rootline/settings/rules"`).
2. Click **New ruleset**, then **Import a ruleset**.
3. Choose the file `.github/rulesets/main.json` (the WSL file system is visible in Windows Explorer under `\\wsl$\Ubuntu\home\arkhash0309\projects\rootline\.github\rulesets`).
4. Check that the page shows the name `protect-main`, enforcement `Active`, the target branch `main`, and the required status check `ci / required`; click **Create**.
5. Repeat steps 2 to 4 with `.github/rulesets/develop.json` and the name `protect-develop`.

### Failure behaviour

| Symptom | Cause | Action |
|---|---|---|
| HTTP 401 | `gh` token missing or expired | `gh auth login` as `arkhash0309`, then rerun the failed step |
| HTTP 403 with the text `Upgrade to GitHub Pro or make this repository public to enable this feature` | The plan of `arkhash0309` does not enforce rulesets on a private repository | Stop. Making the repository public or buying GitHub Pro changes scope and cost (CLAUDE.md "When the source material is ambiguous", item 2): ask the owner. Until the owner decides, no branch protection exists and the PR flow of overview §7.6 is followed by convention only |
| HTTP 404 | Repository name wrong or the token lacks access to it | Run prerequisite 2 and 3 again |
| HTTP 422 `Name must be unique` | A ruleset with that name exists | List with step 3, then update it: `gh api -X PUT repos/arkhash0309/rootline/rulesets/<id> --input <file>` |
| Step 1 succeeds and step 2 fails | Partial creation | Rerun only step 2; the rulesets are independent |
| After import, a pull request into `develop` never shows the check `ci / required` | The `required` job was renamed, or `ci.yml` is not on the base branch | Compare the job name in `.github/workflows/ci.yml` with the `context` value in the JSON files and make them identical |

### Rollback

Delete one ruleset with `gh api -X DELETE repos/arkhash0309/rootline/rulesets/<id>`; the response is HTTP 204. Deleting a ruleset removes its protection immediately and changes no file in the repository.

## GitHub Apps

Not implemented yet; planned in W2-T07 (`rootline-faultlab`) and W3-T10 (`rootline-agent`, `rootline-gate`, ruleset `protect-main` for `rootline-env` per SEC-081).
