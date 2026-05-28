---
doc_type: prompt
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - prompt
  - obsidian
  - vault
---

# CODEX Obsidian Update Prompt

**Use Case:** Sync vault + update notes  
**Complexity:** Low  
**Duration:** 10-20 minutes

---

## Context

Obsidian vault needs update after doc changes.

Repository: `/home/Martin/Dominion`  
Vault: `/home/Martin/Dominion/vault/`

---

## Mission

1. Sync docs to vault
2. Validate links
3. Update Home.md (if needed)
4. Check vault integrity

---

## Workflow

### Step 1: Sync Docs (2 min)

```bash
# Sync all docs
python scripts/vault_sync.py

# Or single file
python scripts/vault_sync.py --file [path/to/file.md]
```

Verify sync:
```bash
# Check synced timestamp
head -20 vault/files/docs/[file].md | grep "synced:"
```

### Step 2: Validate Links (3 min)

```bash
python scripts/dominion_cli.py vault doctor --json
```

Check output:
```json
{
  "ok": true | false,
  "total_notes": 945,
  "broken_links": [],
  "invalid_frontmatter": [],
  "orphan_notes": []
}
```

**If broken links:**
```bash
# List broken links
python scripts/dominion_cli.py vault doctor --json | jq '.broken_links[]'

# Fix options:
# 1. Create missing target note
# 2. Update link to correct target
# 3. Remove link if no longer relevant
```

### Step 3: Update Home.md (if needed) (5 min)

**When to update:**
- New major doc added
- New section/folder created
- Navigation structure changed

```markdown
# vault/Home.md additions

## New Section

### [Category]
- [[New Doc]] — Brief description
- [[Another Doc]] — Brief description
```

### Step 4: Check Orphan Notes (3 min)

```bash
# List orphan notes (not linked from anywhere)
python scripts/dominion_cli.py vault doctor --json | jq '.orphan_notes[]'
```

**Fix orphans:**
- Add link from Home.md or relevant hub note
- Or mark as intentional orphan (add `orphan: true` to frontmatter)

### Step 5: Validate Symbol Notes (if applicable) (5 min)

```bash
# Count symbol notes
find vault/symbols/ -name "*.md" | wc -l

# Check structure
ls vault/symbols/[module]/
```

**Symbol note checklist:**
- [ ] Frontmatter complete (symbol, type, file, line)
- [ ] Links to related symbols
- [ ] Links to docs
- [ ] Usage example included

### Step 6: Test Graph View (optional) (2 min)

If Obsidian open:
1. Open vault in Obsidian
2. Open graph view (Ctrl+G)
3. Check:
   - New notes visible
   - Links render correctly
   - Color groups working (tags)
   - No isolated clusters (unless expected)

---

## Validation

Vault updated when:
- [ ] All docs synced (check `synced:` timestamp)
- [ ] No broken links (or documented exceptions)
- [ ] Orphan count reasonable (<50)
- [ ] Home.md includes new major docs
- [ ] Graph view renders correctly (if checked)

---

## Output

Brief confirmation:
```
Vault updated:
- Synced: XX files
- Broken links: XX (down from YY)
- Orphan notes: XX
- New symbol notes: XX
- Validation: PASS
```

---

## Common Issues

**Issue: Sync fails**
```bash
# Check permissions
ls -la vault/files/docs/

# Check disk space
df -h

# Check for locked files
lsof | grep vault
```

**Issue: Many broken links**
- Template examples (expected, ignore)
- Real missing targets (create or fix links)
- Case sensitivity (rename target to match link)

**Issue: Symbol notes missing**
- Check vault/symbols/ structure
- Verify frontmatter correct
- Check file path matches `file:` field

---

## Automation

**Auto-sync enabled (post-commit hook):**
```bash
# Check hook
cat .git/hooks/post-commit

# Should contain:
# python scripts/vault_sync.py --quiet
```

**If not enabled:**
```bash
# See [[CODEX_HEALTH_CHECK_PROMPT]] Task 3
cp docs/git-hooks/post-commit .git/hooks/
chmod +x .git/hooks/post-commit
```

---

## Related Prompts

- [[CODEX_DOC_UPDATE_PROMPT]] — Update docs then sync vault
- [[CODEX_RAGD_UPDATE_PROMPT]] — Rebuild RAGD after vault update

---

## Related Docs

- [[OBSIDIAN_VAULT_MANIFEST]] — Vault structure + conventions
- [[Vault Structure]] — Technical details

---

## Retrieval Hints

- "sync vault"
- "obsidian update"
- "vault sync"
- "broken links"
