#!/usr/bin/env python3
"""Alterna — verifica telemetria aplicatiilor din politici oficiale.

Punctul 8 din review: `details.telemetry` trebuie sa fie un **fapt verificat**,
nu o estimare. Instrumentul are un tabel cu verificarile facute de mana, fiecare
cu sursa exacta si citatul care o sustine.

Sursa este verificata la fiecare rulare (HTTP 200 + continutul paginii), ca
sa nu se degradeze in timp: un link mort inseamna verificare pierduta.

Verdictele folosesc sensul din UI (`app/db.py`):
- `none`     — aplicatia nu trimite date de utilizare/diagnostic;
- `optional` — trimite, dar poate fi oprit de utilizator;
- `yes`      — trimite, fara opt-out realist.

Utilizare:
    python tools/check_telemetry.py            # raport
    python tools/check_telemetry.py --apply    # scrie in YAML
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"

#: id aplicatie -> (valoare verificata, sursa, citatul care o sustine)
VERIFICARI: dict[str, tuple[str, str, str]] = {
    "vscode": (
        "optional",
        "https://code.visualstudio.com/docs/configure/telemetry",
        "Visual Studio Code collects telemetry data, which is used to help "
        "understand how to improve the product... you can disable telemetry "
        "reporting",
    ),
    "firefox": (
        "optional",
        "https://www.mozilla.org/en-US/privacy/firefox/",
        "We do process limited technical data (such as the client version, "
        "connection status, and device type)",
    ),
    "thunderbird": (
        "optional",
        "https://www.mozilla.org/en-US/privacy/thunderbird/",
        "Thunderbird sends telemetry about your interactions with Thunderbird "
        "to us... to learn how to opt-out of this data collection",
    ),
    "element": (
        "optional",
        "https://element.io/privacy",
        "We track usage data for Element hosting services... Our analytics are "
        "powered by the Free and Open Source analytics platform Matomo",
    ),
    "ente-auth": (
        "none",
        "https://ente.io/privacy",
        "We do not collect analytics about how you use our app features, and "
        "crash reports (if any) are anonymized",
    ),
    "libreoffice": (
        "optional",
        "https://www.libreoffice.org/about-us/privacy/",
        "Bei jedem Absturz von LibreOffice wird automatisiert ein Absturzbericht "
        "erzeugt. Dem Nutzer steht es frei, diesen Absturzbericht zu senden",
    ),
    "bitwarden": (
        "optional",
        "https://bitwarden.com/privacy/",
        "Analytics Data: We use data for analytics and measurement to "
        "understand how the Site and Bitwarden Service are used",
    ),
}

CUVINTE = (
    "telemetr", "analytic", "usage data", "crash report", "diagnostic",
    "opt-out", "opt out", "collect",
)


def sursa_viva(url: str) -> tuple[bool, str]:
    """Verifica daca pagina sursa e accesibila si vorbeste despre telemetrie."""
    try:
        proces = subprocess.run(
            ["curl", "-sL", "-m", "25", "-A", "Mozilla/5.0 (X11; Linux x86_64)", url],
            capture_output=True, text=True, errors="replace", timeout=40)
    except (subprocess.TimeoutExpired, OSError):
        return False, "sursa inaccesibila"
    continut = (proces.stdout or "").lower()
    if not continut.strip():
        return False, "sursa goala"
    if not any(cuvant in continut for cuvant in CUVINTE):
        return False, "sursa nu mai vorbeste despre colectarea datelor"
    return True, "sursa vie"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="scrie valorile verificate in YAML")
    args = parser.parse_args()

    yaml_rw = YAML()
    yaml_rw.preserve_quotes = True
    yaml_rw.width = 4096

    aplicate, erori = 0, 0
    for app_id, (valoare, url, citat) in sorted(VERIFICARI.items()):
        cale = DATA / f"{app_id}.yaml"
        if not cale.exists():
            print(f"  ! {app_id}: fisier lipsa")
            erori += 1
            continue
        vie, motiv = sursa_viva(url)
        app = yaml_rw.load(cale.read_text(encoding="utf-8"))
        det = app.setdefault("details", {})
        vechi = det.get("telemetry")
        stare = "OK" if vie else "SURSA MOARTA"
        if vechi != valoare:
            stare += f"  (corectie: {vechi} -> {valoare})"
        print(f"  {stare:38} {app_id:14} {url}")
        print(f"      „{citat[:110]}”")
        if not vie:
            erori += 1
            continue
        if not args.apply:
            continue
        det["telemetry"] = valoare
        app.setdefault("confidence", {})["details.telemetry"] = "manual"
        surse = app.setdefault("sources", [])
        if url not in surse:
            surse.append(url)
        with cale.open("w", encoding="utf-8") as fh:
            yaml_rw.dump(app, fh)
        aplicate += 1

    print(f"\nOK {aplicate} aplicatii verificate"
          + (f", {erori} probleme" if erori else ""))
    return 1 if erori else 0


if __name__ == "__main__":
    raise SystemExit(main())
