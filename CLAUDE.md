# CLAUDE.md — Rootline

Instructions for every AI coding agent working in this repository. These rules override default agent behaviour.

Project: **Rootline**, an AI SRE agent that diagnoses incidents in its own Kubernetes cluster.
Source of truth: [docs/superpowers/specs/2026-11-25-rootline-design.md](docs/superpowers/specs/2026-11-25-rootline-design.md) (SPEC-ROOTLINE-001).

## Documentation rule: every document must be detailed and unambiguous

All implementation in this project is done by AI coding agents. Any gap or vague statement in a document will be filled with a guess, so every document must leave **nothing open to interpretation**. Length does not matter: a document can run to thousands of lines.

### Scope

This rule applies to every document an agent writes or edits in this repository, including:

| Document type | Location |
|---|---|
| Design specs | `docs/superpowers/specs/` |
| Implementation plans | `docs/superpowers/plans/` |
| Wiki pages | `wiki/` |
| Architecture Decision Records (ADRs) | `wiki/adr/` |
| Runbooks | `wiki/runbooks/` |
| READMEs, `CLAUDE.md`, `AGENTS.md` and other files aimed at agents | anywhere in the repo |
| Code comments and docstrings that describe behaviour, contracts or invariants | source files |

It does not apply to commit messages or PR descriptions, though those should still be specific.

### Requirements

A document complies with this rule only if all of the following hold:

1. **Exact values are pinned.** Write the literal value, never a placeholder or a range. This covers versions, defaults, thresholds, limits, timeouts, names, file paths, ports, environment variable names, error codes, model IDs and prices.
   - Wrong: "use a recent version of Keycloak", "a short timeout".
   - Right: "Keycloak `26.8.0`", "timeout `30 s`".
2. **Every open choice is resolved.** If the document presents options, it states which one is chosen. If a choice must be made at run time, it gives the decision rule *and* the default that applies when the rule does not decide.
3. **Interfaces are fully specified.** For every API endpoint, MCP tool, function, CLI command, queue message, database table or config file, the document defines inputs (names, types, required/optional, constraints), outputs (shape and types), errors (codes and when each occurs) and side effects. Naming a component without its interface does not comply.
4. **Terms are defined.** Every project-specific term is defined in the document or links to its definition (the spec's glossary, §2).
5. **No vague words.** These words and phrases are forbidden unless immediately followed by the concrete meaning: "etc.", "and so on", "as needed", "appropriate", "reasonable", "where applicable", "if necessary", "some", "various", "TBD", "TODO", "later".
6. **Requirements carry IDs.** Normative statements carry a stable ID of the form `<AREA>-<NNN>`, using the area prefixes in the spec's §0.2 (for example `EVL-040`, `SEC-021`), so plans, tests and code comments can reference them. Implementation plans cite these IDs in task descriptions; tests cite them in docstrings. Normative language follows the spec's §0.1: **MUST**, **MUST NOT**, **SHOULD**, **MAY**.
7. **Tables over prose for structured facts.** Catalogues, mappings, settings, budgets and comparisons are written as tables.
8. **Examples are concrete.** Where an example helps, give a complete, valid one (a full JSON payload, a full command line), not a fragment with `...`.
9. **Failure behaviour is stated.** For every operation, the document says what happens on timeout, invalid input, missing dependency and partial failure.
10. **Cross-references are exact.** Refer to other material by requirement ID, section number and file path, never by "see above" or "the relevant section".

### When the source material is ambiguous

If an agent finds that the spec or another document does not answer a question it needs answered:

1. Do not guess silently. Choosing without recording is a defect.
2. If the decision changes cost, security, scope or anything the owner has already approved, stop and ask the owner before proceeding.
3. Otherwise, follow the spec's §0.3: pick the option that is simplest, cheapest and safest, in that priority order.
4. Record the decision as an ADR in `wiki/adr/` (spec §21.3) in the same pull request, with the label `spec-gap`.
5. Add the question and the decision to the spec's gap log (§26) in that same pull request.

### Self-check before finishing a document

Before declaring a document done, the agent re-reads it and confirms:

- [ ] Every value an implementer needs is written down literally.
- [ ] No forbidden vague word from requirement 5 remains.
- [ ] Every interface has inputs, outputs, errors and side effects.
- [ ] Every cross-reference resolves to an existing ID, section or file.
- [ ] No two statements contradict each other.
- [ ] Someone with no access to the conversation that produced the document could implement from it without asking a question.
