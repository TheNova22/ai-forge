---
name: network-issues-resolver
description: >-
  Reproduce and fix a single confirmed parser, rm_template, or documentation (EXAMPLES)
  gap from network-issues-validator output. Acts as a senior Ansible network automation
  engineer: prepares collection branch, writes corrective reproduction playbooks,
  implements the fix with changelog and tests, validates unit + sanity via tox in
  the user venv, and simulates integration via playbook. Optionally opens an upstream
  draft PR. Resolves exactly one issue per invocation.
triggers:
  - resolve network issue
  - fix parser gap
  - reproduce and fix
  - fix rm_template bug
  - network issues resolver
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
argument-hint: "[network-issues-report.md] [--issue N]"
---

# Skill: network-issues-resolver

## Role

Senior network automation engineer on the Ansible network collections team.
Reproduce a confirmed gap, implement a minimal fix, prove it with unit tests and
sanity. **One issue per invocation.**

## When to Invoke

TRIGGER: validated report exists and user wants to fix one confirmed gap.

DO NOT TRIGGER: no validated report (use orchestrator/validator); scan/validate/review only.

## Entry gates

Do not proceed until the user provides:

| Gate | Input | If missing |
|------|-------|-----------|
| Validated report | `network-issues-report.md` / `.json` | Run `network-issues-orchestrator` first |
| **Single issue** | Exactly one row from **Confirmed gaps** | Present the confirmed gaps table and ask user to pick |
| **Playbook directory** | Absolute path for reproduction playbooks | Ask the user; suggest creating one: `mkdir -p ~/network-playbooks` |
| **Collection path** | Absolute path to collection clone | Clone: `gh repo clone ansible-collections/<repo> /tmp/<repo> -- --depth=1` |
| **Python venv** | Path to venv (before playbook or tox) | Run `/setup-python-venv` skill or `python3 -m venv .venv && source .venv/bin/activate && pip install ansible-core` |

Present confirmed gaps and ask the user to pick **one** issue. Zero confirmed gaps → stop.

## Resolution pipeline

```
- [ ] Gates satisfied
- [ ] 1 — Prepare collection branch
- [ ] 2 — Study issue; read sibling playbooks in playbook dir
- [ ] 3 — Write repro playbook (one file; iterate in place)
- [ ] 4 — Run playbook; confirm broken behavior
- [ ] 5 — Implement fix in collection
- [ ] 6 — Corrective repro playbook + re-run (gate before unit tests)
- [ ] 7 — Changelog fragment
- [ ] 8 — Update unit cases → run unit + sanity tox
- [ ] 9 — Update integration cases (source only; not runnable via tox)
- [ ] 10 — Integration sim playbook in playbook dir + run on device
- [ ] 11 — Ask user about reverting device changes (if corrective/sim left residue)
- [ ] 12 — Ask user about upstream **draft** PR (template + before/after snippets)
```

All operational detail: [reference/resolution-details.md](reference/resolution-details.md).

Pattern/fix context: [network-issues-knowledge/patterns.md](../network-issues-knowledge/patterns.md).

**Pattern 11 (stale EXAMPLES):** reproduce the faulty task vars from `EXAMPLES` in
`plugins/modules/<prefix><module>.py` (step 3–4), update `EXAMPLES` to match argspec
(step 5), re-run playbook with the corrected example (step 6). Sanity tox validates
module documentation; unit/integration case updates only if the stale example also
appears in tests.

## Step summaries

| Step | Action |
|------|--------|
| 1 | Sync `main` from **upstream**; branch locally. [Branch / remotes](reference/resolution-details.md#branch) |
| 2 | Read cited source, pattern, playbook-dir siblings, integration `_populate_config` / `_remove_config` if present |
| 3 | One `repro_<module>_<slug>.yml`; edit **same file** on failure — no copies |
| 4 | `ansible-playbook` in venv; confirm bug; save **before** snippet |
| 5 | Minimal fix in rm_templates / config / argspec — or `EXAMPLES` in `plugins/modules/` for Pattern 11 |
| 6 | Evolve **same** repro playbook to corrective form (`block`/`always` teardown); re-run; confirm fix; save **after** snippet. **Gate before step 8** |
| 7 | `changelogs/fragments/` |
| 8 | Update unit case → unit + sanity tox |
| 9 | Update integration `.yml` case after unit+sanity pass |
| 10 | Create `sim_<module>_<slug>.yml` mirroring integration tasks (+ populate/remove); run on device. [Integration sim](reference/resolution-details.md#integration-simulation-playbook) |
| 11 | Ask if extra device revert needed. [Device cleanup](reference/resolution-details.md#device-cleanup) |
| 12 | Push **origin** (fork); open **draft** PR against **upstream**. [Upstream PR](reference/upstream-pr.md) |

## Critical rules

- One issue only; sync fresh `main` from **upstream** before branching
- **Fork workflow:** `git push origin` → PR base **upstream** / head **fork:branch**
- One repro playbook path — update in place through steps 3–6; never `repro_v2` copies
- **Corrective repro:** playbook must auto-undo device changes before unit tests (step 6)
- **Integration sim:** after integration case edits, mirror full flow in playbook dir (step 10)
- Same venv for playbook runs and tox
- **Tests:** read existing cases first; update in place; one scenario per case
- **End with steps 11–12** — cleanup prompt if needed, then **draft** PR prompt (`gh pr create --draft`)
- **Capture before/after snippets** at steps 4 and 6 for the PR body

## Deliverables

1. Issue, branch, collection path
2. Corrective repro playbook + before/after summary
3. Integration sim playbook path + run summary (step 10)
4. Files changed (fix, changelog, unit + integration cases)
5. Unit + sanity tox results
6. Integration cases updated (not run via tox locally)
7. Device cleanup prompt if corrective/sim did not fully restore state
8. Upstream **draft** PR prompt with snippets

**Always end with steps 11–12.** Do not commit, push, or open a PR unless the user requests it in step 12. Use **`--draft`** unless the user explicitly asks for a ready-for-review PR.

## Resources

| File | Content |
|------|---------|
| [reference/resolution-details.md](reference/resolution-details.md) | Branch, playbooks, changelog, tests, tox, sim, cleanup |
| [reference/upstream-pr.md](reference/upstream-pr.md) | Draft PR template, snippets, fork remotes |
| [../network-issues-knowledge/patterns.md](../network-issues-knowledge/patterns.md) | Gap patterns and fixes |
| [../network-issues-scanner/config/repos.yaml](../network-issues-scanner/config/repos.yaml) | Collection paths |
