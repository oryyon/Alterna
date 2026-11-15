"""Alterna — pagina de comparație (sec. 14 și 15 din IDEI_PROIECT.md).

Tabel: aplicațiile ca coloane, cele 14 criterii ca rânduri, cu evidențierea
verde a celei mai bune valori pe rând + matricea de funcționalități normalizată
(doar când toate aplicațiile sunt din aceeași categorie cu taxonomie definită).
Export în 5 formate (md / csv / html / txt / json) cu dialog nativ de salvare.
"""

from __future__ import annotations

import json
from datetime import date
from html import escape
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .confidence import (CONF_COLORS, LEVEL_HINTS, LEVEL_LABELS, LEVEL_MARKS,
                      weakest)
from .db import (FEATURE_DISPLAY, FEATURE_EXPORT, LICENSE_LABELS,
                  PLATFORM_LABELS, TELEMETRY_LABELS, format_size)

BEST_BG = QColor(39, 174, 96, 60)  # verde transparent — „cea mai bună valoare"

def row_confidence(field: str, apps: list[dict]) -> str:
    """Nivelul de certitudine al unui rând: cel mai slab dintre celulele lui.

    Un rând e doar atât de credibil cât cea mai slabă valoare din el — dacă
    o singură aplicație are o valoare estimată, rândul e estimat.
    """
    if not field:
        return "estimated"
    levels = [(a.get("confidence") or {}).get(field, "estimated") for a in apps]
    return weakest(levels)


# ---------------------------------------------------------------------------
# Datele comparației — sursă comună pentru tabel și export (ca în machetă)
# ---------------------------------------------------------------------------

def comparison_rows(apps: list[dict], taxonomy: list[tuple[str, str]],
                    for_export: bool = False) -> list[tuple[str, list[str], dict]]:
    """Returnează rândurile: (etichetă, [valori], {'best': set(indexuri)})."""
    def row(label, values, best=(), field=""):
        return (label, [str(v) for v in values],
                {"best": set(best), "field": field})

    platforms = [", ".join(PLATFORM_LABELS[p] for p in a["platforms"]) for a in apps]
    best_dim = min((a["install_size_mb"] for a in apps
                    if a["install_size_mb"] is not None), default=None)
    best_release = max(a["latest_release"] or "" for a in apps)

    rows = [
        row("Descriere", [a["description"] for a in apps], field="description"),
        row("Dezvoltator", [a["developer"] for a in apps], field="developer"),
        row("Categorie", [a["category_name"] for a in apps], field="category"),
        row("Licență", [LICENSE_LABELS[a["license"]] for a in apps],
            [i for i, a in enumerate(apps) if a["license"] == "foss"],
            field="license"),
        row("Preț", ["Gratuit" if a["price"] == "free" else "Cu plată" for a in apps],
            [i for i, a in enumerate(apps) if a["price"] == "free"],
            field="price"),
        row("Platforme", platforms,
            [i for i, a in enumerate(apps) if "linux" in a["platforms"]],
            field="platforms"),
        row("Site oficial", [a["website"] for a in apps], field="website"),
        row("Dimensiune la instalare",
            [format_size(a["install_size_mb"]) for a in apps],
            [i for i, a in enumerate(apps)
             if a["install_size_mb"] is not None and a["install_size_mb"] == best_dim],
            field="details.install_size_mb"),
        row("Anul primei versiuni", [a["first_release_year"] or "—" for a in apps],
            field="details.first_release_year"),
        row("Ultima versiune", [a["latest_release"] or "—" for a in apps],
            [i for i, a in enumerate(apps) if a["latest_release"] == best_release],
            field="indicators.latest_release"),
        row("Telemetrie", [TELEMETRY_LABELS.get(a["telemetry"], "—") for a in apps],
            [i for i, a in enumerate(apps) if a["telemetry"] == "none"],
            field="details.telemetry"),
        row("Limbă română",
            ["—" if a["romanian_language"] is None
             else ("✓ Da" if not for_export and a["romanian_language"]
                   else "Da" if a["romanian_language"] else "✗ Nu" if not for_export else "Nu")
             for a in apps],
            [i for i, a in enumerate(apps) if a["romanian_language"]],
            field="details.romanian_language"),
        row("Formate de fișiere",
            [", ".join(a["file_formats"]) if a["file_formats"] else "—" for a in apps],
            field="details.file_formats"),
        row("Taguri", [" ".join("#" + t for t in a["tags"]) for a in apps],
            field="tags"),
    ]

    # Matricea de funcționalități (sec. 15): doar aceeași categorie cu taxonomie
    if taxonomy and len({a["category"] for a in apps}) == 1:
        labels = FEATURE_EXPORT if for_export else FEATURE_DISPLAY
        rows.append(row("FUNCȚIONALITĂȚI", [""] * len(apps), field="features"))
        for key, label in taxonomy:
            values = []
            best = []
            for i, a in enumerate(apps):
                feat = a["features"].get(key)
                value = feat["value"] if feat else "unknown"
                values.append(labels[value])
                if value == "free":
                    best.append(i)
            rows.append(row(label, values, best, field="features"))
    return rows


# ---------------------------------------------------------------------------
# Export — cei 5 generatori (porțiți fidel din machetă)
# ---------------------------------------------------------------------------

EXPORT_FORMATS = {
    "md": ("Markdown (*.md)", "text/markdown"),
    "csv": ("CSV (*.csv)", "text/csv"),
    "html": ("HTML (*.html)", "text/html"),
    "txt": ("Text (*.txt)", "text/plain"),
    "json": ("JSON (*.json)", "application/json"),
}


def export_content(fmt: str, apps: list[dict], rows: list[tuple[str, list[str], dict]]) -> str:
    names = [a["name"] for a in apps]
    today = date.today().strftime("%d.%m.%Y")
    plain = [[label, *values] for label, values, _ in rows]

    if fmt == "md":
        line = lambda cells: "| " + " | ".join(cells) + " |"
        return "\n".join([
            f"# Comparație: {' vs '.join(names)}", "",
            f"_Generat cu Alterna — {today}_", "",
            line(["Criteriu", *(f"**{n}**" for n in names)]),
            line(["---"] * (len(names) + 1)),
            *(line(r) for r in plain), "",
        ])
    if fmt == "csv":
        cell = lambda v: '"' + str(v).replace('"', '""') + '"'
        return "\r\n".join(";".join(cell(c) for c in r)
                          for r in [["Criteriu", *names], *plain])
    if fmt == "html":
        return "\n".join([
            '<!DOCTYPE html><html lang="ro"><head><meta charset="utf-8">',
            f"<title>Comparație: {escape(' vs '.join(names))}</title>",
            "<style>body{font-family:sans-serif;margin:2em}"
            "table{border-collapse:collapse}"
            "th,td{border:1px solid #999;padding:6px 10px;text-align:left;vertical-align:top}"
            "th{background:#eee}</style></head><body>",
            f"<h1>Comparație: {escape(' vs '.join(names))}</h1>",
            f"<p><em>Generat cu Alterna — {today}</em></p>",
            "<table><tr><th>Criteriu</th>"
            + "".join(f"<th>{escape(n)}</th>" for n in names) + "</tr>",
            *("<tr><th>" + escape(r[0]) + "</th>"
              + "".join(f"<td>{escape(c)}</td>" for c in r[1:]) + "</tr>" for r in plain),
            "</table></body></html>",
        ])
    if fmt == "txt":
        width = max(len(r[0]) for r in plain + [["Criteriu"]])
        return "\n".join([
            f"COMPARAȚIE: {' vs '.join(names)}",
            f"Generat cu Alterna — {today}",
            "=" * 60, "",
            *(r[0].ljust(width) + "  " + "  |  ".join(r[1:]) for r in plain), "",
        ])
    if fmt == "json":
        return json.dumps({
            "generat": today, "de": "Alterna",
            "aplicatii": names,
            "criterii": {r[0]: r[1:] for r in plain},
        }, ensure_ascii=False, indent=2)
    raise ValueError(f"format necunoscut: {fmt}")


# ---------------------------------------------------------------------------
# Widgetul propriu-zis
# ---------------------------------------------------------------------------

class CompareView(QScrollArea):
    """Tabelul de comparație + legenda. Emite open_app la click pe numele unei aplicații."""

    open_app = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.apps: list[dict] = []
        self.rows: list[tuple[str, list[str], dict]] = []
        self.taxonomy: list[tuple[str, str]] = []

    def show_comparison(self, apps: list[dict], taxonomy: list[tuple[str, str]]) -> None:
        self.apps = apps
        self.taxonomy = taxonomy
        self.rows = comparison_rows(apps, taxonomy)

        content = QWidget()
        content.setObjectName("view")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)

        n = len(apps)
        table = QTableWidget(len(self.rows) + 1, n + 1)
        table.setHorizontalHeaderLabels([""] + [a["name"] for a in apps])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setWordWrap(True)
        # Coloana criteriilor = la conținut; coloanele aplicațiilor împart egal restul
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents)
        for col in range(1, n + 1):
            header.setSectionResizeMode(col, header.ResizeMode.Stretch)

        # Antet: aplicațiile (click pe nume → pagina de detalii, sec. 14)
        for col, a in enumerate(apps, start=1):
            item = QTableWidgetItem(a["name"])
            item.setForeground(QColor("#3daee9"))
            font = item.font()
            font.setBold(True)
            font.setUnderline(True)
            item.setFont(font)
            item.setToolTip(f"Deschide pagina: {a['name']}")
            table.setItem(0, col, item)

        feature_keys = dict(taxonomy)
        matrix_start = next((i for i, (label, _, _) in enumerate(self.rows)
                             if label == "FUNCȚIONALITĂȚI"), None)

        for r, (label, values, meta) in enumerate(self.rows, start=1):
            is_separator = label == "FUNCȚIONALITĂȚI"
            head = QTableWidgetItem("Funcționalități" if is_separator else label)
            f = head.font()
            f.setBold(True)
            head.setFont(f)
            if not is_separator:
                # Marcajul de certitudine al rândului (sec. 8): cel mai slab
                # nivel dintre celulele rândului. E în prima coloană, ca
                # lectura criteriului să nu fie tulburată de dată.
                level = row_confidence(meta.get("field", ""), apps)
                head.setText(f"{LEVEL_MARKS[level]} {label}")
                head.setToolTip(f"Certitudine: {LEVEL_LABELS[level]} — "
                                f"{LEVEL_HINTS[level]}")
                head.setForeground(CONF_COLORS[level])
            table.setItem(r, 0, head)
            if is_separator:
                table.setSpan(r, 0, 1, n + 1)
                continue
            for c, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                if c - 1 in meta["best"]:
                    item.setBackground(BEST_BG)
                # Tooltip cu explicația la „⚠ parțial" (sec. 15)
                # rândul r din tabel = rândul r-1 din self.rows; funcționalitățile
                # încep după separatorul FUNCȚIONALITĂȚI (index matrix_start)
                if matrix_start is not None and r - 1 > matrix_start:
                    key = list(feature_keys)[r - matrix_start - 2]
                    feat = apps[c - 1]["features"].get(key)
                    if feat and feat.get("note"):
                        item.setToolTip(feat["note"])
                table.setItem(r, c, item)

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        # Tabelul trăiește într-un QScrollArea: îi calculăm înălțimea completă
        # și îi oprim scroll-ul intern, ca să deruleze pagina, nu tabelul.
        height = (table.horizontalHeader().height()
                  + sum(table.rowHeight(r) for r in range(table.rowCount())) + 6)
        table.setMinimumHeight(height)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.cellClicked.connect(self._cell_clicked)
        layout.addWidget(table)

        legend = QLabel(
            "🟩 = cea mai bună valoare din selecție, pe acel criteriu. "
            "Click pe numele unei aplicații pentru pagina ei de detalii.<br>"
            "Funcționalitățile sunt <b>normalizate per categorie</b>: aceeași funcție apare "
            "pe același rând, indiferent de denumirea comercială din fiecare aplicație.<br>"
            "⚠ <i>parțial</i> = funcția există, dar cu limitări "
            "(ține cursorul pe celulă pentru explicație).<br>"
            "<b>Certitudine pe rând:</b> ⟳ verificată automat · "
            "✓ verificată manual · ≈ valoare estimată · "
            "? valoare necunoscută. Rândul e marcat cu cel mai slab "
            "nivel dintre celulele lui.")
        legend.setProperty("dim", "true")
        legend.setWordWrap(True)
        layout.addWidget(legend)

        self.setWidget(content)

    def _cell_clicked(self, row: int, col: int) -> None:
        if row == 0 and col >= 1:
            self.open_app.emit(self.apps[col - 1]["id"])

    def export(self, parent: QWidget, fmt: str) -> Path | None:
        """Dialog nativ de salvare + generarea fișierului. Returnează calea sau None."""
        filter_text = EXPORT_FORMATS[fmt][0]
        path, _ = QFileDialog.getSaveFileName(
            parent, "Salvează comparația", f"comparatie-alterna.{fmt}", filter_text)
        if not path:
            return None
        out = Path(path)
        rows = comparison_rows(self.apps, self.taxonomy, for_export=True)
        out.write_text(export_content(fmt, self.apps, rows), encoding="utf-8")
        return out
