#!/usr/bin/env python3
"""Mechanical pre-scan for common parser gap signals in network resource modules.

This script performs fast, repo-local pattern matching across the full gap
catalog (coverage, boolean toggles, negate capture, generate/parse symmetry,
stale parsers, and more). It produces candidate findings for agent review —
not definitive gap reports.

Usage:
  python scripts/scan_mechanical_signals.py /path/to/cisco.iosxr
  python scripts/scan_mechanical_signals.py /path/to/cisco.iosxr --json

Requires: local clone of the collection repository.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


SET_SUBOPTION_RE = re.compile(
    r"""['"]set['"]\s*:\s*\{[^}]*['"]type['"]\s*:\s*['"]bool['"]""",
    re.DOTALL,
)

PARSER_NAME_RE = re.compile(r"""['"]name['"]\s*:\s*['"]([^'"]+)['"]""")
COMPVAL_RE = re.compile(r"""['"]compval['"]\s*:\s*['"]([^'"]+)['"]""")

STATIC_SETVAL_RE = re.compile(
    r"""['"]setval['"]\s*:\s*['"]([^'"{][^'"]*)['"]\s*,?\s*$""",
    re.MULTILINE,
)

SET_DEFINED_ONLY_RE = re.compile(
    r"""['"]set['"]\s*:\s*['"]\{\{\s*True\s+if\s+\w+\s+is\s+defined\s*\}\}['"]""",
)

GETVAL_BLOCK_RE = re.compile(
    r"""['"]getval['"]\s*:\s*re\.compile\(\s*r?['\"]{3}(.*?)['\"]{3}""",
    re.DOTALL,
)

VALID_COMP_PATH_RE = re.compile(r"^[\w][\w.]*$")

PARSER_BLOCK_RE = re.compile(
    r"""\{\s*['"]name['"]\s*:\s*['"]([^'"]+)['"]""",
    re.DOTALL,
)

# Argspec metadata keys — not CLI parameter paths
ARGS_META_KEYS = frozenset(
    {
        "type",
        "elements",
        "choices",
        "required",
        "default",
        "description",
        "options",
        "suboptions",
        "mutually_exclusive",
        "aliases",
        "version_added",
        "deprecated",
        "removed_in_version",
        "fallback",
        "contains",
        "no_log",
        "removed_at_date",
        "removed_from_collection",
    }
)


MODULE_LEVEL_KEYS = frozenset({"state", "running_config", "gather_network_resources"})


def find_argspec_files(collection_root: Path, platform: str) -> list[Path]:
    argspec_dir = collection_root / "plugins/module_utils/network" / platform / "argspec"
    if not argspec_dir.is_dir():
        return []
    return sorted(argspec_dir.rglob("*.py"))


def find_rm_template_files(collection_root: Path, platform: str) -> list[Path]:
    tmpl_dir = collection_root / "plugins/module_utils/network" / platform / "rm_templates"
    if not tmpl_dir.is_dir():
        return []
    return sorted(tmpl_dir.rglob("*.py"))


def module_name_from_path(path: Path, prefix: str) -> str:
    stem = path.stem
    if stem.startswith(prefix):
        return stem
    return f"{prefix}{stem}"


def _literal_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _dict_field(d: ast.Dict, field: str) -> ast.AST | None:
    for k, v in zip(d.keys, d.values):
        if _literal_str(k) == field:
            return v
    return None


def walk_argspec_node(
    node: ast.AST | None,
    prefix: str = "",
    *,
    inside_list: bool = False,
) -> list[tuple[str, str, bool]]:
    """Extract (dotted_path, type, inside_list) leaves from argspec dicts."""
    if not isinstance(node, ast.Dict):
        return []

    leaves: list[tuple[str, str, bool]] = []
    elements = _literal_str(_dict_field(node, "elements"))
    in_list = inside_list or elements == "dict"

    options = _dict_field(node, "options") or _dict_field(node, "suboptions")
    if options and isinstance(options, ast.Dict):
        for k, v in zip(options.keys, options.values):
            key = _literal_str(k)
            if not key or key in ARGS_META_KEYS:
                continue
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(v, ast.Dict):
                sub_options = _dict_field(v, "options") or _dict_field(v, "suboptions")
                sub_type = _literal_str(_dict_field(v, "type"))
                if sub_options:
                    leaves.extend(walk_argspec_node(v, path, inside_list=in_list))
                elif sub_type:
                    leaves.append((path, sub_type, in_list))
    elif not prefix:
        for k, v in zip(node.keys, node.values):
            key = _literal_str(k)
            if not key or key in ARGS_META_KEYS:
                continue
            if isinstance(v, ast.Dict):
                leaves.extend(walk_argspec_node(v, key, inside_list=False))
    else:
        typ = _literal_str(_dict_field(node, "type"))
        if typ:
            leaves.append((prefix, typ, in_list))
    return leaves


def extract_argspec_leaves(argspec_path: Path) -> list[tuple[str, str, bool]]:
    """Parse argspec Python file and return leaf parameter paths with types."""
    text = argspec_path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _extract_argspec_leaves_regex(text)

    leaves: list[tuple[str, str, bool]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in (
                    "argument_spec",
                    "spec",
                    "options",
                ):
                    leaves.extend(walk_argspec_node(node.value))
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if not isinstance(item, ast.Assign):
                    continue
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "argument_spec":
                        leaves.extend(walk_argspec_node(item.value))
    if leaves:
        return _dedupe_leaves(leaves)
    return [(p, t, False) for p, t in _extract_argspec_leaves_regex(text)]


def _dedupe_leaves(leaves: list[tuple[str, str, bool]]) -> list[tuple[str, str, bool]]:
    seen: set[str] = set()
    out: list[tuple[str, str, bool]] = []
    for path, typ, in_list in leaves:
        if path not in seen:
            seen.add(path)
            out.append((path, typ, in_list))
    return out


def _extract_argspec_leaves_regex(text: str) -> list[tuple[str, str]]:
    """Fallback when AST parse fails — shallow leaf detection."""
    leaves: list[tuple[str, str]] = []
    for match in re.finditer(
        r"""['"](\w+)['"]\s*:\s*\{[^{}]*['"]type['"]\s*:\s*['"](\w+)['"]""",
        text,
    ):
        leaves.append((match.group(1), match.group(2)))
    return leaves


def config_relative_path(path: str) -> str:
    return path[7:] if path.startswith("config.") else path


def extract_parser_comparison_paths(template_text: str) -> dict[str, str]:
    """Map parser name -> effective comparison path (compval if set, else name)."""
    paths: dict[str, str] = {}
    for match in PARSER_NAME_RE.finditer(template_text):
        name = match.group(1)
        chunk = template_text[match.start() : match.start() + 4000]
        compval_match = COMPVAL_RE.search(chunk)
        paths[name] = compval_match.group(1) if compval_match else name
    return paths


def is_valid_comparison_path(path: str) -> bool:
    """Filter Jinja/dynamic parser names from path-based heuristics."""
    if "{{" in path or "}}" in path or "{%" in path:
        return False
    return bool(VALID_COMP_PATH_RE.match(path))


def path_is_covered(leaf: str, comparison_paths: set[str]) -> bool:
    """True when a comparison path matches the leaf or is an intentional parent."""
    if leaf in comparison_paths:
        return True
    return any(leaf.startswith(f"{cp}.") for cp in comparison_paths)


def scan_argspec_set_comparison_path_mismatch(
    argspec_path: Path,
    template_path: Path | None,
    module: str,
    repo: str,
) -> list[dict]:
    findings: list[dict] = []
    text = argspec_path.read_text(encoding="utf-8", errors="replace")

    if not SET_SUBOPTION_RE.search(text):
        return findings

    comparison_paths: set[str] = set()
    parser_by_path: dict[str, str] = {}
    if template_path and template_path.is_file():
        template_text = template_path.read_text(encoding="utf-8", errors="replace")
        for parser_name, path in extract_parser_comparison_paths(template_text).items():
            comparison_paths.add(path)
            parser_by_path[path] = parser_name

    parent_keys = re.findall(
        r"""['"](\w+)['"]\s*:\s*\{[^}]*['"]set['"]\s*:\s*\{""",
        text,
        re.DOTALL,
    )

    for parent in set(parent_keys):
        dotted = f"{parent}.set"
        if parent in comparison_paths and dotted not in comparison_paths:
            parser_name = parser_by_path.get(parent, parent)
            tmpl_line = 1
            if template_path and template_path.is_file():
                tmpl_line = _line_number(
                    template_path.read_text(encoding="utf-8", errors="replace"),
                    f'"name": "{parser_name}"',
                )
            findings.append(
                _finding(
                    repo,
                    module,
                    dotted,
                    template_path,
                    tmpl_line,
                    (
                        f"Argspec defines '{dotted}' (bool) but parser '{parser_name}' "
                        f"compares at '{parent}' — likely cannot detect set:false transitions"
                    ),
                    (
                        f"Set comparison path to '{dotted}' (compval or dot-namespaced name); "
                        "add negate-aware getval/result"
                    ),
                    "boolean-set-comparison-path-mismatch",
                    "medium",
                )
            )
    return findings


def scan_argspec_coverage_gaps(
    argspec_path: Path,
    template_path: Path | None,
    module: str,
    repo: str,
) -> list[dict]:
    """Argspec leaves with no parser comparison path (Pattern 4)."""
    if not template_path or not template_path.is_file():
        return []

    leaves = extract_argspec_leaves(argspec_path)
    if not leaves:
        return []

    template_text = template_path.read_text(encoding="utf-8", errors="replace")
    comparison_paths = set(extract_parser_comparison_paths(template_text).values())
    findings: list[dict] = []

    for path, typ, inside_list in leaves:
        rel_path = config_relative_path(path)
        if path in MODULE_LEVEL_KEYS or rel_path in MODULE_LEVEL_KEYS:
            continue
        if not path.startswith("config.") and path != "config":
            continue
        if inside_list:
            continue
        if rel_path.count(".") > 3:
            continue
        if path_is_covered(rel_path, comparison_paths):
            continue
        if rel_path.replace(".", "_") in template_text or rel_path in template_text:
            continue

        line = _line_number(argspec_path.read_text(encoding="utf-8", errors="replace"), f'"{rel_path.split(".")[-1]}"')
        findings.append(
            _finding(
                repo,
                module,
                rel_path,
                argspec_path,
                line,
                (
                    f"Argspec documents '{rel_path}' ({typ}) but no parser comparison path "
                    f"(name/compval) covers it — parameter may be a silent no-op"
                ),
                "Add rm_template parser with matching name/compval; register in config class",
                "argspec-template-coverage-gap",
                "low",
            )
        )
    return findings


def scan_stale_parser_paths(
    argspec_path: Path,
    template_path: Path,
    module: str,
    repo: str,
) -> list[dict]:
    """Parser comparison paths with no corresponding argspec leaf (Pattern 8)."""
    argspec_text = argspec_path.read_text(encoding="utf-8", errors="replace")
    leaves = {config_relative_path(p) for p, _, _ in extract_argspec_leaves(argspec_path)}
    template_text = template_path.read_text(encoding="utf-8", errors="replace")
    findings: list[dict] = []

    for parser_name, comp_path in extract_parser_comparison_paths(template_text).items():
        if not is_valid_comparison_path(comp_path):
            continue
        if comp_path in leaves or any(leaf.endswith(f".{comp_path}") for leaf in leaves):
            continue
        if any(leaf.startswith(f"{comp_path}.") for leaf in leaves):
            continue
        # Dotted parser names often mirror argspec — check last segment
        last_seg = comp_path.split(".")[-1]
        if f'"{last_seg}"' in argspec_text or f"'{last_seg}'" in argspec_text:
            continue

        line = _line_number(template_text, f'"name": "{parser_name}"')
        findings.append(
            _finding(
                repo,
                module,
                comp_path,
                template_path,
                line,
                (
                    f"Parser '{parser_name}' compares at '{comp_path}' but argspec has "
                    "no matching leaf — possible stale or misnamed parser"
                ),
                "Align parser name/compval with current argspec or remove dead parser",
                "stale-parser-path",
                "low",
            )
        )
    return findings


def scan_template_static_setval(
    template_path: Path,
    module: str,
    repo: str,
) -> list[dict]:
    findings: list[dict] = []
    text = template_path.read_text(encoding="utf-8", errors="replace")

    for match in STATIC_SETVAL_RE.finditer(text):
        setval = match.group(1)
        if setval in ("", " "):
            continue
        line = text[: match.start()].count("\n") + 1
        window = text[max(0, match.start() - 800) : match.end() + 800]
        if '"set"' in window and SET_DEFINED_ONLY_RE.search(window):
            findings.append(
                _finding(
                    repo,
                    module,
                    "(boolean .set toggle)",
                    template_path,
                    line,
                    (
                        f"Static setval '{setval}' adjacent to .set result that only "
                        "checks 'is defined' — negate/disable path may be missing"
                    ),
                    "Use conditional setval or comparison path parent.set with negate getval",
                    "static-setval-toggle",
                    "medium",
                )
            )
    return findings


def scan_getval_missing_negate(
    template_path: Path,
    module: str,
    repo: str,
) -> list[dict]:
    findings: list[dict] = []
    text = template_path.read_text(encoding="utf-8", errors="replace")

    for match in GETVAL_BLOCK_RE.finditer(text):
        regex_body = match.group(1)
        line = text[: match.start()].count("\n") + 1
        context_start = max(0, match.start() - 400)
        context_end = min(len(text), match.end() + 1200)
        context = text[context_start:context_end]

        has_negate_handling = (
            "False if" in context
            or "set: false" in context.lower()
            or SET_DEFINED_ONLY_RE.search(context)
            or ".set" in context
        )
        has_negate_group = "negate" in regex_body or r"\sno" in regex_body

        if has_negate_handling and not has_negate_group:
            findings.append(
                _finding(
                    repo,
                    module,
                    "(getval block)",
                    template_path,
                    line,
                    "getval regex lacks optional 'no' capture but template handles negate/disable",
                    "Add (?P<negate>\\sno)? before command keyword in getval",
                    "missing-negate-getval",
                    "high",
                )
            )
    return findings


def scan_getval_without_setval(
    template_path: Path,
    module: str,
    repo: str,
) -> list[dict]:
    """Parsers that parse config but cannot generate commands (Pattern 4 generate gap)."""
    findings: list[dict] = []
    text = template_path.read_text(encoding="utf-8", errors="replace")

    for match in PARSER_BLOCK_RE.finditer(text):
        parser_name = match.group(1)
        block_end = text.find("},", match.start())
        if block_end < 0:
            block_end = min(len(text), match.start() + 3000)
        block = text[match.start() : block_end]

        has_getval = '"getval"' in block or "'getval'" in block
        has_setval = '"setval"' in block or "'setval'" in block
        if has_getval and not has_setval:
            line = text[: match.start()].count("\n") + 1
            findings.append(
                _finding(
                    repo,
                    module,
                    parser_name,
                    template_path,
                    line,
                    (
                        f"Parser '{parser_name}' has getval but no setval — "
                        "gather/parse may work but config generation is missing"
                    ),
                    "Add setval or confirm parse-only intent in docs",
                    "getval-without-setval",
                    "low",
                )
            )
    return findings


def scan_result_defined_only(
    template_path: Path,
    module: str,
    repo: str,
) -> list[dict]:
    """result uses 'True if X is defined' without False branch — idempotency risk."""
    findings: list[dict] = []
    text = template_path.read_text(encoding="utf-8", errors="replace")

    for match in SET_DEFINED_ONLY_RE.finditer(text):
        line = text[: match.start()].count("\n") + 1
        window = text[max(0, match.start() - 200) : match.end() + 200]
        if "False if" in window:
            continue
        findings.append(
            _finding(
                repo,
                module,
                "(result expression)",
                template_path,
                line,
                (
                    "result sets .set via 'True if X is defined' only — "
                    "cannot distinguish enabled vs explicitly disabled"
                ),
                "Branch result for True, False, and None/absent states",
                "result-defined-only",
                "medium",
            )
        )
    return findings


def _finding(
    repo: str,
    module: str,
    parameter: str,
    location_path: Path | None,
    line: int,
    issue: str,
    potential_fix: str,
    pattern: str,
    confidence: str,
) -> dict:
    loc = f"{location_path}:{line}" if location_path else ""
    return {
        "repo": repo,
        "module": module,
        "parameter": parameter,
        "location": loc,
        "issue": issue,
        "potential_fix": potential_fix,
        "pattern": pattern,
        "confidence": confidence,
    }


def _line_number(text: str, needle: str) -> int:
    idx = text.find(needle)
    if idx < 0:
        return 1
    return text[:idx].count("\n") + 1


def infer_platform(collection_root: Path) -> str | None:
    net_dir = collection_root / "plugins/module_utils/network"
    if not net_dir.is_dir():
        return None
    children = [p.name for p in net_dir.iterdir() if p.is_dir()]
    return children[0] if len(children) == 1 else None


def infer_prefix(platform: str) -> str:
    return f"{platform}_"


def scan_collection(collection_root: Path, repo: str | None = None) -> list[dict]:
    collection_root = collection_root.resolve()
    repo_name = repo or collection_root.name
    platform = infer_platform(collection_root)
    if not platform:
        print(f"warning: could not infer platform under {collection_root}", file=sys.stderr)
        return []

    prefix = infer_prefix(platform)
    argspec_files = find_argspec_files(collection_root, platform)
    template_files = find_rm_template_files(collection_root, platform)

    template_by_stem = {p.stem: p for p in template_files}
    all_findings: list[dict] = []

    for argspec_path in argspec_files:
        stem = argspec_path.stem
        module = module_name_from_path(argspec_path, prefix)
        tmpl = template_by_stem.get(stem)
        all_findings.extend(
            scan_argspec_set_comparison_path_mismatch(argspec_path, tmpl, module, repo_name)
        )
        all_findings.extend(scan_argspec_coverage_gaps(argspec_path, tmpl, module, repo_name))
        if tmpl:
            all_findings.extend(scan_stale_parser_paths(argspec_path, tmpl, module, repo_name))

    for template_path in template_files:
        module = module_name_from_path(template_path, prefix)
        all_findings.extend(scan_template_static_setval(template_path, module, repo_name))
        all_findings.extend(scan_getval_missing_negate(template_path, module, repo_name))
        all_findings.extend(scan_getval_without_setval(template_path, module, repo_name))
        all_findings.extend(scan_result_defined_only(template_path, module, repo_name))

    return all_findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection_root", type=Path, help="Path to collection repo clone")
    parser.add_argument("--repo", help="Repo short name override (e.g. cisco.iosxr)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of table")
    args = parser.parse_args()

    if not args.collection_root.is_dir():
        print(f"error: not a directory: {args.collection_root}", file=sys.stderr)
        return 1

    findings = scan_collection(args.collection_root, args.repo)

    if args.json:
        print(json.dumps(findings, indent=2))
        return 0

    if not findings:
        print("No mechanical gap signals found.")
        return 0

    headers = ["Repo", "Module", "Parameter", "Location", "Issue", "Potential Fix", "Confidence"]
    rows = [
        [
            f["repo"],
            f["module"],
            f["parameter"],
            f["location"],
            f["issue"],
            f["potential_fix"],
            f["confidence"],
        ]
        for f in findings
    ]

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], min(len(cell), 60))

    def fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            truncated = cell if len(cell) <= 60 else cell[:57] + "..."
            parts.append(truncated.ljust(widths[i]))
        return " | ".join(parts)

    print(fmt_row(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row(row))

    print(f"\n{len(findings)} candidate signal(s) — requires agent review.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
