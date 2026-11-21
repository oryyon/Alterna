#!/usr/bin/env python3
"""Alterna — reîmprospătarea indicatorilor obiectivi (sec. 8 din IDEI_PROIECT.md).

Actualizează câmpurile `indicators.*` din fișierele YAML (data/apps/) din trei
surse publice, fără chei API:

- **popcon Debian** (`popcon_rank`): o singură descărcare a clasamentului
  by_inst de pe popcon.debian.org, mapare după câmpul `package` (sau `id`).
- **packages.ubuntu.com** (`in_ubuntu_repos`): pachetul există în Ubuntu LTS.
- **GitHub** (`stars`, `latest_release`): API pentru stele (1 apel/repo;
  token opțional prin GITHUB_TOKEN pentru limită mai mare) + feed Atom al
  releases pentru data ultimei versiuni.

Fișierele YAML sunt rescrise in-place cu ruamel.yaml (round-trip), deci
comentariile și formatarea se păstrează. Rulează săptămânal prin GitHub
Actions (.github/workflows/refresh.yml) și deschide PR — fluxul din sec. 7.

Utilizare:
    python tools/refresh_indicators.py [--dry-run] [--only github|popcon|ubuntu]
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from ruamel.yaml import YAML

POPCON_URL = "https://popcon.debian.org/by_inst"
POPCON_GZ_URL = "https://popcon.debian.org/by_inst.gz"
UBUNTU_URL = "https://packages.ubuntu.com/noble/{}"
GITHUB_API = "https://api.github.com/repos/{}"
GITHUB_ATOM = "https://github.com/{}/releases.atom"

UA = {"User-Agent": "Alterna-indicators-refresh (github.com/alterna-app)"}
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def fetch(url: str, timeout: int = 30, token: str | None = None) -> bytes:
    headers = dict(UA)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout).read()


# ---------------------------------------------------------------------- popcon
def load_popcon() -> dict[str, int]:
    """Clasamentul by_inst: {nume_pachet: rang}. O singură descărcare."""
    try:
        raw = fetch(POPCON_GZ_URL)
        text = gzip.decompress(raw).decode("utf-8", "replace")
    except Exception:
        text = fetch(POPCON_URL).decode("utf-8", "replace")
    ranks = {}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2:
            ranks[parts[1]] = int(parts[0].rstrip("."))
    return ranks


# ---------------------------------------------------------------------- ubuntu
def ubuntu_has_package(package: str) -> bool:
    try:
        page = fetch(UBUNTU_URL.format(package)).decode("utf-8", "replace")
        return f"Package: {package}" in page
    except Exception:
        return False


# ---------------------------------------------------------------------- github
def github_repo(url: str) -> str | None:
    """'https://github.com/owner/repo...' → 'owner/repo'."""
    m = re.match(r"https?://github\.com/([^/]+/[^/?#]+)", url or "")
    return m.group(1).rstrip("/") if m else None


def github_stars(repo: str, token: str | None) -> int | None:
    try:
        data = json.loads(fetch(GITHUB_API.format(repo), token=token))
        return data.get("stargazers_count")
    except Exception:
        return None


def github_latest_release(repo: str) -> str | None:
    """Data (YYYY-MM) celei mai recente versiuni, din feed-ul Atom al releases."""
    try:
        root = ET.fromstring(fetch(GITHUB_ATOM.format(repo)))
        entry = root.find(f"{ATOM_NS}entry/{ATOM_NS}updated")
        if entry is not None and entry.text:
            return entry.text[:7]  # YYYY-MM
    except Exception:
        pass
    return None


# ------------------------------------------------------------------ forje diverse
#: Forjele care au API public pentru numarul de stele. GitLab ascunde
#: proiectele la proiecte cu slash, deci drumul se codifică.
FORJE = [
    # GitHub e detectat aici doar ca să fie găsit în `sources` când
    # `stars_url` lipsește; stelele lui se citesc prin API-ul GitHub.
    ("github.com", "github", ""),
    ("codeberg.org", "gitea", "https://codeberg.org/api/v1/repos/{}"),
    ("invent.kde.org", "gitea", "https://invent.kde.org/api/v1/repos/{}"),
    ("gitlab.com", "gitlab", "https://gitlab.com/api/v4/projects/{}"),
    ("gitlab.torproject.org", "gitlab",
     "https://gitlab.torproject.org/api/v4/projects/{}"),
    ("gitlab.gnome.org", "gitlab",
     "https://gitlab.gnome.org/api/v4/projects/{}"),
    ("gitlab.xfce.org", "gitlab",
     "https://gitlab.xfce.org/api/v4/projects/{}"),
]


def repo_din_sursa(url: str) -> tuple[str, str, str] | None:
    """Adresa unui repo din `sources`: (domeniu, tip, cale).

    De exemplu „https://invent.kde.org/office/calligra” → („invent.kde.org”,
    „gitea”, „office/calligra”).
    """
    m = re.match(r"https?://([^/]+)/([^/?#]+(?:/[^/?#]+)*)", url or "")
    if not m:
        return None
    domeniu = m.group(1).lower()
    cale = m.group(2).rstrip("/")
    if cale.endswith(".git"):        # „…/GNOME/baobab.git” → proiectul e
        cale = cale[:-4]              # „GNOME/baobab”
    for host, tip, api in FORJE:
        if domeniu == host:
            return domeniu, tip, cale
    return None


def stele_forja(domeniu: str, tip: str, cale: str) -> int | None:
    """Numarul de stele de la o forja non-GitHub (Gitea / GitLab)."""
    for host, tip_forja, api in FORJE:
        if host != domeniu or tip_forja != tip:
            continue
        if tip == "gitea":
            url = api.format(cale)
            camp = "stars_count"
        else:
            url = api.format(urllib.parse.quote(cale, safe=""))
            camp = "star_count"
        try:
            date = json.loads(fetch(url))
            valoare = date.get(camp)
            return int(valoare) if valoare is not None else None
        except Exception:
            return None
    return None


# ------------------------------------------------------------------------ main
def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=root / "data" / "apps")
    parser.add_argument("--dry-run", action="store_true",
                        help="afișează schimbările fără a scrie fișierele")
    parser.add_argument("--only", choices=["github", "forge", "popcon", "ubuntu"])
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    yaml = YAML()
    yaml.allow_duplicate_keys = False
    yaml.preserve_quotes = True
    yaml.width = 4096  # nu rescrie liniile lungi

    popcon = None
    if args.only in (None, "popcon"):
        try:
            popcon = load_popcon()
            print(f"popcon: {len(popcon)} pachete în clasament")
        except Exception as exc:
            print(f"⚠ popcon indisponibil ({exc}); sar peste", file=sys.stderr)

    changed_files = 0
    for path in sorted(args.data.glob("*.yaml")):
        app = yaml.load(path.read_text(encoding="utf-8"))
        if not isinstance(app, dict):
            continue
        app_id = app.get("id", path.stem)
        package = app.get("package") or app_id
        ind = app.setdefault("indicators", {})
        changes: list[str] = []

        # Ubuntu mai întâi: popcon se actualizează doar dacă pachetul există
        # real în depozite — altfel numele poate aparține altui pachet Debian
        # (ex. „zed" = ZFS Event Daemon, nu editorul Zed).
        # in_ubuntu_repos: false→true NU se scrie automat (risc de coliziune de
        # nume cu pachete neînrudite, ex. „notion" = window manager); se raportează
        # pentru revizuire umană în PR. true→false (eliminări din depozite) se scrie.
        in_repo: bool | None = None
        if args.only in (None, "ubuntu"):
            in_repo = ubuntu_has_package(package)
            current = bool(ind.get("in_ubuntu_repos"))
            if current and not in_repo:
                changes.append("in_ubuntu_repos True → False")
                ind["in_ubuntu_repos"] = False
            elif in_repo and not current:
                print(f"  ? {app_id}: pachetul „{package}” există în Ubuntu — "
                      f"de verificat manual (nu s-a scris)", file=sys.stderr)
                in_repo = current  # nu influența popcon pe baza unei coliziuni posibile

        if popcon is not None and args.only in (None, "popcon"):
            known_packaged = (in_repo if in_repo is not None
                              else bool(ind.get("in_ubuntu_repos"))) or "package" in app
            rank = popcon.get(package) if known_packaged else None
            if ind.get("popcon_rank") != rank:
                changes.append(f"popcon {ind.get('popcon_rank')} → "
                               f"{('#' + str(rank)) if rank else 'null'}")
                ind["popcon_rank"] = rank

        # --- Stelele: GitHub sau alta forja (Gitea/Codeberg, GitLab) ---
        # Candidati: `stars_url` (dacă există) și apoi sursele — unele
        # aplicații au în `stars_url` o adresă fără API (oglindă cgit, grup
        # GitLab), dar au o oglindă pe o forjă cu API în `sources`.
        candidati = []
        if ind.get("stars_url"):
            candidati.append(str(ind["stars_url"]))
        for sursa in app.get("sources") or []:
            if str(sursa) not in candidati:
                candidati.append(str(sursa))

        if args.only in (None, "github", "forge"):
            for url_repo in candidati:
                repo = github_repo(url_repo)
                if repo:
                    if args.only in (None, "github"):
                        stars = github_stars(repo, token)
                        if stars is not None and ind.get("stars") != stars:
                            changes.append(f"stars {ind.get('stars')} → {stars}")
                            ind["stars"] = stars
                        release = github_latest_release(repo)
                        if release and ind.get("latest_release") != release:
                            changes.append(
                                f"latest_release {ind.get('latest_release')} → {release}")
                            ind["latest_release"] = release
                    if ind.get("stars_url") != url_repo:
                        changes.append(f"stars_url → {url_repo}")
                        ind["stars_url"] = url_repo
                    break
                gasit = repo_din_sursa(url_repo)
                if not gasit:
                    continue
                domeniu, tip, cale = gasit
                stele = stele_forja(domeniu, tip, cale)
                if stele is None:
                    continue
                if ind.get("stars") != stele:
                    changes.append(f"stars {ind.get('stars')} → {stele}")
                    ind["stars"] = stele
                adresa = f"https://{domeniu}/{cale}"
                if ind.get("stars_url") != adresa:
                    changes.append(f"stars_url → {adresa}")
                    ind["stars_url"] = adresa
                break

        if changes:
            changed_files += 1
            print(f"{app_id}: " + "; ".join(changes))
            if not args.dry_run:
                with path.open("w", encoding="utf-8") as fh:
                    yaml.dump(app, fh)

    print(f"\n{'(dry-run) ' if args.dry_run else ''}Fișiere actualizate: {changed_files}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
