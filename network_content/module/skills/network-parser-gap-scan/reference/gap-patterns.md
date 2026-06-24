# Parser Gap Patterns

Reference catalog of known parser/template gap types. Each pattern includes
detection signals and real-world examples from network collection history.

**Read this entire catalog during every scan.** Do not anchor on a single gap
family (e.g. boolean `shutdown.set` toggles). Coverage gaps, type mismatches,
unregistered parsers, and idempotency issues are equally common and often more
severe than toggle bugs.

---

## Gap families at a glance

| Family | Patterns | Typical symptom |
|--------|----------|-----------------|
| **Coverage** | 4, 8, generate gaps | Documented option accepted but never parsed or generated |
| **Comparison granularity** | 1 | `set: false` or disable transitions not detected |
| **Negate / CLI symmetry** | 2, 3 | `no …` not parsed or not generated |
| **Type / schema alignment** | 5, 7 | Wrong type, wrong keyword, conflicting suboptions |
| **Round-trip / idempotency** | 6 | Second run reports `changed: true` |
| **Test hygiene** | 9 | Failure mode never exercised in CI |

---

## Parser comparison paths (read first)

Each rm_template entry is a **parser** with these roles:

| Key | Role |
|---|---|
| `name` | Parser identifier; **default comparison path** for want/have diff |
| `getval` | Regex to parse device config into facts |
| `setval` | Jinja/function to generate CLI from desired state |
| `result` | Facts tree populated from parsed data — **not** the comparison path |
| `compval` | **Optional** override when comparison granularity differs from `name` |

**Important:** Most parsers do **not** have `compval`. In `cisco.iosxr`, modules
like `logging_global`, `snmp_server`, `route_maps`, and `ntp_global` use parser
`name` alone (often zero `compval` entries). Direct-value options such as
`receive_buffer_size` compare by parser name — that is normal, not a gap.

Use `compval` only when parsers are split into namespace-style pieces and the
comparison key must differ from `name`. See the
[Resource Module dev guide](https://github.com/ansible-network/networking-docs/blob/main/rm_dev_guide.md).

**Comparison path rule:** `compval` if present, else parser `name` (supports dot
notation, e.g. `use.neighbor_group`, `bgp.cluster_id`, `max_metric.router_lsa.on_startup`).

When crosswalking argspec → templates, collect **both** parser names and
compvals. Do not treat absent `compval` as missing coverage.

---

## Pattern 1 — Boolean `.set` comparison-path mismatch

**Symptom:** Argspec documents `parameter.set: true|false` but the parser
compares at `parameter` (parent dict) instead of `parameter.set`.

**Why it breaks:** RMEngineBase diff runs at the wrong granularity. It cannot
detect a `True → False` transition, so `set: false` does not emit the negate
CLI (`no …`).

**Applies to:** Any `*.set` boolean suboption — `shutdown`, `enable`, `passive`,
`logging`, `bfd`, etc. Shutdown is a frequent instance, not the only one.

**Detection:**
- Argspec has a dict suboption with only `set:` (bool) under a parent key
- Parser comparison path (compval or name) resolves to the parent key, not `parent.set`
- `result` expression sets `"set": "{{ True if X is defined }}"` with no False branch

**Examples:**
- [cisco.iosxr PR #623](https://github.com/ansible-collections/cisco.iosxr/pull/623) —
  `neighbors.shutdown.set` vs parser comparing at `shutdown`
- Same class of bug on `enable.set`, `passive.set`, or any toggle dict in interface/BGP/OSPF modules

**Potential fix:** Set comparison path to `parameter.set` (via `compval` or
dot-namespaced `name`), update `getval` to capture `no`, and branch
`result`/`setval` for True, False, None.

---

## Pattern 2 — Missing negate capture in getval regex

**Symptom:** Device CLI supports `no <command>` but the template `getval` regex
does not include a `(?P<negate>\sno)?` group before the command keyword.

**Why it breaks:** Parsed running config always reports the feature as present
(enabled) even when the device shows `no …`. Idempotency and state reconciliation fail.

**Detection:**
- Argspec or docs mention enable/disable, `set: false`, or negate semantics
- `getval` regex matches the affirmative command only
- No `negate` or `no` capture group in the regex

**Examples:**
- PR #623 — `getval` matched `shutdown` but not `no shutdown`
- Incomplete `logging` / `snmp-server` / `feature` toggles where device uses `no feature …`

**Potential fix:** Add optional negate group to `getval`; branch `result` on it.

---

## Pattern 3 — Static setval for toggle parameters

**Symptom:** Template `setval` is a fixed CLI string with no Jinja conditional
for the disabled/negated state.

**Why it breaks:** When desired state is off/false, the module still emits the
affirmative command.

**Detection:**
- `setval` is a plain string, not a Jinja expression
- Argspec parameter is boolean or has `set:` suboption
- No companion template entry for the negate case

**Examples:**
- Static `"shutdown"` or `"enable"` setvals (common but not exclusive)
- Fixed `"passive"` / `"bfd"` / feature keyword strings without `no` branch

**Potential fix:** Use conditional Jinja in `setval` or rely on compval + negate-aware result.

---

## Pattern 4 — Argspec/template coverage gap

**Symptom:** Parameter appears in argspec and module documentation but has no
parser that covers it (no matching parser `name` or `compval` path, and no
parser whose `getval`/`result` populates that argspec leaf).

**Why it breaks:** Module accepts the parameter at validation time but never
generates or parses the CLI — silent no-op or wrong `changed` result.

**Detection (primary scan focus):**
- Walk argspec nested keys; match each leaf to a parser comparison path (`name`
  or `compval`) and verify `getval`/`setval`/`result` exist
- Check config class `self.parsers` lists — parser must be registered to participate in diff
- Check for recently added argspec options without template additions
- Changelog or docs mention feature; rm_templates unchanged
- Parser has `getval` but no `setval` when generate path is required

**Examples:**
- [cisco.iosxr PR #615](https://github.com/ansible-collections/cisco.iosxr/pull/615) —
  `max-metric router-lsa` suboptions (`external_lsa`, `summary_lsa`, `on_startup`,
  `include_stub`) incomplete in templates
- New scalar options (`cluster_id`, timers, ACL names) added to argspec without rm_template entries
- Parser defined in rm_templates but missing from config `self.parsers`

**Potential fix:** Add template entries with correct getval/setval/compval/result;
register parsers in config class.

---

## Pattern 5 — Argspec type vs CLI semantics mismatch

**Symptom:** Argspec declares a type that does not match device CLI behavior.

**Why it breaks:** Users pass values the parser cannot round-trip; merged state
generates wrong commands.

**Detection:**
- Compare argspec `type`/`choices` against template getval capture groups
- Look for renamed/deprecated parameters still in argspec
- Docs describe mutual exclusivity not enforced in templates
- Integer argspec for a keyword-only CLI (or vice versa)

**Examples:**
- PR #615 — `wait_for_bgp_asn` (int) corrected to `wait_for_bgp` (bool) for IOS-XR
- `max_metric_value` (int) vs `set` (bool) representing the same CLI knob
- `choices` list not matching device enum strings in getval/setval

**Documentation Reference:** Utilize the [cisco documentation](https://www.cisco.com/c/en/us/support/ios-nx-os-software/index.html) to better understand the CLI semantics.

**Potential fix:** Align argspec type/choices with CLI; update getval/setval accordingly.

---

## Pattern 6 — Idempotency gap for merged/replaced/overridden

**Symptom:** First application works but re-running with the same desired state
reports `changed: true` or emits spurious commands.

**Why it breaks:** Parsed state from device does not match normalized desired
state — often caused by Patterns 1–3 combined, but also by value normalization
(string vs int, list ordering, default omission).

**Detection:**
- Unit tests only cover initial merge, not second-run idempotency
- Integration tests lack `changed: false` after converge step
- Template `result` maps device output to different structure than argspec expects
- Gathered facts use different key names or nesting than want dict

**Examples:**
- PR #615 — max-metric idempotency fixed across merged, replaced, overridden
- List-of-dict parsers where key order or optional fields differ between parse and want

**Potential fix:** Fix parse/generate symmetry; add idempotent re-run tests.

---

## Pattern 7 — Missing mutual exclusivity in parser layer

**Symptom:** Argspec documents mutually exclusive suboptions but templates allow
both to be set independently.

**Why it breaks:** Module sends conflicting CLI; device may reject or apply
unpredictably.

**Detection:**
- Argspec has `mutually_exclusive` or description notes exclusivity
- Templates use independent compval paths with no conflict handling
- No validation in config class before template rendering

**Examples:**
- PR #615 — `max_metric_value` vs `set`, `wait_for_bgp` vs `wait_period`
- Timer value vs keyword-only forms across OSPF/ISIS/BGP modules

**Potential fix:** Enforce in argspec + config validation; single template with branches.

---

## Pattern 8 — Stale or dead config/parser code

**Symptom:** Helper functions or template entries reference removed argspec paths;
copy-paste artifacts from other modules.

**Why it breaks:** Misleading code paths; subtle wrong key building in list/dict conversion.

**Detection:**
- Functions in config classes referencing argspec keys that no longer exist
- `_build_key` or similar helpers with unused/wrong field names
- Parser comparison paths (name/compval) not found in current argspec tree
- Parser names from a different module copied into rm_templates

**Examples:**
- PR #623 — stale `_build_key` in `bgp_global.py` config removed
- Renamed argspec keys with old compval strings left in templates

**Potential fix:** Remove dead code; align config normalization with current argspec.

---

## Pattern 9 — Test coverage blind spots

**Symptom:** Toggle, negate CLI, coverage, or idempotent re-run scenarios untested.

**Why it matters:** Gaps reach production because CI never exercises the failure mode.

**Detection:**
- Compare argspec leaf paths against unit test task vars and integration playbooks
- Search for `set: false`, negate CLI strings (`no ` prefix), and second-run idempotency
- rendered/gathered/parsed states missing examples for new options
- Integration tests assert commands but not `changed: false` on re-apply

**Potential fix:** Add unit test with mocked running config + integration idempotency task
for each high-risk parameter class (toggles, new scalars, list merges).

---

## Scan priority (avoid overfitting)

When triaging findings, weight discovery as follows:

1. **Argspec/template crosswalk (Step 4)** — catches the broadest set of real gaps
2. **Mechanical script output** — all pattern families, not only boolean toggles
3. **Boolean `.set` / negate patterns (1–3)** — high impact but one family among many
4. **Type, exclusivity, idempotency (5–7)** — require reading argspec + device CLI semantics
5. **Tests and stale code (8–9)** — supporting evidence, often lower immediate user impact

Do not stop after finding shutdown/enable issues. Continue the full module crosswalk.
