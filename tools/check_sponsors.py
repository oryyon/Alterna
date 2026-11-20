#!/usr/bin/env python3
"""Alterna — verifică dacă pagina de donații (GitHub Sponsors) chiar primește donații.

Regulă a proiectului (sec. 13): „un buton către o pagină inexistentă e exact
«false promise»”. Un HTTP 200 **nu** e suficient: pagina de Sponsors se
randează cu JavaScript, iar un cont fără niveluri sau fără metodă de plată
răspunde tot 200 — și butonul ar duce într-un loc mort.

Verificarea se face pe două niveluri:
1. **pagina există?** — HTTP pe URL (fără autentificare);
2. **Sponsors e activat?** — API-ul GitHub (`GET /repos/{owner}/{repo}/sponsors`),
   care dă 200 (listă, eventual goală) dacă Sponsors e activat pentru cont,
   și 404 dacă nu. Endpointul cere scope `read:user`; fără el, răspunsul nu
   e concludent și instrumentul spune limpede „nu se poate verifica”.

Utilizare:
    python tools/check_sponsors.py
    GITHUB_TOKEN=$(gh auth token) python tools/check_sponsors.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.links import DONATION_TARGETS  # noqa: E402

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}
REPO = "oryyon/Alterna"


def http_status(url: str, token: str = "") -> int:
    """Codul HTTP al paginii (0 dacă nu se poate contacta)."""
    antet = dict(UA)
    if token:
        antet["Authorization"] = f"Bearer {token}"
    try:
        cerere = urllib.request.Request(url, headers=antet)
        with urllib.request.urlopen(cerere, timeout=25) as răspuns:
            return răspuns.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def scope_uri(token: str) -> str:
    """Scope-urile tokenului (din antetul răspunsului la GET /user)."""
    if not token:
        return ""
    try:
        cerere = urllib.request.Request("https://api.github.com/user",
                                       headers={**UA, "Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(cerere, timeout=25) as răspuns:
            return răspuns.headers.get("x-oauth-scopes", "")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return ""


def sponsors_api(repo: str, token: str) -> tuple[str, object]:
    """Starea Sponsors din API: „activ”, „inactiv” sau „necunoscut”."""
    if not token:
        return "necunoscut", "fără token"
    cerere = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/sponsors",
        headers={**UA, "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(cerere, timeout=25) as răspuns:
            date = json.loads(răspuns.read().decode("utf-8", "replace"))
        return "activ", date
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "inactiv", "404"
        return "necunoscut", f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return "necunoscut", str(exc)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        token = os.environ.get("GH_TOKEN", "")
    scope = scope_uri(token)
    are_read_user = "read:user" in scope

    print("Verificare canale de donație (Alterna)")
    print("=" * 52)
    probleme = 0

    for target in DONATION_TARGETS:
        url = target["url"]
        print(f"\n▸ {target['label']} — {url}")
        cod = http_status(url)
        if cod == 0:
            print("  ✗ pagina nu poate fi contactată")
            probleme += 1
            continue
        if cod != 200:
            print(f"  ✗ pagina răspunde HTTP {cod} — butonul ar duce într-un loc mort")
            probleme += 1
            continue
        print("  ✓ pagina există (HTTP 200)")
        if any(domeniu in url for domeniu in ("paypal.me", "ko-fi.com")):
            # Paginile PayPal.Me și Ko-fi sunt aplicații JavaScript: răspund
            # 200 și pentru handle inexistente, deci HTTP-ul nu dovedește
            # nimic. Verificarea e manuală (textul din pagină).
            print("  ? pagină randată cu JavaScript — verifică manual în "
                  "browser: dacă poți plăti, linkul e real")

        if "github.com/sponsors/" in url:
            stare, detaliu = sponsors_api(REPO, token)
            if stare == "activ":
                print(f"  ✓ Sponsors e activ pentru contul de GitHub "
                      f"(API: {REPO}/sponsors)")
                if isinstance(detaliu, list):
                    print(f"    sponsori publici: {len(detaliu)}")
            elif stare == "inactiv":
                if not are_read_user:
                    print("  ? nu se poate confirma: tokenul nu are scope "
                          "`read:user` (rulează: gh auth refresh -s read:user)")
                    print("    verificare manuală: deschide pagina în browser — "
                          "dacă apare butonul „Sponsor” și poți alege o sumă, e gata")
                else:
                    print("  ✗ Sponsors NU e activ pentru acest cont")
                    print("    configurează-l: GitHub → Settings → Sponsors → "
                          "„Set up sponsors for myself” (niveluri + metodă de plată)")
                    probleme += 1
            else:
                print(f"  ? stare necunoscută ({detaliu}) — verifică manual în browser")

    print("\n" + "=" * 52)
    if probleme:
        print(f"✗ {probleme} canal(e) de donație cu probleme.")
        return 1
    print("✓ toate canalele de donație par să fie funcționale.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
