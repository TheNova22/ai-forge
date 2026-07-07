# Upstream pull request

**After step 11 (device cleanup).** Ask the user:

> “Do you want a **draft** pull request opened against upstream (`ansible-collections/<repo>`)?”

Do **not** commit, push, or open a PR unless the user explicitly says yes. **Always use draft PRs** — never open a ready-for-review PR unless the user explicitly requests it.

---

## Fork remotes (read first)

Collection work uses a **fork** of `ansible-collections/<repo>`. Remotes:

| Remote | Points to | Used for |
|--------|-----------|----------|
| **`upstream`** | `ansible-collections/<repo>` | Sync `main`; PR **base** target |
| **`origin`** | Your fork (`<github-user>/<repo>`) | Push feature branch; PR **head** source |

**Branch lives on `origin` (fork). PR is opened against `upstream` (ansible-collections).**

Verify before step 1 or step 12:

```bash
cd <collection-path>
git remote -v
# origin    git@github.com:<you>/cisco.nxos.git (fetch)
# upstream  git@github.com:ansible-collections/cisco.nxos.git (fetch)
```

If `upstream` is missing:

```bash
git remote add upstream https://github.com/ansible-collections/<repo>.git
git fetch upstream
```

---

## Prerequisites

- Fix complete; unit + sanity tox passed
- Changelog fragment and test updates committed-ready
- **Before/after snippets captured** during repro (step 4) and corrective verify (step 6) — required for PR body

---

## Workflow

```bash
cd <collection-path>

# 0. Confirm remotes (origin = fork, upstream = ansible-collections)
git remote -v

# 1. Read the repo template — structure varies slightly; always use the collection's file
cat .github/PULL_REQUEST_TEMPLATE.md

# 2. Stage only resolver-related files (fix, changelog, tests — not repro playbooks)
git add <paths>
git status

# 3. Commit
git commit -m "$(cat <<'EOF'
Fix <module> <short description>

EOF
)"

# 4. Push branch to YOUR FORK (origin) — not upstream
git push -u origin HEAD

# 5. Open DRAFT PR: base = upstream/main, head = your fork + branch
#    Option A — from fork clone (gh resolves cross-repo PR):
gh pr create \
  --draft \
  --repo ansible-collections/<repo> \
  --base main \
  --head <github-user>:<branch-name> \
  --title "<Title>" \
  --body "$(cat <<'EOF'
<filled template>
EOF
)"

#    Option B — if already on fork remote and gh defaults work:
# gh pr create --draft --base main --head <branch-name> --title "..." --body "..."
```

| Step | Remote / target |
|------|-----------------|
| `git push -u origin HEAD` | Branch on **fork** |
| `gh pr create --draft --repo ansible-collections/<repo>` | **Draft** PR into **upstream** |
| `--head <github-user>:<branch>` | Head ref on **fork** |

Do **not** push directly to `upstream` unless the user explicitly has write access and asks for it.

Return the draft PR URL to the user. Confirm the PR shows as **Draft** on GitHub.

---

## Filling `.github/PULL_REQUEST_TEMPLATE.md`

Read the template from the **target collection** at
`.github/PULL_REQUEST_TEMPLATE.md` and preserve its headings and checkboxes.

Network collections (cisco.ios, cisco.nxos, cisco.iosxr, arista.eos) typically include:

| Section | What to write |
|---------|----------------|
| **Description** | What / why / how — tie to validated report issue and pattern |
| **Type of Change** | Check **Bug fix** (and **Test update** if tests changed) |
| **Component Name** | Module FQCN, e.g. `cisco.nxos.nxos_hsrp_interfaces` |
| **Self-Review Checklist** | Check applicable items |
| **Testing Instructions** | Prerequisites, steps (repro playbook), expected results |
| **Command Output / Logs** | **Mandatory before/after snippets** (see below) |
| **Required Actions** | Check changelog, unit/integration test updates as applicable |

Do not strip template sections — fill or mark N/A. Match tone of merged PRs in that repo.

---

## Before / after snippets (required)

Snippets are the fastest way for reviewers to see the bug. Include **both** in the PR body
under **Command Output / Logs** and/or **Test Results**.

### What to capture

| When | Capture |
|------|---------|
| **Before fix** (step 4) | `ansible-playbook` task result: `changed`, `commands`, errors, malformed CLI |
| **After fix** (step 6) | Corrective repro run: corrected `commands` / `changed` + assert pass |

Use **verbatim** output — trim only unrelated noise, not the failing lines.

### Format in PR body

```markdown
### Before (broken)

\`\`\`
TASK [Expose the bug] ...
ok: [lab-nxos]

TASK [Debug] ...
ok: [lab-nxos] => {
    "result": {
        "changed": false,
        "commands": []
    }
}
\`\`\`

### After (fixed)

\`\`\`
TASK [Expose the bug] ...
changed: [lab-nxos]

TASK [Debug] ...
ok: [lab-nxos] => {
    "result": {
        "changed": true,
        "commands": [
            "interface Vlan218",
            "hsrp 218",
            "no preempt delay reload 20",
            "preempt delay sync 55"
        ]
    }
}
\`\`\`
```

Also paste relevant **unit test** pass output if it adds context:

```markdown
### Unit tests

\`\`\`
tox -e <unit-env> -- tests/unit/modules/network/<platform>/test_<module>.py
  ...
  passed
\`\`\`
```

If reproduction was playbook-only, snippets are still **required** — do not open a PR without them unless the user accepts an exception.

---

## PR title

Concise, module-focused:

```
<module> | <short fix description>
```

Examples:

- `nxos_hsrp_interfaces | Fix preempt replaced state and setval for partial sub-keys`
- `iosxr_bgp_global | Add parser coverage for max_metric router-lsa suboptions`

Match title style of recent merged PRs in the same collection.

---

## Related issue

If the user provides a GitHub issue number, set `Fixes #NNN` in **Related Issue**.
Otherwise leave placeholders or omit.

---

## What not to include in the PR

- Reproduction playbooks from the user's playbook directory (stay local)
- Validator/scanner report artifacts
- Unrelated collection changes
