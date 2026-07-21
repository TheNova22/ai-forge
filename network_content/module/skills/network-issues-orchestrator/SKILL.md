---
name: network-issues-orchestrator
description: >-
  End-to-end network collection parser and rm_template issue audit. Runs
  network-issues-scanner first to collect candidate hits across cisco.ios,
  cisco.nxos, cisco.iosxr, and arista.eos, then network-issues-validator to
  verify each hit and drop false positives. Delivers a validated gap report.
  Use when asked to scan parser gaps, audit resource modules, or find template
  bugs with confirmed results.
triggers:
  - network issues audit
  - validate network parser issues
  - confirmed gap report
  - full parser gap pipeline
  - end-to-end network audit
  - scan and validate parser gaps
  - audit resource modules with confirmed results
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
argument-hint: "[--repo cisco.iosxr] [--module iosxr_bgp_global]"
---

# Skill: network-issues-orchestrator

## Purpose

Run the full **scan → validate** pipeline for parser and rm_template issues in
Ansible network collection resource modules.

1. **Scanner** (`network-issues-scanner`) — cast a wide net; emit candidate hits
2. **Validator** (`network-issues-validator`) — verify each hit; drop false positives

Deliverable: `network-issues-report.md` (validated gaps only).

Implementing fixes is out of scope unless the user explicitly asks.

## When to Invoke

TRIGGER when:

- User asks to scan parser gaps, audit resource modules, or find template bugs
- User wants **confirmed** gap results (not raw scanner candidates)
- User wants proactive QA across network collections before a release

DO NOT TRIGGER when:

- User only wants raw candidate hits without validation → use `network-issues-scanner`
- User already has scanner output and only needs validation → use `network-issues-validator`
- User wants to triage GitHub issues → use `network-collection-triage`
- User wants to review a specific PR diff → use `pr-review`

## Prerequisites

- `gh` CLI authenticated (for cloning collection repos)
- Local clone of target collection(s), or network access via `gh api`
- Child skills and shared knowledge:
  - [network-issues-scanner](../network-issues-scanner/SKILL.md)
  - [network-issues-validator](../network-issues-validator/SKILL.md)
  - [network-issues-knowledge](../network-issues-knowledge/README.md)

---

## Mode Detection

### Full audit mode (default)

No `--repo` or `--module` provided. Scan and validate **all four collections**.
Do NOT ask clarifying questions — run the full pipeline automatically.

### Targeted mode

User specifies `--repo`, `--module`, or a collection name. Scan and validate only
that scope.

---

## Orchestration Pipeline

Track progress with a checklist:

```
Orchestrator Progress:
- [ ] Phase 1 — Scanner (network-issues-scanner)
- [ ] Phase 2 — Validator (network-issues-validator)
- [ ] Phase 3 — Deliver final report
```

### Phase 1 — Scanner

Read and follow [network-issues-scanner/SKILL.md](../network-issues-scanner/SKILL.md)
in full. Execute its 7-step scan pipeline.

**Outputs required before Phase 2:**

- `network-issues-scanner-hits.md`
- `network-issues-scanner-hits.json`

If the scanner finds zero hits, skip to Phase 3 with an empty validated report.

### Phase 2 — Validator

Read and follow [network-issues-validator/SKILL.md](../network-issues-validator/SKILL.md)
in full. Pass the Phase 1 output files as input.

Execute all 5 validation steps. Process every hit — do not skip `candidate` rows.

**Outputs:**

- `network-issues-report.md`
- `network-issues-report.json`

### Phase 3 — Deliver final report

Present the user with:

1. **Executive summary** — modules scanned, scanner hits, confirmed gaps, drop rate (dropped ÷ scanner hits)
2. **Confirmed gaps table** — from `network-issues-report.md`
3. **Notable drops** — only if high-confidence scanner hits were dropped (explain why)
4. **Artifact paths** — list all four output files

To fix a single confirmed gap, hand off to `network-issues-resolver` with the report
and user-selected issue, playbook directory (unless `--skip-device`), collection path,
and venv. Optional flags: `--skip-device`, `--dry-run`.

Do not present raw scanner hits as final results unless the user explicitly asks
for intermediate output.

---

## Handoff contract

| Artifact | Producer | Consumer | Purpose |
|----------|----------|----------|---------|
| `network-issues-scanner-hits.md` | Scanner | Validator, User (optional) | Human-readable candidates |
| `network-issues-scanner-hits.json` | Scanner | Validator | Machine handoff |
| `network-issues-report.md` | Validator | User, Resolver | Final validated gaps |
| `network-issues-report.json` | Validator | User, Resolver | Structured confirmed + dropped |

---

## Critical rules

- **Always run scanner before validator** in a single orchestrator invocation.
- **Never skip validation** — scanner output alone is not the deliverable.
- **Preserve scope** — if the user targeted one repo/module, both phases use the same scope.
- **Reuse clones** — validator should use the same collection paths the scanner used.
- **Artifact naming** — when running targeted scans (e.g. `--repo cisco.iosxr`), suffix artifacts
  with the scope to prevent overwriting previous full-scan results:
  `network-issues-scanner-hits.cisco.iosxr.md`, `network-issues-report.cisco.iosxr.md`.
  Full-scope scans use the default names.

---

## Resources

| Skill / file | Role |
|---|---|
| [network-issues-scanner](../network-issues-scanner/SKILL.md) | Phase 1 — candidate discovery |
| [network-issues-validator](../network-issues-validator/SKILL.md) | Phase 2 — verification and filtering |
| [network-issues-knowledge](../network-issues-knowledge/README.md) | Shared patterns, crosswalk, verification |
| [network-issues-resolver](../network-issues-resolver/SKILL.md) | Fix one confirmed gap (after validation) |
| [network-issues-scanner/config/repos.yaml](../network-issues-scanner/config/repos.yaml) | Collection scope and paths |
