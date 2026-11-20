"""Linkuri externe oficiale ale proiectului Alterna.

Punctul unic de definiție pentru URL-urile repository-ului. Astfel, o
repoziționare sau o schimbare de organizație se face într-un singur loc.
"""

from __future__ import annotations


#: Numele repository-ului GitHub.
REPO_NAME = "Alterna"

#: Organizația (owner) de pe GitHub.
REPO_OWNER = "oryyon"

#: URL-ul repository-ului.
REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"

#: URL-ul paginii de issues.
ISSUES_URL = f"{REPO_URL}/issues"

#: URL pentru deschiderea unui issue nou, cu template-ul de propunere.
NEW_ISSUE_URL = (
    f"{ISSUES_URL}/new?template=propunere-aplicatie.yml"
    "&labels=propunere-aplicatie"
)

#: Link către pagina de contribuție.
CONTRIBUTING_URL = f"{REPO_URL}/blob/main/CONTRIBUTING.md"

#: Link către fișierul de licențe al datelor în repository.
DATA_LICENSE_URL = f"{REPO_URL}/blob/main/LICENSE-DATA"

#: Link către issue-urile deschise.
OPEN_ISSUES_URL = f"{ISSUES_URL}/q/is%3Aissue+is%3Aopen"

# ---------------------------------------------------------------------------
# Actualizarea catalogului (sec. 7 — sincronizare opțională, inițiată de
# utilizator; offline-first rămâne implicit)
# ---------------------------------------------------------------------------

#: API-ul GitHub pentru ultima versiune publicată (endpoint JSON, nu pagina HTML).
LATEST_RELEASE_API = (f"https://api.github.com/repos/{REPO_OWNER}"
                      f"/{REPO_NAME}/releases/latest")

#: Pagina umană a ultimei versiuni (pentru „vezi detaliile").
LATEST_RELEASE_PAGE = f"{REPO_URL}/releases/latest"

#: Numele asset-ului cu catalogul compilat, publicat la fiecare release.
CATALOG_ASSET = "catalog.db"

#: Numele asset-ului cu amprenta SHA-256 a catalogului.
CATALOG_CHECKSUM_ASSET = "catalog.db.sha256"

# ---------------------------------------------------------------------------
# Donații (sec. 13 — modalul „Donează”)
# ---------------------------------------------------------------------------

#: Canalul de donații care funcționează **fără entitate fiscală**: PayPal.Me
#: (donație unică, cont PayPal personal) sau Ko-fi (donație unică, fără cont).
#:
#: URL-ul trebuie să fie REAL: un handle inexistent înseamnă „This link
#: doesn't exist” — adică tot buton într-un loc mort. Se creează în două
#: minute (PayPal → Settings → PayPal.Me → Create link, sau ko-fi.com).
PAYPAL_ME_URL = "https://www.paypal.me/oryyon"

#: Alternativă, tot pentru donație unică: contul Ko-fi al proiectului.
#: Gol = butonul nu apare (nicio promisiune falsă).
KOFI_URL = ""

#: GitHub Sponsors (donații recurente, 0% comision) — se activează când
#: profilul are niveluri ȘI metodă de plată, adică după ce contul GitHub
#: primește plata prin Stripe/PayPal. Până atunci, gol: butonul nu apare.
GITHUB_SPONSORS_URL = ""

#: Destinațiile de donație. Fiecare are nevoie de un cont REAL al
#: proiectului: un buton către o pagină inexistentă e exact „false
#: promise” (review, datoria 6). Cheia `url` trebuie să fie o pagină care
#: există și primește donații; una goală e ignorată (nu se afișează).
DONATION_TARGETS = [
    {
        "key": "paypal",
        "label": "PayPal.Me",
        "note": "donație unică, fără cont (card sau PayPal)",
        "url": PAYPAL_ME_URL,
    },
    {
        "key": "kofi",
        "label": "Ko-fi",
        "note": "donație unică, fără cont (card sau PayPal)",
        "url": KOFI_URL,
    },
    {
        "key": "github",
        "label": "GitHub Sponsors",
        "note": "donații recurente, fără comisioane (card)",
        "url": GITHUB_SPONSORS_URL,
    },
]


def donation_targets(enabled_only: bool = True) -> list[dict]:
    """Destinațiile de donație configurate."""
    targets = DONATION_TARGETS
    if enabled_only:
        targets = [t for t in targets if t.get("url")]
    return targets

