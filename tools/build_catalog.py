#!/usr/bin/env python3
"""Alterna — script de build al catalogului.

Citește fișierele-sursă YAML din data/ (sursa adevărului — sec. 7, 17 din
IDEI_PROIECT.md), aplică validările din data/README.md și generează
catalog.db (SQLite) — produs generat automat, NU se editează manual.

Utilizare:
    python tools/build_catalog.py                # data/ -> catalog.db (în rădăcină)
    python tools/build_catalog.py --out build/catalog.db

Cod de ieșire: 0 = succes (eventual cu avertismente), 1 = erori de validare.
Dependențe: Python 3.10+, PyYAML (vezi requirements.txt).
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

import yaml

SCHEMA_VERSION = 2

# --- Valori legale (oglindă data/README.md) -----------------------------------
LICENSES = {"foss", "freemium", "commercial"}
PRICES = {"free", "paid"}
PLATFORMS = {"linux", "windows", "macos", "android", "web"}
TELEMETRY = {"none", "optional", "yes"}
FEATURE_VALUES = {"free", "paid", "partial", "no", "unknown"}
#: Distribuția din care vine dimensiunea la instalare. Dimensiunile din
#: distribuții diferite nu sunt comparabile (un .deb și un AppImage nu se
#: raportează la același lucru), deci comparația se face doar în grupuri.
SIZE_BASES = {"deb", "flatpak", "snap", "appimage", "web", "other"}
ID_RE = re.compile(r"^[a-z0-9-]+$")
RELEASE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
STALE_YEARS = 2  # regula 6: latest_release mai veche de 2 ani -> avertisment

# Câmpuri obligatorii (✅ în specificație)
REQUIRED_FIELDS = [
    "id", "name", "description", "category", "license", "price",
    "developer", "website", "platforms", "tags", "alternatives",
]
# Câmpuri „✅*": cheia trebuie să existe; valoarea poate fi null -> avertisment
REQUIRED_DETAILS = [
    "install_size_mb", "first_release_year", "file_formats",
    "telemetry", "romanian_language",
]
REQUIRED_INDICATORS = ["latest_release", "in_ubuntu_repos"]

# --- Certitudine (sec. 8) ----------------------------------------------------
# Nivelurile declarabile în YAML. „unknown" NU se declară: se deduce
# automat din absența valorii (null/vid) — nu poți verifica ce nu există.
CONFIDENCE_LEVELS = ("auto", "manual", "estimated")
#: Câmpurile de nivel superior care pot purta un marcaj de certitudine.
CONFIDENCE_TOP_FIELDS = (
    "name", "description", "category", "license", "price", "developer",
    "website", "platforms", "tags", "alternatives", "popularity", "features",
)
#: Câmpurile din grupele `details` și `indicators`.
CONFIDENCE_GROUP_FIELDS = {
    "details": ("install_size_mb", "first_release_year", "file_formats",
                "telemetry", "romanian_language"),
    "indicators": ("popcon_rank", "stars", "stars_url", "latest_release",
                   "in_ubuntu_repos"),
}
#: Toate câmpurile marcabile, în ordine stabilă.
CONFIDENCE_FIELDS = (
    CONFIDENCE_TOP_FIELDS
    + tuple(f"details.{f}" for f in CONFIDENCE_GROUP_FIELDS["details"])
    + tuple(f"indicators.{f}" for f in CONFIDENCE_GROUP_FIELDS["indicators"])
)


def known_confidence_field(field: str) -> bool:
    """Adevărat dacă `field` e un câmp care poate purta marcaj."""
    if field in CONFIDENCE_TOP_FIELDS:
        return True
    if "." in field:
        group, key = field.split(".", 1)
        return key in CONFIDENCE_GROUP_FIELDS.get(group, ())
    return False


def confidence_value(app: dict, field: str):
    """Valoarea brută a unui câmp marcabil (None dacă lipsește)."""
    if "." in field:
        group, key = field.split(".", 1)
        return (app.get(group) or {}).get(key)
    return app.get(field)


def is_absent(value) -> bool:
    """Adevărat dacă valoarea e lipsă (nu poate fi verificată)."""
    if value is None:
        return True
    if isinstance(value, (str, list, dict)) and len(value) == 0:
        return True
    return False


def resolve_size_basis(details: dict) -> str:
    """Distribuția din care vine dimensiunea la instalare.

    Implicit: o aplicație web (`install_size_mb: 0`) nu se instalează local,
    iar orice altă aplicație e măsurată ca pachet Debian/Ubuntu — convenția
    din `package` (câmpul e doar override-ul când numele diferă de `id`).
    Poate fi declarat explicit în YAML, pentru aplicațiile distribuite altfel.
    """
    explicit = details.get("size_basis")
    if explicit:
        return explicit
    if details.get("install_size_mb") == 0:
        return "web"
    return "deb"


SCHEMA = """
CREATE TABLE metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE categories (
    slug     TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    position INTEGER NOT NULL
);
CREATE TABLE applications (
    id                 TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    description        TEXT NOT NULL,
    category           TEXT NOT NULL REFERENCES categories(slug),
    license            TEXT NOT NULL,
    price              TEXT NOT NULL,
    developer          TEXT NOT NULL,
    website            TEXT NOT NULL,
    logo               TEXT,
    editors_choice     INTEGER NOT NULL DEFAULT 0,
    popularity         INTEGER,
    install_size_mb    INTEGER,
    size_basis         TEXT NOT NULL DEFAULT 'deb',
    first_release_year INTEGER,
    telemetry          TEXT,
    romanian_language  INTEGER,
    popcon_rank        INTEGER,
    stars              INTEGER,
    stars_url          TEXT,
    latest_release     TEXT,
    in_ubuntu_repos    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE platforms (
    app_id   TEXT NOT NULL REFERENCES applications(id),
    platform TEXT NOT NULL,
    PRIMARY KEY (app_id, platform)
);
CREATE TABLE alternatives (
    app_id         TEXT NOT NULL REFERENCES applications(id),
    alternative_id TEXT NOT NULL REFERENCES applications(id),
    PRIMARY KEY (app_id, alternative_id)
);
CREATE TABLE tags (
    app_id TEXT NOT NULL REFERENCES applications(id),
    tag    TEXT NOT NULL,
    PRIMARY KEY (app_id, tag)
);
CREATE TABLE file_formats (
    app_id TEXT NOT NULL REFERENCES applications(id),
    format TEXT NOT NULL,
    PRIMARY KEY (app_id, format)
);
CREATE TABLE sources (
    app_id TEXT NOT NULL REFERENCES applications(id),
    url    TEXT NOT NULL,
    PRIMARY KEY (app_id, url)
);
CREATE TABLE confidence (
    app_id TEXT NOT NULL REFERENCES applications(id),
    field  TEXT NOT NULL,
    level  TEXT NOT NULL,
    PRIMARY KEY (app_id, field)
);
CREATE TABLE taxonomy (
    category TEXT NOT NULL REFERENCES categories(slug),
    key      TEXT NOT NULL,
    label    TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (category, key)
);
CREATE TABLE features (
    app_id      TEXT NOT NULL REFERENCES applications(id),
    feature_key TEXT NOT NULL,
    value       TEXT NOT NULL,
    note        TEXT,
    PRIMARY KEY (app_id, feature_key),
    FOREIGN KEY (app_id) REFERENCES applications(id)
);
CREATE INDEX idx_apps_category ON applications(category);
CREATE INDEX idx_tags_tag ON tags(tag);
"""


class Reporter:
    """Colectează erorile (blochează build-ul) și avertismentele (nu blochează)."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def load_yaml(path: Path, rep: Reporter):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        rep.error(f"{path.name}: YAML invalid — {exc}")
        return None


def validate_app(path: Path, app: dict, taxonomies: dict[str, set], rep: Reporter) -> None:
    """Validările 1, 2, 4, 5, 6 din data/README.md (la nivel de fișier)."""
    name = path.name
    if not isinstance(app, dict):
        rep.error(f"{name}: conținutul nu este un mapping YAML")
        return

    # Câmpuri obligatorii prezente
    for field in REQUIRED_FIELDS:
        if field not in app or app[field] is None:
            rep.error(f"{name}: câmp obligatoriu lipsă — '{field}'")
    for field in REQUIRED_DETAILS:
        if "details" not in app or field not in app.get("details", {}):
            rep.error(f"{name}: details.{field} lipsește")
        elif app["details"][field] is None:
            rep.warn(f"{name}: details.{field} este null (regula ≥90% acoperire)")
    for field in REQUIRED_INDICATORS:
        if "indicators" not in app or field not in app.get("indicators", {}):
            rep.error(f"{name}: indicators.{field} lipsește")

    # Regula 1: id == numele fișierului, format [a-z0-9-]
    app_id = app.get("id")
    if app_id is not None:
        if app_id != path.stem:
            rep.error(f"{name}: id '{app_id}' ≠ numele fișierului '{path.stem}'")
        if not ID_RE.match(str(app_id)):
            rep.error(f"{name}: id '{app_id}' nu respectă [a-z0-9-]+")

    # Regula 4: enum-uri legale
    if app.get("license") not in LICENSES:
        rep.error(f"{name}: license invalidă — {app.get('license')!r}")
    if app.get("price") not in PRICES:
        rep.error(f"{name}: price invalid — {app.get('price')!r}")
    for p in app.get("platforms", []) or []:
        if p not in PLATFORMS:
            rep.error(f"{name}: platformă invalidă — {p!r}")
    tel = (app.get("details") or {}).get("telemetry")
    if tel is not None and tel not in TELEMETRY:
        rep.error(f"{name}: telemetry invalid — {tel!r}")

    release = (app.get("indicators") or {}).get("latest_release")
    if release is not None:
        if not RELEASE_RE.match(str(release)):
            rep.error(f"{name}: latest_release '{release}' nu are formatul YYYY-MM")
        else:
            year = int(str(release)[:4])
            if date.today().year - year > STALE_YEARS:
                rep.warn(f"{name}: latest_release '{release}' mai veche de {STALE_YEARS} ani")

    # Regula 5: features doar pentru categorii cu taxonomie
    features = app.get("features")
    category = app.get("category")
    if features:
        if category not in taxonomies:
            rep.error(f"{name}: 'features' fără taxonomie pentru categoria {category!r}")
        else:
            for key, val in features.items():
                if key not in taxonomies[category]:
                    rep.error(f"{name}: features.{key} nu există în taxonomia '{category}'")
                value = val.get("value") if isinstance(val, dict) else val
                if value not in FEATURE_VALUES:
                    rep.error(f"{name}: features.{key} = {value!r} invalid "
                              f"(ateptat: {'/'.join(sorted(FEATURE_VALUES))}; "
                              f"atenție: 'no' se scrie cu ghilimele!)")

    # Regula 6: surse
    if not app.get("sources"):
        rep.warn(f"{name}: 'sources' gol — indicatorii trebuie să aibă sursă citată")
    for url in app.get("sources") or []:
        if not str(url).startswith("https://"):
            rep.warn(f"{name}: sursa '{url}' nu e HTTPS — linkul e afișat în UI, "
                     f"deci trebuie să fie sigur")

    # Regula 7: site-ul oficial trebuie să fie și el sursă (verificabilitate)
    website = app.get("website")
    if website and website not in (app.get("sources") or []):
        rep.warn(f"{name}: site-ul oficial '{website}' nu apare în 'sources'")

    # Regula 8: marcajele de certitudine per aplicație
    for field, level in (app.get("confidence") or {}).items():
        if not known_confidence_field(field):
            rep.error(f"{name}: confidence.{field} — câmp necunoscut")
            continue
        if level == "unknown":
            rep.error(f"{name}: confidence.{field} — 'unknown' se deduce automat "
                      f"din valoarea lipsă; nu se declară")
        elif level not in CONFIDENCE_LEVELS:
            rep.error(f"{name}: confidence.{field} — nivel invalid {level!r} "
                      f"(permise: {'/'.join(CONFIDENCE_LEVELS)})")

    # Regula 9: distribuția dimensiunii la instalare (comparabilitate)
    basis = (app.get("details") or {}).get("size_basis")
    if basis is not None and basis not in SIZE_BASES:
        rep.error(f"{name}: details.size_basis invalid {basis!r} "
                  f"(permise: {'/'.join(sorted(SIZE_BASES))})")


def load_confidence_defaults(data_dir: Path, rep: Reporter) -> dict[str, str]:
    """Citește data/confidence.yaml — nivelul implicit per tip de câmp.

    Configurația e sursa adevărului pentru „cât de mult te poți baza pe
    fiecare tip de valoare". O aplicație poate avea alt nivel, declarat în
    fișierul ei YAML (cheia `confidence:`).
    """
    raw = load_yaml(data_dir / "confidence.yaml", rep)
    if not isinstance(raw, dict):
        rep.error("confidence.yaml: conținutul nu e un mapping YAML")
        return {}
    defaults = raw.get("defaults") or {}
    if not isinstance(defaults, dict):
        rep.error("confidence.yaml: 'defaults' nu e un mapping")
        return {}

    for field, level in defaults.items():
        if not known_confidence_field(field):
            rep.error(f"confidence.yaml: câmp necunoscut {field!r}")
            continue
        if level == "unknown":
            rep.error(f"confidence.yaml: {field} — 'unknown' se deduce automat; "
                      f"nu se declară")
        elif level not in CONFIDENCE_LEVELS:
            rep.error(f"confidence.yaml: {field} — nivel invalid {level!r} "
                      f"(permise: {'/'.join(CONFIDENCE_LEVELS)})")

    # Avertisment pentru câmpuri marcabile fără nivel implicit: ar moșteni
    # „estimated" tacit, iar contributorul n-ar ști că trebuie să declare.
    lipsa = [f for f in CONFIDENCE_FIELDS if f not in defaults]
    if lipsa:
        rep.warn(f"confidence.yaml: fără nivel implicit pentru: {', '.join(lipsa)}")
    return defaults


def resolve_confidence(app: dict, defaults: dict[str, str]) -> list[tuple[str, str]]:
    """Nivelul efectiv de certitudine pentru fiecare câmp marcabil.

    Precedență: override-ul din fișierul aplicației > implicitul din
    `confidence.yaml`. Dacă valoarea e lipsă (null/vid), nivelul e „unknown",
    oricât s-ar declara altfel — nu poți verifica ceea ce nu există.
    """
    overrides = app.get("confidence") or {}
    rezultat = []
    for field in CONFIDENCE_FIELDS:
        level = overrides.get(field) or defaults.get(field) or "estimated"
        if is_absent(confidence_value(app, field)):
            level = "unknown"
        rezultat.append((field, level))
    return rezultat


def build(data_dir: Path, out_path: Path) -> bool:
    rep = Reporter()

    # --- Categorii -------------------------------------------------------------
    categories_raw = load_yaml(data_dir / "categories.yaml", rep) or []
    categories = [(c["slug"], c["name"], i) for i, c in enumerate(categories_raw)]
    category_slugs = {c[0] for c in categories}

    # --- Certitudine (sec. 8) --------------------------------------------------
    confidence_defaults = load_confidence_defaults(data_dir, rep)

    # --- Taxonomii -------------------------------------------------------------
    taxonomies: dict[str, set] = {}
    taxonomy_rows: list[tuple[str, str, str, int]] = []
    for tax_file in sorted((data_dir / "taxonomy").glob("*.yaml")):
        tax = load_yaml(tax_file, rep) or {}
        cat = tax.get("category", tax_file.stem)
        keys = set()
        for i, (key, label) in enumerate((tax.get("features") or {}).items()):
            keys.add(key)
            taxonomy_rows.append((cat, key, label, i))
        taxonomies[cat] = keys

    # --- Aplicații ---------------------------------------------------------------
    apps: list[dict] = []
    seen_ids: set[str] = set()
    for app_file in sorted((data_dir / "apps").glob("*.yaml")):
        app = load_yaml(app_file, rep)
        if app is None:
            continue
        # Regula 2: categoria există
        if app.get("category") not in category_slugs:
            rep.error(f"{app_file.name}: categorie necunoscută — {app.get('category')!r}")
        validate_app(app_file, app, taxonomies, rep)
        if app.get("id") in seen_ids:
            rep.error(f"{app_file.name}: id duplicat — {app.get('id')!r}")
        seen_ids.add(app.get("id"))
        apps.append(app)

    # Regula 3: alternatives referă id-uri existente
    for app in apps:
        for alt in app.get("alternatives", []) or []:
            if alt not in seen_ids:
                rep.error(f"{app.get('id')}: alternativă inexistentă — '{alt}'")

    # popularity: avertisment la valori duplicate (ordine editorială ambiguă)
    seen_pop: dict[int, str] = {}
    for app in apps:
        pop = app.get("popularity")
        if pop is None:
            continue
        if pop in seen_pop:
            rep.warn(f"{app.get('id')}: popularity {pop} duplicat "
                     f"(la fel ca {seen_pop[pop]})")
        seen_pop[pop] = app.get("id")

    # --- Raport ------------------------------------------------------------------
    for w in rep.warnings:
        print(f"  ⚠ {w}")
    if rep.errors:
        for e in rep.errors:
            print(f"  ✗ {e}", file=sys.stderr)
        print(f"\nEȘEC: {len(rep.errors)} erori, {len(rep.warnings)} avertismente. "
              f"catalog.db NU a fost generat.", file=sys.stderr)
        return False

    # --- Scrierea bazei de date ----------------------------------------------------
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    con = sqlite3.connect(out_path)
    try:
        with con:
            con.executescript(SCHEMA)
            con.executemany(
                "INSERT INTO categories VALUES (?, ?, ?)", categories)
            con.executemany(
                "INSERT INTO taxonomy VALUES (?, ?, ?, ?)", taxonomy_rows)
            con.executemany(
                "INSERT INTO metadata VALUES (?, ?)",
                [("schema_version", str(SCHEMA_VERSION)),
                 ("generated_at", date.today().isoformat()),
                 ("app_count", str(len(apps)))])

            for app in apps:
                det = app.get("details") or {}
                ind = app.get("indicators") or {}
                con.execute(
                    """INSERT INTO applications VALUES
                       (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (app["id"], app["name"], app["description"], app["category"],
                     app["license"], app["price"], app["developer"], app["website"],
                     app.get("logo"), int(bool(app.get("editors_choice"))),
                     app.get("popularity"),
                     det.get("install_size_mb"), resolve_size_basis(det),
                     det.get("first_release_year"),
                     det.get("telemetry"),
                     None if det.get("romanian_language") is None
                     else int(bool(det["romanian_language"])),
                     ind.get("popcon_rank"), ind.get("stars"), ind.get("stars_url"),
                     ind.get("latest_release"),
                     int(bool(ind.get("in_ubuntu_repos")))))
                for table, column, values in (
                    ("platforms", "platform", app.get("platforms")),
                    ("alternatives", "alternative_id", app.get("alternatives")),
                    ("tags", "tag", app.get("tags")),
                    ("file_formats", "format", det.get("file_formats")),
                    ("sources", "url", app.get("sources")),
                ):
                    con.executemany(
                        f"INSERT INTO {table} (app_id, {column}) VALUES (?, ?)",
                        [(app["id"], v) for v in (values or [])])
                for key, val in (app.get("features") or {}).items():
                    if isinstance(val, dict):
                        value, note = val["value"], val.get("note")
                    else:
                        value, note = val, None
                    con.execute(
                        "INSERT INTO features VALUES (?, ?, ?, ?)",
                        (app["id"], key, value, note))
                # Marcajele de certitudine (sec. 8) — vezi data/confidence.yaml
                con.executemany(
                    "INSERT INTO confidence (app_id, field, level) VALUES (?, ?, ?)",
                    [(app["id"], field, level)
                     for field, level in resolve_confidence(app, confidence_defaults)])
    finally:
        con.close()

    print(f"✔ catalog.db generat: {len(apps)} aplicații, "
          f"{len(categories)} categorii, "
          f"{len(taxonomy_rows)} rânduri de taxonomie "
          f"({len(rep.warnings)} avertismente)")
    return True


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Build catalog Alterna: YAML -> SQLite")
    parser.add_argument("--data", type=Path, default=root / "data",
                        help="directorul-sursă YAML (implicit: data/)")
    parser.add_argument("--out", type=Path, default=root / "catalog.db",
                        help="fișierul SQLite generat (implicit: catalog.db în rădăcină)")
    args = parser.parse_args()

    if not args.data.is_dir():
        print(f"Directorul de date nu există: {args.data}", file=sys.stderr)
        return 1
    return 0 if build(args.data, args.out) else 1


if __name__ == "__main__":
    sys.exit(main())
