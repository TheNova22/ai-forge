# Scan Workflow Details

Read this file during Steps 2, 4, and 6 of the parser gap scan pipeline.

---

## Module layout

Resource modules follow this layout (see [config/repos.yaml](../config/repos.yaml) for path templates):

```
plugins/module_utils/network/{platform}/argspec/{module}/
plugins/module_utils/network/{platform}/facts/{module}/{module}.py
plugins/module_utils/network/{platform}/rm_templates/{module}.py
plugins/module_utils/network/{platform}/config/{module}/
plugins/modules/{prefix}{module}.py
tests/unit/modules/network/{platform}/test_{prefix}{module}.py
tests/integration/targets/{prefix}{module}/
```

Enumerate modules:

```bash
find plugins/modules/ -mindepth 1 -maxdepth 1 -type f -name "*.py"
```

Record module name, argspec path, facts path, rm_template path, config path, test paths.

---

## Supplemental grep commands (Step 3)

Run after the mechanical pre-scan script. Do **not** grep only for `shutdown` or `enable`.

```bash
# result that only checks is defined — cannot represent explicit disable
rg '"set": "\{\{ True if \w+ is defined \}\}"' plugins/module_utils/network/*/rm_templates/

# Static setval strings (review adjacent boolean .set or toggle result)
rg -n '"setval": "[^{]' plugins/module_utils/network/*/rm_templates/

# getval blocks missing optional 'no' capture (review negate-handling context)
rg -l '"getval":' plugins/module_utils/network/*/rm_templates/ | while read f; do
  rg -q 'negate|\\sno' "$f" || echo "review negate: $f"
done

# Argspec options added recently without template changes (if git available)
git log --oneline -5 -- plugins/module_utils/network/*/argspec/

# mutually_exclusive in argspec — cross-check template branches
rg -n 'mutually_exclusive' plugins/module_utils/network/*/argspec/

# Parser names in rm_templates vs config registration
rg -o '"name": "[^"]+"' plugins/module_utils/network/*/rm_templates/*.py | sort -u > /tmp/parsers.txt
rg -o "['\"][a-z_]+['\"]" plugins/module_utils/network/*/config/*/*.py | sort -u
```

---

## Step 4 — Argspec vs template crosswalk (primary discovery)

This step finds the **most gaps** across all modules. Run exhaustively for every
resource module — do not skip modules after finding toggle issues.

For each resource module, build a crosswalk:

1. **Parse argspec tree** — read `argspec/{module}/{module}.py` (or nested files).
   Extract every leaf parameter path (e.g. `neighbors.shutdown.set`,
   `max_metric.router_lsa.on_startup.wait_for_bgp`).

2. **Extract parser comparison paths** — from `rm_templates/{module}.py`, for each
   parser entry collect:
   - `"name": "..."` (always)
   - `"compval": "..."` (when present — overrides name for diff)
   - Effective comparison path = `compval` or `name`

3. **Cross-reference config registration** — read `config/{module}/{module}.py`
   and note which parser lists are passed to `compare()`. A parser not registered
   here never participates in command generation even if defined in rm_templates.

4. **Diff:**
   - Argspec leaf with no parser whose comparison path covers it → **coverage gap**
   - Argspec has `parent.set` (bool) but comparison path is `parent` only → **boolean-set mismatch**
   - Comparison path exists but argspec leaf absent → stale parser (note separately)
   - Parser exists with `getval`/`result` but no `setval` and state requires generate → **generate gap**

5. **Check types** — for each shared path, compare argspec `type`/`choices` against
   what getval captures and setval generates.

**Do not** flag absent `compval` as a gap. Flag missing or misaligned parser
`name`/`compval` relative to argspec.

Document file paths and line numbers for every mismatch.

---

## Step 6 — Test coverage gap check

For each module with confirmed or suspected gaps, crosswalk **argspec leaf paths**
against unit and integration tests:

```bash
# Unit tests exercising disable / negate paths
rg -l 'set:\s*false|"set":\s*False' tests/unit/modules/network/

# Integration idempotency assertions (second-run changed: false)
rg 'changed.*false|changed\]\s*==\s*false' tests/integration/targets/

# Negate CLI in integration command assertions
rg '"no |\'no ' tests/integration/targets/

# Per-module: do test task vars mention each high-risk argspec path?
rg -n '<argspec_leaf_or_parent>' tests/unit/modules/network/<platform>/test_<module>.py
rg -n '<argspec_leaf_or_parent>' tests/integration/targets/<module>/
```

Flag any argspec leaf (boolean `.set`, new scalar, list merge key) with no test
coverage. Reference the test file path and note what's missing.

---

## Analysis checklists

### Argspec leaf coverage (every module)

For each argspec leaf path (scalar, struct field, or `*.set` bool):

- [ ] A parser comparison path (`compval` or `name`) matches the leaf or valid parent
- [ ] Parser has `getval` if gather/parse is required; `setval` if configure is required
- [ ] Parser is registered in config class `self.parsers` (or equivalent list)
- [ ] Unit or integration test references the parameter path
- [ ] EXAMPLES block uses the same dotted path as the parser

### Scalar and struct parsers (name-only, no compval)

When a module has zero or few `compval` entries, that is **normal**. For these:

- Match argspec leaves to parser `name` (dot paths like `bgp.cluster_id`, `receive_buffer_size`)
- Verify `getval`/`setval`/`result` round-trip the scalar or struct
- Flag leaves with no matching parser name — common coverage gap
- Do not require adding `compval` unless comparison granularity is wrong

### Boolean toggle checklist (one pattern family)

When argspec defines `option.set: bool` (any parent key — not only shutdown/enable), verify ALL of:

- [ ] Parser comparison path (`compval` or `name`) is `option.set`, not `option`
- [ ] `getval` captures optional `no` prefix
- [ ] `result` distinguishes True, False, and None/absent
- [ ] `setval` or template engine emits correct negate CLI
- [ ] Parser is registered in config class `self.parsers`
- [ ] Unit test with pre-existing enabled state + `set: false`
- [ ] Integration test asserts negate CLI (`no …`) and idempotent re-run

### Type and exclusivity checklist

When argspec defines `type`, `choices`, or `mutually_exclusive`:

- [ ] getval capture group types match argspec (`int`, `str`, bool keywords)
- [ ] setval generates the same CLI form the device returns
- [ ] Conflicting suboptions are not independently templated without validation

### New argspec option checklist

When argspec adds options recently (check git log if available):

- [ ] Matching rm_template entry exists
- [ ] getval regex matches actual device output format
- [ ] rendered/gathered/parsed integration tests cover the option
- [ ] Module EXAMPLES block matches working parser paths

### Cross-collection sweep

After scanning one collection, note **pattern families** that likely repeat elsewhere:

- Argspec leaves without template coverage (new options often land in argspec first)
- Boolean `.set` comparison at parent instead of `parent.set` (any toggle dict)
- `mutually_exclusive` groups with independent parsers
- getval without optional `no` on negate-capable CLI

Apply the same crosswalk to sibling collections — do not limit the sweep to
shutdown/enable keywords.

---

## Example invocations

**User:** "Scan parser gaps across network collections"

→ Full scan mode. Clone/read all four repos, run pipeline, deliver table + JSON.

**User:** "Check iosxr_bgp_global for parser gaps"

→ Targeted mode. Deep-dive single module, exhaustive crosswalk.

**User:** "Find boolean toggle issues like PR 623"

→ Pattern 1–3 deep dive across all modules (any `*.set` parent, not only shutdown).

**User:** "Check for missing parsers / coverage gaps"

→ Emphasize Step 4 crosswalk; report uncovered argspec leaves and unregistered parsers.
