# Gap Report Template

Use this format for Step 7 output. Save as `parser-gap-report.md` in the working directory.

```markdown
# Network Parser Gap Scan Report

**Scan date:** YYYY-MM-DD
**Scope:** cisco.ios, cisco.nxos, cisco.iosxr, arista.eos (or subset)
**Modules scanned:** N
**Gaps found:** M

| Repo | Module | Parameter | File:Line | Issue | Potential Fix |
|------|--------|-----------|-----------|-------|---------------|
| cisco.iosxr | iosxr_bgp_global | max_metric.router_lsa.on_startup.wait_for_bgp | plugins/.../argspec/bgp_global.py:412 | Argspec documents option but no parser comparison path covers it — silent no-op on configure | Add parser with name/compval `max_metric.router_lsa.on_startup.wait_for_bgp`; register in config |
| cisco.ios | ios_interfaces | interfaces[].enable.set | plugins/.../rm_templates/interfaces.py:88 | Parser compares at `enable` not `enable.set`; static setval — `set: false` may not emit `no enable` | Set comparison path to `enable.set`; conditional setval; negate getval |
| cisco.nxos | nxos_ospf_interfaces | ... | ... | ... | ... |
```

## Column rules

- **Repo** — collection name (`cisco.iosxr`)
- **Module** — full module name (`iosxr_bgp_global`)
- **Parameter** — dotted argspec path (`neighbors.shutdown.set`)
- **File:Line** — repo-relative path with line number
- **Issue** — concise description of the gap and user-visible symptom
- **Potential Fix** — brief direction (not a full implementation)

## Sort order

Sort by severity (high first), then repo, then module.

Mark confidence as `confirmed`, `likely`, or `candidate` when emitting JSON alongside the markdown table.
