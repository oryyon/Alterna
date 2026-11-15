"""Alterna — widgeturi reutilizabile (carduri de aplicație, badge-uri, pictograme).

Logo-urile reale vin post-MVP (sec. 6); până atunci folosim pictograme generate:
inițiale + culoare derivată stabil din id-ul aplicației.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)

from .db import LICENSE_LABELS, TELEMETRY_LABELS  # noqa: F401  (re-export convenabil)
from .paths import logos_dir

LOGOS_DIR = logos_dir()


class ComboBox(QComboBox):
    """QComboBox cu popup mereu SUB casetă (ca în machetă / HTML <select>).

    Implicit, QComboBox în stilul Fusion deschide popup-ul cu elementul curent
    SUPRAPUS peste casetă (deci popup-ul „urcă" sau „coboară" după selecție).
    Aici îl repoziționăm mereu sub casetă; dacă nu încape pe ecran, îl punem
    deasupra (fallback standard).
    """

    def showPopup(self) -> None:
        super().showPopup()
        popup = self.view().window()
        below = self.mapToGlobal(QPoint(0, self.height()))
        screen = self.screen().availableGeometry()
        if below.y() + popup.height() > screen.bottom():
            popup.move(self.mapToGlobal(QPoint(0, -popup.height())))
        else:
            popup.move(below)


def initials(name: str) -> str:
    """Inițiale pentru pictograma-provizorie (ex. „Adobe Photoshop" → „AP", „GIMP" → „Gi")."""
    words = [w for w in name.split() if w and w[0].isalnum()]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return name[:1].upper() + (name[1:2].lower() if len(name) > 1 else "")


def color_for(app_id: str) -> QColor:
    """Culoare stabilă derivată din id (aceeași la fiecare rulare)."""
    hue = sum((i + 1) * ord(c) for i, c in enumerate(app_id)) % 360
    return QColor.fromHsl(hue, 130, 95)


def source_label(url: str) -> str:
    """Text lizibil pentru o sursă: fără schemă, fără slash final.

    „https://www.gimp.org" → „www.gimp.org"; sursele rămân identificabile
    la un glance, iar URL-ul complet stă în tooltip (sec. 8).
    """
    text = (url or "").strip()
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.rstrip("/")


class LinkLabel(QLabel):
    """Etichetă-hiperlink (sec. 8): click-ul emite URL-ul, îl deschide gazda.

    Emite `clicked` în loc să deschidă browserul singură — așa rămâne
    testabil (offscreen) și controlul rămâne în view-ul care o conține.
    """

    clicked = Signal(str)

    def __init__(self, text: str, url: str, parent=None):
        super().__init__(text, parent)
        self.url = url
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("link", "true")
        self.setToolTip(url)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.url:
            self.clicked.emit(self.url)
        super().mouseReleaseEvent(event)


class IconLabel(QLabel):
    """Pictograma aplicației: logo-ul SVG real dacă există în data/logos/
    (descărcat de tools/fetch_logos.py), altfel inițiale pe pătrat colorat."""

    def __init__(self, app: dict, size: int = 44, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        for ext in ("svg", "png", "jpg"):
            logo = LOGOS_DIR / f"{app['id']}.{ext}"
            if logo.exists():
                margin = max(4, size // 8)
                self.setPixmap(QIcon(str(logo)).pixmap(size - margin, size - margin))
                return
        self.setText(initials(app["name"]))
        c = color_for(app["id"])
        self.setStyleSheet(
            f"background: {c.name()}; color: white; border-radius: 8px; "
            f"font-weight: bold; font-size: {size // 3}px;")


def make_badge(text: str, kind: str) -> QLabel:
    """Badge colorat: kind ∈ foss / freemium / commercial / tag."""
    label = QLabel(text)
    label.setProperty("badge", kind)
    return label


def license_badges(app: dict) -> list[QLabel]:
    """Badge-ul de licență + „cu plată" dacă e cazul (ca în machetă)."""
    badges = [make_badge(LICENSE_LABELS[app["license"]], app["license"])]
    if app["price"] == "paid":
        badges.append(make_badge("cu plată", "commercial"))
    return badges


def indicators_text(app: dict, show: dict[str, bool]) -> str:
    """Indicatorii obiectivi de pe card (sec. 8), respectând comutatoarele din Setări."""
    parts = []
    if show.get("popcon") and app["popcon_rank"] is not None:
        parts.append(f"Popcon: <b>#{app['popcon_rank']}</b>")
    if show.get("stars") and app["stars"] is not None:
        parts.append(f"★ GitHub: <b>{app['stars']:,}</b>".replace(",", "."))
    if show.get("repo") and app["in_ubuntu_repos"]:
        parts.append("✓ în repo Ubuntu")
    if show.get("release") and app["latest_release"]:
        parts.append(f"Ultima versiune: <b>{app['latest_release']}</b>")
    return "  ·  ".join(parts)


class AppCard(QFrame):
    """Card de aplicație (listă + alternative). Clickabil; suportă modul comparație."""

    clicked = Signal(str)

    def __init__(self, app: dict, show_indicators: dict[str, bool],
                 compare_mode: bool = False, selected: bool = False, parent=None):
        super().__init__(parent)
        self.app_id = app["id"]
        self.setObjectName("appCard")
        self.setProperty("selected", selected)
        self.setCursor(Qt.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 10, 10, 10)
        row.setSpacing(12)

        if compare_mode:
            from PySide6.QtWidgets import QCheckBox
            self.check = QCheckBox()
            self.check.setChecked(selected)
            self.check.setAttribute(Qt.WA_TransparentForMouseEvents)  # click pe card
            row.addWidget(self.check, 0, Qt.AlignTop)

        row.addWidget(IconLabel(app), 0, Qt.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(3)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel(app["name"])
        title.setProperty("h2", "true")
        title_row.addWidget(title)
        for badge in license_badges(app):
            title_row.addWidget(badge)
        if app["editors_choice"]:
            pick = QLabel("✎ Recomandarea editorilor")
            pick.setProperty("dim", "true")
            pick.setToolTip("Opinie subiectivă — singura marcată explicit ca atare (sec. 8)")
            title_row.addWidget(pick)
        title_row.addStretch(1)
        info.addLayout(title_row)

        desc = QLabel(app["description"])
        desc.setWordWrap(True)
        info.addWidget(desc)

        meta = indicators_text(app, show_indicators)
        if meta:
            meta_label = QLabel(meta)
            meta_label.setProperty("dim", "true")
            info.addWidget(meta_label)
        row.addLayout(info, 1)

        alt = QLabel(f"<b>{len(app['alternatives'])}</b><br>alternative")
        alt.setAlignment(Qt.AlignCenter)
        alt.setProperty("dim", "true")
        row.addWidget(alt, 0, Qt.AlignVCenter)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.app_id)
        super().mouseReleaseEvent(event)


def empty_state(text: str) -> QWidget:
    """Mesaj când filtrele nu întorc nimic (ca în machetă)."""
    label = QLabel(f"🔍<br><br>{text}")
    label.setAlignment(Qt.AlignCenter)
    label.setProperty("dim", "true")
    label.setWordWrap(True)
    return label
