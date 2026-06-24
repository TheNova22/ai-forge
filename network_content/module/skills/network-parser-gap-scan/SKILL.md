---
name: network-parser-gap-scan
description: >-
  Scan Ansible network collection resource modules (cisco.ios, cisco.nxos,
  cisco.iosxr, arista.eos) for parser and rm_template gaps where argspec or
  documentation promises behavior the parser pipeline (getval/setval/name/optional
  compval) cannot deliver. Detects argspec/template coverage gaps, unregistered
  parsers, type mismatches, boolean toggle/idempotency issues, missing negate
  regex, stale parsers, and test blind spots before users hit them. Use when
  asked to scan parser gaps, find template bugs, audit resource modules, or
  proactively check parser correctness.
triggers:
  - scan parser gaps
  - parser gap analysis
  - audit resource modules
  - find template bugs
  - parser audit
  - rm_template gaps
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
argument-hint: "[--repo cisco.iosxr] [--module iosxr_bgp_global]"
---

# Skill: network-parser-gap-scan

## Purpose

Proactively identify **parser and template gaps** in network collection resource
modules — cases where the argspec and documentation describe behavior that the
parser pipeline (`getval` / `setval` / `name` / optional `compval` / `result`)
cannot correctly parse, generate, or reconcile.

**Scope balance:** Boolean toggle bugs (`*.set`, `no …` negate) are one gap
family. Equally important are **coverage gaps**, **unregistered parsers**,
**type/CLI mismatches**, **idempotency** failures, and **stale template paths**.
Do not over-index on `shutdown` / `enable` — treat them as examples of Patterns
1–3, not the scan target.

This skill **detects and lists** gaps. Implementing fixes is out of scope unless
the user explicitly asks.

## When to Invoke

TRIGGER when:

- User asks to scan for parser gaps, template bugs, or argspec/template mismatches
- User asks to audit resource module idempotency or boolean toggle handling
- User wants proactive QA across network collections before a release
- User references PR #623, #615, or similar parser-gap fix patterns

DO NOT TRIGGER when:

- User wants to triage GitHub issues (use `network-collection-triage`)
- User wants to review a specific PR diff (use `pr-review`)
- User wants to fix a known bug (use bugfix workflow)
- Collections outside the scope list are requested (unless user expands scope)

## Prerequisites

- `gh` CLI authenticated (for cloning or fetching repo content)
- Local clone of target collection(s), **or** network access to read files via `gh api`

## Scope and reference material

- Collections, platforms, and paths: [config/repos.yaml](config/repos.yaml)
- Parser anatomy and pattern catalog: [reference/gap-patterns.md](reference/gap-patterns.md)
- Detailed workflow steps, grep commands, checklists: [reference/workflow-details.md](reference/workflow-details.md)
- Report format: [reference/report-template.md](reference/report-template.md)

**Comparison path rule:** `compval` if set, else parser `name`. Absent `compval`
is normal for direct-value parsers — do not flag it as a gap. Read
gap-patterns.md § Parser comparison paths before Step 4.

---

## Mode Detection

### Full scan mode (default)

No specific repo or module provided. Scan **all four collections** end-to-end.
Do NOT ask clarifying questions — run the full pipeline automatically.

### Targeted mode

User specifies `--repo`, `--module`, or a collection name. Scan only that scope.

---

## Scan Pipeline

Execute all steps. Track progress with a checklist:

```
Scan Progress:
- [ ] Step 1 — Acquire collection source
- [ ] Step 2 — Enumerate resource modules
- [ ] Step 3 — Mechanical pre-scan
- [ ] Step 4 — Argspec vs template crosswalk
- [ ] Step 5 — Deep pattern analysis
- [ ] Step 6 — Test coverage gap check
- [ ] Step 7 — Produce gap report
```

Read [reference/workflow-details.md](reference/workflow-details.md) before Steps 2, 4, and 6.

### Step 1 — Acquire collection source

For each repo in [config/repos.yaml](config/repos.yaml), ensure source is available:

```bash
# Prefer existing local clone; otherwise shallow clone to /tmp
gh repo clone ansible-collections/cisco.iosxr /tmp/cisco.iosxr -- --depth=1 2>/dev/null || true
```

If the user already has the repo checked out, use that path instead.

### Step 2 — Enumerate resource modules

Glob `plugins/modules/*.py`; pair argspec and rm_template files by stem name.
See workflow-details.md for full module layout and path recording.

### Step 3 — Mechanical pre-scan

Run on each collection clone (script is relative to this skill):

```bash
python scripts/scan_mechanical_signals.py /path/to/cisco.iosxr --json
```

Produces **candidate signals** — input to Steps 4–5, not the final report.
Parser registration (`self.parsers` vs template entries) is verified in Step 4.
Run supplemental grep commands from workflow-details.md.

### Step 4 — Argspec vs template crosswalk (primary discovery)

Finds the **most gaps**. Run exhaustively for every module — do not stop after
toggle issues. Build argspec leaf → parser comparison path → config registration
crosswalk. See workflow-details.md for the full procedure.

### Step 5 — Deep pattern analysis

Classify every candidate from Steps 3–4 against
[gap-patterns.md](reference/gap-patterns.md). Review **all pattern families** per
module before moving on.

For each finding, read the surrounding parser entry and argspec definition.
Confirm the gap is real — eliminate false positives where a sibling parser
covers the path or config class handles logic outside templates.

**Severity hints:** High — silent no-op, wrong commands, broken disable/toggle.
Medium — type mismatch, idempotency, exclusivity. Low — stale code or test gaps.

### Step 6 — Test coverage gap check

Crosswalk argspec leaf paths against unit and integration tests for modules with
confirmed or suspected gaps. See workflow-details.md for grep commands.

### Step 7 — Produce gap report

Emit markdown per [report-template.md](reference/report-template.md). Save as
`parser-gap-report.md` in the working directory.

---

## Critical rules

**Do not over-index boolean toggles.** Coverage gaps and unregistered parsers
are equally common and often more severe than `shutdown`/`enable` issues.

**False positive filters** — do NOT report when:

- Parser uses `name` only and comparison path correctly matches argspec
- Template uses a separate parser for negate (distinct entry for `no` form)
- Parameter is intentionally parsed-only or config-only and docs say so
- `set: false` is handled by config class logic outside rm_templates (verify first)
- Mechanical script flags a pattern that manual review disproves

**Analysis checklists** (argspec coverage, boolean toggles, type/exclusivity,
new options, cross-collection sweep): see workflow-details.md.

---

## Resources

| File | When to read |
|---|---|
| [reference/gap-patterns.md](reference/gap-patterns.md) | Step 5 — pattern classification |
| [reference/workflow-details.md](reference/workflow-details.md) | Steps 2, 4, 6 — layout, crosswalk, tests, checklists |
| [reference/report-template.md](reference/report-template.md) | Step 7 — output format |
| [config/repos.yaml](config/repos.yaml) | Step 1 — repos, platforms, paths |
| [scripts/scan_mechanical_signals.py](scripts/scan_mechanical_signals.py) | Step 3 — mechanical pre-scan |
