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
