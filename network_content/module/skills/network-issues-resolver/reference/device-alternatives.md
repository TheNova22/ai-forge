# Device alternatives and `--skip-device`

How to resolve confirmed gaps **without** a lab device, and what counts as a
mock when hardware is unavailable.

Use when the user passes **`--skip-device`**, or says “code-only”, “no lab”,
“offline”, or “skip device steps”.

Full pipeline and flags: [../SKILL.md](../SKILL.md).

---

## When to use `--skip-device`

**Good fit:**

- Parser / setval / getval / registration gaps proven by unit fixtures
- Pattern 11 (stale EXAMPLES) verified by sanity + corrected example vars
- Contributors without lab access who can still land unit + sanity evidence

**Do not use `--skip-device` when:**

- Pattern 10 (`replaced` / `overridden`) residue on device cannot be shown in units
- Negate / CLI semantics need live device confirmation beyond fixtures
- The user explicitly wants lab before/after for the PR

If unsure, prefer the default device path (steps 3–4, 6, 10–11).

---

## Pipeline under `--skip-device`

| Steps | Behavior |
|-------|----------|
| 1 | Branch locally (unless `--dry-run` — stay on current branch) |
| 2 | Study source + pattern; skip playbook-dir siblings if no playbook dir |
| 3–4 | **N/A** — do not write or run device repro. Record expected broken behavior from code (wrong/missing `commands`, path, etc.) |
| 5 | Implement fix |
| 6 | **N/A** — gate before unit tests = fix applied + rationale. Before/after = unit expectations |
| 7–9 | Changelog → unit + sanity tox → integration YAML updates (unchanged) |
| 10–11 | **N/A** |
| 12 | Ask about draft PR; use [unit-only snippets](upstream-pr.md#unit-only-evidence-skip-device) |

Mark skipped steps in the checklist as N/A (`[-]`). Do not invent a lab or invent playbook runs.

### Entry gates

| Gate | Required? |
|------|-----------|
| Validated report + one issue | Yes |
| Collection path | Yes |
| Python venv | Yes (tox) |
| Playbook directory | **No** |

---

## Mock / no-device alternatives (preference order)

### 1. Unit fixtures (primary mock)

Supported “mock device” for code-only fixes.

`tests/unit/modules/network/<platform>/test_<module>.py`:

- Mocked running-config fixtures
- `set_module_args` for the want config / state
- Assert expected `commands` (or `changed`)

Read an existing case for the same state/parameter family; update in place.
See [resolution-details.md — Unit cases](resolution-details.md#unit-cases).

### 2. `state: rendered` / `state: parsed`

When the module supports these states, they can validate CLI generation or parse
round-trip **without** `network_cli` to hardware (often localhost / no device
connection). Useful for setval / template checks.

Not a substitute for full `merged` / `replaced` lab proof. Optional supplement
to unit fixtures — not required under `--skip-device`.

### 3. Real lab / sim playbooks (default path)

Without `--skip-device`, use reproduction and integration sim playbooks against
a real device (or whatever inventory the playbook dir already targets).

See [resolution-details.md — Reproduction playbook](resolution-details.md#reproduction-playbook)
and [Integration simulation](resolution-details.md#integration-simulation-playbook).

### 4. External mock platforms (optional)

If the user’s playbook directory already points at CISSHGO, Molecule, or similar
mock-device inventory, those hosts may be used in the **default** (non-skip)
path as the “device”. Do **not** require installing new mock infra for
`--skip-device`. A future `network-integration-tests` skill may cover scaffolding;
it is not required here.

---

## Evidence without a device

| Artifact | Source under `--skip-device` |
|----------|----------------------------|
| Before (broken) | Pre-fix expected `commands` / failure from code analysis, or failing unit expectation |
| After (fixed) | Updated unit assertions + tox unit pass output |
| Integration | Case YAML updated in source; not run locally via tox |
| PR Testing Instructions | State: “Validated via unit + sanity only; no device run” |

Details: [upstream-pr.md](upstream-pr.md#unit-only-evidence-skip-device).
