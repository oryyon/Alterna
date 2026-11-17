"""Alterna — pagina de detalii a unei aplicații (sec. 6, 8, 13 din IDEI_PROIECT.md).

Faptele (indicatori obiectivi) sunt afișate în 5 carduri separate — layout agreat.
Lista de alternative e clickabilă (navigare în lanț).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QScrollArea, QVBoxLayout, QWidget)

from .confidence import ConfidenceBadge, field_label
from .db import PLATFORM_LABELS
from .installed import comanda_instalare, linkuri_instalare
from .widgets import (AppCard, IconLabel, LinkLabel, installed_source_label,
                      license_badges, make_badge, source_label)

#: Sursa concretă a rangului popcon (indicatorul e chiar de acolo).
POPCON_URL = "https://popcon.debian.org"


def _release_url(stars_url: str, website: str) -> str:
    """Unde se poate verifica data ultimei versiuni.

    Preferăm pagina de release-uri a repo-ului (sursa reală a indicatorului
    „Ultima versiune", sincronizată automat); altfel, site-ul oficial.
    """
    if stars_url:
        return f"{stars_url.rstrip('/')}/releases"
    return website or ""


def _ubuntu_search_url(name: str) -> str:
    """Căutarea în depozitele Ubuntu după numele aplicației."""
    from urllib.parse import quote

    return f"https://packages.ubuntu.com/search?keywords={quote(name)}"


class DetailView(QScrollArea):
    """Pagina unei aplicații. Emite open_app la click pe o alternativă."""

    open_app = Signal(str)

    def __init__(self, catalog, parent=None):
        super().__init__(parent)
        self.catalog = catalog
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._container = QWidget()
        self._container.setObjectName("view")
        self.setWidget(self._container)

    # ------------------------------------------------------------------ surse
    def open_url(self, url: str) -> None:
        """Deschide o sursă în browserul implicit (sec. 8)."""
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _install_links_block(self, linkuri: list[tuple[str, str]]) -> QFrame:
        """Cardul cu linkuri directe către magazinele de pachete.

        Linkurile folosesc schema standard a magazinului (`apt://`, `snap://`,
        `flathub://`), deci desktopul le deschide cu handlerul lui — un click
        și ajunge la pagina de instalare, fără să tastăm comanda.
        """
        box = QFrame()
        box.setObjectName("fact")
        layout = QVBoxLayout(box)
        titlu = QLabel("Instalează direct")
        titlu.setProperty("dim", "true")
        layout.addWidget(titlu)
        rand = QHBoxLayout()
        rand.setSpacing(8)
        for eticheta, url in linkuri:
            buton = LinkLabel(eticheta, url)
            buton.setProperty("installLink", "true")
            buton.clicked.connect(self.open_url)
            rand.addWidget(buton)
        rand.addStretch(1)
        layout.addLayout(rand)
        indiciu = QLabel("Linkul deschide magazinul implicit al sistemului.")
        indiciu.setProperty("dim", "true")
        layout.addWidget(indiciu)
        return box

    def _sources_block(self, app: dict) -> QFrame:
        """Panoul „Surse": linkuri către sursele citate în fișierul YAML.

        Fiecare sursă e un link clicabil, cu URL-ul complet în tooltip —
        promisiunea „totul e verificabil" devine clicabilă, nu declarativă.
        """
        box = QFrame()
        box.setObjectName("fact")
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(4)

        title = QLabel("🔗 Surse — de unde provin datele")
        title.setProperty("h2", "true")
        box_layout.addWidget(title)

        urls = app.get("sources") or []
        if not urls:
            none = QLabel("— nicio sursă citată încă")
            none.setProperty("dim", "true")
            box_layout.addWidget(none)
            return box

        for url in urls:
            link = LinkLabel(f"🔗 {source_label(url)}", url)
            link.clicked.connect(self.open_url)
            box_layout.addWidget(link)

        hint = QLabel(f"{len(urls)} surse oficiale, din fișierul "
                      f"data/apps/{app['id']}.yaml")
        hint.setProperty("dim", "true")
        box_layout.addWidget(hint)
        return box

    def _confidence_block(self, app: dict) -> QFrame:
        """Panoul „Certitudine": defalajul pe niveluri, pe câmpuri.

        Răspunde la întrebarea „cât de mult te poți baza pe datele acestei
        aplicații?" — grupând câmpurile după nivel, nu lista goală.
        """
        box = QFrame()
        box.setObjectName("fact")
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(4)

        levels = app.get("confidence") or {}
        title = QLabel("◷ Certitudine — cât de mult te poți baza pe aceste date")
        title.setProperty("h2", "true")
        box_layout.addWidget(title)

        if not levels:
            none = QLabel("— nu există marcaje de certitudine")
            none.setProperty("dim", "true")
            box_layout.addWidget(none)
            return box

        # Grupăm câmpurile după nivel, în ordinea puterii (cea mai bună întâi).
        grupuri: dict[str, list[str]] = {}
        for field, level in levels.items():
            grupuri.setdefault(level, []).append(field)

        for level in ("auto", "manual", "estimated", "unknown"):
            fields = grupuri.get(level)
            if not fields:
                continue
            row = QHBoxLayout()
            row.setSpacing(8)
            badge = ConfidenceBadge(level, full=True)
            badge.setAlignment(Qt.AlignTop)
            row.addWidget(badge, 0, Qt.AlignTop)
            names = ", ".join(field_label(f) for f in sorted(fields))
            text = QLabel(names)
            text.setProperty("dim", "true")
            text.setWordWrap(True)
            text.setMinimumWidth(0)
            row.addWidget(text, 1)
            box_layout.addLayout(row)

        legend = QLabel(
            "✓ automat = sincronizat din surse publice · "
            "✓ manual = verificat de un om împotriva sursei · "
            "≈ estimat = valoare editorială · "
            "? necunoscut = nu există valoare")
        legend.setProperty("dim", "true")
        legend.setWordWrap(True)
        legend.setMinimumWidth(0)
        box_layout.addWidget(legend)
        return box

    def show_app(self, app: dict, show_indicators: dict[str, bool],
                 installed=None) -> None:
        # Reconstruim conținutul la fiecare navigare
        content = QWidget()
        content.setObjectName("view")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # --- Antet: pictogramă + nume + badge + descriere + taguri ------------
        header = QHBoxLayout()
        header.setSpacing(14)
        header.addWidget(IconLabel(app, size=64), 0, Qt.AlignTop)
        info = QVBoxLayout()
        title_row = QHBoxLayout()
        title = QLabel(app["name"])
        title.setProperty("h1", "true")
        title_row.addWidget(title)
        for badge in license_badges(app):
            title_row.addWidget(badge)
        title_row.addStretch(1)
        info.addLayout(title_row)
        desc = QLabel(app["description"])
        desc.setWordWrap(True)
        info.addWidget(desc)
        tags_row = QHBoxLayout()
        tags_row.setSpacing(6)
        for p in app["platforms"]:
            tags_row.addWidget(make_badge(PLATFORM_LABELS[p], "tag"))
        for t in app["tags"]:
            tags_row.addWidget(make_badge(f"#{t}", "tag"))
        tags_row.addStretch(1)
        info.addLayout(tags_row)
        header.addLayout(info, 1)
        layout.addLayout(header)

        # --- Fapte: 5 carduri separate (sec. 13), cu sursa citată (sec. 8) ----
        facts = QGridLayout()
        facts.setSpacing(10)
        # (etichetă, valoare, textul sursei, URL-ul sursei, vizibil, câmp)
        # Dacă indicatorul nu are valoare, sursa se descrie ca lipsă — nu se
        # trimite utilizatorul la o pagină care nu are ce verifica.
        fact_data = [
            ("Popcon Ubuntu",
             f"#{app['popcon_rank']}" if app["popcon_rank"] is not None else "—",
             "sursa: popularity-contest" if app["popcon_rank"] is not None
             else "nu e pachet Debian/Ubuntu",
             POPCON_URL if app["popcon_rank"] is not None else "",
             show_indicators.get("popcon", True), "indicators.popcon_rank"),
            ("Stele GitHub",
             f"★ {app['stars']:,}".replace(",", ".") if app["stars"] is not None else "—",
             "sursa: GitHub API" if app["stars"] is not None
             else "fără repo public",
             app["stars_url"] or "",
             show_indicators.get("stars", True), "indicators.stars"),
            ("Ultima versiune", app["latest_release"] or "—",
             "sursa: catalog / Wikidata" if app["latest_release"]
             else "data ultimei versiuni necunoscută",
             _release_url(app["stars_url"], app["website"])
             if app["latest_release"] else "",
             show_indicators.get("release", True), "indicators.latest_release"),
            ("În depozitele Ubuntu",
             "✓ Da — apt install" if app["in_ubuntu_repos"] else "✗ Nu",
             "sursa: apt", _ubuntu_search_url(app["name"]),
             show_indicators.get("repo", True), "indicators.in_ubuntu_repos"),
            ("Preț", "Gratuit" if app["price"] == "free" else "Cu plată",
             "sursa: catalog", app["website"] or "", True, "price"),
        ]
        # Starea locală (punctul 16): fapt verificat direct pe computer, nu
        # valoare de catalog — deci nu primește marcaj de certitudine.
        if installed is not None:
            versiune = f" {installed.version}" if installed.version else ""
            fact_data.append((
                "Pe acest computer",
                f"✓ Instalată ({installed.source}{versiune})",
                f"{installed_source_label(installed.source)}: {installed.name}",
                "", True, ""))
        else:
            comanda = comanda_instalare(app)
            if comanda:
                fact_data.append((
                    "Pe acest computer",
                    "Nu e instalată",
                    f"instalează cu: {comanda[0]} ({comanda[1]})",
                    "", True, ""))
        for i, (label, value, source, url, visible, field) in enumerate(fact_data):
            if not visible:
                continue
            card = QFrame()
            card.setObjectName("fact")
            card_layout = QVBoxLayout(card)
            # Marcajul de certitudine stă pe rândul etichetei: rândul sursei
            # rămâne la lățimea textului, altfel cardul ar împinge grila.
            head_row = QHBoxLayout()
            head_row.setSpacing(6)
            l = QLabel(label)
            l.setProperty("dim", "true")
            head_row.addWidget(l)
            head_row.addStretch(1)
            if field:
                head_row.addWidget(ConfidenceBadge(
                    app.get("confidence", {}).get(field, "unknown")))
            v = QLabel(value)
            v.setProperty("h2", "true")
            if label == "În depozitele Ubuntu" and app["in_ubuntu_repos"]:
                v.setStyleSheet("color: #27ae60;")
            if label == "Pe acest computer" and installed is not None:
                v.setStyleSheet("color: #27ae60;")
            if url:
                # Sursa indicatorului e un link: utilizatorul poate verifica
                # valoarea chiar ea, în browser (sec. 8 — „totul verificabil").
                s = LinkLabel(source, url)
                s.clicked.connect(self.open_url)
            else:
                s = QLabel(source)
                s.setProperty("dim", "true")
            card_layout.addLayout(head_row)
            card_layout.addWidget(v)
            card_layout.addWidget(s)
            # 5 carduri pe rând (sec. 13); dacă sunt mai multe (ex.
            # „Pe acest computer"), restul trece pe rândul următor — altfel
            # cardurile ar depăși lățimea ferestrei.
            facts.addWidget(card, i // 5, i % 5)
        layout.addLayout(facts)

        # --- Instalează direct: linkuri către magazinele de pachete ----------
        linkuri = linkuri_instalare(app)
        if linkuri:
            layout.addWidget(self._install_links_block(linkuri))

        # --- Surse (sec. 8): de unde provin datele aplicației ---------------
        layout.addWidget(self._sources_block(app))

        # --- Certitudine: cât de mult te poți baza pe datele acestei aplicații -
        layout.addWidget(self._confidence_block(app))

        # --- Alternative (navigare în lanț — sec. 6) ---------------------------
        alt_title = QLabel(f"Alternative <small>— {len(app['alternatives'])} "
                           f"programe similare</small>")
        alt_title.setProperty("h2", "true")
        layout.addWidget(alt_title)
        for alt_id in app["alternatives"]:
            alt = self.catalog.get(alt_id)
            if alt is None:
                continue
            card = AppCard(alt, show_indicators)
            card.clicked.connect(self.open_app)
            layout.addWidget(card)
        layout.addStretch(1)

        self.setWidget(content)  # widgetul vechi e șters automat de Qt
