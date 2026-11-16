"""Paze împotriva bugurilor pe care suita de teste nu le vedea.

Trei clase de probleme, toate întâlnite în proiect:

1. **Variabile nedefinite** — Pylance a semnalat în `app/dialogs.py` un `Path`
   folosit fără import: un *bug real*, nu un warning, care arunca `NameError`
   abia la apăsarea butonului „Actualizează catalogul acum”. Verificarea e
   făcută cu `symtable` (doar biblioteca standardă), deci rulează **mereu** —
   pyflakes rămâne doar o verificare în plus, pentru cei care îl au instalat.

2. **Ocolirea codului nou prin steaguri de constructor** — testele punctului 16
   porneau fereastra cu `detecta=False`, adică dezactivau exact drumul care
   crăpa la pornire. Orice astfel de ocolire trebuie **înregistrată** și
   trebuie să aibă un test care acoperă calea pornită.

3. **Clase de test cu nume dublu** — Python păstrează doar a doua definiție,
   deci teste dispar din suita fără niciun semn.
"""

from __future__ import annotations

import ast
import builtins
import symtable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

#: Nume pe care Python le injectează în modul — nu sunt „nedefinite”.
SPECIALE = {"__file__", "__name__", "__doc__", "__package__", "__spec__",
            "__loader__", "__builtins__", "__class__", "__qualname__",
            "__annotations__", "__debug__"}

#: Ocoliri justificate: caracteristica oprită în teste → testul care acoperă
#: calea **pornită**. Fiecare intrare e o regulă, nu o scuză.
OCOLIRI = {
    "detecta": {
        "motiv": "detectarea instalării pornește un QThread și interoghează "
                 "sistemul de pachete — lent și dependent de mașină",
        "acoperit_de": "TestDetectareInThread",
    },
}


#: Ocoliri prin `monkeypatch` pe modulele noastre: ținta → motiv. Aici
#: înlocuirea e la *granița externă* (rețea, setări de utilizator), nu pe
#: logica aplicației — de aceea e acceptabilă, dar trebuie să fie declarată.
OCOLIRI_MONKEYPATCH = {
    "app.ai._post_json": {
        "motiv": "graniță de rețea: răspunsul Claude API e simulat, nu cerut",
    },
    "app.main_window.QSettings": {
        "motiv": "setările utilizatorului sunt izolate într-un fișier "
                 "temporar, ca testul să nu atingă configurația reală",
    },
}

# --------------------------------------------------------------------------
# 1. Variabile nedefinite
# --------------------------------------------------------------------------
def _nedefinite(sursă: str, nume: str) -> list[str]:
    """Numele folosite într-un modul, dar nicăieri definite (doar stdlib)."""
    tabel = symtable.symtable(sursă, nume, "exec")
    definite = {s.get_name() for s in tabel.get_symbols()
                if s.is_assigned() or s.is_imported() or s.is_namespace()}
    probleme: list[str] = []

    def parcurge(t, domeniu: str) -> None:
        for simbol in t.get_symbols():
            nume_simbol = simbol.get_name()
            if nume_simbol in SPECIALE or hasattr(builtins, nume_simbol):
                continue
            if (simbol.is_global() and simbol.is_referenced()
                    and nume_simbol not in definite):
                probleme.append(f"{nume}: {nume_simbol} (în {domeniu})")
        for copil in t.get_children():
            parcurge(copil, f"{domeniu}/{copil.get_name()}")

    parcurge(tabel, "modul")
    return probleme


class TestVariabileNedefinite:
    """Numele folosite trebuie să fie definite sau importate."""

    def _module(self, fișier: Path) -> list[str]:
        sursă = fișier.read_text(encoding="utf-8")
        compile(sursă, str(fișier), "exec")   # sintaxă greșită = test eșuat
        return _nedefinite(sursă, str(fișier))

    def test_nicio_variabila_nedefinita_in_aplicatie(self):
        probleme = []
        for fișier in sorted((ROOT / "app").glob("*.py")):
            probleme += self._module(fișier)
        assert not probleme, ("nume nedefinite în app/:\n  "
                              + "\n  ".join(probleme))

    def test_nicio_variabila_nedefinita_in_unelte(self):
        probleme = []
        for fișier in sorted((ROOT / "tools").glob("*.py")):
            probleme += self._module(fișier)
        assert not probleme, ("nume nedefinite în tools/:\n  "
                              + "\n  ".join(probleme))

    def test_verificarea_detecteaza_numele_uitate(self):
        """Testul trebuie să prindă o eroare — altfel nu verifică nimic."""
        cod = ("from pathlib import Path\n"
               "def ok():\n    return Path('x')\n"
               "def gresit():\n    return Text('y')\n")
        probleme = _nedefinite(cod, "demo.py")
        assert any("Text" in p for p in probleme), probleme


# --------------------------------------------------------------------------
# 2. Ocolirile prin steaguri de constructor
# --------------------------------------------------------------------------
def _comutatoare_bool(produse: list[Path]) -> set[str]:
    """Parametrii `bool` din codul de producție (comutatoare de caracteristici)."""
    nume: set[str] = set()
    for fișier in produse:
        arbore = ast.parse(fișier.read_text(encoding="utf-8"))
        for nod in ast.walk(arbore):
            if isinstance(nod, (ast.FunctionDef, ast.AsyncFunctionDef)):
                argumente = list(nod.args.args) + list(nod.args.kwonlyargs)
                for argument in argumente:
                    if (argument.annotation is not None
                            and ast.unparse(argument.annotation) == "bool"):
                        nume.add(argument.arg)
    return nume


def _dezactivate_in_teste() -> dict[str, list[str]]:
    """Ce caracteristici sunt oprite (`X=False`) în teste, și unde."""
    folosite: dict[str, list[str]] = {}
    for fișier in sorted(TESTS.glob("test_*.py")):
        arbore = ast.parse(fișier.read_text(encoding="utf-8"))
        for nod in ast.walk(arbore):
            if isinstance(nod, ast.Call):
                for argument in nod.keywords:
                    if (isinstance(argument.value, ast.Constant)
                            and argument.value.value is False):
                        folosite.setdefault(argument.arg, []).append(
                            f"{fișier.name}:{argument.lineno}")
    return folosite


def _clase_numite(nume: str) -> list:
    """Nodurile AST ale claselor cu numele dat, din toate testele."""
    gasite = []
    for fișier in sorted(TESTS.glob("test_*.py")):
        arbore = ast.parse(fișier.read_text(encoding="utf-8"))
        for nod in ast.walk(arbore):
            if isinstance(nod, ast.ClassDef) and nod.name == nume:
                gasite.append(nod)
    return gasite


def _dezactivate_in_nod(nod) -> set[str]:
    """Caracteristicile oprite (`X=False`) în interiorul unui nod AST."""
    oprite = set()
    for sub in ast.walk(nod):
        if isinstance(sub, ast.Call):
            for argument in sub.keywords:
                if (isinstance(argument.value, ast.Constant)
                        and argument.value.value is False):
                    oprite.add(argument.arg)
    return oprite


def _tinte_monkeypatch() -> dict[str, list[str]]:
    """Ce module ale aplicației sunt înlocuite cu `monkeypatch`, și unde."""
    tinte: dict[str, list[str]] = {}
    for fișier in sorted(TESTS.glob("test_*.py")):
        arbore = ast.parse(fișier.read_text(encoding="utf-8"))
        for nod in ast.walk(arbore):
            if (isinstance(nod, ast.Call)
                    and isinstance(nod.func, ast.Attribute)
                    and nod.func.attr == "setattr"
                    and nod.args
                    and isinstance(nod.args[0], ast.Constant)
                    and isinstance(nod.args[0].value, str)
                    and nod.args[0].value.startswith("app.")):
                tinte.setdefault(nod.args[0].value, []).append(
                    f"{fișier.name}:{nod.lineno}")
    return tinte


class TestOcoliriInregistrate:
    """Nicio caracteristică nu poate fi oprită în teste fără acord explicit."""

    def test_ocolirile_sunt_inregistrate(self):
        comutatoare = _comutatoare_bool(sorted((ROOT / "app").glob("*.py")))
        oprite = _dezactivate_in_teste()
        neinregistrate = sorted((set(oprite) & comutatoare) - set(OCOLIRI))
        assert not neinregistrate, (
            "caracteristici oprite în teste fără înregistrare: "
            f"{neinregistrate} — adaugă-le în OCOLIRI (tests/test_lint.py) "
            "și un test care acoperă calea pornită")

    def test_fiecare_ocolire_are_test_ce_acopera_calea_pornita(self):
        """Ocolirea e justificată doar dacă există testul care o activează."""
        for caracteristică, înregistrare in OCOLIRI.items():
            acoperitor = înregistrare["acoperit_de"]
            clase = _clase_numite(acoperitor)
            assert clase, (f"{caracteristică}: nu există clasa {acoperitor} "
                           "care să acopere calea pornită")
            # clasa care acoperă nu trebuie să ocolească ea însăși
            for nod in clase:
                oprite = _dezactivate_in_nod(nod)
                assert caracteristică not in oprite, (
                    f"{acoperitor} ocolește chiar ea {caracteristică} — "
                    "nu acoperă calea pornită")

    def test_ocolirile_prin_monkeypatch_sunt_inregistrate(self):
        """Înlocuirea unui modul al aplicației trebuie declarată și motivată."""
        tinte = _tinte_monkeypatch()
        neinregistrate = sorted(set(tinte) - set(OCOLIRI_MONKEYPATCH))
        assert not neinregistrate, (
            "module înlocuite cu monkeypatch fără înregistrare: "
            f"{neinregistrate} — adaugă-le în OCOLIRI_MONKEYPATCH "
            "(tests/test_lint.py), cu motivul graniței înlocuite")

    def test_inregistrarile_monkeypatch_sunt_explicite(self):
        for tintă, înregistrare in OCOLIRI_MONKEYPATCH.items():
            assert înregistrare.get("motiv", "").strip(), tintă

    def test_inregistrarile_sunt_explicite(self):
        """Motivul trebuie scris: „de ce” e mai util decât „ce”."""
        for caracteristică, înregistrare in OCOLIRI.items():
            assert înregistrare.get("motiv", "").strip(), caracteristică
            assert înregistrare.get("acoperit_de", "").strip(), caracteristică


# --------------------------------------------------------------------------
# 3. Clase cu nume dublu
# --------------------------------------------------------------------------
def test_nicio_clasa_de_test_nu_are_nume_dublu():
    """O clasă cu același nume umbrește cealaltă — și teste dispar în tăcere.

    S-a întâmplat: o clasă nouă `TestDialoguri` a umbrit o clă existentă cu
    același nume, iar patru teste au dispărut din suita fără niciun semn.
    """
    import re
    from collections import Counter

    for fișier in sorted(TESTS.glob("test_*.py")):
        nume = re.findall(r"^class (\w+)", fișier.read_text(encoding="utf-8"),
                          re.M)
        duble = [n for n, c in Counter(nume).items() if c > 1]
        assert not duble, f"{fișier.name}: clase cu nume dublu {duble}"
