# Named-test registry

This directory lists every named test of the spec (overview `docs/superpowers/plans/2026-11-26-rootline-00-overview.md` §6.1) so that the integration gate (overview §7.7, check G8, implemented by `scripts/integration_gate.py`) can prove that each named test still exists and passes after several task branches are combined. Requirements: PG-16, TST-002, TST-010.

## File format

One YAML file per named test per task. Validation schema: [`schema.json`](schema.json) (JSON Schema draft 2020-12).

| Key | Type | Required | Constraint |
|---|---|---|---|
| `id` | string | yes | `^TST-[A-Z0-9]+-[0-9]{3}$`, a named test ID of overview §6.1, for example `TST-LAB-001` |
| `introduced_by` | string | yes | `^W[1-8]-T[0-9]{2}$`, the plan task that creates this file, for example `W2-T06` |
| `selectors` | list | yes | at least 1 item; each item has the two keys below and no other key |
| `selectors[].kind` | string | yes | one of `pytest`, `vitest`, `opa`, `kyverno`, `playwright` |
| `selectors[].target` | string | yes | non-empty; meaning per `kind` in the next table |

| `kind` | `target` | Command run by G8 (from the repository root of the checked-out branch) | Pass condition |
|---|---|---|---|
| `pytest` | `<path>::<test name>` | `uv run pytest <target> -q` | exit 0; exit 5 (no test collected) fails with `collects no tests` |
| `vitest` | test file path under `apps/console/` | `npm --prefix apps/console run test -- --run <target>` | exit 0 |
| `opa` | directory with `*_test.rego` files | `opa test <target>` | exit 0 |
| `kyverno` | directory with Kyverno test files | `kyverno test <target>` | exit 0 |
| `playwright` | spec file path | not run by G8 | listed only; executed by `e2e.yml` and W6-T10 |

Example, file `tests/registry/TST-LAB-001--W2-T06.yaml`:

```yaml
id: TST-LAB-001
introduced_by: W2-T06
selectors:
  - kind: pytest
    target: services/faultlab/tests/test_generate.py::test_tst_lab_001_counts
```

## File name

The file name is `<TST-ID>--<task-id>.yaml`, so it equals `<id>--<introduced_by>.yaml` (two hyphens between the parts). Several tasks may each register selectors for the same `TST-ID` (for example `TST-MCP-001` from W3-T06, W3-T07 and W3-T08); each task owns exactly its own file. A task never edits another task's file (overview §7.4).

## Who creates a file

The task that creates a named test of overview §6.1 creates the registry file for it in the same commit series. The schedule (`docs/superpowers/plans/2026-11-26-rootline-schedule.yaml`) lists each registry file under that task's `owns`.

## What G8 checks

| Check | Failure behaviour |
|---|---|
| Each file parses as YAML and satisfies `schema.json` | `fail`, reason names the file and the first violation |
| File name equals `<id>--<introduced_by>.yaml` | `fail`, reason `<name>: file name must be <expected>` |
| Each non-`playwright` selector passes (table above) | `fail`, reason names the file, the selector and the exit code |
| The tool of a selector (`uv`, `npm`, `opa`, `kyverno`) is on `PATH` | `fail`, reason names the missing tool |
| No registry file present at the base is missing on the branch | `fail`, reason `<name>: registry file removed without registry-removal: <TST-ID> <reason>` |
| `tests/registry/` exists on the branch or on the base | `skip`, reason `tests/registry missing` when neither has it |

## Exemption lines in the integration PR body

Each line starts at the beginning of a line of the PR description, has a non-empty reason, and applies to one check of the gate.

| Line | Exempts | Reviewer rule |
|---|---|---|
| `registry-removal: <TST-ID> <reason>` | G8 file-removal check for every removed file whose name starts with `<TST-ID>--` | the integration reviewer approves the reason |
| `test-removal: <reason>` | G9 (collected test count on the branch lower than on the base) | the integration reviewer approves the reason |
| `baseline-change: <reason>` | G10 (smoke predictions differ from `eval/baselines/baseline-smoke.json`), only when the same PR also updates that file | the integration reviewer approves the reason |
