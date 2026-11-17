"""Alterna — fereastra principală (reproduce macheta mockup-ui/, sec. 13).

Layout: bară de titlu (Propune / Donează / Setări) → bară de căutare + filtre +
sortare → panou categorii (stânga) + vederi stivă (listă / detalii / comparație)
→ bară de stare. Butonul „⇄ Compară" apare doar în liste filtrate (sec. 14).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, QSettings, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QMessageBox, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QMainWindow, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from .compare_view import EXPORT_FORMATS, CompareView
from .db import Catalog
from .detail_view import DetailView
from .dialogs import DonateDialog, SettingsDialog
from .installed import (Installed, aplicatii_neacoperite,
                       detecteaza)
from .links import NEW_ISSUE_URL
from .theme import apply_theme
from .widgets import AppCard, ComboBox, LinkLabel, empty_state

MAX_COMPARE = 4  # limita e configurabilă / poate fi extinsă ulterior (sec. 14)


class DetectWorker(QObject):
    """Detectarea aplicațiilor instalate, într-un thread (sec. 16).

    Interogarea pachetelor poate dura o fracțiune de secundă — suficient
    cât să blochezi interfața, deci rulează în afara thread-ului UI.
    """

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, apps: list[dict]):
        super().__init__()
        self._apps = apps

    def run(self) -> None:
        try:
            rezultat = detecteaza(self._apps)
            # Maparea inversă: aplicațiile instalate care nu-s în catalog.
            neacoperite = aplicatii_neacoperite(self._apps)
        except Exception as exc:  # noqa: BLE001 — UI-ul nu trebuie să cadă
            self.failed.emit(str(exc))
        else:
            self.finished.emit((rezultat, neacoperite))



class MainWindow(QMainWindow):
    def __init__(self, catalog: Catalog, detecta: bool = True):
        super().__init__()
        self.catalog = catalog
        self.settings = QSettings("Alterna", "Alterna")
        #: Detectarea instalării poate fi oprită (din Setări sau la construire).
        self._detect_enabled = detecta

        # Stare (oglindă `state` din machetă)
        self.state = {"search": "", "category": "", "license": "",
                      "platform": "", "price": "", "sort": "", "installed": ""}
        self.compare_mode = False
        self.selected: list[str] = []  # ordonat, max MAX_COMPARE
        self._current_detail: str | None = None  # pagina de detalii afișată
        # Aplicațiile deja instalate pe computer (punctul 16)
        self.installed: dict[str, Installed] = {}
        self._detect_thread: QThread | None = None
        self._detect_worker: DetectWorker | None = None

        self.setWindowTitle("Alterna — descoperă alternative software")
        self.resize(1100, 720)
        self._build_ui()
        self.refresh_list()
        self.status.showMessage("Gata.")
        self._detect_installed()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        # --- Bară de titlu (conținut; decorațiile ferestrei rămân ale lui KWin) ---
        titlebar = QFrame()
        titlebar.setObjectName("panel")
        tb = QHBoxLayout(titlebar)
        tb.setContentsMargins(10, 6, 10, 6)
        name = QLabel("◈ <b>Alterna</b> <span style='color:gray'>— descoperă alternative software</span>")
        tb.addWidget(name)
        tb.addStretch(1)
        propose = QPushButton("＋ Propune")
        propose.setToolTip("Propune o aplicație (deschide GitHub cu un template precompletat)")
        propose.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(NEW_ISSUE_URL)))
        donate = QPushButton("♥ Donează")
        donate.clicked.connect(lambda: DonateDialog(self).exec())
        settings_btn = QPushButton("⚙ Setări")
        settings_btn.clicked.connect(self._open_settings)
        for b in (propose, donate, settings_btn):
            tb.addWidget(b)
        root.addWidget(titlebar)

        # --- Bară de căutare + filtre + sortare -----------------------------------
        toolbar = QFrame()
        toolbar.setObjectName("panel")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(10, 8, 10, 8)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Caută o aplicație… (ex: Photoshop)")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search)
        bar.addWidget(self.search_edit, 1)

        self.filter_license = self._combo(
            [("", "Licență: toate"), ("foss", "Open Source"),
             ("freemium", "Freemium"), ("commercial", "Comercial")],
            lambda v: self._set_state("license", v))
        self.filter_platform = self._combo(
            [("", "Platformă: toate"), ("linux", "Linux"), ("windows", "Windows"),
             ("macos", "macOS"), ("android", "Android"), ("web", "Web")],
            lambda v: self._set_state("platform", v))
        self.filter_price = self._combo(
            [("", "Preț: orice"), ("free", "Gratuit"), ("paid", "Cu plată")],
            lambda v: self._set_state("price", v))
        self.filter_installed = self._combo(
            [("", "Instalare: toate"), ("yes", "Doar instalate"),
             ("no", "Doar neinstalate")],
            lambda v: self._set_state("installed", v))
        self.sort_select = self._combo(
            [("", "Sortare: implicită"), ("az", "Nume A → Z"), ("za", "Nume Z → A"),
             ("recent", "Recent actualizate"), ("mic", "Dimensiune mică → mare")],
            lambda v: self._set_state("sort", v))
        for c in (self.filter_license, self.filter_platform,
                  self.filter_price, self.filter_installed, self.sort_select):
            bar.addWidget(c)
        root.addWidget(toolbar)

        # --- Conținut: categorii + vederi -------------------------------------------
        content = QHBoxLayout()
        content.setContentsMargins(10, 8, 10, 8)
        content.setSpacing(10)

        sidebar = QFrame()
        sidebar.setObjectName("panel")
        sidebar.setFixedWidth(230)
        side = QVBoxLayout(sidebar)
        cat_title = QLabel("Categorii")
        cat_title.setProperty("h2", "true")
        side.addWidget(cat_title)
        self.category_list = QListWidget()
        self.category_list.addItem(f"☰ Toate ({self.catalog.app_count})")
        for slug, label in self.catalog.categories:
            count = len(self.catalog.search(category=slug))
            self.category_list.addItem(f"{label} ({count})")
        self.category_list.currentRowChanged.connect(self._on_category)
        side.addWidget(self.category_list, 1)
        db_status = QLabel(
            f"🟢 Catalog local: <b>{self.catalog.app_count} aplicații</b><br>"
            f"<small>actualizat: {self.catalog.generated_at}</small>")
        db_status.setProperty("dim", "true")
        side.addWidget(db_status)
        content.addWidget(sidebar)

        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)
        root.addLayout(content, 1)

        # Vedere: listă
        list_page = QWidget()
        list_layout = QVBoxLayout(list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        self.list_title = QLabel()
        self.list_title.setProperty("h2", "true")
        self.result_count = QLabel()
        self.result_count.setProperty("dim", "true")
        self.compare_btn = QPushButton("⇄ Compară")
        self.compare_btn.setToolTip("Activează modul de comparare")
        self.compare_btn.clicked.connect(self._toggle_compare_mode)
        header.addWidget(self.list_title)
        header.addWidget(self.result_count)
        header.addStretch(1)
        header.addWidget(self.compare_btn)
        list_layout.addLayout(header)

        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.list_container = QWidget()
        self.list_container.setObjectName("view")
        self.list_box = QVBoxLayout(self.list_container)
        self.list_box.setSpacing(8)
        self.list_scroll.setWidget(self.list_container)
        list_layout.addWidget(self.list_scroll, 1)

        # Bara plutitoare de comparare (sec. 14)
        self.compare_bar = QFrame()
        self.compare_bar.setObjectName("panel")
        cb = QHBoxLayout(self.compare_bar)
        self.compare_count = QLabel()
        self.open_compare_btn = QPushButton("Vezi comparația")
        self.open_compare_btn.setProperty("primary", True)
        self.open_compare_btn.clicked.connect(self._show_comparison)
        cb.addWidget(self.compare_count)
        cb.addStretch(1)
        cb.addWidget(self.open_compare_btn)
        self.compare_bar.setVisible(False)
        list_layout.addWidget(self.compare_bar)
        self.stack.addWidget(list_page)

        # Vedere: detalii
        detail_page = QWidget()
        detail_layout = QVBoxLayout(detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        back = QPushButton("← Înapoi la rezultate")
        back.setProperty("flat", True)
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        detail_layout.addWidget(back, 0, Qt.AlignLeft)
        self.detail_view = DetailView(self.catalog)
        self.detail_view.open_app.connect(self._open_detail)
        detail_layout.addWidget(self.detail_view, 1)
        self.stack.addWidget(detail_page)

        # Vedere: comparație
        compare_page = QWidget()
        compare_layout = QVBoxLayout(compare_page)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        actions = QHBoxLayout()
        compare_back = QPushButton("← Înapoi la rezultate")
        compare_back.setProperty("flat", True)
        compare_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.export_format = ComboBox()
        for fmt, (label, _) in EXPORT_FORMATS.items():
            self.export_format.addItem(label, fmt)
        export_btn = QPushButton("💾 Salvează în fișier")
        export_btn.setToolTip("Salvează comparația în fișier")
        export_btn.clicked.connect(self._export)
        actions.addWidget(compare_back)
        actions.addStretch(1)
        actions.addWidget(self.export_format)
        actions.addWidget(export_btn)
        compare_layout.addLayout(actions)
        self.compare_view = CompareView()
        self.compare_view.open_app.connect(self._open_detail)
        compare_layout.addWidget(self.compare_view, 1)
        self.stack.addWidget(compare_page)

        # Bară de stare
        from PySide6.QtWidgets import QStatusBar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Gata.")
        self.installed_label = QLabel("Se verifică aplicațiile instalate…")
        self.installed_label.setProperty("dim", "true")
        self.status.addPermanentWidget(self.installed_label)
        #: Aplicațiile instalate care NU sunt în catalog (maparea inversă).
        self.neacoperite: list = []
        self.neacoperite_label = LinkLabel("", "")
        self.neacoperite_label.setProperty("link", "true")
        self.neacoperite_label.setVisible(False)
        self.neacoperite_label.clicked.connect(self._arată_neacoperite)
        self.status.addPermanentWidget(self.neacoperite_label)
        right = QLabel("Offline • SQLite local")
        right.setProperty("dim", "true")
        self.status.addPermanentWidget(right)

    # ------------------------------------------------------------------ ajutătoare
    def _combo(self, items, on_change) -> ComboBox:
        combo = ComboBox()
        # lățimea casetei = textul cel mai lung, fără trunchere cu „..."
        combo.setSizeAdjustPolicy(ComboBox.SizeAdjustPolicy.AdjustToContents)
        for value, label in items:
            combo.addItem(label, value)
        combo.currentIndexChanged.connect(
            lambda i: on_change(combo.itemData(i)))
        return combo

    def _indicator_flags(self) -> dict[str, bool]:
        return {k: self.settings.value(f"show_{k}", True, type=bool)
                for k in ("popcon", "stars", "release", "repo")}

    def _set_state(self, key: str, value: str) -> None:
        self.state[key] = value
        self.refresh_list()

    def _on_search(self, text: str) -> None:
        self.state["search"] = text.strip()
        self.refresh_list()

    def _on_category(self, row: int) -> None:
        if row < 0:
            return
        self.state["category"] = ("" if row == 0
                                  else self.catalog.categories[row - 1][0])
        self.refresh_list()

    # ------------------------------------------------------------------ logica
    def refresh_list(self) -> None:
        results = self.catalog.search(
            category=self.state["category"], text=self.state["search"],
            license_=self.state["license"], platform=self.state["platform"],
            price=self.state["price"], sort=self.state["sort"])

        # Filtrarea după starea de instalare (punctul 16)
        if self.state["installed"]:
            dorite = self.state["installed"] == "yes"
            results = [a for a in results
                       if (a["id"] in self.installed) is dorite]

        # Titlu + număr rezultate (ca în machetă)
        if self.state["category"]:
            title = dict(self.catalog.categories)[self.state["category"]]
        elif self.state["search"]:
            title = f"Căutare: „{self.state['search']}”"
        else:
            title = "Aplicații populare"
        self.list_title.setText(title)
        self.result_count.setText(f"{len(results)} rezultate")

        # Reconstruiește cardurile
        while self.list_box.count():
            item = self.list_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        flags = self._indicator_flags()
        if not results:
            self.list_box.addWidget(empty_state(
                "Nicio aplicație nu corespunde filtrelor.<br>"
                "Încearcă să le relaxezi sau propune o aplicație nouă."))
        for app in results:
            card = AppCard(app, flags, compare_mode=self.compare_mode,
                           selected=app["id"] in self.selected,
                           installed=self.installed.get(app["id"]))
            card.clicked.connect(self._on_card_clicked)
            self.list_box.addWidget(card)
        self.list_box.addStretch(1)

        # „⇄ Compară" doar în liste filtrate; la revenirea la „Toate" se anulează (sec. 14)
        in_filtered = bool(self.state["category"] or self.state["search"])
        self.compare_btn.setVisible(in_filtered)
        if not in_filtered and self.compare_mode:
            self._toggle_compare_mode()

        self.status.showMessage(
            f"Mod comparație activ — {len(self.selected)} selectate."
            if self.compare_mode else
            f"Afișate {len(results)} din {self.catalog.app_count} aplicații.")

    def _on_card_clicked(self, app_id: str) -> None:
        if self.compare_mode:
            self._toggle_select(app_id)
        else:
            self._open_detail(app_id)

    def _open_detail(self, app_id: str) -> None:
        app = self.catalog.get(app_id)
        if app is None:
            return
        self._current_detail = app_id  # pentru re-randare la comutarea temei
        self.detail_view.show_app(app, self._indicator_flags(),
                                  self.installed.get(app_id))
        self.stack.setCurrentIndex(1)
        self.status.showMessage(f"Detalii: {app['name']}")

    # ------------------------------------------------------------------ instalare
    def _detect_installed(self) -> None:
        """Verifică ce aplicații din catalog sunt deja instalate (punctul 16).

        Rulează într-un thread: interogarea sistemului de pachete poate dura
        o fracțiune de secundă, iar interfața nu trebuie să îngheze.
        """
        if not (self._detect_enabled
                and self.settings.value("detect_installed", True, type=bool)):
            self.installed_label.setText("Detectarea instalării: oprită")
            return
        apps = self.catalog.search()
        worker = DetectWorker(apps)
        thread = QThread()
        worker.moveToThread(thread)
        worker.finished.connect(self._on_installed)
        worker.failed.connect(self._on_detect_failed)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        # Referințele Python ale ambelor obiecte trebuie păstrate: altfel
        # garbage collectorul distruge workerul în timp ce thread-ul rulează,
        # iar Qt accesează un obiect C++ deja eliberat → segfault. E aceeași
        # capcană pe care `net.py` o tratează cu `_net_tasks`.
        self._detect_thread = thread
        self._detect_worker = worker
        thread.start()

    def _on_installed(self, rezultat) -> None:
        if isinstance(rezultat, tuple):
            rezultat, neacoperite = rezultat
        else:
            neacoperite = []
        self.installed = rezultat
        self.neacoperite = neacoperite
        n = len(rezultat)
        self.installed_label.setText(
            f"✓ {n} de aplicații instalate" if n != 1
            else ("✓ 1 aplicație instalată" if n
                  else "Nicio aplicație din catalog nu e instalată"))
        # Maparea inversă: ce aplicații are utilizatorul, dar catalogul nu
        # le cunoaște — exact lista de intrări care îmbogățește catalogul.
        m = len(neacoperite)
        self.neacoperite_label.setText(
            f"+{m} necunoscute" if m else "")
        self.neacoperite_label.setVisible(bool(m))
        self.refresh_list()
        if self.stack.currentIndex() == 1 and self._current_detail:
            self._open_detail(self._current_detail)

    def _arată_neacoperite(self) -> None:
        """Arată aplicațiile instalate care nu sunt în catalog.

        Maparea inversă: de aceste intrări se facețează propunerile pentru
        catalog („am aceste aplicații, lipsesc din listă”).
        """
        if not self.neacoperite:
            return
        lista = "\n".join(f"• {i.name} ({i.version})" if i.version
                           else f"• {i.name}"
                           for i in self.neacoperite[:80])
        if len(self.neacoperite) > 80:
            lista += f"\n… și încă {len(self.neacoperite) - 80}"
        QMessageBox.information(
            self, "Aplicații instalate, lipsite din catalog",
            "Catalogul nu conține încă aceste aplicații:\n\n" + lista +
            "\n\nPoți propune-le ca intrări noi (fișierul de propunere e "
            "la .github/ISSUE_TEMPLATE/propunere-aplicatie.yml).")

    def _on_detect_failed(self, mesaj: str) -> None:
        self.installed_label.setText("Starea instalării nu a putut fi verificată")
        self.status.showMessage(f"Detectarea instalării a eșuat: {mesaj}")

    def closeEvent(self, event) -> None:  # noqa: N802 — semnătură Qt
        """Oprește thread-ul de detectare înainte de a închide fereastra."""
        thread = self._detect_thread
        if thread is not None:
            thread.quit()
            thread.wait(2000)
            self._detect_thread = None
        super().closeEvent(event)

    # ------------------------------------------------------------------ comparare
    def _toggle_compare_mode(self) -> None:
        self.compare_mode = not self.compare_mode
        if not self.compare_mode:
            self.selected.clear()
        self.compare_btn.setText("✕ Anulează" if self.compare_mode else "⇄ Compară")
        self.compare_bar.setVisible(self.compare_mode)
        self._update_compare_bar()
        self.refresh_list()

    def _toggle_select(self, app_id: str) -> None:
        if app_id in self.selected:
            self.selected.remove(app_id)
        elif len(self.selected) >= MAX_COMPARE:
            self.status.showMessage(
                f"Poți compara maximum {MAX_COMPARE} aplicații — "
                f"deselectează una mai întâi.")
            return
        else:
            self.selected.append(app_id)
        self._update_compare_bar()
        self.refresh_list()

    def _update_compare_bar(self) -> None:
        n = len(self.selected)
        self.compare_count.setText(f"{n} selectate (max {MAX_COMPARE})")
        self.open_compare_btn.setEnabled(n >= 2)

    def _show_comparison(self) -> None:
        apps = [self.catalog.get(i) for i in self.selected]
        taxonomy = self.catalog.taxonomy(apps[0]["category"])
        self.compare_view.show_comparison(apps, taxonomy)
        self.stack.setCurrentIndex(2)
        self.status.showMessage(
            "Comparație: " + " vs ".join(a["name"] for a in apps))

    def _export(self) -> None:
        out = self.compare_view.export(self, self.export_format.currentData())
        if out:
            self.status.showMessage(f"Comparația a fost salvată: {out.name}")

    # ------------------------------------------------------------------ setări
    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.catalog, self)
        dialog.theme_changed.connect(self._on_theme_changed)
        if dialog.exec() == 0:  # închis fără „Închide" — nu salvăm restul opțiunilor
            return
        self.refresh_list()  # comutatoarele de indicatori se aplică la închidere
        # Detectarea instalării poate fi pornită sau oprită din Setări.
        if self.settings.value("detect_installed", True, type=bool):
            self._detect_installed()
        else:
            self.installed = {}
            self.installed_label.setText("Detectarea instalării: oprită")
            self.refresh_list()

    def _on_theme_changed(self, theme: str) -> None:
        """Previzualizare live a temei (emis de SettingsDialog la fiecare schimbare)."""
        self.settings.setValue("theme", theme)
        apply_theme(self._app(), theme)
        self.refresh_list()
        # Re-randăm vederea curentă: după comutarea temei, widgeturile vechi
        # pot păstra stiluri învechite; conținutul reconstruit e garantat curat.
        if self.stack.currentIndex() == 1 and self._current_detail:
            self._open_detail(self._current_detail)
        elif self.stack.currentIndex() == 2 and len(self.selected) >= 2:
            self._show_comparison()

    def _app(self):
        from PySide6.QtWidgets import QApplication
        return QApplication.instance()
