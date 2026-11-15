"""Alterna — marcajul de certitudine al datelor (sec. 8 din IDEI_PROIECT.md).

Proiectul promite „totul e verificabil". Promisiunea e onestă doar dacă
utilizatorul poate vedea cât de mult se poate baza pe fiecare valoare. Deci
fiecare câmp comparabil poartă un nivel de certitudine:

- ``auto``      — valoare sincronizată automat din surse publice
                  (``tools/refresh_indicators.py``: popcon, GitHub, Ubuntu);
- ``manual``    — valoare verificată de un om împotriva sursei citate;
- ``estimated`` — valoare estimată/editorială, fără verificare individuală;
- ``unknown``   — valoare lipsă; se deduce automat, nu se configurează.

Nivelurile se configurează în ``data/confidence.yaml`` (implicit pe tip de
câmp) și se pot ridica per aplicație, în fișierul ei YAML:

    confidence:
      details.romanian_language: manual

Regulă: o valoare ``null``/vidă e întotdeauna ``unknown``, oricât s-ar
declara altfel — nu poți verifica ceea ce nu există.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel

#: Nivelurile de certitudine, de la cel mai puternic la cel mai slab.
#: Ordinea contează: comparația marchează rândul cu cel mai slab nivel.
LEVELS = ("auto", "manual", "estimated", "unknown")

#: Puterea fiecărui nivel — folosită ca să alegem „cel mai slab" pe un rând.
LEVEL_RANK = {"auto": 3, "manual": 2, "estimated": 1, "unknown": 0}

#: Textul afișat în UI, pentru fiecare nivel.
LEVEL_LABELS = {
    "auto": "✓ verificată automat",
    "manual": "✓ verificată manual",
    "estimated": "≈ valoare estimată",
    "unknown": "? valoare necunoscută",
}

#: Text scurt, pentru panoul de certitudine (rânduri dedicate).
LEVEL_SHORT = {
    "auto": "✓ automat",
    "manual": "✓ manual",
    "estimated": "≈ estimat",
    "unknown": "? necunoscut",
}

#: Simbolul compact, pentru marcajele din cardurile de fapt. Patru semne
#: distincte — marcajul trebuie să se citească și fără culoare (tema
#: „A sistemului" nu aplică QSS) și să încapă în cardul îngust.
LEVEL_MARKS = {
    "auto": "⟳",      # se sincronizează automat
    "manual": "✓",    # verificat de un om
    "estimated": "≈",  # valoare estimată
    "unknown": "?",   # nu există valoare
}

#: Explicația lungă — tooltip.
LEVEL_HINTS = {
    "auto": "Valoare sincronizată automat din surse publice "
            "(popcon.debian.org, GitHub API, packages.ubuntu.com).",
    "manual": "Valoare verificată manual de un contributor, împotriva "
              "sursei citate în secțiunea „Surse”.",
    "estimated": "Valoare estimată sau editorială — nu a fost verificată "
                 "individual împotriva sursei.",
    "unknown": "Nu există valoare pentru acest câmp la această aplicație.",
}

#: Culorile marcajelor, folosite în celulele tabelului de comparație.
#: Aceleași culori ca în QSS (temă), ca marcajul să arate la fel peste tot.
CONF_COLORS = {
    "auto": QColor("#27ae60"),       # verde — verificată
    "manual": QColor("#27ae60"),     # verde — verificată
    "estimated": QColor("#f39c12"),  # portocaliu — estimată
    "unknown": QColor("#9aa0a6"),    # cenușiu — necunoscută
}

#: Etichetele umane ale câmpurilor, pentru panoul de certitudine.
FIELD_LABELS = {
    "name": "Nume",
    "description": "Descriere",
    "category": "Categorie",
    "license": "Licență",
    "price": "Preț",
    "developer": "Dezvoltator",
    "website": "Site oficial",
    "platforms": "Platforme",
    "tags": "Taguri",
    "alternatives": "Alternative",
    "popularity": "Ordine în catalog",
    "details.install_size_mb": "Dimensiune la instalare",
    "details.first_release_year": "Anul primei versiuni",
    "details.file_formats": "Formate de fișiere",
    "details.telemetry": "Telemetrie",
    "details.romanian_language": "Limbă română",
    "indicators.popcon_rank": "Rang popcon",
    "indicators.stars": "Stele GitHub",
    "indicators.stars_url": "Repository GitHub",
    "indicators.latest_release": "Ultima versiune",
    "indicators.in_ubuntu_repos": "În depozitele Ubuntu",
    "features": "Funcționalități (matrice)",
}

#: Câmpurile care pot purta un marcaj de certitudine.
CONFIDENCE_FIELDS = tuple(FIELD_LABELS)


def weakest(levels) -> str:
    """Cel mai slab nivel dintr-o mulțime — pentru marcarea unui rând.

    Un rând de comparație e doar atât de credibil cât cea mai slabă celulă:
    dacă o singură aplicație are o valoare estimată, rândul e estimat.
    """
    nivel = None
    for lvl in levels:
        if nivel is None or LEVEL_RANK.get(lvl, 0) < LEVEL_RANK.get(nivel, 0):
            nivel = lvl
    return nivel or "unknown"


def field_label(field: str) -> str:
    """Eticheta umană a unui câmp (cu fallback pe cheia brută)."""
    return FIELD_LABELS.get(field, field)


class ConfidenceBadge(QLabel):
    """Marcaj compact de certitudine: „⟳", „✓", „≈", „?".

    Textul scurt e suficient de explicit încât să se citească și fără culoare
    (tema „A sistemului" nu aplică QSS), iar culoarea vine din temă.
    Varianta `full=True` arată textul lung, pentru rândurile dedicate.
    """

    def __init__(self, level: str, full: bool = False, parent=None):
        super().__init__(parent)
        self.level = level if level in LEVELS else "unknown"
        self.setText(LEVEL_SHORT[self.level] if full else LEVEL_MARKS[self.level])
        self.setProperty("conf", self.level)
        self.setToolTip(f"{LEVEL_LABELS[self.level]} — {LEVEL_HINTS[self.level]}")
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
