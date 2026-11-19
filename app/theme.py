"""Alterna — teme vizuale (sec. 13 din IDEI_PROIECT.md).

Reproduce cele 4 opțiuni din machetă: „A sistemului" (nativ Plasma, fără
stylesheet), „Breeze Dark", „Breeze Light", „Ocean". Culorile sunt cele din
mockup-ui/style.css. Alegerea persistă între sesiuni (QSettings).
"""

from __future__ import annotations

from pathlib import Path

from .paths import resource_path

THEMES = {
    "system": "A sistemului (urmează Plasma)",
    "dark": "Breeze Dark",
    "light": "Breeze Light",
    "ocean": "Ocean (albastru închis)",
}

# Palete — valorile exacte din machetă
_PALETTES = {
    "dark": {
        "bg_window": "#232629", "bg_panel": "#2a2e32", "bg_view": "#1b1e20",
        "bg_hover": "#31363b", "bg_active": "#223d65ff",
        "accent": "#3daee9", "text": "#eff0f1", "text_dim": "#9aa0a6",
        "border": "#3a3f44",
    },
    "light": {
        "bg_window": "#f5f6f7", "bg_panel": "#ffffff", "bg_view": "#eef1f4",
        "bg_hover": "#e3e9ef", "bg_active": "#221d6fc4",
        "accent": "#1d6fc4", "text": "#232629", "text_dim": "#5c6166",
        "border": "#cfd5db",
    },
    "ocean": {
        "bg_window": "#0f1b26", "bg_panel": "#14232f", "bg_view": "#0b151d",
        "bg_hover": "#1b2f3f", "bg_active": "#2200b8d4",
        "accent": "#00b8d4", "text": "#e0f2f7", "text_dim": "#7fa3b0",
        "border": "#23404f",
    },
}

# Comune tuturor temelor (badge-uri de licență — din machetă)
FOSS = "#27ae60"
FREEMIUM = "#f39c12"
COMMERCIAL = "#e74c3c"

# Bifa albă pentru checkbox-uri (cale absolută — QSS nu rezolvă căi relative)
_CHECK_ICON = resource_path("app", "assets", "check.svg").as_posix()


def build_qss(theme: str) -> str:
    """Stylesheet-ul QSS pentru o temă ("" pentru „system" — aspect nativ Plasma)."""
    p = _PALETTES.get(theme)
    if p is None:
        return ""
    return f"""
    QMainWindow, QDialog {{ background: {p['bg_window']}; color: {p['text']}; }}
    QWidget {{ color: {p['text']}; font-family: "Noto Sans", sans-serif; font-size: 13px; }}
    /* NOTĂ: QWidget{{color}} NU ajunge la QLabel-urile din containere QWidget pure
       (constatat empiric pe Qt6/Fusion) — de aceea QLabel are regulă explicită: */
    QLabel {{ color: {p['text']}; }}
    QToolTip {{ background: {p['bg_panel']}; color: {p['text']};
                border: 1px solid {p['border']}; padding: 4px; }}

    QFrame#panel, QFrame#appCard, QFrame#fact {{
        background: {p['bg_panel']}; border: 1px solid {p['border']}; border-radius: 6px;
    }}
    QFrame#appCard:hover {{ border-color: {p['accent']}; background: {p['bg_hover']}; }}
    QFrame#appCard[selected="true"] {{ border: 2px solid {p['accent']}; }}
    /* containerele de conținut sunt QWidget pur (nu QFrame) — selector fără clasă: */
    #view {{ background: {p['bg_view']}; border: none; }}

    QLabel[dim="true"] {{ color: {p['text_dim']}; }}
    QLabel[h1="true"] {{ font-size: 20px; font-weight: bold; color: {p['text']}; }}
    QLabel[h2="true"] {{ font-size: 15px; font-weight: bold; color: {p['text']}; }}
    QLabel[link="true"] {{ color: {p['accent']}; }}
    QLabel[link="true"]:hover {{ color: {p['text']}; }}
    /* Captura de ecran: imaginea aplicației, cu colț rotunjit. */
    QLabel[screenshot="true"] {{ border: 1px solid {p['border']}; border-radius: 6px;
                                background: {p['bg_view']}; }}

    /* Linkurile de instalare arată ca butoane: sunt acțiuni, nu citări.
       ATENȚIE: hover-ul trebuie să declare și `color` — altfel culoarea textului
       e moștenită de la regula QLabel[link="true"]:hover (culoarea textului
       temei), iar fundalul devine tot aceeași culoare → text alb pe alb,
       invizibil (raportat de utilizator în toate temele). */
    QLabel[installLink="true"] {{ color: {p['bg_view']}; background: {p['accent']};
                                  border: 1px solid {p['accent']}; border-radius: 4px;
                                  padding: 3px 10px; font-weight: bold; }}
    QLabel[installLink="true"]:hover {{ color: {p['text']}; background: {p['bg_window']};
                                        border-color: {p['accent']}; }}

    /* Marcajele de certitudine (sec. 8): verde = verificată, portocaliu =
       estimată, cenușiu = necunoscută. */
    QLabel[conf="auto"] {{ color: {FOSS}; }}
    QLabel[conf="manual"] {{ color: {FOSS}; }}
    QLabel[conf="estimated"] {{ color: {FREEMIUM}; }}
    QLabel[conf="unknown"] {{ color: {p['text_dim']}; }}

    QLabel[badge="foss"] {{ color: {FOSS}; background: #2627ae60; border: 1px solid #5527ae60;
                            border-radius: 4px; padding: 1px 6px; font-size: 11px; }}
    QLabel[badge="freemium"] {{ color: {FREEMIUM}; background: #26f39c12; border: 1px solid #55f39c12;
                                border-radius: 4px; padding: 1px 6px; font-size: 11px; }}
    QLabel[badge="commercial"] {{ color: {COMMERCIAL}; background: #26e74c3c; border: 1px solid #55e74c3c;
                                  border-radius: 4px; padding: 1px 6px; font-size: 11px; }}
    QLabel[badge="tag"] {{ color: {p['text_dim']}; background: {p['bg_view']};
                           border: 1px solid {p['border']}; border-radius: 4px;
                           padding: 1px 6px; font-size: 11px; }}
    /* Marcajul „✓ instalat” (punctul 16): starea locală, verificată direct. */
    QLabel[badge="installed"] {{ color: {FOSS}; background: #2627ae60;
                                 border: 1px solid #5527ae60; border-radius: 4px;
                                 padding: 1px 6px; font-size: 11px; }}

    QLineEdit, QComboBox {{
        background: {p['bg_view']}; color: {p['text']};
        border: 1px solid {p['border']}; border-radius: 5px; padding: 5px 8px;
    }}
    /* NOTĂ (bug Qt6/Fusion+QSS, izolat prin bisecție): `padding` și/sau
       `border-radius` pe QComboBox fac textul să se deseneze suprapus vechi/nou
       după schimbarea selecției. QComboBox e separat, fără ele: */
    QComboBox {{
        border-radius: 0; padding: 0;
        min-height: 28px;
    }}
    QLineEdit:focus, QComboBox:focus {{ border-color: {p['accent']}; }}
    /* Editorul de text (propunerea AI): fără regulă, QTextEdit păstra
       fundalul alb al stilului nativ, iar textul lua culoarea deschisă din
       paletă → contrast 1.98:1, text ilizibil pe fundalul temei. */
    QTextEdit, QPlainTextEdit {{
        background: {p['bg_view']}; color: {p['text']};
        border: 1px solid {p['border']}; border-radius: 5px;
        selection-background-color: {p['accent']};
    }}
    /* Listele și arborii (lista de fișiere din dialogul „Salvează ca fișier…”):
       itemele folosesc paleta, nu culoarea QWidget — deci au nevoie de
       regulă proprie, cu text lizibil. */
    QAbstractItemView {{ color: {p['text']}; }}
    QListView, QTreeView, QTableView {{
        background: {p['bg_view']}; color: {p['text']};
        border: 1px solid {p['border']}; border-radius: 5px;
        selection-background-color: {p['accent']};
    }}
    QComboBox QAbstractItemView {{
        background: {p['bg_panel']}; color: {p['text']};
        border: 1px solid {p['border']}; selection-background-color: {p['accent']};
    }}

    QPushButton {{
        background: {p['bg_panel']}; color: {p['text']};
        border: 1px solid {p['border']}; border-radius: 5px; padding: 6px 12px;
    }}
    QPushButton:hover {{ background: {p['bg_hover']}; border-color: {p['accent']}; }}
    QPushButton:disabled {{ color: {p['text_dim']}; }}
    QPushButton[primary="true"] {{
        background: {p['accent']}; color: {p['bg_window']}; font-weight: bold;
    }}
    QPushButton[flat="true"] {{ border: none; background: transparent; }}
    QPushButton[flat="true"]:hover {{ color: {p['accent']}; }}

    QListWidget {{
        background: {p['bg_view']}; border: 1px solid {p['border']};
        border-radius: 6px; outline: none;
    }}
    QListWidget::item {{ padding: 6px 8px; border-radius: 4px; }}
    QListWidget::item:hover {{ background: {p['bg_hover']}; }}
    QListWidget::item:selected {{ background: {p['accent']}; color: {p['bg_window']}; }}

    QTableWidget {{
        background: {p['bg_panel']}; gridline-color: {p['border']};
        border: 1px solid {p['border']}; border-radius: 6px;
    }}
    QTableWidget::item {{ padding: 4px; }}
    QHeaderView::section {{
        background: {p['bg_panel']}; color: {p['text_dim']};
        border: none; border-bottom: 1px solid {p['border']}; padding: 6px;
    }}

    QScrollArea {{ border: none; background: transparent; }}
    /* Conținutul derulant din Setări: fundalul temei, nu al paletei. */
    QWidget#settingsContent {{ background: {p['bg_window']}; }}
    QScrollBar:vertical {{ background: {p['bg_view']}; width: 10px; border-radius: 5px; }}
    QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p['text_dim']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: {p['bg_view']}; height: 10px; border-radius: 5px; }}
    QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 5px; min-width: 30px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    QStatusBar {{ background: {p['bg_panel']}; color: {p['text_dim']};
                  border-top: 1px solid {p['border']}; }}
    QCheckBox {{ spacing: 6px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        background: {p['bg_view']}; border: 1px solid {p['border']};
    }}
    QCheckBox::indicator:hover {{ border-color: {p['accent']}; }}
    QCheckBox::indicator:checked {{
        background: {p['accent']}; border-color: {p['accent']};
        image: url("{_CHECK_ICON}");
    }}
    """


def apply_theme(app, choice: str) -> None:
    """Aplică tema pe QApplication. „system" = stylesheet gol (aspect nativ Plasma).

    NOTĂ: fără unpolish/polish manual pe toate widgeturile — am constatat empiric
    că bucla respectivă strică popup-urile QComboBox create ulterior (apar
    netematizate). setStyleSheet cu conținut nou declanșează singur evenimentul
    StyleSheetChange, iar Qt re-polisează corect widgeturile existente; vederea
    curentă e oricum re-randată de MainWindow la comutarea temei.
    """
    app.setStyleSheet("" if choice == "system" else build_qss(choice))
