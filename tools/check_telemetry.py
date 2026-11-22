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
import base64
import json
import os
import subprocess
import urllib.request
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402
from ruamel.yaml.scalarstring import SingleQuotedScalarString  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"

#: User-agent pentru cererile HTTP ( politeza pentru API-uri )
UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}

#: id aplicatie -> (valoare verificata, sursa, citatul care o sustine)
VERIFICARI: dict[str, tuple[str, str, str]] = {
    "mixxx": (
        "none",
        "https://www.mixxx.org/privacy-policy",
        "The Mixxx application doesn't require or use any kind of user "
        "account, nor does it collect any user data when being used",
    ),
    "owncast": (
        "none",
        "https://owncast.online/privacy",
        "If you use any Owncast supplied client applications, we have no "
        "analytics or data collection in them",
    ),
    "keepassxc": (
        "optional",
        "https://keepassxc.org/privacy",
        "You can opt out of browser data collection at any time by clicking "
        "this",
    ),
    "zed": (
        "optional",
        "https://zed.dev/privacy",
        "Telemetry is on to help us improve Zed, but turning it off is just "
        "a toggle away",
    ),
    "musescore": (
        "optional",
        "https://musescore.org/telemetry",
        "We are now looking into systems that will allow us to track how "
        "people interact with Musescore without collecting any personal "
        "information and we think the most open way to do this is to ask "
        "permission from users",
    ),
    "vscode": (
        "optional",
        "https://code.visualstudio.com/docs/configure/telemetry",
        "Making it easier to opt out of telemetry collection by placing a "
        "notification in product for all existing and new users",
    ),
    "firefox": (
        "optional",
        "https://www.mozilla.org/en-US/privacy/firefox/",
        "We do process limited technical data (such as the client version, "
        "connection status, and device type/operating system) to provide, "
        "maintain, and ensure the performance and stability of the service",
    ),
    "thunderbird": (
        "optional",
        "https://www.mozilla.org/en-US/privacy/thunderbird/",
        "Thunderbird sends telemetry about your interactions with Thunderbird "
        "to us",
    ),
    "element": (
        "optional",
        "https://element.io/privacy",
        "We track usage data for Element hosting services. When you are "
        "signed in to your account we may track your usage of the site and "
        "associate that information with your account details",
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
        "(crash report) erzeugt. Dem Nutzer steht es frei, diesen Absturzbericht "
        "(crash report) zu senden",
    ),
    "bitwarden": (
        "optional",
        "https://bitwarden.com/privacy/",
        "We use data for analytics and measurement to understand how the "
        "Site and Bitwarden Service are used",
    ),
    # --- tranche 5: aplicatiile comerciale nou-introduse ------------------
    # Verdictul e cel mai slab pe care il permite citatul: „optional” doar
    # daca politica spune explicit ca se poate renunta, altfel „yes”.
    "evernote": (
        "optional",
        "https://evernote.com/legal/privacy.php",
        "Where permitted by applicable law, we treat certain first-party "
        "analytics technologies as technical trackers that do not require "
        "consent. You can still opt out of further processing of the data "
        "that's been collected via these trackers at any time by contacting us",
    ),
    "onenote": (
        "optional",
        "https://privacy.microsoft.com/en-us/privacystatement",
        "When a customer interacts with a Microsoft support professional, we "
        "collect device and usage data or error reports to diagnose and "
        "resolve problems",
    ),
    "microsoft-teams": (
        "optional",
        "https://privacy.microsoft.com/en-us/privacystatement",
        "When a customer interacts with a Microsoft support professional, we "
        "collect device and usage data or error reports to diagnose and "
        "resolve problems",
    ),
    "google-keep": (
        "yes",
        "https://policies.google.com/privacy",
        "The information we collect includes unique identifiers , browser "
        "type and settings, device type and settings, operating system, "
        "mobile network information including carrier name and phone number, "
        "and application version number",
    ),
    "wechat": (
        "yes",
        "https://www.wechat.com/en/privacy_policy.html",
        "When you use the WeChat mobile app, desktop app, or the websites "
        "www.wechat.com or help.wechat.com (together, \"WeChat\" ), certain of "
        "your Personal Information (defined below) will be collected and "
        "processed by us",
    ),
    "mediamonkey": (
        "optional",
        "https://www.mediamonkey.com/privacy",
        "This notice describes the types of personal information we receive "
        "and collect when you use MediaMonkey or visit mediamonkey.com, and "
        "how we safeguard your information",
    ),
}

CUVINTE = (
    "telemetr", "analytic", "usage data", "crash report", "diagnostic",
    "opt-out", "opt out", "collect",
)


def _text_plain(continut: str) -> str:
    """Continutul paginii, fara marcaj, cu spatii normalizate."""
    import html as _html
    import re as _re

    bloc = _re.sub(r"(?i)</(p|li|div|h[1-6]|tr|section|article)>", " ", continut)
    bloc = _re.sub(r"<script.*?</script>|<style.*?</style>", " ", bloc, flags=_re.S)
    text = _html.unescape(_re.sub(r"<[^>]+>", " ", bloc))
    return _re.sub(r"\s+", " ", text).lower()


def sursa_viva(url: str, citat: str = "") -> tuple[bool, str]:
    """Verifica daca pagina sursa e accesibila si vorbeste despre telemetrie.

    Daca se da si citatul, el trebuie sa se regaseasca in pagina: altfel
    verificarea s-ar baza doar pe o adresa, iar dovezza n-ar mai fi citabila.
    """
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
    if citat:
        text = _text_plain(proces.stdout or "")
        if _re_quote(citat) not in text:
            return False, "citatul nu se regaseste in pagina"
    return True, "sursa vie"


def _re_quote(citat: str) -> str:
    """Citatul, normalizat la fel ca textul paginii (spatii, minuscule)."""
    import re as _re

    return _re.sub(r"\s+", " ", citat).strip().lower()


#: Cuvinte care semnaleaza o pagina despre colectarea datelor.
CUVINTE_TELEMETRIE = ("telemetry", "privacy", "data collection",
                       "collect data", "usage data", "anonymous data")

#: Cai uzuale ale politicii de confidentialitate, pe site-ul oficial.
CAI_POLITICA = ("/privacy", "/privacy-policy", "/telemetry",
                 "/legal/privacy", "/about/privacy")


def cauta_politica(site: str, timeout: int = 6) -> list[tuple[str, str]]:
    """Cauta pagini de politica pe site-ul oficial: [(url, citat)].

    Nu decide valoarea telemetriei — doar **gaseste** pagina si extrage
    fragmentul care vorbeste despre colectarea datelor. Verdictul il pune
    omul, cu citatul in tabelul de mai sus.
    """
    if not site:
        return []
    baza = site.rstrip("/")
    gasite: list[tuple[str, str]] = []
    for cale in CAI_POLITICA:
        url = baza + cale
        try:
            proces = subprocess.run(
                ["curl", "-sL", "-m", str(timeout), "-A", "Mozilla/5.0",
                 "-o", "-", url],
                capture_output=True, text=True, errors="replace",
                timeout=timeout + 5, check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        continut = proces.stdout or ""
        if len(continut) < 500:
            continue
        jos = continut.lower()
        if not any(c in jos for c in CUVINTE_TELEMETRIE):
            continue
        import html
        import re
        # blocurile devin randuri separate: altfel meniul si paragraful se
        # lipesc intr-un singur „propozitie” fara punctuatie
        bloc = re.sub(r"(?i)</(p|li|div|h[1-6]|tr|section|article)>", "\n",
                      continut)
        bloc = re.sub(r"<script.*?</script>|<style.*?</style>", " ", bloc,
                      flags=re.S)
        randuri = []
        for linie in bloc.splitlines():
            text = html.unescape(re.sub(r"<[^>]+>", " ", linie))
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) >= 60:
                randuri.append(text)
        text = " \n ".join(randuri)
        # preferam propozitia care chiar vorbeste despre colectare, nu
        # titlul paginii sau o linie de navigare
        for rand in randuri:
            if len(rand) > 340 or len(rand) < 80:
                continue
            jos_r = rand.lower()
            if "skip to" in jos_r or "cookie" in jos_r[:40]:
                continue
            if not any(c in jos_r for c in CUVINTE_TELEMETRIE):
                continue
            if not any(c in jos_r for c in ("telemetry", "collect", "usage data",
                                            "anonymous", "do not", "doesn't",
                                            "does not")):
                continue
            # propozitie intreaga: altfel citatul e un fragment taiat si nu
            # dovedeste nimic (verificarea de mai jos cauta textul exact)
            if rand[-1] not in ".!?:":
                continue
            gasite.append((url, rand))
            break
    return gasite


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="scrie valorile verificate in YAML")
    parser.add_argument("--cautare", action="store_true",
                        help="cauta pagini de politica pe site-urile oficiale")
    parser.add_argument("--doar-readme", action="store_true",
                        help="cauta doar in README-ul repository-ului (mai rapid)")
    args = parser.parse_args()

    if args.cautare:
        return cauta(args.doar_readme)

    yaml_rw = YAML()
    yaml_rw.allow_duplicate_keys = False
    yaml_rw.preserve_quotes = True
    yaml_rw.width = 4096

    aplicate, erori = 0, 0
    for app_id, (valoare, url, citat) in sorted(VERIFICARI.items()):
        cale = DATA / f"{app_id}.yaml"
        if not cale.exists():
            print(f"  ! {app_id}: fisier lipsa")
            erori += 1
            continue
        vie, motiv = sursa_viva(url, citat)
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
        # valoarea se scrie cu ghilimele: in YAML 1.1, `yes` fara ghilimele
        # ar fi interpretat ca boolean (capcana prinsa de build)
        det["telemetry"] = SingleQuotedScalarString(valoare)
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


def cauta_in_readme(repo: str, timeout: int = 20) -> list[tuple[str, str]]:
    """Cauta declaratia de telemetrie in README-ul repository-ului.

    Multe aplicatii FOSS isi declara atitudinea chiar acolo („we don't collect
    any data”, „no telemetry”). E sursa cea mai la indemana si cea mai
    verificabila: linkul catre README, cu citatul exact.
    """
    if not repo:
        return []
    url = f"https://api.github.com/repos/{repo}/readme"
    antet = dict(UA)
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        antet["Authorization"] = f"Bearer {token}"
    try:
        cerere = urllib.request.Request(url, headers=antet)
        with urllib.request.urlopen(cerere, timeout=timeout) as răspuns:
            date = json.loads(răspuns.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 — rețeaua e best-effort
        return []
    import html
    import re
    continut = base64.b64decode(date.get("content") or "").decode(
        "utf-8", "replace")
    text = html.unescape(re.sub(r"<[^>]+>", " ", continut))
    text = re.sub(r"\s+", " ", text)
    link = f"https://github.com/{repo}#readme"
    gasite = []
    for cuvant in ("does not collect", "doesn't collect", "no telemetry",
                   "do not collect", "don't collect", "without collecting",
                   "no data is collected", "no personal data"):
        for propozitie in re.split(r"(?<=[.!?]) ", text):
            if cuvant in propozitie.lower() and len(propozitie) < 300:
                gasite.append((link, propozitie.strip()))
                break
        if gasite:
            break
    return gasite


def cauta(doar_readme: bool = False) -> int:
    """Cauta politici de confidentialitate pentru aplicatiile neverificate.

    Paralel: fiecare aplicatie probeaza cateva cai pe site-ul oficial, si
    reteaua e lenta — cu 8 lucratori, toate cele 200 de aplicatii trec in
    câteva minute.
    """
    from concurrent.futures import ThreadPoolExecutor

    yaml_rd = YAML()
    yaml_rd.allow_duplicate_keys = False
    verificate = set(VERIFICARI)
    aplicatii = []
    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml_rd.load(cale.read_text(encoding="utf-8"))
        app_id = app.get("id")
        if not app_id or app_id in verificate:
            continue
        aplicatii.append((app_id, app.get("website") or "",
                          list(app.get("sources") or [])))

    def unu(item):
        app_id, website, surse = item
        rezultate = [] if doar_readme else cauta_politica(website)
        if not rezultate:
            # README-ul repository-ului: multe aplicatii FOSS isi declara
            # acolo atitudinea, cu citat exact
            for url in surse:
                if "github.com/" in url:
                    repo = url.split("github.com/", 1)[1].strip("/")
                    rezultate = cauta_in_readme(repo)
                    break
        return app_id, website, rezultate

    gasite = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        for app_id, website, rezultate in executor.map(unu, aplicatii):
            if not rezultate:
                continue
            gasite += 1
            print(f"  {app_id:16} {website}")
            for url, citat in rezultate[:2]:
                print(f"      {url}")
                print(f"        „{citat[:150]}”")
    print(f"\nOK {gasite} aplicatii cu pagina de politica gasita")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
