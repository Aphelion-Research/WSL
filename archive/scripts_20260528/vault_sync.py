#!/usr/bin/env python3
"""
Vault sync script: Mirror docs/ structure to vault/files/docs/

Usage:
    python scripts/vault_sync.py                  # Sync all docs
    python scripts/vault_sync.py --file path.md   # Sync single file
    python scripts/vault_sync.py --dry-run        # Preview without changes
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---\n"):
        return {}, content

    try:
        _, fm_str, body = content.split("---\n", 2)
    except ValueError:
        return {}, content

    # Simple YAML parser (no dependencies)
    frontmatter = {}
    for line in fm_str.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def inject_synced_timestamp(content: str) -> str:
    """Add or update 'synced' timestamp in frontmatter."""
    frontmatter, body = parse_frontmatter(content)

    # Update synced timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    frontmatter["synced"] = now

    # Rebuild frontmatter
    fm_lines = ["---"]
    for key, value in frontmatter.items():
        fm_lines.append(f"{key}: {value}")
    fm_lines.append("---")

    return "\n".join(fm_lines) + "\n" + body


def sync_file(source: Path, target: Path, dry_run: bool = False, quiet: bool = False) -> None:
    """Sync single file from docs/ to vault/files/docs/."""
    if not source.exists():
        if not quiet:
            print(f"SKIP: {source} does not exist")
        return

    if not source.is_file():
        if not quiet:
            print(f"SKIP: {source} is not a file")
        return

    # Read source
    try:
        content = source.read_text(encoding="utf-8")
    except Exception as e:
        if not quiet:
            print(f"ERROR: Cannot read {source}: {e}")
        return

    # Inject synced timestamp
    synced_content = inject_synced_timestamp(content)

    # Write to target
    if dry_run:
        if not quiet:
            print(f"WOULD SYNC: {source} → {target}")
        return

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(synced_content, encoding="utf-8")
        if not quiet:
            print(f"SYNCED: {source} → {target}")
    except Exception as e:
        if not quiet:
            print(f"ERROR: Cannot write {target}: {e}")


def sync_all(source_dir: Path, target_dir: Path, dry_run: bool = False, quiet: bool = False) -> None:
    """Sync all markdown files from docs/ to vault/files/docs/."""
    if not source_dir.exists():
        if not quiet:
            print(f"ERROR: Source directory {source_dir} does not exist")
        sys.exit(1)

    # Find all markdown files
    md_files = list(source_dir.rglob("*.md"))
    if not quiet:
        print(f"Found {len(md_files)} markdown files in {source_dir}")

    synced_count = 0
    for source_file in md_files:
        # Calculate relative path
        rel_path = source_file.relative_to(source_dir)
        target_file = target_dir / rel_path

        # Sync
        sync_file(source_file, target_file, dry_run=dry_run, quiet=quiet)
        synced_count += 1

    if not quiet:
        print(f"\n{'DRY RUN: Would sync' if dry_run else 'Synced'} {synced_count}/{len(md_files)} files")


def main():
    parser = argparse.ArgumentParser(description="Sync docs/ to vault/files/docs/")
    parser.add_argument("--file", type=str, help="Sync single file (relative to docs/)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()

    # Paths
    repo_root = Path(__file__).parent.parent
    source_dir = repo_root / "docs"
    target_dir = repo_root / "vault" / "files" / "docs"

    if args.file:
        # Sync single file
        source_file = source_dir / args.file
        target_file = target_dir / args.file
        sync_file(source_file, target_file, dry_run=args.dry_run, quiet=args.quiet)
    else:
        # Sync all files
        sync_all(source_dir, target_dir, dry_run=args.dry_run, quiet=args.quiet)


if __name__ == "__main__":
    main()
