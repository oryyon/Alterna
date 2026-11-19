"""Alterna — dialogurile Setări și Donații (sec. 13 din IDEI_PROIECT.md).

Setări: temă (persistă prin QSettings), catalog de date, indicatori afișați,
asistent AI (dezactivat, post-MVP).
Donații: text onest + cele 3 opțiuni agreate; butoanele sunt dezactivate până
există paginile reale de donații (nota din sec. 13).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QFrame,
                                QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QScrollArea,
                               QTextEdit, QVBoxLayout, QWidget)

from . import links
from .ai import (CLAUDE_DEFAULT_MODEL, OLLAMA_DEFAULT_MODEL,
                  OLLAMA_DEFAULT_URL, ClaudeClient, OllamaClient,
                  extract_yaml, validate_proposal)
from .net import clear_threads, run_in_thread
from .paths import user_catalog_path, user_data_dir
from .theme import THEMES
from .widgets import ComboBox

# Indicatorii obiectivi care pot fi porniți/opriți individual (sec. 13)
INDICATOR_OPTIONS = [
    ("popcon", "Rang popcon Ubuntu"),
    ("stars", "Stele GitHub"),
    ("release", "Data ultimei versiuni"),
    ("repo", "„În depozitele Ubuntu”"),
]

#: Cheile QSettings pentru asistentul AI.
AI_SOURCE_KEY = "ai_source"
AI_MODEL_KEY = "ai_model"
AI_OLLAMA_URL_KEY = "ai_ollama_url"
AI_CLAUDE_KEY_KEY = "ai_claude_key"

#: Surse AI disponibile: "none" | "ollama" | "claude".
AI_SOURCES = [
    ("none", "Dezactivat (implicit)"),
    ("ollama", "Model local (Ollama)"),
    ("claude", "Claude API — cheie proprie"),
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
        # Catalogul e păstrat ca atribut: „Actualizează catalogul acum" și
        # „Propune o aplicație cu AI…" au nevoie de el (fără, arunca
        # AttributeError în thread → „Eroare neașteptată").
        self.catalog = catalog
        self.setWindowTitle("⚙ Setări")
        self.setMinimumWidth(480)

        # Conținutul e într-o zonă de derulare: pe ecrane mici (sau cu conținut
        # extins) rândurile de jos nu mai sunt tăiate — apare un scrollbar.
        outer = QVBoxLayout(self)
        outer.setSpacing(12)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("settingsContent")
        layout = QVBoxLayout(content)
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

        self.update_status = QLabel("—")
        self.update_status.setProperty("dim", "true")
        self.update_status.setWordWrap(True)
        layout.addWidget(self.update_status)

        # --- Aplicațiile deja instalate (punctul 16) -----------------------------
        self.detect_installed = QCheckBox("Detectează aplicațiile deja instalate")
        self.detect_installed.setChecked(
            settings.value("detect_installed", True, type=bool))
        layout.addWidget(self.detect_installed)
        layout.addWidget(self._hint(
            "Se verifică local, cu dpkg / snap / flatpak — nimic nu iese de pe "
            "computer. Dacă oprești, marcajul „✓ instalat” nu mai apare."))

        self.update_btn = QPushButton("Actualizează catalogul acum")
        self.update_btn.setEnabled(True)
        self.update_btn.clicked.connect(self._update_catalog)
        layout.addWidget(self.update_btn)
        layout.addWidget(self._hint(
            "Catalogul vine din release-urile publice și e verificat cu "
            "SHA-256 înainte de a fi folosit; catalogul vechi rămâne ca "
            "backup. Rețeaua e folosită doar când apeși butonul."))

        # --- Indicatori afișați ----------------------------------------------------
        layout.addWidget(self._group_title("Indicatori afișați"))
        self.indicator_checks: dict[str, QCheckBox] = {}
        for key, label in INDICATOR_OPTIONS:
            check = QCheckBox(label)
            check.setChecked(settings.value(f"show_{key}", True, type=bool))
            self.indicator_checks[key] = check
            layout.addWidget(check)

        # --- Asistent AI -----------------------------------------------------------
        layout.addWidget(self._group_title("Asistent AI"))
        self.ai_combo = ComboBox()
        for key, label in AI_SOURCES:
            self.ai_combo.addItem(label, key)
        current_ai = settings.value(AI_SOURCE_KEY, "none")
        if current_ai not in dict(AI_SOURCES):
            current_ai = "none"
        self.ai_combo.setCurrentIndex([k for k, _ in AI_SOURCES].index(current_ai))
        self.ai_combo.currentIndexChanged.connect(self._on_ai_source_changed)
        ai_form = QFormLayout()
        ai_form.addRow("Sursă AI", self.ai_combo)
        layout.addLayout(ai_form)

        # --- Configurarea Ollama (local, fără cheie) --------------------------------
        self.ai_ollama_url = QLineEdit(
            settings.value(AI_OLLAMA_URL_KEY, "", type=str))
        self.ai_ollama_url.setPlaceholderText(OLLAMA_DEFAULT_URL)
        ollama_form = QFormLayout()
        ollama_form.addRow("Adresa serverului", self.ai_ollama_url)
        layout.addLayout(ollama_form)

        self.ai_ollama_model = QLineEdit(
            settings.value(AI_MODEL_KEY, OLLAMA_DEFAULT_MODEL, type=str))
        model_form = QFormLayout()
        model_form.addRow("Model", self.ai_ollama_model)
        layout.addLayout(model_form)

        # Cheia Claude e a utilizatorului: o introduce el, e stocată local
        # în QSettings și nu e inclusă în aplicație (regulă din sec. 13).
        self.ai_claude_key = QLineEdit(
            settings.value(AI_CLAUDE_KEY_KEY, "", type=str))
        self.ai_claude_key.setEchoMode(QLineEdit.Password)
        self.ai_claude_key.setPlaceholderText("sk-ant-…")
        claude_form = QFormLayout()
        claude_form.addRow("Cheie Claude API", self.ai_claude_key)
        layout.addLayout(claude_form)

        self.ai_test_btn = QPushButton("Testează conexiunea")
        self.ai_test_btn.clicked.connect(self._test_ai)
        layout.addWidget(self.ai_test_btn)

        self.ai_status = QLabel("—")
        self.ai_status.setProperty("dim", "true")
        self.ai_status.setWordWrap(True)
        layout.addWidget(self.ai_status)

        self.ai_propose_btn = QPushButton("Propune o aplicație cu AI…")
        self.ai_propose_btn.clicked.connect(self._open_ai_proposal)
        layout.addWidget(self.ai_propose_btn)

        layout.addWidget(self._hint(
            "AI-ul completează o propunere de catalog — nu scrie nimic în "
            "catalog. Datele generate trec prin validatorul proiectului, "
            " apoi le revizuiești și le trimiți prin fluxul GitHub. "
            "Nicio cheie API nu e inclusă în aplicație."))
        self._on_ai_source_changed()

        # Conținutul merge în zona de derulare; butonul „Închide" rămâne
        # permanent vizibil, în afara ei (altfel ar dispărea sub margine).
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)

        # --- Butoane ------------------------------------------------------------------
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("Închide")
        ok.setProperty("primary", True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(ok)
        outer.addLayout(buttons)

    # --------------------------------------------------------- actualizare catalog
    def showEvent(self, event) -> None:
        """Limitează dialogul la ecran — altfel conținutul iese din vedere.

        QScrollArea cu `widgetResizable` ar întinde dialogul până la
        dimensiunea conținutului (adic NU ar apărea scrollbar-ul); de aceea
        limităm explicit înălțimea la cea disponibilă pe ecran.
        """
        super().showEvent(event)
        screen = self.screen()
        if screen is None:
            return
        disponibil = screen.availableGeometry().height() - 40
        if self.height() > disponibil:
            self.resize(self.width(), disponibil)

    def _update_catalog(self) -> None:
        """Descarcă catalogul nou de la release-ul public și îl aplică.

        Descarcarea merge în directorul de date al utilizatorului: într-o
        instalare de sistem (`.deb` în `/opt`, AppImage) directorul aplicației
        e read-only, iar scrierea acolo ar arunca „Permission denied".
        """
        from .catalog_update import (UpdateError, download_catalog,
                                     install_catalog)

        self.update_btn.setEnabled(False)
        self.update_status.setText("Se descarcă catalogul…")

        def _done(path):
            try:
                final, backup = install_catalog(path, self.catalog.db_path,
                                                user_catalog_path())
            except UpdateError as exc:
                self.update_status.setText(f"✗ {exc}")
                self.update_btn.setEnabled(True)
                return
            if backup is not None:
                mesaj = (f"✓ Catalog actualizat (backup: {backup.name}). "
                         f"Reia aplicația pentru a vedea datele noi.")
            else:
                mesaj = (f"✓ Catalog actualizat pentru utilizatorul tău "
                         f"({final}). Reia aplicația pentru a vedea datele noi.")
            # fisierul descarcat temporar nu mai e necesar
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
            self.update_status.setText(mesaj)
            self.update_btn.setEnabled(True)

        def _failed(message: str) -> None:
            self.update_status.setText(f"✗ {message}")
            self.update_btn.setEnabled(True)

        def _work():
            target_dir = user_data_dir()
            target_dir.mkdir(parents=True, exist_ok=True)
            # se descarca sub alt nume: catalogul deja instalat ramane
            # neatins pana cand verificam amprenta
            return download_catalog(target_dir, filename="catalog-nou.db")

        run_in_thread(self, _work, _done, _failed)

    # ------------------------------------------------------------------ asistent AI
    def _ai_client(self):
        """Clientul AI configurat, sau None dacă sursa nu e utilizabilă."""
        source = self.ai_combo.currentData()
        model = self.ai_ollama_model.text().strip() or OLLAMA_DEFAULT_MODEL
        if source == "ollama":
            url = self.ai_ollama_url.text().strip()
            return OllamaClient(url or OLLAMA_DEFAULT_URL, model)
        if source == "claude":
            key = self.ai_claude_key.text().strip()
            if not key:
                return None
            return ClaudeClient(key, model or CLAUDE_DEFAULT_MODEL)
        return None

    def _on_ai_source_changed(self) -> None:
        """Activează doar ce e folosibil pentru sursa aleasă."""
        source = self.ai_combo.currentData()
        folosibil = source != "none"
        self.ai_ollama_url.setEnabled(source == "ollama")
        self.ai_ollama_model.setEnabled(folosibil)
        self.ai_claude_key.setEnabled(source == "claude")
        self.ai_test_btn.setEnabled(folosibil)
        self.ai_propose_btn.setEnabled(folosibil)
        if source == "none":
            self.ai_status.setText(
                "Asistentul AI e dezactivat. Fără configurație, funcția "
                "nu apare — nimic nu e trimis în rețea.")
        elif source == "claude" and not self.ai_claude_key.text().strip():
            self.ai_status.setText("Introdu cheia ta Claude API pentru a folosi sursa.")
        else:
            self.ai_status.setText("Apasă „Testează conexiunea” ca să verifici sursa.")

    def _test_ai(self) -> None:
        """Verifică dacă sursa AI configurată răspunde."""
        client = self._ai_client()
        if client is None:
            self.ai_status.setText("✗ Sursa AI nu e configurată complet.")
            return
        self.ai_test_btn.setEnabled(False)
        self.ai_status.setText("Se testează conexiunea…")

        def _work():
            if isinstance(client, OllamaClient):
                models = client.list_models()
                return f"✓ Ollama răspunde. Modele disponibile: {len(models)}" + (
                    f" ({', '.join(models[:5])})" if models else
                    " — nu ai încă niciun model instalat (ex.: `ollama pull llama3.1`).")
            return "✓ Cheia Claude e acceptată de client (verificarea reală "
            "are loc la generare)."

        def _done(message: str) -> None:
            self.ai_status.setText(message)
            self.ai_test_btn.setEnabled(True)

        def _failed(message: str) -> None:
            self.ai_status.setText(f"✗ {message}")
            self.ai_test_btn.setEnabled(True)

        run_in_thread(self, _work, _done, _failed)

    def _open_ai_proposal(self) -> None:
        """ Deschide formularul de propunere, completat de AI."""
        client = self._ai_client()
        if client is None:
            self.ai_status.setText("✗ Configurează mai întâi o sursă AI.")
            return
        dialog = AiProposalDialog(self, client, self.catalog)
        dialog.exec()

    def closeEvent(self, event) -> None:
        clear_threads(self)
        super().closeEvent(event)

    def accept(self) -> None:
        self.settings.setValue("theme", self.theme_combo.currentData())
        self.settings.setValue("auto_update", self.auto_update.isChecked())
        self.settings.setValue("detect_installed",
                               self.detect_installed.isChecked())
        for key, check in self.indicator_checks.items():
            self.settings.setValue(f"show_{key}", check.isChecked())
        # Setările asistentului AI (cheia Claude rămâne locală, în QSettings)
        self.settings.setValue(AI_SOURCE_KEY, self.ai_combo.currentData())
        self.settings.setValue(AI_MODEL_KEY, self.ai_ollama_model.text().strip())
        self.settings.setValue(AI_OLLAMA_URL_KEY, self.ai_ollama_url.text().strip())
        self.settings.setValue(AI_CLAUDE_KEY_KEY, self.ai_claude_key.text().strip())
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


class AiProposalDialog(QDialog):
    """Formularul de propunere de aplicație, completat de AI.

    Fluxul: utilizatorul descrie aplicația → AI-ul generează YAML → propunerea
    e validată cu validatorul proiectului → omul o revizuiește, o copiază
    sau o salvează și o trimite prin fluxul GitHub.

    Nimic nu e scris în catalog: AI-ul propune, omul aprobă.
    """

    def __init__(self, parent, client, catalog):
        super().__init__(parent)
        self.client = client
        self.catalog = catalog
        self.setWindowTitle("✨ Propunere de aplicație (AI)")
        self.setMinimumWidth(640)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QLabel(
            "Descrie aplicația (nume, ce face, pentru cine). AI-ul completează "
            "fișierul YAML; apoi îl verifici și îl trimiți prin GitHub.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.request = QTextEdit()
        self.request.setPlaceholderText(
            "ex.: Inkscape — editor de grafică vectorială liber, pentru "
            "ilustrații și diagrame, disponibil pe Linux.")
        self.request.setMaximumHeight(90)
        layout.addWidget(self.request)

        self.generate_btn = QPushButton("Generează propunerea")
        self.generate_btn.clicked.connect(self._generate)
        layout.addWidget(self.generate_btn)

        self.status = QLabel("—")
        self.status.setProperty("dim", "true")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.output = QTextEdit()
        self.output.setAcceptRichText(False)
        self.output.setPlaceholderText(
            "Propunerea YAML apare aici. O poți edita înainte de a o copia.")
        layout.addWidget(self.output)

        buttons = QHBoxLayout()
        copy_btn = QPushButton("Copiază YAML-ul")
        copy_btn.clicked.connect(self._copy)
        buttons.addWidget(copy_btn)
        save_btn = QPushButton("Salvează ca fișier…")
        save_btn.clicked.connect(self._save)
        buttons.addWidget(save_btn)
        propose_btn = QPushButton("Trimite prin GitHub")
        propose_btn.clicked.connect(self._send_to_github)
        buttons.addWidget(propose_btn)
        buttons.addStretch(1)
        close_btn = QPushButton("Închide")
        close_btn.setProperty("primary", True)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    # ------------------------------------------------------------------ generare
    def _generate(self) -> None:
        cerere = self.request.toPlainText().strip()
        if not cerere:
            self.status.setText("✗ Descrie mai întâi aplicația.")
            return
        self.generate_btn.setEnabled(False)
        self.status.setText("Se generează…")

        def _done(text: str) -> None:
            self.generate_btn.setEnabled(True)
            yaml_text = extract_yaml(text)
            self.output.setPlainText(yaml_text)
            categorii = {c for c, _ in self.catalog.categories}
            date, probleme = validate_proposal(yaml_text, categorii)
            if date is None:
                self.status.setText(
                    "✗ Propunerea nu e YAML valid: " + "; ".join(probleme))
            elif probleme:
                self.status.setText(
                    "⚠ Propunerea e generată, dar are de completat manual: "
                    + "; ".join(probleme))
            else:
                self.status.setText(
                    "✓ Propunerea e validă. Revizuiește și trimite-o prin "
                    "GitHub — ea nu intră în catalog direct.")

        def _failed(message: str) -> None:
            self.generate_btn.setEnabled(True)
            self.status.setText(f"✗ {message}")

        run_in_thread(self, lambda: self.client.generate(cerere), _done, _failed)

    # ------------------------------------------------------------------ actiuni
    def _copy(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.output.toPlainText())
        self.status.setText("✓ YAML copiat în clipboard.")

    def _save(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        text = self.output.toPlainText().strip()
        if not text:
            self.status.setText("✗ Nu e nimic de salvat.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvează propunerea", "propunere.yaml", "YAML (*.yaml)")
        if not path:
            return
        try:
            Path(path).write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            self.status.setText(f"✗ Nu s-a putut salva: {exc}")
            return
        self.status.setText(f"✓ Salvat: {path}")

    def _send_to_github(self) -> None:
        """Deschide fluxul GitHub cu propunerea în clipboard."""
        from PySide6.QtWidgets import QApplication

        text = self.output.toPlainText().strip()
        if not text:
            self.status.setText("✗ Generează o propunere mai întâi.")
            return
        QApplication.clipboard().setText(text)
        QDesktopServices.openUrl(QUrl(links.NEW_ISSUE_URL))
        self.status.setText(
            "✓ Propunerea e în clipboard. Completează issue-ul pe GitHub "
            "și lipește YAML-ul în ea.")

    def closeEvent(self, event) -> None:
        clear_threads(self)
        super().closeEvent(event)


class DonateDialog(QDialog):
    """Modalul „♥ Donează” (sec. 13).

    Butoanele deschid **real** pagini de donație — nu butoane decorative
    dezactivate (review, datoria 6). Destinațiile sunt centralizate în
    `app/links.py`, ca un buton să nu poată ajunge la o pagină inexistentă.
    """

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

        targets = links.donation_targets()
        if not targets:
            none = QLabel("— nu există încă un canal de donații configurat.")
            none.setProperty("dim", "true")
            layout.addWidget(none)
        for target in targets:
            btn = QPushButton(f"♥ {target['label']}  —  {target['note']}")
            btn.setToolTip(target["url"])
            btn.clicked.connect(lambda _, t=target: self._open(t["url"]))
            layout.addWidget(btn)

        hint = QLabel("Fiecare opțiune deschide pagina în browserul implicit — "
                      "aplicația nu atinge plăți sau date financiare.")
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

    def _open(self, url: str) -> None:
        """Deschide pagina de donații în browserul implicit."""
        if not QDesktopServices.openUrl(QUrl(url)):
            hint = QLabel("Nu s-a putut deschide browserul — copiază adresa "
                           "manual din tooltip.")
            hint.setProperty("dim", "true")
            hint.setWordWrap(True)
            self.layout().addWidget(hint)
