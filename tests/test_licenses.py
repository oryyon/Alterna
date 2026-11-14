"""Teste pentru licențe, notificarea de aplicare și delimitarea datelor."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_license_files_exist_and_are_not_empty():
    assert (ROOT / "LICENSE").stat().st_size > 20_000
    assert (ROOT / "LICENSE-DATA").stat().st_size > 15_000


def test_gplv3_text_is_present():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in text
    assert "Version 3, 29 June 2007" in text
    assert "END OF TERMS AND CONDITIONS" in text


def test_cc_by_sa_4_text_is_present():
    text = (ROOT / "LICENSE-DATA").read_text(encoding="utf-8")
    assert "Attribution-ShareAlike 4.0 International" in text
    assert "Section 1 -- Definitions." in text
    assert "Section 8 -- Interpretation." in text


def test_notice_defines_scope_and_logo_exception():
    text = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "GNU General Public" in text
    assert "version 3 (GPLv3)" in text
    assert "Creative Commons Attribution-ShareAlike 4.0 International" in text
    assert "NU sunt acoperite" in text


def test_readme_links_to_license_files():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[LICENSE](LICENSE)" in text
    assert "[LICENSE-DATA](LICENSE-DATA)" in text
    assert "[NOTICE](NOTICE)" in text
