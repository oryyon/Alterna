"""Alterna — detectarea aplicațiilor deja instalate pe computer (punctul 16).

Catalogul spune ce aplicații există; acest modul spune care dintre ele sunt
**deja instalate** pe mașina utilizatorului, ca lista să poată fi filtrată
după „ce am deja” și fiecare card să poată purta marcajul „✓ instalat”.

Trei surse, toate locale și fără privilegii:

- **deb** — `dpkg-query` (alternativ: fișierul `/var/lib/dpkg/status`);
- **snap** — `snap list` (alternativ: `/var/lib/snapd/snaps/*.snap`);
- **flatpak** — `flatpak list` (alternativ: directoarele de instalare).

Nicio comandă nu e obligatorie: dacă lipsește, sursa e raportată ca
„indisponibilă”, nu ca „fără aplicații instalate” — diferența contează pentru
utilizator (nu vrem să spunem „nu ai nimic instalat” când de fapt nu am putut
verifica).

Aplicația e asociată cu pachetul ei prin numele din catalog: `package`
(pentru deb), `snap` și `flatpak` (opționale, în YAML).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

#: Surse recunoscute, în ordinea în care sunt căutate.
SOURCES = ("deb", "snap", "flatpak")

#: Nume afișate utilizatorului.
SOURCE_LABELS = {"deb": "pachet Debian", "snap": "snap", "flatpak": "Flatpak"}

#: Timp maxim pentru o comandă de sistem (secunde).
TIMEOUT = 5


@dataclass(frozen=True)
class Installed:
    """O aplicație din catalog, găsită instalată pe computer."""

    app_id: str
    source: str          # "deb" | "snap" | "flatpak"
    name: str            # numele pachetului / snap-ului / app ID-ului
    version: str = ""    # versiunea instalată, dacă e cunoscută

    @property
    def label(self) -> str:
        """Eticheta scurtă pentru UI: „deb 2.10.38”."""
        versiune = f" {self.version}" if self.version else ""
        return f"{self.source}{versiune}"


def ruleaza(args: list[str], timeout: int = TIMEOUT) -> str:
    """Execută o comandă și întoarce stdout-ul; „” dacă nu e disponibilă."""
    try:
        proces = subprocess.run(args, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return proces.stdout or ""


# --------------------------------------------------------------------------
# Surse individuale
# --------------------------------------------------------------------------
def citeste_deb(alergator: Callable[[list[str]], str] = ruleaza,
               cale_stare: Path | None = None) -> dict[str, str]:
    """Pachetele Debian instalate: {pachet: versiune}.

    `dpkg-query` e interogat direct; dacă lipsește, se citește
    `/var/lib/dpkg/status` (formatul e același ca în `dpkg --info`).
    """
    ieșire = alergator([
        "dpkg-query", "-W",
        "-f=${Package}\\t${Version}\\t${db:Status-Status}\\n",
    ])
    pachete: dict[str, str] = {}
    for linie in ieșire.splitlines():
        câmpuri = linie.split("\t")
        if len(câmpuri) >= 3 and câmpuri[2] == "installed":
            pachete[câmpuri[0].strip()] = câmpuri[1].strip()
    if pachete:
        return pachete

    stare = cale_stare if cale_stare is not None \
        else Path("/var/lib/dpkg/status")
    if not stare.is_file():
        return {}
    pachet = versiune = status = ""
    for linie in stare.read_text(encoding="utf-8", errors="replace").splitlines():
        if not linie.strip():
            if pachet and status == "installed":
                pachete[pachet] = versiune
            pachet = versiune = status = ""
        elif linie.startswith("Package: "):
            pachet = linie.split(": ", 1)[1].strip()
        elif linie.startswith("Version: "):
            versiune = linie.split(": ", 1)[1].strip()
        elif linie.startswith("Status: "):
            status = linie.split(": ", 1)[1].strip().split()[-1]
    if pachet and status == "installed":
        pachete[pachet] = versiune
    return pachete


def citeste_snap(alergator: Callable[[list[str]], str] = ruleaza,
                director: Path | None = None) -> dict[str, str]:
    """Snap-urile instalate: {nume: versiune}."""
    ieșire = alergator(["snap", "list"])
    snapuri: dict[str, str] = {}
    for linie in ieșire.splitlines()[1:]:  # prima linie e antetul coloanelor
        câmpuri = linie.split()
        if len(câmpuri) >= 2:
            snapuri[câmpuri[0]] = câmpuri[1]
    if snapuri:
        return snapuri

    # Fallback: fișierele din /var/lib/snapd/snaps (nume_rev.snap)
    cale = director if director is not None \
        else Path("/var/lib/snapd/snaps")
    if not cale.is_dir():
        return {}
    for fișier in cale.glob("*.snap"):
        nume, _, rev = fișier.stem.rpartition("_")
        if nume and rev.isdigit():
            snapuri[nume] = ""
    return snapuri


def citeste_flatpak(alergator: Callable[[list[str]], str] = ruleaza,
                    directoare: tuple[Path, ...] | None = None) -> dict[str, str]:
    """Aplicațiile Flatpak instalate: {app ID: versiune}."""
    ieșire = alergator(
        ["flatpak", "list", "--app", "--columns=application,version"])
    aplicatii: dict[str, str] = {}
    for linie in ieșire.splitlines():
        câmpuri = linie.split("\t")
        if câmpuri[0].strip():
            aplicatii[câmpuri[0].strip()] = (câmpuri[1].strip()
                                             if len(câmpuri) > 1 else "")
    if aplicatii:
        return aplicatii

    # Fallback: directoarele de instalare (numele lor e app ID-ul)
    baze = directoare if directoare is not None else (
        Path.home() / ".local/share/flatpak/app",
        Path("/var/lib/flatpak/app"),
    )
    for bază in baze:
        if not bază.is_dir():
            continue
        for director in bază.iterdir():
            if director.is_dir():
                aplicatii.setdefault(director.name, "")
    return aplicatii


CITITORI: dict[str, Callable[[], dict[str, str]]] = {
    "deb": citeste_deb,
    "snap": citeste_snap,
    "flatpak": citeste_flatpak,
}


# --------------------------------------------------------------------------
# Asoocierea cu catalogul
# --------------------------------------------------------------------------
def nume_pachet(app: dict) -> str:
    """Numele pachetului deb al aplicației (`package` sau, prin convenție, `id`)."""
    return (app.get("package") or app.get("id") or "").strip()


def detecteaza(apps: Iterable[dict],
               surse: dict[str, dict[str, str]] | None = None) -> dict[str, Installed]:
    """Asociază aplicațiile din catalog cu cele instalate local.

    `surse` permite injectarea unor seturi false (testele nu depind de sistem).
    Dacă o sursă nu e disponibilă, e tratată ca „gol”, nu ca eroare.
    """
    if surse is None:
        surse = {nume: CITITORI[nume]() for nume in SOURCES}
    jos = {nume: {n.lower(): n for n in dicționar}
           for nume, dicționar in surse.items()}

    găsite: dict[str, Installed] = {}
    for app in apps:
        app_id = app.get("id") or ""
        if not app_id:
            continue
        for sursă, câmp in (("deb", nume_pachet(app)),
                            ("snap", app.get("snap") or ""),
                            ("flatpak", app.get("flatpak") or "")):
            if not câmp:
                continue
            original = jos[sursă].get(câmp.lower())
            if original is None:
                continue
            versiune = surse[sursă].get(original, "")
            găsite.setdefault(app_id, Installed(app_id, sursă, original, versiune))
            break
    return găsite


def surse_disponibile() -> dict[str, bool]:
    """Ce surse de pachete există pe sistem (pentru mesajul din UI)."""
    comenzi = {"deb": "dpkg-query", "snap": "snap", "flatpak": "flatpak"}
    disponibile: dict[str, bool] = {}
    for nume, comandă in comenzi.items():
        try:
            rezultat = subprocess.run(
                ["which", comandă], capture_output=True, text=True,
                timeout=TIMEOUT, check=False)
            disponibile[nume] = rezultat.returncode == 0
        except (OSError, subprocess.SubprocessError):
            disponibile[nume] = False
    return disponibile


#: Unde caută fișierele .desktop (un pachet care are unul e o aplicație,
#: nu o bibliotecă — semnalul e obiectiv, nu o ghicire).
CAI_DESKTOP = (
    Path("/usr/share/applications"),
    Path("/var/lib/flatpak/exports/share/applications"),
    Path("/var/lib/snapd/desktop/applications"),
    Path.home() / ".local/share/applications",
)


def desktop_uri(cai: Iterable[Path] = CAI_DESKTOP) -> set[str]:
    """Mulțimea numelor de pachete cu intrare de meniu.

    Se construiește **o singură dată**: un `stat` pentru fiecare pachet
    instalat (mii de apeluri) ar ține threadul de detectare ocupat mult prea
    mult — și fereastra se închidea în timpul lui.
    """
    numere: set[str] = set()
    for director in cai:
        try:
            for intrare in director.glob("*.desktop"):
                numere.add(intrare.stem)
        except OSError:
            continue
    return numere


def are_desktop(pachet: str,
                cai: Iterable[Path] = CAI_DESKTOP,
                cunoscute: set[str] | None = None) -> bool:
    """Pachetul are o intrare de meniu? (deci e aplicație, nu bibliotecă)"""
    if cunoscute is None:
        cunoscute = desktop_uri(cai)
    return pachet in cunoscute


def aplicatii_neacoperite(apps: Iterable[dict],
                          surse: dict[str, dict[str, str]] | None = None,
                          cai_desktop: Iterable[Path] = CAI_DESKTOP,
                          ) -> list[Installed]:
    """Aplicațiile instalate pe computer care **nu sunt** în catalog.

    Maparea inversă: catalogul spune ce aplicații există, dar utilizatorul
    are și aplicații pe care Alterna nu le cunoaște. Raportăm acele
    aplicații — e exact lista de intrări care îmbogățește catalogul.

    Se raportează doar ce are o intrare de meniu (`.desktop`): bibliotecile
    și pachetele de sistem nu sunt „aplicații” și ar umple raportul cu zgomot.
    """
    if surse is None:
        surse = {nume: CITITORI[nume]() for nume in SOURCES}
    cunoscute: set[str] = set()
    for app in apps:
        for câmp in (nume_pachet(app), app.get("snap") or "",
                     app.get("flatpak") or ""):
            if câmp:
                cunoscute.add(câmp.lower())

    cu_desktop = desktop_uri(cai_desktop)
    rezultat: list[Installed] = []
    for nume, pachete in surse.items():
        for pachet, versiune in pachete.items():
            if pachet.lower() in cunoscute:
                continue
            # doar ce are intrare de meniu: bibliotecile și pachetele de
            # sistem nu sunt „aplicații” și ar umple raportul cu zgomot
            if pachet not in cu_desktop:
                continue
            rezultat.append(Installed("", nume, pachet, versiune))
    rezultat.sort(key=lambda i: i.name)
    return rezultat


def linkuri_instalare(app: dict) -> list[tuple[str, str]]:
    """Linkuri directe către magazinele de pachete: [(etichetă, url)].

    Fiecare link folosește schema standard a magazinului, deci desktopul îl
    poate deschide cu handlerul lui: ``apt://`` (GNOME Software / apturl),
    ``snap://`` (Snap Store) şi ``flathub://`` (Flathub).

    Se oferă doar sursele **verificate**: pachetul din Ubuntu (dacă
    `in_ubuntu_repos`), snap-ul şi aplicația Flatpak confirmate în registre.
    """
    linkuri: list[tuple[str, str]] = []
    pachet = nume_pachet(app)
    if app.get("in_ubuntu_repos") and pachet:
        linkuri.append(("APT", f"apt://{pachet}"))
    snap = app.get("snap")
    if snap:
        linkuri.append(("Snap", f"snap://{snap}"))
    flatpak = app.get("flatpak")
    if flatpak:
        linkuri.append(("Flatpak", f"flathub://{flatpak}"))
    return linkuri


def comanda_instalare(app: dict) -> tuple[str, str] | None:
    """Comanda de instalare potrivită: (comandă, descriere).

    Preferă sursa pe care utilizatorul o are deja la îndemână: pachetul din
    Ubuntu, snap-ul sau aplicația Flatpak.
    """
    pachet = nume_pachet(app)
    if app.get("in_ubuntu_repos") and pachet:
        return (f"sudo apt install {pachet}", "din pachetele Ubuntu")
    snap = app.get("snap")
    if snap:
        return (f"sudo snap install {snap}", "ca snap")
    flatpak = app.get("flatpak")
    if flatpak:
        return (f"flatpak install flathub {flatpak}", "din Flathub")
    return None
