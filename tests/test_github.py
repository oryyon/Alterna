"""Teste pentru integrarea GitHub: issue template, etichete și workflow-uri."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent


def test_github_issue_template_is_valid_yaml():
    data = yaml.safe_load(
        (ROOT / ".github" / "ISSUE_TEMPLATE" / "propunere-aplicatie.yml")
        .read_text(encoding="utf-8")
    )
    assert data["name"] == "Propunere aplicație"
    assert "propunere-aplicatie" in data["labels"]
    ids = {field.get("id") for field in data["body"] if "id" in field}
    assert {"nume", "id", "categorie", "licenta", "pret", "website"} <= ids


def test_github_labels_config_is_valid_yaml():
    data = yaml.safe_load(
        (ROOT / ".github" / "labels.yml").read_text(encoding="utf-8")
    )
    names = {label["name"] for label in data}
    assert {"propunere-aplicatie", "date", "automat"} <= names
    for label in data:
        assert label["color"].isalnum() and len(label["color"]) == 6


def test_ci_workflow_exists_and_runs_tests():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pytest" in text
    assert "build_catalog.py" in text
    assert "desktop-file-validate" in text


def test_release_workflow_builds_appimage():
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "build_appimage.sh" in text
    assert "action-gh-release" in text
    assert "tags:" in text


def test_refresh_workflow_runs_tests_before_opening_pr():
    text = (ROOT / ".github" / "workflows" / "refresh.yml").read_text(encoding="utf-8")
    assert "pytest" in text
    assert "create-pull-request" in text
    assert text.index("pytest") < text.index("create-pull-request")


def test_issue_template_and_workflows_are_valid_yaml():
    """Toate fișierele YAML din .github/ trebuie să fie parsabile."""
    for path in sorted((ROOT / ".github").rglob("*.yml")):
        yaml.safe_load(path.read_text(encoding="utf-8"))


def test_issue_template_matches_appdata_id():
    """ID-ul AppStream și repository-ul trebuie să fie coerente."""
    root = ET.parse(
        ROOT / "packaging" / "org.alterna.app.appdata.xml"
    ).getroot()
    assert root.findtext("id") == "org.alterna.app"
