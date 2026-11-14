"""Alterna — pagina de detalii a unei aplicații (sec. 6, 8, 13 din IDEI_PROIECT.md).

Faptele (indicatori obiectivi) sunt afișate în 5 carduri separate — layout agreat.
Lista de alternative e clickabilă (navigare în lanț).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QScrollArea, QVBoxLayout, QWidget)

from .db import PLATFORM_LABELS
from .widgets import AppCard, IconLabel, license_badges, make_badge


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

    def show_app(self, app: dict, show_indicators: dict[str, bool]) -> None:
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
        fact_data = [
            ("Popcon Ubuntu",
             f"#{app['popcon_rank']}" if app["popcon_rank"] is not None else "—",
             "sursa: popularity-contest", show_indicators.get("popcon", True)),
            ("Stele GitHub",
             f"★ {app['stars']:,}".replace(",", ".") if app["stars"] is not None else "—",
             "sursa: GitHub API", show_indicators.get("stars", True)),
            ("Ultima versiune", app["latest_release"] or "—",
             "sursa: catalog / Wikidata", show_indicators.get("release", True)),
            ("În depozitele Ubuntu",
             "✓ Da — apt install" if app["in_ubuntu_repos"] else "✗ Nu",
             "sursa: apt", show_indicators.get("repo", True)),
            ("Preț", "Gratuit" if app["price"] == "free" else "Cu plată",
             "sursa: catalog", True),
        ]
        for i, (label, value, source, visible) in enumerate(fact_data):
            if not visible:
                continue
            card = QFrame()
            card.setObjectName("fact")
            card_layout = QVBoxLayout(card)
            l = QLabel(label)
            l.setProperty("dim", "true")
            v = QLabel(value)
            v.setProperty("h2", "true")
            if label == "În depozitele Ubuntu" and app["in_ubuntu_repos"]:
                v.setStyleSheet("color: #27ae60;")
            s = QLabel(source)
            s.setProperty("dim", "true")
            card_layout.addWidget(l)
            card_layout.addWidget(v)
            card_layout.addWidget(s)
            facts.addWidget(card, 0, i)
        layout.addLayout(facts)

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
