#!/usr/bin/env python3
"""Alterna — reîmprospătează dimensiunea la instalare din arhiva Ubuntu.

Dimensiunea la instalare era o estimare editorală — și, cum arată
`tools/check_packages.py`, greșită cu un ordin de mărime pentru 78% dintre
aplicațiile cu pachet (VLC: 80 MB în catalog, ~470 MB real).

**Metrica:** dimensiunea totală ocupată de pachet *și de dependențele sale*
în Ubuntu 24.04 — adică „cât ocupă pe disc dacă îl instalez de la zero".
E calculată din indexul arhivei (`Installed-Size` + rezolvarea `Depends`),
deci e **reproducibilă** și verificabilă, nu o estimare.

De ce nu doar `Installed-Size` al pachetului: pentru metapachete
(`vlc`, `chromium-browser`, `firefox`) valoarea e ~0 KB, fiindcă
implementarea reală stă în pachete dependente. Rezolvarea dependențelor
arată dimensiunea reală.

Instrumentul scrie în YAML, in-place, ca `tools/refresh_indicators.py`:
- `details.install_size_mb` — dimensiunea reală, în MB;
- `confidence.details.install_size_mb` — `auto`, pentru că valoarea tocmai
  a fost verificată din arhivă;
- aplicațiile fără pachet Ubuntu (snaps, web, comerciale) rămân `0`
  (web) — nu se inventează nimic.

Utilizare:
    python tools/refresh_sizes.py --dry-run   # doar raportul
    python tools/refresh_sizes.py             # scrie în YAML
"""

from __future__ import annotations

import argparse
import gzip
import io
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"

#: Listele APT locale (indexul arhivei, dacă e deja descărcat).
APT_LISTS = Path("/var/lib/apt/lists")

#: Arhiva Ubuntu Noble — sursa de adevăr, ca fallback.
ARCHIVE_URLS = (
    "http://archive.ubuntu.com/ubuntu/dists/noble/main/binary-amd64/Packages.gz",
    "http://archive.ubuntu.com/ubuntu/dists/noble/universe/binary-amd64/Packages.gz",
)

#: Regex pentru secțiunea de pachet din formatul Debian.
_PKG_RE = re.compile(r"^Package: (\S+)$")
_SIZE_RE = re.compile(r"^Installed-Size: (\d+)$")
_NAME_RE = re.compile(r"^([a-z0-9][a-z0-9+.\-]*)")


class Arhiva:
    """Indexul arhivei Ubuntu: dimensiuni și dependențe per pachet."""

    def __init__(self) -> None:
        self.dimensiuni: dict[str, int] = {}   # MB (Installed-Size)
        self.dependente: dict[str, list[str]] = {}
        self.tranzitionare: set[str] = set()  # pachete care doar tranzitioneaza

    def adauga_index(self, text: str) -> None:
        """Extrage dimensiunile și dependențele dintr-un index Debian."""
        pachet: str | None = None
        dependente: list[str] = []
        for linie in text.splitlines():
            m = _PKG_RE.match(linie)
            if m:
                if pachet and pachet not in self.dependente:
                    self.dependente[pachet] = dependente
                pachet = m.group(1)
                dependente = []
                continue
            if pachet is None:
                continue
            m = _SIZE_RE.match(linie)
            if m:
                # Installed-Size e în KiB; catalogul folosește MB
                self.dimensiuni.setdefault(pachet, int(m.group(1)) // 1024)
                continue
            if linie.startswith("Description: "):
                # „Transitional package - X -> Y snap": pachetul nu conține
                # aplicația, deci dimensiunea lui nu o reprezintă.
                if linie.startswith("Description: Transitional package"):
                    self.tranzitionare.add(pachet)
                continue
            if linie.startswith(("Depends: ", "Pre-Depends: ")):
                for grup in linie.split(": ", 1)[1].split(","):
                    for alternativă in grup.split("|"):
                        mm = _NAME_RE.match(alternativă.strip())
                        if mm:
                            dependente.append(mm.group(1))
        if pachet and pachet not in self.dependente:
            self.dependente[pachet] = dependente

    def footprint(self, pachet: str, vizitate: set[str] | None = None) -> int:
        """Dimensiunea pachetului + a dependențelor sale (în MB)."""
        vizitate = vizitate if vizitate is not None else set()
        if pachet in vizitate or pachet not in self.dimensiuni:
            return 0
        vizitate.add(pachet)
        return (self.dimensiuni[pachet]
                + sum(self.footprint(d, vizitate)
                      for d in self.dependente.get(pachet, [])))


def încarcă_arhiva() -> Arhiva:
    """Indexul arhivei Ubuntu Noble — preferă listele locale, altfel descarcă."""
    arhiva = Arhiva()
    fișiere = sorted(APT_LISTS.glob(
        "archive.ubuntu.com_ubuntu_dists_noble_*_binary-amd64_Packages"))
    if fișiere:
        for fișier in fișiere:
            arhiva.adauga_index(
                fișier.read_text(encoding="utf-8", errors="replace"))
        if arhiva.dimensiuni:
            return arhiva

    for url in ARCHIVE_URLS:
        parte = "/".join(url.split("/")[-3:-2])
        print(f"  descărcare {parte}/…", file=sys.stderr)
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent":
                              "Alterna/0.2 (+https://github.com/oryyon/Alterna)"})
            with urllib.request.urlopen(request, timeout=180) as răspuns:
                text = gzip.decompress(răspuns.read()).decode("utf-8", "replace")
        except OSError as exc:
            print(f"  ⚠ nu s-a putut descărca: {exc}", file=sys.stderr)
            continue
        arhiva.adauga_index(text)
    return arhiva


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="doar raportul, nu scrie în YAML")
    args = parser.parse_args()

    arhiva = încarcă_arhiva()
    if not arhiva.dimensiuni:
        print("✗ nu s-a putut obține indexul arhivei Ubuntu", file=sys.stderr)
        return 1
    print(f"✔ index Ubuntu: {len(arhiva.dimensiuni)} pachete")

    yaml_rw = YAML()
    yaml_rw.preserve_quotes = True
    yaml_rw.width = 4096

    schimbate, verificate, imposibile = 0, 0, 0
    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml_rw.load(cale.read_text(encoding="utf-8"))
        app_id = app.get("id", cale.stem)
        explicit = app.get("package")
        in_repo = bool((app.get("indicators") or {}).get("in_ubuntu_repos"))
        if not explicit and not in_repo:
            # Nu presupunem că id-ul e numele pachetului: aplicația poate nici
            # să nu fie în Ubuntu (ex. „notion” e un window manager ≠ Notion).
            imposibile += 1
            continue
        pachet = explicit or app_id
        if pachet in arhiva.tranzitionare:
            # pachet tranziționar (snap) → dimensiunea .deb nu e a aplicației
            imposibile += 1
            continue
        real = arhiva.footprint(pachet)
        det = app.setdefault("details", {})
        if real <= 0:
            # fără pachet, sau doar metapachet nerezolvabil → nu inventăm
            imposibile += 1
            continue
        vechi = det.get("install_size_mb")
        if vechi == real:
            verificate += 1
            continue
        det["install_size_mb"] = real
        # valoarea tocmai a fost verificată din arhivă → certitudine `auto`
        app.setdefault("confidence", {})["details.install_size_mb"] = "auto"
        schimbate += 1
        print(f"  {app_id:20} {vechi} → {real} MB  (pachet: {pachet})")
        if not args.dry_run:
            with cale.open("w", encoding="utf-8") as fh:
                yaml_rw.dump(app, fh)

    print(f"\n✔ {schimbate} dimensiuni corectate, {verificate} deja corecte, "
          f"{imposibile} fără pachet Ubuntu (rămân 0 = web/necunoscut)")
    if args.dry_run and schimbate:
        print("(rulează fără --dry-run pentru a scrie în YAML)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
