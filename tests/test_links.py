"""Teste pentru linkurile externe centralizate (app/links.py)."""

from __future__ import annotations

from app import links


def test_repo_name_and_owner():
    assert links.REPO_NAME == "Alterna"
    assert links.REPO_OWNER == "oryyon"


def test_urls_are_derived_from_repo_url():
    assert links.REPO_URL == "https://github.com/oryyon/Alterna"
    assert links.ISSUES_URL == f"{links.REPO_URL}/issues"
    assert links.CONTRIBUTING_URL.endswith("/blob/main/CONTRIBUTING.md")
    assert links.DATA_LICENSE_URL.endswith("/blob/main/LICENSE-DATA")
    assert links.OPEN_ISSUES_URL.startswith(links.ISSUES_URL)


def test_new_issue_url_uses_template_and_label():
    assert "template=propunere-aplicatie.yml" in links.NEW_ISSUE_URL
    assert "labels=propunere-aplicatie" in links.NEW_ISSUE_URL
    assert links.NEW_ISSUE_URL.startswith(links.ISSUES_URL)


def test_appdata_urls_match_links_module():
    """Metadata AppStream și aplicația trebuie să indice același repository."""
    from pathlib import Path
    import xml.etree.ElementTree as ET

    root = Path(__file__).resolve().parent.parent
    meta = ET.parse(root / "packaging" / "org.alterna.app.appdata.xml").getroot()
    homepage = meta.findtext("url[@type='homepage']")
    bugtracker = meta.findtext("url[@type='bugtracker']")
    assert homepage == links.REPO_URL
    assert bugtracker == links.ISSUES_URL
