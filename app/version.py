"""Versiunea unică a aplicației Alterna.

Punctul unic de adevăr folosit de UI, pipeline-urile de packaging și
metadata pachetului Debian. Nu modifica nimic altfel.
"""

from __future__ import annotations


#: Versiunea aplicației, în format semantic (fără sufix Debian).
VERSION = "0.1.21"

#: Numele aplicației, folosit în titluri, metadata și numele pachetului.
APP_NAME = "Alterna"

#: Identificatorul unic al aplicației (AppStream / reverse-DNS).
APP_ID = "org.alterna.app"

#: Titularul drepturilor de autor, folosit în copyright-ul pachetului.
COPYRIGHT_HOLDER = "Alterna contributors"


def deb_version(revision: int = 1) -> str:
    """Versiunea în format Debian: ``MAJOR.MINOR.PATCH-REVISION``.

    Debian cere ca partea de revizie să fie un întreg pozitiv.
    """
    return f"{VERSION}-{revision}"


def get_version() -> str:
    """Versiunea aplicației, pentru afișare în interfață."""
    return VERSION
