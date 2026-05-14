from __future__ import annotations

from ragd_vault.doctor import inspect_vault


def test_vault_doctor_catches_broken_links_and_frontmatter(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "bad.md").write_text("---\ntitle: [bad\n---\n\n[[missing]]\n", encoding="utf-8")
    report = inspect_vault(vault)
    assert not report.ok
    assert report.broken_links
    assert report.invalid_frontmatter
