#!/usr/bin/env python3
"""Alterna — genereaza pagina web a catalogului (statica, offline).

Pagina e un mirror al catalogului: aceleasi date, aceeasi regula — fiecare
valoare isi are sursa, iar marcajul de certitudine se vede. Generata din
`catalog.db`, ca nu poata diverge de aplicatia desktop.

Nu e un site dinamic: un singur HTML + un JS mic de cautare/filtru. Se
publica pe GitHub Pages din `site/`.

Utilizare:
    python tools/build_site.py            # scrie in site/
    python tools/build_site.py --out /tmp/site
"""

from __future__ import annotations

import argparse
import html
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "site"

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
input, select { background: var(--panel); color: var(--text);
  border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px;
  font: inherit; }
input { min-width: 260px; }
#rez { color: var(--dim); margin-left: auto; align-self: center; }
.grid { display: grid; gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); }
.card { background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px; }
.card h3 { margin: 0 0 4px; font-size: 16px; }
.card .cat { color: var(--accent); font-size: 12px; text-transform: uppercase;
  letter-spacing: .04em; }
.card p { margin: 6px 0 10px; color: var(--dim); font-size: 14px; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; }
.tag { background: #222834; border: 1px solid var(--border); border-radius: 4px;
  padding: 1px 7px; font-size: 11px; color: var(--dim); }
.meta { margin-top: 10px; font-size: 12px; color: var(--dim);
  display: flex; gap: 12px; flex-wrap: wrap; }
.meta a { color: var(--accent); }
.ok { color: var(--ok); }
footer { padding: 20px 22px; color: var(--dim); border-top: 1px solid var(--border);
  font-size: 13px; }
"""

JS = """
document.getElementById('data-azi').textContent =
  new Date().toLocaleDateString('ro-RO');
const caut = document.getElementById('caut');
const categorie = document.getElementById('categorie');
const rez = document.getElementById('rez');
const carduri = [...document.querySelectorAll('.card')];
function aplica() {
  const q = caut.value.trim().toLowerCase();
  const c = categorie.value;
  let n = 0;
  for (const card of carduri) {
    const t = (card.dataset.caut || '').toLowerCase();
    const viz = (!c || card.dataset.categorie === c) && (!q || t.includes(q));
    card.style.display = viz ? '' : 'none';
    if (viz) n++;
  }
  rez.textContent = n + ' din ' + carduri.length + ' aplicații';
}
caut.addEventListener('input', aplica);
categorie.addEventListener('change', aplica);
aplica();
"""


def citeste_catalog(db: Path) -> tuple[list[dict], list[tuple[str, str]]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    categorii = [(r["slug"], r["name"]) for r in con.execute(
        "SELECT slug, name FROM categories ORDER BY position")]
    aplicatii = []
    for r in con.execute("SELECT * FROM applications ORDER BY popularity"):
        app = dict(r)
        for camp, sql in (
            ("platforms", "SELECT platform FROM platforms WHERE app_id=?"),
            ("tags", "SELECT tag FROM tags WHERE app_id=?"),
            ("alternatives", "SELECT alternative_id FROM alternatives WHERE app_id=?"),
            ("sources", "SELECT url FROM sources WHERE app_id=?"),
        ):
            app[camp] = [x[0] for x in con.execute(sql, (app["id"],))]
        aplicatii.append(app)
    return aplicatii, categorii


def randare(app: dict, nume_categorii: dict[str, str]) -> str:
    nume = html.escape(app["name"])
    categorie = html.escape(nume_categorii.get(app["category"], app["category"]))
    descriere = html.escape(app["description"] or "")
    caut = " ".join([app["name"], app["description"], app["developer"],
                     app["category"], " ".join(app["tags"] or [])]).lower()
    etichete = "".join(f'<span class="tag">{html.escape(t)}</span>'
                       for t in (app["tags"] or []))
    meta = []
    if app.get("stars") is not None:
        meta.append('<span class="ok">★ '
                    + f'{app["stars"]:,}'.replace(",", ".") + "</span>")
    if app.get("latest_release"):
        meta.append(f'<span>versiune {html.escape(app["latest_release"])}</span>')
    if app.get("install_size_mb"):
        meta.append(f'<span>{app["install_size_mb"]} MB</span>')
    if app.get("in_ubuntu_repos"):
        meta.append('<span class="ok">✓ în Ubuntu</span>')
    if app.get("website"):
        meta.append('<a href="' + html.escape(app["website"])
                    + '" rel="noopener">site oficial</a>')
    if app.get("sources"):
        meta.append('<a href="' + html.escape(app["sources"][-1])
                    + '" rel="noopener">sursă</a>')
    return f"""    <article class="card" data-categorie="{html.escape(app['category'])}"
             data-caut="{html.escape(caut)}">
      <div class="cat">{categorie}</div>
      <h3>{nume}</h3>
      <p>{descriere}</p>
      <div class="tags">{etichete}</div>
      <div class="meta">{"".join(meta)}</div>
    </article>"""


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

    aplicatii, categorii = citeste_catalog(args.db)
    nume_categorii = dict(categorii)
    optiuni = "".join(f'<option value="{html.escape(slug)}">'
                      f'{html.escape(nume)}</option>' for slug, nume in categorii)
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
  </div>
  <div class="grid">
{carduri}
  </div>
</main>
<footer>
  Generat din <code>catalog.db</code> cu <code>tools/build_site.py</code> ·
  sursa și licența datelor:
  <a href="https://github.com/oryyon/Alterna">oryyon/Alterna</a>
</footer>
<script src="catalog.js"></script>
</body>
</html>
"""
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "index.html").write_text(pagina, encoding="utf-8")
    (args.out / "style.css").write_text(CSS, encoding="utf-8")
    (args.out / "catalog.js").write_text(JS, encoding="utf-8")
    (args.out / "catalog.json").write_text(
        json.dumps(aplicatii, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK pagina generata: {args.out / 'index.html'} "
          f"({len(aplicatii)} aplicatii, {len(categorii)} categorii)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
