#!/usr/bin/env python3
"""Alterna — completeaza indicatorii unei aplicatii cu ajutorul AI.

Fluxul: AI-ul propune **surse** (repository, pachet Ubuntu, pagina de
release-uri), iar instrumentul **verifica** fiecare sursa si scrie doar
valorile confirmate. Regula de aur a proiectului se pastreaza: valoarea
nesurprinsa de nicaieri nu ajunge in catalog — ramane `estimated` sau goala.

Fara AI, instrumentul poate folosi direct sursele deja din fisierul YAML
(pasul --fara-ai), caz in care completarea e 100% determinista.

Utilizare:
    python tools/complete_indicators.py gimp
    python tools/complete_indicators.py --fara-ai gimp
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"
UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}


def github_json(url: str, token: str = "") -> dict | None:
    """GET JSON de pe api.github.com (cu token, daca exista)."""
    antet = dict(UA)
    if token:
        antet["Authorization"] = f"Bearer {token}"
    try:
        cerere = urllib.request.Request(url, headers=antet)
        with urllib.request.urlopen(cerere, timeout=20) as răspuns:
            return json.loads(răspuns.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _acelasi_site(a: str, b: str) -> bool:
    """Aceleași domeniu, ignorând schema, www. și slash-ul final."""
    def domeniu(url: str) -> str:
        url = (url or "").strip().lower()
        url = re.sub(r"^https?://", "", url)
        url = re.sub(r"^www\.", "", url)
        return url.rstrip("/").split("/")[0]
    return bool(a) and bool(b) and domeniu(a) == domeniu(b)


def verifica_repo(repo: str, token: str = "", website: str = "") -> dict:
    """Stele + ultima versiune, dintr-un repository GitHub.

    **Garda:** repository-ul trebuie să declare drept homepage site-ul
    aplicației (sau același domeniu). Fără asta, AI-ul ar putea propune
    „KDE/ark” în loc de „flame-engine/ark” — iar stelele ar fi ale altui
    proiect, adică o valoare *corectă* pentru altceva. Cel mai rău lucru
    pentru onestitatea catalogului.
    """
    info = github_json(f"https://api.github.com/repos/{repo}", token)
    if not info or "stargazers_count" not in info:
        return {}
    if website:
        homepage = str(info.get("homepage") or "")
        descriere = str(info.get("description") or "")
        if not (_acelasi_site(homepage, website)
                or _acelasi_site(descriere, website)):
            # nu putem lega repo-ul de aplicație -> nu scriem nimic
            return {}
    rezultat = {"stars": int(info.get("stargazers_count") or 0),
                "stars_url": f"https://github.com/{repo}"}
    eliberare = github_json(
        f"https://api.github.com/repos/{repo}/releases/latest", token)
    if eliberare and eliberare.get("published_at"):
        rezultat["latest_release"] = str(eliberare["published_at"])[:7]
    return rezultat


def verifica_pachet(pachet: str, liste: Path | None = None) -> dict:
    """Pachetul exista in arhiva Ubuntu?

    `liste` permite injectarea unui index (testele nu depind de masina).
    """
    radacina = liste or Path("/var/lib/apt/lists")
    for fișier in radacina.glob(
            "archive.ubuntu.com_ubuntu_dists_noble_*_binary-amd64_Packages"):
        text = fișier.read_text(encoding="utf-8", errors="replace")
        if re.search(rf"^Package: {re.escape(pachet)}$", text, re.M):
            return {"in_ubuntu_repos": True, "package": pachet}
    return {}


def surse_din_ai(app: dict, model: str = "", timeout: int = 600) -> dict:
    """Cere AI-ului sursele pentru indicatorii aplicatiei."""
    from app import ai

    cerere = (f"Aplicație: {app.get('name')} ({app.get('id')})\n"
              f"Site oficial: {app.get('website', '')}\n"
              f"Descriere: {app.get('description', '')}")
    backend = ai.OllamaClient(model=model) if model else ai.OllamaClient()
    if not backend.is_available():
        raise RuntimeError("Ollama nu răspunde — pornește `ollama serve` "
                           "și instalează un model (de ex. llama3.1).")
    text = backend.generate(ai.indicators_prompt(cerere),
                             timeout=timeout,
                             system=ai.INDICATORS_SYSTEM_PROMPT)
    bloc = ai.extract_yaml(text)
    date = YAML(typ="safe", pure=True).load(bloc) or {}
    return {k: v for k, v in date.items() if v}


def aplica(app: dict, surse: dict, token: str = "",
           liste: Path | None = None) -> dict:
    """Verifica sursele si intoarce valorile confirmate."""
    rezultat = {}
    repo = str(surse.get("github_repo") or "")
    if repo:
        repo = re.sub(r"^https?://(www\.)?github\.com/", "", repo).strip("/")
        if "/" in repo:
            rezultat.update(verifica_repo(repo, token, str(app.get("website") or "")))
    pachet = str(surse.get("ubuntu_package") or "")
    if pachet:
        rezultat.update(verifica_pachet(pachet, liste))
    site = str(surse.get("website") or "")
    if site and site not in (app.get("sources") or []):
        rezultat["website"] = site
    return rezultat


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app_id", help="id-ul aplicației din catalog")
    parser.add_argument("--fara-ai", action="store_true",
                        help="folosește sursele deja din YAML, fără AI")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", ""),
                        help="modelul Ollama (implicit: primul disponibil)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="timp maxim pentru model (implicit: 600 s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="nu scrie în YAML")
    args = parser.parse_args()

    yaml = YAML()
    yaml.allow_duplicate_keys = False
    yaml.preserve_quotes = True
    yaml.width = 4096

    cale = DATA / f"{args.app_id}.yaml"
    if not cale.exists():
        print(f"✗ nu există {cale}", file=sys.stderr)
        return 1
    app = yaml.load(cale.read_text(encoding="utf-8"))

    if args.fara_ai:
        surse = {}
        for url in app.get("sources") or []:
            if "github.com/" in url or "gitlab.com/" in url:
                surse["github_repo"] = url
                break
        surse["ubuntu_package"] = app.get("package") or app.get("id") or ""
        surse["website"] = app.get("website") or ""
    else:
        surse = surse_din_ai(app, args.model, args.timeout)

    token = os.environ.get("GITHUB_TOKEN", "")
    valori = aplica(app, surse, token)
    if not valori:
        print("✗ nicio sursă nu s-a putut verifica — valorile rămân goale")
        return 1

    print(f"✔ {args.app_id}: valori confirmate")
    for cheie, valoare in valori.items():
        print(f"    {cheie:16} {valoare}")

    if args.dry_run:
        return 0
    ind = app.setdefault("indicators", {})
    for cheie, valoare in valori.items():
        if cheie == "website":
            app["website"] = valoare
            surse_liste = app.setdefault("sources", [])
            if valoare not in surse_liste:
                surse_liste.append(valoare)
            continue
        if cheie == "package":
            app["package"] = valoare
            continue
        ind[cheie] = valoare
        conf = app.setdefault("confidence", {})
        conf[f"indicators.{cheie}"] = "auto"
    with cale.open("w", encoding="utf-8") as fh:
        yaml.dump(app, fh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
