---
name: release-orchestrator
description: >-
  Orchestrates parallel Ansible collection releases across multiple
  repositories configured in config.yaml. Wraps the release skill and runs
  Section 1 (release PR creation through Step 9) for each repository
  concurrently. Use when releasing multiple collections at once, batch
  releasing, or coordinating a multi-collection release wave.
user-invocable: true
argument-hint: "[--config <path>] [--repos <id,...>] [--dry-run] [--resume]"
---

# Skill: release-orchestrator

## Purpose

Coordinate **parallel release PR creation** for multiple Ansible collections.
Wraps [`release`](../release/SKILL.md) **Steps 1–9 only** — no tagging,
Galaxy publish, or announcements (future sections).

## When to Invoke

TRIGGER: batch release, release wave, multi-collection release, or
`release-orchestrator` with changelog fragments ready across repos.

DO NOT TRIGGER: single collection (use `release`), merging existing PRs,
or post-merge tagging/announcements.

## Scope

| Section | Scope | Status |
| ------- | ----- | ------ |
| **Section 1** | Release PR creation (release Steps 1–9) | **Implemented** |
| Section 2 | Tag and push after merge (Steps 10–11) | Planned |
| Section 3 | GitHub release + Bullhorn (Steps 12–13) | Planned |

## Configuration — Source of Truth

**`config.yaml` is the single source of truth.** Read it first; do not
hard-code paths, remotes, or repository lists elsewhere.

Resolution order:

1. `--config <path>` if provided
2. `config.yaml` beside this skill

Schema and defaults are documented in [`config.yaml`](config.yaml). Key fields:

- `collections_path` — base for `${collections_path}/${namespace}/${name}` when `path` is omitted
- `venv_path` — shared Python venv for `antsibull-changelog`
- `upstream_remote` — canonical remote name (default: `upstream`)
- `repositories[]` — `id`, `upstream`, optional `enabled`, `path`, `version`

Filter to enabled entries; apply `--repos id1,id2` if given.

## Flags

| Flag | Description |
| ---- | ----------- |
| `--config <path>` | Config file (default: skill `config.yaml`) |
| `--repos <id,...>` | Subset of repository `id` values |
| `--dry-run` | Plan and pre-flight only; no branches, commits, or PRs |
| `--resume` | Retry failed repos from `.release-orchestrator-state.json` |

## Pre-flight (before anything else)

**Complete all pre-flight steps for every enabled repository before launching
any release session.** No parallel work until pre-flight passes and the human
confirms the plan.

### 1. Load config and resolve paths

1. Read the resolved config file.
2. For each enabled repository, resolve checkout path (`path` or derive from
   `collections_path` + `id`).

### 2. Sync each repository to latest main

For **each** repository in the approved plan:

```bash
cd PATH
git checkout main
git pull --rebase origin main
git status          # must be clean
git remote -v       # origin present
ls changelogs/fragments/
```

Requirements per repo:

- On `main`, clean working tree
- Latest changes pulled from **`origin main`**
- Changelog fragments present
- `origin` (or configured remote) points to canonical repo
- If any changes exist, git stash the change as to be on the latest changes from the origin main branch

**CONFIRM:** Present per-repo pre-flight summary. Exclude failures unless the
human fixes and retries.


### 3. Validate directories and venv

For **each** resolved checkout path:

- Directory exists and is a git repository

For the shared venv (`venv_path` from config, or `.venv`):

- Python and `antsibull-changelog` are available

Record `VENV_PATH` for all sessions.
Also verify once globally: `gh auth status`.

**CONFIRM:** Report any missing path or venv problem. Block live execution
until resolved or repos are excluded.

Build a release plan: planned version from `repositories[].version`, config
   overrides, or fragment analysis.

**CONFIRM:** Present the plan table and wait for approval:

```
| id         | upstream                       | path (resolved)     | version | enabled |
|------------|--------------------------------|---------------------|---------|---------|
| cisco.ios  | ansible-collections/cisco.ios  | ~/.../cisco/ios     | 9.5.0   | yes     |
```

## Section 1 — Parallel release sessions

After pre-flight and human confirmation, launch one **parallel session** per
repository (Task subagent or equivalent) in a **single message**.

Each session:

1. `cd` to the repository path (already on synced `main`)
2. Follow [`release`](../release/SKILL.md) **Steps 1–9 only**
3. Use `"${VENV_PATH}/bin/antsibull-changelog"` for changelog generation
4. Stop after Step 9 (PR created). Do **not** run Steps 10–13.
5. Return a result object:

```json
{
  "id": "cisco.ios",
  "upstream": "ansible-collections/cisco.ios",
  "path": "/abs/path",
  "version": "9.5.0",
  "branch": "release_9.5.0",
  "pr_url": "https://github.com/.../pull/1234",
  "status": "success",
  "error": null
}
```

Sessions are independent. Each inherits **CONFIRM** gates from the `release`
skill (Steps 2, 4, 7, 8, 9). Use the approved plan version unless the human
overrides at Step 2.

## Aggregate and finish

1. Collect session results into `.release-orchestrator-state.json`:

```json
{
  "section": 1,
  "timestamp": "2026-06-12T10:00:00",
  "config": "/path/to/config.yaml",
  "venv_path": "/path/to/.venv",
  "repositories": []
}
```

2. Present summary table (`id`, `version`, `branch`, PR, `status`).

**CONFIRM (Section 1 complete):** Remind the human to monitor CI, obtain
reviews, and merge each PR manually. Do not tag or announce.

## Dry run and resume

**`--dry-run`:** Execute pre-flight (config, paths, venv, git read-only
checks) and report planned versions/branches. No branches, commits, pushes, or
PRs. Still require plan **CONFIRM**.

**`--resume`:** Read state file; skip `"status": "success"` repos; re-run
Section 1 for failed or incomplete repos; merge results into state file.

## Error handling

| Condition | Action |
| --------- | ------ |
| Config missing or no enabled repos | Stop |
| Path or venv invalid | Stop or exclude repo |
| Pre-flight failure (dirty tree, no fragments) | Exclude unless human retries |
| Session failure | Record in state; other sessions continue |
| Partial success | Mixed summary; offer `--resume` |

## Integration

| Skill | Role |
| ----- | ---- |
| [`release`](../release/SKILL.md) | Steps 1–9 per repository |
| [`python-virtual-env`](../python-virtual-env/SKILL.md) | Shared venv setup |
| [`config.yaml`](config.yaml) | Source of truth for repos and paths |

## Usage

```bash
/release-orchestrator
/release-orchestrator --repos cisco.ios,cisco.nxos
/release-orchestrator --config ~/my-wave.yaml
/release-orchestrator --dry-run
/release-orchestrator --resume
```
