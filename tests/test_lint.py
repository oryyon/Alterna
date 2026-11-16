"""Verificare statică: nicio variabilă nedefinită (pyflakes).

Pylance a semnalat în `app/dialogs.py` un `Path` folosit fără import — un
**bug real**, nu un warning: butonul „Actualizează catalogul acum" ar fi aruncat
`NameError` abia la apăsare, iar suita de teste nu trece prin acel cod.

Testul de mai jos rulează pyflakes pe tot codul proiectului și eșuează la
orice nume nedefinit. Importurile nefolosite sunt doar avertismente (nu
blochează): ele nu rup nimic la runtime.

Dacă pyflakes nu e instalat, testul e sărit — dar în CI e întotdeauna
prezent (requirements.txt, grupul „Dezvoltare/testare").
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _are_pyflakes() -> bool:
    try:
        subprocess.run([sys.executable, "-m", "pyflakes", "--version"],
                       capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


pytestmark = pytest.mark.skipif(not _are_pyflakes(),
                                reason="pyflakes nu e instalat")


def test_nicio_variabila_nedefinita():
    """Niciun nume folosit fără să fie definit sau importat."""
    rezultat = subprocess.run(
        [sys.executable, "-m", "pyflakes", "app", "tools", "tests"],
        capture_output=True, text=True, cwd=ROOT, timeout=120, check=False)
    nedefinite = [linie for linie in rezultat.stdout.splitlines()
                  if "undefined name" in linie]
    assert not nedefinite, ("nume nedefinite în cod:\n  "
                             + "\n  ".join(nedefinite))


def test_dialogurile_au_importul_de_path():
    """Regresie: `Path` e folosit în dialoguri, deci trebuie importat."""
    text = (ROOT / "app" / "dialogs.py").read_text(encoding="utf-8")
    assert "from pathlib import Path" in text


def test_nicio_clasa_de_test_nu_are_nume_dublu():
    """O clasă cu același nume umbrește cealaltă — și teste dispar în tăcere.

    S-a întâmplat: o clasă nouă `TestDialoguri` a umbrit o clă existentă cu
    același nume, iar patru teste au dispărut din suita fără niciun semn.
    """
    import re
    from collections import Counter

    for fișier in sorted((ROOT / "tests").glob("test_*.py")):
        nume = re.findall(r"^class (\w+)", fișier.read_text(encoding="utf-8"),
                          re.M)
        duble = [n for n, c in Counter(nume).items() if c > 1]
        assert not duble, f"{fișier.name}: clase cu nume dublu {duble}"
