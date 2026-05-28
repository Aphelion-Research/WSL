---
doc_type: vault
system: vault
ragd_priority: 7
audience:
  - owner
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - obsidian
  - vault
  - knowledge-graph
---

# Obsidian Vault Manifest

**Purpose:** Structure and conventions for Dominion Obsidian vault.

**Vault Location:** `/home/Martin/Dominion/vault/`

**Status:** 878 notes, 0 broken links (as of 2026-05-19)

---

## Vault Structure

```
vault/
├── Home.md                    # Entry point
├── _index/                    # Auto-generated indexes
│   ├── files-index.md
│   ├── symbols-index.md
│   └── daily-index.md
├── _daily/                    # Daily notes
│   └── YYYY-MM-DD.md
├── _templates/                # Note templates
│   ├── daily-note.md
│   ├── feature-note.md
│   └── decision-note.md
├── files/                     # File snapshots (mirrored repo structure)
│   ├── docs/
│   ├── domdata/
│   ├── data_pipeline/
│   └── ...
├── symbols/                   # Code symbol notes (mirrored repo structure)
│   ├── docs/
│   ├── domdata/
│   ├── data_pipeline/
│   └── ...
└── .obsidian/                 # Obsidian config
    ├── workspace.json
    ├── app.json
    └── plugins/
```

---

## Naming Conventions

**Wiki Links:**
<!-- Examples below are syntax demonstrations, not actual links -->
- `[[File Name]]` — Link to note (spaces OK)
- `[[File Name|Display Text]]` — Link with custom text
- `[[#Heading]]` — Link to heading in current note
- `[[File Name#Heading]]` — Link to heading in other note

**File Names:**
- Use spaces: `Agent README.md`
- Capitalize first letter: `Agent README.md`
- Avoid special chars: No `/:*?"<>|`
- No extension in links: `[[Agent README]]` not `[[Agent README.md]]`

**Folder Names:**
- Leading underscore for system folders: `_index/`, `_daily/`, `_templates/`
- No underscores for content folders: `files/`, `symbols/`

---

## Frontmatter Schema

Every vault note should have:

```yaml
---
created: YYYY-MM-DD HH:MM
modified: YYYY-MM-DD HH:MM
tags:
  - tag1
  - tag2
aliases:
  - Alternate Name 1
  - Alternate Name 2
---
```

**Optional fields:**
```yaml
---
status: active | archived | deprecated
priority: high | medium | low
related:
  - [[Related Note 1]]
  - [[Related Note 2]]
source: path/to/original/file.md
---
```

---

## Tag Taxonomy

### System Tags

- `#system` — System-level notes
- `#architecture` — Architecture docs
- `#ragd` — RAGD-related
- `#agent` — Agent operations
- `#feature` — Feature specs
- `#roadmap` — Planning docs
- `#decision` — ADRs
- `#risk` — Risk/security
- `#backlog` — Work queue items

### Status Tags

- `#active` — Currently relevant
- `#archived` — Historical record
- `#deprecated` — No longer used
- `#draft` — Work in progress

### Priority Tags

- `#p0` — Critical
- `#p1` — High priority
- `#p2` — Medium priority
- `#p3` — Low priority

### Subsystem Tags

- `#domdata` — MT5 data bridge
- `#data-pipeline` — Multi-source fusion
- `#microstructure` — LOB/Exec/TCA/Toxicity
- `#vault` — Obsidian vault
- `#agent-os` — Agent operating system

---

## Link Conventions

### Internal Links

**Good:**
<!-- Examples below show real links to actual vault notes -->
```markdown
See [[Agent README]] for operating manual.
Read [[RAGD Overview]] for RAGD docs.
Check [[Data Pipeline Feature]] for spec.
```

**Bad:**
```markdown
See [Agent README](../docs/AGENT_README.md)  # Don't use relative paths
Read AGENT_README.md  # Not a wiki link
```

### External Links

**For docs/ files:**
```markdown
Source: [docs/AGENT_README.md](file:///home/Martin/Dominion/docs/AGENT_README.md)
```

**For code:**
```markdown
Implementation: [data_pipeline/pipeline.py:123](file:///home/Martin/Dominion/data_pipeline/pipeline.py#L123)
```

---

## Daily Notes

**Location:** `_daily/YYYY-MM-DD.md`

**Template:**
```markdown
---
created: YYYY-MM-DD 00:00
tags:
  - daily
---

# YYYY-MM-DD

## Work Log

- Task 1: description
- Task 2: description

## Decisions

- Decision 1: description, rationale

## Notes

- Note 1
- Note 2

## Links

- [[Related Note 1]]
- [[Related Note 2]]
```

**Automation:**
- Daily note created automatically (if configured)
- Template applied via Obsidian Templates plugin

---

## File Snapshots

**Purpose:** Mirror repo structure for easy navigation.

**Location:** `vault/files/<repo-path>`

**Example:**
- Repo: `/home/Martin/Dominion/docs/AGENT_README.md`
- Vault: `vault/files/docs/AGENT_README.md`

**Update Strategy:**
- Manual: Copy file to vault after significant changes
- Automated: Symlink or sync script (future enhancement)

**Frontmatter:**
```yaml
---
source: /home/Martin/Dominion/docs/AGENT_README.md
synced: YYYY-MM-DD HH:MM
tags:
  - file-snapshot
  - agent
---
```

---

## Symbol Notes

**Purpose:** Index code symbols (classes, functions).

**Location:** `vault/symbols/<repo-path>`

**Example:**
<!-- Template below shows symbol note structure -->
```markdown
---
symbol: KalmanFilter
type: class
file: /home/Martin/Dominion/data_pipeline/fusion/kalman.py
line: 45
tags:
  - symbol
  - data-pipeline
  - kalman
---

# KalmanFilter

**Type:** Class
**File:** `data_pipeline/fusion/kalman.py:45`

## Purpose

6-timescale Kalman filter for multi-source data fusion.

## Key Methods

- `update(measurement)` — Update filter with new measurement
- `predict()` — Predict next state
- `reset()` — Reset filter state

## Related

- [[Data Pipeline Feature]]  (real link)
- [[Kalman Fusion Algorithm]]  (example link, may not exist)
```

---

## Templates

### Feature Note Template

**Location:** `_templates/feature-note.md`

<!-- Template variables like {{date}} and [[File 1]] are placeholders, not actual links -->
```markdown
---
created: {{date}} {{time}}
tags:
  - feature
  - {{tag}}
status: active
---

# {{title}}

## Purpose

{{purpose}}

## Status

- Implementation: {{status}}
- Tests: {{test_status}}
- Docs: {{doc_status}}

## Key Files

- [[File 1]]  (replace with actual filename)
- [[File 2]]  (replace with actual filename)

## Related

- [[Related Feature 1]]  (replace with actual note)
- [[Related Feature 2]]  (replace with actual note)

## Notes

{{notes}}
```

### Decision Note Template

**Location:** `_templates/decision-note.md`

<!-- Template variables like {{date}} and [[ADR {{number}}]] are placeholders, not actual links -->
```markdown
---
created: {{date}} {{time}}
tags:
  - decision
  - adr
status: active
---

# Decision: {{title}}

## Context

{{context}}

## Decision

{{decision}}

## Consequences

**Positive:**
- {{pro_1}}

**Negative:**
- {{con_1}}

## Related

- [[Related Decision 1]]  (replace with actual ADR)
- [[ADR {{number}}]]  (replace with actual ADR number)
```

---

## Graph View Configuration

**Settings** (in `.obsidian/app.json`):
```json
{
  "showInlineTitle": true,
  "showFrontmatter": false,
  "defaultViewMode": "preview",
  "alwaysUpdateLinks": true
}
```

**Graph View Filters:**
- Hide `_index/`, `_templates/` folders
- Show only `#active` and `#p0`, `#p1` tags
- Group by tags: `#system`, `#feature`, `#agent`

**Color Scheme:**
- `#system` — Blue
- `#feature` — Green
- `#agent` — Purple
- `#decision` — Orange
- `#risk` — Red

---

## Plugins (Recommended)

### Core Plugins

- **Daily notes** — Auto-create daily notes
- **Templates** — Insert templates
- **Graph view** — Visualize links
- **Backlinks** — Show incoming links
- **Tag pane** — Browse by tags
- **File explorer** — Navigate folders

### Community Plugins (Optional)

- **Dataview** — Query notes with SQL-like syntax
- **Calendar** — Calendar view of daily notes
- **Advanced Tables** — Better table editing
- **Obsidian Git** — Auto-commit vault changes
- **Mind Map** — Mind map view

---

## Maintenance

### Daily

- [ ] Create daily note
- [ ] Update work log
- [ ] Link related notes

### Weekly

- [ ] Review open notes
- [ ] Archive completed work
- [ ] Check for broken links: `vault doctor`

### Monthly

- [ ] Audit tag usage
- [ ] Clean up duplicates
- [ ] Update templates
- [ ] Sync file snapshots

### Quarterly

- [ ] Review vault structure
- [ ] Archive old notes
- [ ] Update this manifest

---

## Vault Doctor

**Purpose:** Validate vault integrity.

```bash
# Check for broken links
python scripts/dominion_cli.py vault doctor --json

# Expected output
{
  "ok": true,
  "notes_checked": 878,
  "broken_links": 0,
  "stale_links": 0,
  "invalid_frontmatter": 0
}
```

**Common Issues:**

| Issue | Fix |
|---|---|
| Broken `[[link]]` | Update link or create missing note |
| Stale file snapshot | Re-sync from source |
| Missing frontmatter | Add frontmatter to note |
| Duplicate notes | Merge or delete duplicate |

---

## Sync Strategy

**Current:** Manual sync

**Future:** Automated sync

**Manual Sync Steps:**
1. Identify changed docs in `docs/`
2. Copy to `vault/files/docs/`
3. Update frontmatter `synced` date
4. Run vault doctor

**Automated Sync (Future):**
```bash
# Sync all docs/ to vault/files/docs/
python scripts/vault_sync.py --source docs/ --target vault/files/docs/

# Sync specific file
python scripts/vault_sync.py --file docs/AGENT_README.md
```

---

## Search Tips

**Basic Search:**
- Text: Just type in search box
- Tag: `tag:#agent`
- File: `file:README`
- Path: `path:docs/`

**Advanced Search:**
```
# Find agent-related active notes
tag:#agent tag:#active

# Find high-priority features
tag:#feature tag:#p1

# Find recent daily notes
path:_daily/ modified:>2026-05-01
```

**Graph Search:**
- Click node → See connections
- Filter by tags → Focus on subsystem
- Local graph → Show nearby notes only

---

## Backup Strategy

**Vault is git-tracked** (part of Dominion repo).

**Backup locations:**
1. Git history (commit frequently)
2. GitHub remote (push regularly)
3. Local backups (in `backups/` folder)

**Recovery:**
```bash
# Restore from git
git checkout HEAD -- vault/

# Restore from backup
cp -r backups/vault-YYYYMMDD/ vault/
```

---

## Related Docs

- [INDEX.md](INDEX.md) — Master navigation
- [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md) — RAGD indexing
- [09_RISK_AND_SECURITY/OBSIDIAN_SYNC_RISKS.md](09_RISK_AND_SECURITY/OBSIDIAN_SYNC_RISKS.md) — Sync risks

---

## Retrieval Hints

- "obsidian vault"
- "vault structure"
- "wiki links"
- "obsidian conventions"
- "vault manifest"
