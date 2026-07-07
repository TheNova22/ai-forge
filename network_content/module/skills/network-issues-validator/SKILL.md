---
name: network-issues-validator
description: >-
  Validate network-issues-scanner hits by reading source code and tests for each
  candidate. Thoroughly verify parser and rm_template gaps, drop false positives
  and already-fixed issues, and emit a confirmed gap report. Use after a scanner
  run or when handed scanner-hits output. Prefer network-issues-orchestrator for
  end-to-end scan plus validation.
triggers:
  - validate parser gaps
  - verify scanner hits
  - filter false positives
  - confirm network issues
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
argument-hint: "[scanner-hits.md] [--repo cisco.iosxr]"
---

# Skill: network-issues-validator

## Purpose

Take **scanner hits** and produce a **validated gap report** by verifying each
candidate against live source code, config registration, sibling parsers, and tests.

## When to Invoke

TRIGGER when:

- User has scanner output (`network-issues-scanner-hits.md` or `.json`) to verify
- `network-issues-orchestrator` delegates the validation phase
- User asks to confirm, filter, or validate parser gap findings

DO NOT TRIGGER when:

- No scanner hits exist yet → run `network-issues-scanner` or orchestrator first
- User wants a fresh scan → use scanner or orchestrator

## Prerequisites

- Scanner output in working directory or user-provided path
- Local clone of relevant collection(s) at paths used during the scan

## Common knowledge

Read [network-issues-knowledge/README.md](../network-issues-knowledge/README.md) as needed
during validation:

| File | Use for |
|------|---------|
| [verification.md](../network-issues-knowledge/verification.md) | Per-hit procedure, verdicts, drop codes |
| [patterns.md](../network-issues-knowledge/patterns.md) | Pattern confirm/drop bars (incl. Patterns 10–11) |
| [parser-anatomy.md](../network-issues-knowledge/parser-anatomy.md) | Comparison paths, config registration |
| [crosswalk.md](../network-issues-knowledge/crosswalk.md) | Crosswalk procedure |
| [checklists.md](../network-issues-knowledge/checklists.md) | Test and compound-CLI re-check |

Also: [../network-issues-scanner/config/repos.yaml](../network-issues-scanner/config/repos.yaml),
[reference/validated-report-template.md](reference/validated-report-template.md).

## Input

1. `network-issues-scanner-hits.md` / `.json` in working directory (default)
2. User-provided path to scanner output
3. Inline table or JSON pasted by the user

`--repo` or `--module` limits validation to that subset.

---

## Validation Pipeline

```
Validation Progress:
- [ ] Step 1 — Load scanner hits
- [ ] Step 2 — Resolve collection source paths
- [ ] Step 3 — Verify each hit (per-hit deep review)
- [ ] Step 4 — Re-check test coverage for confirmed gaps
- [ ] Step 5 — Produce validated report
```

Read [verification.md](../network-issues-knowledge/verification.md) before per-hit review.

### Step 1 — Load scanner hits

Parse markdown table or JSON `hits` array. Record count by confidence.

### Step 2 — Resolve collection source paths

Locate collection clones used during the scan. Reuse scanner paths when possible.

### Step 3 — Verify each hit

Follow [verification.md](../network-issues-knowledge/verification.md) for every hit.
For Patterns 5, 6, and 10, consult Cisco documentation before confirming or dropping.
For Pattern 11, compare `EXAMPLES` in `plugins/modules/<prefix><module>.py` against
argspec and integration tests — documentation-only gaps; resolver reproduces the faulty
example and updates `EXAMPLES`.
Apply pattern bars from [patterns.md](../network-issues-knowledge/patterns.md).

Process `confirmed` → `likely` → `candidate`. Do not skip `candidate` hits.

### Step 4 — Re-check test coverage

For each confirmed hit, follow [checklists.md](../network-issues-knowledge/checklists.md).

### Step 5 — Produce validated report

Emit per [validated-report-template.md](reference/validated-report-template.md):

- `network-issues-report.md` (with Validation Summary and Dropped hits sections)
- `network-issues-report.json`

Handoff: [network-issues-resolver](../network-issues-resolver/SKILL.md) consumes this
output to reproduce and fix **one** confirmed gap at a time.

---

## Resources

| File | When to read |
|---|---|
| [../network-issues-knowledge/verification.md](../network-issues-knowledge/verification.md) | Per-hit review |
| [../network-issues-knowledge/patterns.md](../network-issues-knowledge/patterns.md) | Per-pattern bars |
| [reference/validated-report-template.md](reference/validated-report-template.md) | Step 5 — output format |
| [../network-issues-scanner/config/repos.yaml](../network-issues-scanner/config/repos.yaml) | Repo paths and layout |
| [../network-issues-resolver/SKILL.md](../network-issues-resolver/SKILL.md) | Fix a single confirmed gap |
