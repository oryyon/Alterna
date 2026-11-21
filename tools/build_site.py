#!/usr/bin/env python3
"""Alterna — generează pagina publică a catalogului (site/).

Pagina e construită din `catalog.db` — **aceeași sursă ca aplicația desktop**,
deci nu poate diverge de ea. Ce se generează:

- `index.html` — lista tuturor aplicațiilor, cu căutare și filtru pe categorie;
  fiecare card duce la pagina de detaliu a aplicației;
- `app/<id>.html` — **pagina de detaliu** a fiecărei aplicații: faptele
  (5 carduri, ca în aplicație), sursele clicabile, butoanele de instalare,
  captura de ecran (cu atribuire) și **mini-matricea de funcționalități**
  (coloana aplicației din matricea categoriei);
- `catalog.json` — datele brute (inclusiv `features` și taxonomia), pentru
  viitoarele funcții ale site-ului (tabel comparativ);
- `screenshots/` — copiile imaginilor folosite (nu intră în pachetul
  aplicației, dar pe site sunt afișate cu sursa indicată).

Utilizare:
    python tools/build_site.py
    python tools/build_site.py --out /tmp/site --db catalog.db
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import (FEATURE_DISPLAY, LICENSE_LABELS,  # noqa: E402
                    PLATFORM_LABELS, TELEMETRY_LABELS)

DEFAULT_OUT = ROOT / "site"
#: De unde vin capturile (sunt resurse ale unor terți — nu intră în pachetul
#: aplicației, dar pe site sunt afișate cu atribuire).
SURSA_CAPTURI = ROOT / "data" / "screenshots"

#: Marcajele de certitudine (sec. 8) — aceleași ca în aplicație.
CERTITUDINE = {
    "auto": ("⟳", "verificată automat"),
    "manual": ("✓", "verificată manual"),
    "estimated": ("≈", "estimată"),
    "unknown": ("?", "necunoscută"),
}

CSS = """
:root {
  --bg: #12151a; --panel: #1a1f27; --text: #e7ecf3; --dim: #9aa7b8;
  --accent: #4aa3ff; --ok: #27ae60; --border: #2a313d;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
header { padding: 28px 22px 18px; border-bottom: 1px solid var(--border); }
h1 { margin: 0 0 6px; font-size: 24px; }
header p { margin: 0; color: var(--dim); }
main { padding: 18px 22px 60px; max-width: 1180px; margin: 0 auto; }
.bar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
.bar input, .bar select { background: var(--panel); color: var(--text);
  border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px;
  font: inherit; }
.bar input { min-width: 260px; }
.grid { display: grid; gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.card { background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px 16px; }
.card:hover { border-color: var(--accent); }
.card h3 { margin: 0 0 4px; font-size: 16px; }
.card .cat { color: var(--accent); font-size: 12px; text-transform: uppercase;
  letter-spacing: .04em; }
.card p { margin: 6px 0 10px; color: var(--dim); font-size: 14px; }
.tags span { display: inline-block; background: #1f2733; color: var(--dim);
  border-radius: 10px; padding: 1px 8px; font-size: 12px; margin-right: 4px; }
.meta { font-size: 13px; color: var(--dim); }
.meta a, a { color: var(--accent); text-decoration: none; }
.meta a:hover, a:hover { text-decoration: underline; }
.ok { color: var(--ok); }
footer { border-top: 1px solid var(--border); color: var(--dim);
  font-size: 13px; padding: 18px 22px; max-width: 1180px; margin: 0 auto; }
code { background: #1f2733; border-radius: 4px; padding: 1px 5px; }

/* --- pagina de detaliu --- */
.crumb { font-size: 13px; margin-bottom: 4px; }
.desc { color: var(--text); font-size: 17px; max-width: 70ch; }
.submeta { color: var(--dim); font-size: 14px; margin-top: 8px; }
.instalare { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.instalare a { border: 1px solid var(--border); border-radius: 6px;
  padding: 6px 12px; font-size: 14px; }
.instalare a:hover { border-color: var(--accent); }
.captura { margin: 0 0 20px; }
.captura img { width: 100%; max-width: 720px; border-radius: 8px;
  border: 1px solid var(--border); display: block; }
.captura figcaption { color: var(--dim); font-size: 13px; margin-top: 6px; }
.facts { display: grid; gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.fact { background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px 14px; }
.fact h3 { margin: 0 0 8px; font-size: 14px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--dim); }
.fact p { margin: 3px 0; font-size: 14px; }
.cert { color: var(--dim); font-size: 12px; margin-left: 4px; }
h2 { font-size: 18px; margin: 26px 0 10px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border);
  vertical-align: top; }
th { color: var(--dim); font-weight: 600; font-size: 13px;
  text-transform: uppercase; letter-spacing: .03em; }
.matrice td.val { white-space: nowrap; }
.legenda { color: var(--dim); font-size: 13px; margin-top: 8px; }

/* --- comparatie --- */
.compara { display: grid; gap: 16px; grid-template-columns: 280px 1fr;
  align-items: start; }
.lista { background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px; max-height: 70vh; overflow: auto; }
.app { display: flex; gap: 8px; align-items: baseline; padding: 4px 2px;
  font-size: 14px; cursor: pointer; }
.app .nume { flex: 1; }
.app .cat { color: var(--dim); font-size: 11px; text-transform: uppercase; }
.app.ales .nume { color: var(--accent); font-weight: 600; }
.app.plin { opacity: .45; }
table.compara-t { width: 100%; border-collapse: collapse; font-size: 14px; }
table.compara-t th[scope="row"] { color: var(--dim); font-weight: 500;
  text-align: left; width: 220px; }
table.compara-t td { border-bottom: 1px solid var(--border); padding: 6px 8px;
  vertical-align: top; }
table.compara-t td.avantaj { background: rgba(39, 174, 96, .16); }
table.compara-t tr.grupa th { color: var(--accent); text-transform: uppercase;
  letter-spacing: .04em; font-size: 12px; border-bottom: 1px solid var(--border); }
.nota { color: var(--dim); font-size: 12px; }
.cert { color: var(--dim); font-size: 11px; margin-left: 4px; }
.gol { color: var(--dim); padding: 20px; text-align: center; }
.butoane { display: flex; gap: 8px; margin-bottom: 10px; }
.butoane a, .butoane button { background: var(--panel); color: var(--text);
  border: 1px solid var(--border); border-radius: 6px; padding: 5px 10px;
  font: inherit; font-size: 13px; cursor: pointer; }
"""

JS = """
const carduri = [...document.querySelectorAll('.card')];
const caut = document.getElementById('caut');
const categorie = document.getElementById('categorie');
const rez = document.getElementById('rez');
function filtreaza() {
  const c = categorie.value;
  const q = (caut.value || '').trim().toLowerCase();
  let n = 0;
  for (const card of carduri) {
    const t = (card.dataset.caut || '').toLowerCase();
    const viz = (!c || card.dataset.categorie === c) && (!q || t.includes(q));
    card.style.display = viz ? '' : 'none';
    if (viz) n++;
  }
  rez.textContent = n + ' din ' + carduri.length + ' aplicații';
}
caut.addEventListener('input', filtreaza);
categorie.addEventListener('change', filtreaza);
filtreaza();
document.getElementById('data-azi').textContent =
  new Date().toLocaleDateString('ro-RO');
"""



PAGINA_COMPARATIE = """<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comparație — Alterna</title>
<meta name="description" content="Compară aplicații din catalog cu aceleași criterii
  ca în aplicația desktop: fapte, indicatori și matricea de funcționalități.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <p class="crumb"><a href="index.html">← Catalog</a></p>
  <h1>Comparație între aplicații</h1>
  <p>Alege două până la patru aplicații din aceeași categorie. Se evidențiază doar
     criteriile <strong>verificate</strong> (⟳ automat, ✓ manual) — pe un criteriu
     estimat nu se declară niciun avantaj.</p>
</header>
<main>
  <div class="compara">
    <div>
      <div class="bar">
        <input id="caut" type="search" placeholder="Caută…" aria-label="Caută">
        <select id="categorie" aria-label="Categorie"></select>
      </div>
      <div class="lista" id="lista"></div>
    </div>
    <div>
      <div class="butoane">
        <button id="csv">Descarcă CSV</button>
        <button id="md">Descarcă Markdown</button>
        <span id="rez" class="legenda"></span>
      </div>
      <table class="compara-t">
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>
</main>
<footer>
  Generat din <code>catalog.db</code> cu <code>tools/build_site.py</code> ·
  <a href="https://github.com/oryyon/Alterna">oryyon/Alterna</a>
</footer>
<script src="compara.js"></script>
</body>
</html>
"""

def esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def citește_catalog(db: Path) -> tuple[list[dict], list[tuple[str, str]],
                                      dict[str, list[tuple[str, str]]]]:
    """Aplicațiile, categoriile și taxonomia (rândurile matricei)."""
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    categorii = [(r["slug"], r["name"]) for r in con.execute(
        "SELECT slug, name FROM categories ORDER BY position")]
    taxonomie: dict[str, list[tuple[str, str]]] = {}
    for r in con.execute("SELECT category, key, label FROM taxonomy "
                          "ORDER BY category, position"):
        taxonomie.setdefault(r["category"], []).append((r["key"], r["label"]))

    aplicatii = []
    for r in con.execute("SELECT * FROM applications ORDER BY popularity"):
        app = dict(r)
        for camp, sql in (
            ("platforms", "SELECT platform FROM platforms WHERE app_id=?"),
            ("tags", "SELECT tag FROM tags WHERE app_id=?"),
            ("alternatives", "SELECT alternative_id FROM alternatives WHERE app_id=?"),
            ("sources", "SELECT url FROM sources WHERE app_id=?"),
            ("file_formats", "SELECT format FROM file_formats WHERE app_id=?"),
        ):
            app[camp] = [x[0] for x in con.execute(sql, (app["id"],))]
        app["confidence"] = {x["field"]: x["level"] for x in con.execute(
            "SELECT field, level FROM confidence WHERE app_id=?", (app["id"],))}
        app["features"] = {x["feature_key"]: {"value": x["value"], "note": x["note"]}
                           for x in con.execute(
            "SELECT feature_key, value, note FROM features WHERE app_id=?",
            (app["id"],))}
        aplicatii.append(app)
    con.close()
    return aplicatii, categorii, taxonomie


def marcaj(camp: str, confidence: dict) -> str:
    """Marcajul de certitudine al unui câmp (sec. 8), ca în aplicație."""
    nivel = confidence.get(camp)
    if not nivel:
        return ""
    semn, _ = CERTITUDINE.get(nivel, ("", ""))
    return f'<span class="cert" title="valoare {CERTITUDINE.get(nivel, ("", ""))[1]}">{semn}</span>'


def randare(app: dict, nume_categorii: dict[str, str]) -> str:
    """Cardul aplicației din lista principală (cu link spre pagina ei)."""
    nume = esc(app["name"])
    categorie = esc(nume_categorii.get(app["category"], app["category"]))
    descriere = esc(app["description"] or "")
    caut = " ".join([app["name"], app["description"], app["developer"],
                     app["category"], " ".join(app["tags"] or [])]).lower()
    etichete = "".join(f'<span>{esc(t)}</span>' for t in (app["tags"] or []))
    meta = []
    if app.get("stars") is not None:
        meta.append('<span class="ok">★ '
                    + f'{app["stars"]:,}'.replace(",", ".") + "</span>")
    if app.get("latest_release"):
        meta.append(f'<span>versiune {esc(app["latest_release"])}</span>')
    if app.get("install_size_mb"):
        meta.append(f'<span>{app["install_size_mb"]} MB</span>')
    if app.get("in_ubuntu_repos"):
        meta.append('<span class="ok">✓ în Ubuntu</span>')
    meta.append(f'<a href="app/{esc(app["id"])}.html">detalii →</a>')
    if app.get("website"):
        meta.append('<a href="' + esc(app["website"])
                    + '" rel="noopener">site oficial</a>')
    return f"""    <article class="card" data-categorie="{esc(app['category'])}"
             data-caut="{esc(caut)}">
      <div class="cat">{categorie}</div>
      <h3><a href="app/{esc(app['id'])}.html">{nume}</a></h3>
      <p>{descriere}</p>
      <div class="tags">{etichete}</div>
      <div class="meta">{" ".join(meta)}</div>
    </article>"""


def randare_matrice(app: dict, taxonomie: dict[str, list[tuple[str, str]]]) -> str:
    """Mini-matrice: coloana aplicației din matricea categoriei sale."""
    randuri = taxonomie.get(app["category"]) or []
    if not randuri:
        return ""
    feature = app.get("features") or {}
    corp = []
    for cheie, eticheta in randuri:
        valoare = (feature.get(cheie) or {}).get("value") or "unknown"
        nota = (feature.get(cheie) or {}).get("note")
        corp.append(
            f"      <tr><td>{esc(eticheta)}</td>"
            f'<td class="val">{esc(FEATURE_DISPLAY.get(valoare, valoare))}</td>'
            f"<td>{esc(nota) if nota else ''}</td></tr>")
    return f"""    <table class="matrice">
      <thead><tr><th>Funcționalitate</th><th>{esc(app['name'])}</th>
        <th>Detaliu</th></tr></thead>
      <tbody>
{chr(10).join(corp)}
      </tbody>
    </table>
    <p class="legenda">✓ gratuit · 💲 doar în varianta plătită · ⚠ parțial
      (cu limitări) · ✗ nu · — necunoscut. Matricea completă (cu toate
      aplicațiile categoriei) e în aplicația desktop.</p>"""


def randare_fapte(app: dict, confidence: dict, alternative: dict) -> str:
    """Cele 5 carduri de fapte, ca în pagina de detaliu din aplicație."""
    indicatori = []
    if app.get("stars") is not None:
        legatura = (f' <a href="{esc(app["stars_url"])}" rel="noopener">★ '
                    f'{app["stars"]:,}'.replace(",", ".") + "</a>"
                    ) if app.get("stars_url") else f' ★ {app["stars"]:,}'.replace(",", ".")
        indicatori.append(f"<p>{legatura}{marcaj('indicators.stars', confidence)}</p>")
    if app.get("popcon_rank"):
        indicatori.append(f"<p>popcon #{app['popcon_rank']}"
                          f"{marcaj('indicators.popcon_rank', confidence)}</p>")
    if app.get("latest_release"):
        indicatori.append(f"<p>ultima versiune: {esc(app['latest_release'])}"
                          f"{marcaj('indicators.latest_release', confidence)}</p>")
    if app.get("in_ubuntu_repos") is not None:
        stare = ("✓ în depozitele Ubuntu" if app["in_ubuntu_repos"]
                 else "✗ nu e în depozitele Ubuntu")
        indicatori.append(f"<p>{stare}"
                          f"{marcaj('indicators.in_ubuntu_repos', confidence)}</p>")

    detalii = []
    if app.get("install_size_mb"):
        baza = f' ({esc(app["size_basis"])})' if app.get("size_basis") else ""
        detalii.append(f"<p>dimensiune la instalare: ~{app['install_size_mb']} MB"
                       f"{baza}{marcaj('details.install_size_mb', confidence)}</p>")
    if app.get("first_release_year"):
        detalii.append(f"<p>prima versiune: {app['first_release_year']}"
                       f"{marcaj('details.first_release_year', confidence)}</p>")
    if app.get("file_formats"):
        detalii.append("<p>formate de fișiere: "
                       + ", ".join(esc(f) for f in app["file_formats"])
                       + marcaj("details.file_formats", confidence) + "</p>")
    if app.get("telemetry"):
        detalii.append(f"<p>telemetrie: {esc(TELEMETRY_LABELS.get(app['telemetry'], app['telemetry']))}"
                       f"{marcaj('details.telemetry', confidence)}</p>")
    if app.get("romanian_language") is not None:
        da = app["romanian_language"]
        detalii.append(f"<p>limba română: {'da' if da else 'nu'}"
                       f"{marcaj('details.romanian_language', confidence)}</p>")

    identitate = [f"<p>dezvoltator: {esc(app['developer'])}"
                  f"{marcaj('developer', confidence)}</p>",
                  f"<p>licență: {esc(LICENSE_LABELS.get(app['license'], app['license']))}"
                  f"{marcaj('license', confidence)}</p>",
                  f"<p>preț: {'gratuit' if app.get('price') == 'free' else 'cu plată'}"
                  f"{marcaj('price', confidence)}</p>",
                  "<p>platforme: "
                  + ", ".join(esc(PLATFORM_LABELS.get(p, p)) for p in app["platforms"])
                  + f"{marcaj('platforms', confidence)}</p>"]

    legaturi_alternative = []
    for alt_id in app["alternatives"] or []:
        alt = alternative.get(alt_id)
        if alt:
            legaturi_alternative.append(
                f'<li><a href="{esc(alt_id)}.html">{esc(alt["name"])}</a></li>')
    surse = "".join(f'<li><a href="{esc(u)}" rel="noopener">{esc(u)}</a></li>'
                    for u in app["sources"] or [])

    carduri = [
        ("Indicatori obiectivi", "\n".join(indicatori)),
        ("Detalii", "\n".join(detalii)),
        ("Despre aplicație", "\n".join(identitate)),
        ("Alternative", ("<ul>" + "".join(legaturi_alternative) + "</ul>")
         if legaturi_alternative else "<p>—</p>"),
        ("Surse (verificabile)", f"<ul>{surse}</ul>" if surse else "<p>—</p>"),
    ]
    corp = []
    for titlu, continut in carduri:
        if continut.strip() in ("", "<p>—</p>"):
            continue
        corp.append(f'    <div class="fact"><h3>{titlu}</h3>{continut}</div>')
    return "\n".join(corp)


def pagina_detaliu(app: dict, nume_categorii: dict[str, str],
                   taxonomie: dict[str, list[tuple[str, str]]],
                   alternative: dict[str, dict], sursa_captura: str) -> str:
    """Pagina de detaliu a unei aplicații."""
    categorie = esc(nume_categorii.get(app["category"], app["category"]))
    instalare = []
    if app.get("in_ubuntu_repos") and app.get("package"):
        instalare.append(f'<a href="apt://{esc(app["package"])}">APT</a>')
    if app.get("snap"):
        instalare.append(f'<a href="snap://{esc(app["snap"])}">Snap</a>')
    if app.get("flatpak"):
        instalare.append(f'<a href="flathub://{esc(app["flatpak"])}">Flatpak</a>')
    butoane = (f'<div class="instalare">{"".join(instalare)}</div>'
               if instalare else "")

    captura = ""
    if app.get("screenshot"):
        fisier = Path(app["screenshot"]).name
        captura = (f'    <figure class="captura">\n'
                   f'      <img src="../screenshots/{esc(fisier)}" '
                   f'alt="Captură de ecran pentru {esc(app["name"])}">\n'
                   f'      <figcaption>Captură oficială · '
                   f'<a href="{esc(sursa_captura)}" rel="noopener">sursa</a> · '
                   f'<a href="../credite.html">atribuirea imaginilor</a></figcaption>\n'
                   f'    </figure>\n')

    matrice = randare_matrice(app, taxonomie)
    sectiune_matrice = (f'  <h2>Funcționalități (matricea categoriei „{categorie}")</h2>\n'
                        f"{matrice}\n") if matrice else ""

    return f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(app['name'])} — Alterna</title>
<meta name="description" content="{esc(app['description'] or app['name'])}">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header>
  <p class="crumb"><a href="../">← Catalog</a> · {categorie}</p>
  <h1>{esc(app['name'])}</h1>
  <p class="desc">{esc(app['description'])}</p>
  <p class="submeta">Dezvoltator: {esc(app['developer'])} ·
     Licență: {esc(LICENSE_LABELS.get(app['license'], app['license']))} ·
     Preț: {'gratuit' if app.get('price') == 'free' else 'cu plată'}</p>
{butoane}
</header>
<main>
{captura}  <section class="facts">
{randare_fapte(app, app.get('confidence') or {}, alternative)}
  </section>
{sectiune_matrice}</main>
<footer>
  Generat din <code>catalog.db</code> cu <code>tools/build_site.py</code> ·
  sursa și licența datelor:
  <a href="https://github.com/oryyon/Alterna">oryyon/Alterna</a> ·
  <a href="../credite.html">atribuirea imaginilor</a>
</footer>
</body>
</html>
"""


def pagina_credite(aplicatii: list[dict]) -> str:
    """Atribuirea imaginilor afișate pe site (capturile sunt resurse ale unor terți)."""
    rânduri = []
    for app in aplicatii:
        if not app.get("screenshot"):
            continue
        sursa = sursa_capturii(app)
        if not sursa:
            continue
        rânduri.append(f"    <tr><td>{esc(app['name'])}</td>"
                        f'<td><a href="{esc(sursa)}" rel="noopener">{esc(sursa)}</a></td></tr>')
    return f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Atribuirea imaginilor — Alterna</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <p class="crumb"><a href="index.html">← Catalog</a></p>
  <h1>Atribuirea imaginilor</h1>
  <p>Capturile de ecran sunt resurse ale unor terți (Wikimedia Commons, depozite
     oficiale, site-urile oficiale ale aplicațiilor). Fiecare imagine își are
     sursa mai jos; lista completă, cu autorii și licențele, e în
     <a href="https://github.com/oryyon/Alterna/blob/main/data/screenshots/README.md">
     data/screenshots/README.md</a>.</p>
</header>
<main>
  <table>
    <thead><tr><th>Aplicație</th><th>Sursa imaginii</th></tr></thead>
    <tbody>
{chr(10).join(rânduri)}
    </tbody>
  </table>
</main>
<footer>
  Generat din <code>catalog.db</code> cu <code>tools/build_site.py</code> ·
  <a href="https://github.com/oryyon/Alterna">oryyon/Alterna</a>
</footer>
</body>
</html>
"""


def sursa_capturii(app: dict) -> str:
    """Adresa imaginii oficiale a capturii (dacă o știm)."""
    for url in app.get("sources") or []:
        url = str(url)
        if any(url.lower().endswith(ext) for ext in
               (".png", ".jpg", ".jpeg", ".webp", ".gif")):
            return url
        if "commons.wikimedia.org" in url or "github.com" in url:
            return url
    return app.get("sources", [""])[-1] if app.get("sources") else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="directorul de iesire (implicit: site/)")
    parser.add_argument("--db", type=Path, default=ROOT / "catalog.db")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"✗ nu exista {args.db} — ruleaza intai tools/build_catalog.py",
              file=sys.stderr)
        return 1

    aplicatii, categorii, taxonomie = citește_catalog(args.db)
    nume_categorii = dict(categorii)
    alternative = {a["id"]: a for a in aplicatii}
    out = args.out
    (out / "app").mkdir(parents=True, exist_ok=True)

    # --- index ---
    optiuni = "".join(f'<option value="{esc(slug)}">{esc(nume)}</option>'
                      for slug, nume in categorii)
    carduri = "\n".join(randare(a, nume_categorii) for a in aplicatii)
    pagina = f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alterna — catalogul aplicațiilor FOSS</title>
<meta name="description" content="Catalogul Alterna: {len(aplicatii)} aplicații
  open-source și de birou, pe {len(categorii)} categorii, cu sursa fiecărei
  valori.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>Alterna — catalogul aplicațiilor</h1>
  <p>{len(aplicatii)} aplicații pe {len(categorii)} categorii · fiecare valoare
     își are sursa · generat pe <span id="data-azi"></span></p>
</header>
<main>
  <div class="bar">
    <input id="caut" type="search" placeholder="Caută o aplicație…"
           aria-label="Caută o aplicație">
    <select id="categorie" aria-label="Categorie">
      <option value="">Toate categoriile</option>
      {optiuni}
    </select>
    <span id="rez"></span>
    <a href="compara.html">⇄ Comparație</a>
  </div>
  <div class="grid">
{carduri}
  </div>
</main>
<footer>
  Generat din <code>catalog.db</code> cu <code>tools/build_site.py</code> ·
  sursa și licența datelor:
  <a href="https://github.com/oryyon/Alterna">oryyon/Alterna</a> ·
  <a href="credite.html">atribuirea imaginilor</a>
</footer>
<script src="catalog.js"></script>
</body>
</html>
"""
    (out / "index.html").write_text(pagina, encoding="utf-8")
    (out / "style.css").write_text(CSS, encoding="utf-8")
    (out / "catalog.js").write_text(JS, encoding="utf-8")
    (out / "credite.html").write_text(pagina_credite(aplicatii), encoding="utf-8")
    (out / "compara.html").write_text(PAGINA_COMPARATIE, encoding="utf-8")
    (out / "compara.js").write_text(
        (ROOT / "tools" / "compara.js").read_text(encoding="utf-8"),
        encoding="utf-8")

    # --- paginile de detaliu ---
    copiate = 0
    for app in aplicatii:
        (out / "app" / f"{app['id']}.html").write_text(
            pagina_detaliu(app, nume_categorii, taxonomie, alternative,
                           sursa_capturii(app)),
            encoding="utf-8")
        if app.get("screenshot"):
            sursa = SURSA_CAPTURI / Path(app["screenshot"]).name
            if sursa.exists():
                destinatie = out / "screenshots" / sursa.name
                destinatie.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sursa, destinatie)
                copiate += 1

    # --- catalog.json (cu matricea, pentru funcțiile viitoare ale site-ului) ---
    (out / "catalog.json").write_text(
        json.dumps({"aplicatii": aplicatii,
                    "categorii": [{"slug": s, "name": n} for s, n in categorii],
                    "taxonomie": {c: [{"key": k, "label": l} for k, l in r]
                                  for c, r in taxonomie.items()}},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK site generat: {out / 'index.html'} "
          f"({len(aplicatii)} aplicatii, {len(categorii)} categorii, "
          f"{len(aplicatii)} pagini de detaliu, {copiate} capturi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
