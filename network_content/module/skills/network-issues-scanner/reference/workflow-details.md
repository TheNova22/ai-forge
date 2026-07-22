# Scan Workflow Details

Operational procedures for the scanner pipeline: module layout, grep commands,
and test-discovery commands. Domain knowledge (patterns, crosswalk, checklists)
lives in [network-issues-knowledge/](../network-issues-knowledge/README.md).

Read this file during Steps 2, 4, and 6.

Pattern 11 deep check (Step 3): `validate_examples.py` — structural per-task checker; see [scripts/validate_examples.py](../scripts/validate_examples.py).

---

## Module layout

Resource modules follow this layout (see [config/repos.yaml](../config/repos.yaml)):

```
plugins/module_utils/network/{platform}/argspec/{module}/
plugins/module_utils/network/{platform}/facts/{module}/{module}.py
plugins/module_utils/network/{platform}/rm_templates/{module}.py
plugins/module_utils/network/{platform}/config/{module}/
plugins/modules/{prefix}{module}.py   # DOCUMENTATION + EXAMPLES
tests/unit/modules/network/{platform}/test_{prefix}{module}.py
tests/integration/targets/{prefix}{module}/
```

Enumerate modules:

```bash
find plugins/modules/ -mindepth 1 -maxdepth 1 -type f -name "*.py"
```

Record module name, argspec path, module file path (`plugins/modules/`), facts path, rm_template path, config path, test paths.

---

Pattern 11 (stale EXAMPLES): handled by `scan_mechanical_signals.py` (`scan_examples_vs_argspec`). See [patterns.md](../network-issues-knowledge/patterns.md) Pattern 11 for confirm/drop bars.

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

## Step 6 — Test coverage grep commands

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

Checklists: [checklists.md](../network-issues-knowledge/checklists.md).

