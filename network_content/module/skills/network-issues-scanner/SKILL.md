---
name: network-issues-scanner
description: >-
  Scan Ansible network collection resource modules (cisco.ios, cisco.nxos,
  cisco.iosxr, arista.eos) for parser and rm_template issue candidates — argspec
  coverage gaps, unregistered parsers, type mismatches, boolean toggle/idempotency
  issues, missing negate regex, stale parsers, outdated module EXAMPLES, and test
  blind spots. Casts a wide net and emits candidate hits for
  network-issues-validator. Use when raw scanner hits are needed without the full
  validation phase. Prefer network-issues-orchestrator for end-to-end scan plus
  validation.
triggers:
  - scan parser gaps
  - raw scanner hits
  - network issues scan
  - scanner phase only
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
argument-hint: "[--repo cisco.iosxr] [--module iosxr_bgp_global]"
---

# Skill: network-issues-scanner

## Prerequisites

- `gh` CLI authenticated
- Local clone of target collection(s), or network access via `gh api`

## Knowledge files

Read [network-issues-knowledge/README.md](../network-issues-knowledge/README.md) as needed
during the scan pipeline:

| File | Use for |
|------|---------|
| [parser-anatomy.md](../network-issues-knowledge/parser-anatomy.md) | Comparison paths, config registration |
| [patterns.md](../network-issues-knowledge/patterns.md) | Pattern classification (incl. Patterns 10–11) |
| [crosswalk.md](../network-issues-knowledge/crosswalk.md) | Argspec ↔ template crosswalk |
| [confidence-and-severity.md](../network-issues-knowledge/confidence-and-severity.md) | Hit confidence and severity |
| [checklists.md](../network-issues-knowledge/checklists.md) | Module and compound-CLI checklists |

Operational details: [config/repos.yaml](config/repos.yaml),
[reference/workflow-details.md](reference/workflow-details.md),
[reference/scanner-report-template.md](reference/scanner-report-template.md).

---

## Mode Detection

**Full scan (default):** all four collections — run automatically, no clarifying questions.

**Targeted:** user specifies `--repo`, `--module`, or collection name — scan that scope only.

---

## Scan Pipeline

```
Scan Progress:
- [ ] Step 1 — Acquire collection source
- [ ] Step 2 — Enumerate resource modules
- [ ] Step 3 — Mechanical pre-scan
- [ ] Step 4 — Argspec vs template crosswalk (+ EXAMPLES check)
- [ ] Step 5 — Pattern classification (candidates)
- [ ] Step 6 — Test coverage gap check
- [ ] Step 7 — Produce scanner hits report
```

Read [workflow-details.md](reference/workflow-details.md) before Steps 2, 4, and 6.

### Step 1 — Acquire collection source

For each repo in [config/repos.yaml](config/repos.yaml):

```bash
gh repo clone ansible-collections/cisco.iosxr /tmp/cisco.iosxr -- --depth=1 2>/dev/null || true
```

Prefer existing local clones when available.

### Step 2 — Enumerate resource modules

Glob `plugins/modules/*.py`; pair argspec and rm_template files by stem name.
See workflow-details.md for module layout.

### Step 3 — Mechanical pre-scan

```bash
python scripts/scan_mechanical_signals.py /path/to/cisco.iosxr --json
```

Produces candidate signals for Steps 4–5. Run supplemental grep commands from workflow-details.md.

### Step 4 — Argspec vs template crosswalk

Follow [crosswalk.md](../network-issues-knowledge/crosswalk.md). Primary discovery step.
Include Pattern 11: compare `EXAMPLES` in `plugins/modules/<prefix><module>.py` against
the argspec tree and integration test task vars.

### Step 5 — Pattern classification (candidates)

Classify candidates per [patterns.md](../network-issues-knowledge/patterns.md),
including Pattern 10 (hardcoded compound CLI — verify against Cisco docs when flagged)
and Pattern 11 (stale EXAMPLES vs argspec).
Assign confidence per [confidence-and-severity.md](../network-issues-knowledge/confidence-and-severity.md).

**Do not drop hits.** Note mitigating context in `Notes` for the validator.

### Step 6 — Test coverage gap check

Follow [checklists.md](../network-issues-knowledge/checklists.md) and workflow-details.md grep commands.

### Step 7 — Produce scanner hits report

Emit per [scanner-report-template.md](reference/scanner-report-template.md):

- `network-issues-scanner-hits.md`
- `network-issues-scanner-hits.json`

When invoked by `network-issues-orchestrator`, pass both files to the validator.

