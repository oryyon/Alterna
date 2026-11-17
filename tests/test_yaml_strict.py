"""Teste: niciun fișier YAML nu poate avea chei duplicate.

PyYAML și ruamel acceptă cheile duplicate **în tăcere** — ultima câștigă.
Asta a lăsat să treacă o eroare reală de editare în fișierele de semințe
(două câmpuri cu același nume), fără niciun semnal în build sau în teste.

De aceea verificarea e explicită: parserul strict (care refuză cheile
duplicate) rulează asupra **tuturor** fișierelor YAML din repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: Fișierele YAML care trebuie să fie strict-parsabile.
FIȘIERE = sorted(
    list((ROOT / "data").rglob("*.yaml"))
    + list((ROOT / "tools" / "seminte").glob("*.yaml"))
    + list((ROOT / ".github").rglob("*.yml"))
    + list((ROOT / ".github").rglob("*.yaml"))
)


def _strict(text: str):
    """Parsează YAML-ul, refuzând cheile duplicate."""
    import yaml

    class Strict(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            mapping = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                if key in mapping:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        f"cheie duplicată: {key!r}", key_node.start_mark)
                mapping[key] = self.construct_object(value_node, deep=deep)
            return mapping

    return yaml.load(text, Loader=Strict)


def test_yaml_fara_chei_duplicate():
    """Nicio cheie repetată — ultima nu câștigă în tăcere.

    Un singur test pentru toate fișierele: acoperirea e aceeași, iar
    raportul rămâne lizibil (un test per fișier ar însemna 226 de rânduri
    în ieșire, pentru o singură proprietate).
    """
    probleme = []
    for cale in FIȘIERE:
        try:
            _strict(cale.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — mesajul e cel care contează
            probleme.append(f"{cale.relative_to(ROOT)}: {exc}")
    assert not probleme, "\n".join(probleme)


def test_exista_fisiere_verificate():
    """Verificarea să nu fie un test gol (catalogul + semințele există)."""
    assert len(FIȘIERE) > 200
    assert any("data/apps" in str(c) for c in FIȘIERE)
    assert any("seminte" in str(c) for c in FIȘIERE)


def test_semintele_sunt_inregistrate_in_git():
    """Fișierele de semințe sunt sursa editorială — nu pot lipsi din repo."""
    import subprocess

    for fișier in sorted((ROOT / "tools" / "seminte").glob("*.yaml")):
        rezultat = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(fișier.relative_to(ROOT))],
            capture_output=True, text=True, cwd=str(ROOT))
        assert rezultat.returncode == 0, f"{fișier.name} nu e în git"
