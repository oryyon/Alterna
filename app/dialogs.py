"""Alterna — dialogurile Setări și Donații (sec. 13 din IDEI_PROIECT.md).

Setări: temă (persistă prin QSettings), catalog de date, indicatori afișați,
asistent AI (dezactivat, post-MVP).
Donații: text onest + cele 3 opțiuni agreate; butoanele sunt dezactivate până
există paginile reale de donații (nota din sec. 13).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout,
                               QHBoxLayout, QLabel, QPushButton, QVBoxLayout)

from .theme import THEMES
from .widgets import ComboBox

# Indicatorii obiectivi care pot fi porniți/opriți individual (sec. 13)
INDICATOR_OPTIONS = [
    ("popcon", "Rang popcon Ubuntu"),
    ("stars", "Stele GitHub"),
    ("release", "Data ultimei versiuni"),
    ("repo", "„În depozitele Ubuntu”"),
]


class SettingsDialog(QDialog):
    """Modalul ⚙ Setări. Citește/scrie direct în QSettings.

    Tema se aplică IMEDIAT la schimbarea selectorului (previzualizare live,
    ca în machetă) prin semnalul theme_changed — fără să mai fie nevoie de
    închiderea dialogului.
    """

    theme_changed = Signal(str)

    def __init__(self, settings, catalog, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("⚙ Setări")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # --- Aspect -------------------------------------------------------------
        layout.addWidget(self._group_title("Aspect"))
        form = QFormLayout()
        self.theme_combo = ComboBox()
        for key, label in THEMES.items():
            self.theme_combo.addItem(label, key)
        current = settings.value("theme", "system")
        self.theme_combo.setCurrentIndex(list(THEMES).index(current))
        self.theme_combo.currentIndexChanged.connect(
            lambda _: self.theme_changed.emit(self.theme_combo.currentData()))
        form.addRow("Temă", self.theme_combo)
        layout.addLayout(form)
        layout.addWidget(self._hint(
            "La „A sistemului”, aplicația urmează tema Plasma (aspect nativ)."))

        # --- Catalog de date ------------------------------------------------------
        layout.addWidget(self._group_title("Catalog de date"))
        self.auto_update = QCheckBox("Verificare actualizări la pornire")
        self.auto_update.setChecked(
            settings.value("auto_update", True, type=bool))
        layout.addWidget(self.auto_update)
        row = QFormLayout()
        row.addRow("Ultima actualizare", QLabel(catalog.generated_at))
        layout.addLayout(row)
        update_btn = QPushButton("Actualizează acum (post-MVP)")
        update_btn.setEnabled(False)  # sincronizarea catalogului — „Idei pentru viitor"
        layout.addWidget(update_btn)

        # --- Indicatori afișați ----------------------------------------------------
        layout.addWidget(self._group_title("Indicatori afișați"))
        self.indicator_checks: dict[str, QCheckBox] = {}
        for key, label in INDICATOR_OPTIONS:
            check = QCheckBox(label)
            check.setChecked(settings.value(f"show_{key}", True, type=bool))
            self.indicator_checks[key] = check
            layout.addWidget(check)

        # --- Asistent AI (viitor) ----------------------------------------------------
        layout.addWidget(self._group_title("Asistent AI (viitor)"))
        ai_combo = ComboBox()
        ai_combo.addItems(["Dezactivat (implicit)", "Model local (Ollama)",
                           "Claude API — cheie proprie"])
        ai_combo.setEnabled(False)
        ai_form = QFormLayout()
        ai_form.addRow("Sursă AI", ai_combo)
        layout.addLayout(ai_form)
        layout.addWidget(self._hint(
            "Disponibil post-MVP. Nicio cheie nu e inclusă în aplicație."))

        # --- Butoane ------------------------------------------------------------------
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("Închide")
        ok.setProperty("primary", True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def accept(self) -> None:
        self.settings.setValue("theme", self.theme_combo.currentData())
        self.settings.setValue("auto_update", self.auto_update.isChecked())
        for key, check in self.indicator_checks.items():
            self.settings.setValue(f"show_{key}", check.isChecked())
        super().accept()

    @staticmethod
    def _group_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("h2", "true")
        return label

    @staticmethod
    def _hint(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("dim", "true")
        label.setWordWrap(True)
        return label


class DonateDialog(QDialog):
    """Modalul ♥ Donează (sec. 13). Butoanele se activează când există paginile reale."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("♥ Susține Alterna")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        text = QLabel(
            "Alterna este software liber (cod: GPLv3; date originale: CC BY-SA 4.0), "
            "dezvoltat în timpul liber. "
            "Dacă îți este utilă, o donație ajută la întreținerea catalogului "
            "și la dezvoltarea de funcții noi. <b>Absolut opțional</b> — aplicația "
            "rămâne gratuită și completă pentru toată lumea.")
        text.setWordWrap(True)
        layout.addWidget(text)

        options = [
            ("🅻 Liberapay", "donații recurente, fără comisioane (card / SEPA)"),
            ("☕ Ko-fi", "donații unice, „o cafea” (card / PayPal)"),
            ("🅁 Revolut", "link revolut.me — instant, popular în România"),
        ]
        for title, note in options:
            btn = QPushButton(f"{title}  —  {note}")
            btn.setEnabled(False)  # TODO(sec. 13): se activează când există paginile
            layout.addWidget(btn)

        hint = QLabel("Opțiunile se activează când există paginile de donații; "
                      "fiecare va deschide pagina în browserul implicit — aplicația "
                      "nu atinge plăți sau date financiare.")
        hint.setProperty("dim", "true")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("Închide")
        ok.setProperty("primary", True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(ok)
        layout.addLayout(buttons)
