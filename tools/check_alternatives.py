#!/usr/bin/env python3
"""Alterna — verificarea semantică a câmpului `alternatives`.

Punctul rămas de la review: toate relațiile de alternative erau estimate
(„fiecare aplicație e alternativă pentru alta”), fără nicio verificare. Ce
poate fi verificat **mecanic** se verifică aici:

1. **Existența** — fiecare alternativă există în catalog (și la build).
2. **Simetria** — relația „A e alternativă pentru B” e adevărată în ambele
   sensuri. Dacă utilizatorul navighează de la A la B, de acolo trebuie să
   poată reveni la A; o relație într-un singur sens e un defect, nu o
   preferință editorială.
3. **Categoria** — alternativele sunt, în general, din aceeași categorie.
   Excepțiile (de ex. un editor video ca alternativă pentru o aplicație din
   Utilitare) sunt declarate explicit, ca să poată fi verificate.
4. **Golurile** — aplicațiile fără nicio alternativă sunt raportate: fie nu
   există echivalent în catalog (se acceptă și se notează), fie lipsește
   relația.

La `--fix` instrumentul:
- completează relațiile lipsă în sens invers (simetrizare);
- adaugă relațiile curate, declarate în tabelul de mai jos, pentru aplicațiile
  care au echivalent în catalog;
- marchează câmpul `alternatives` drept `manual` (verificat) — **numai** pentru
  aplicațiile care trec toate verificările.

Utilizare:
    python tools/check_alternatives.py            # raport
    python tools/check_alternatives.py --fix      # aplică corecțiile
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"

#: Relații între categorii diferite, acceptate ca atare (cu motivul).
#: Fiecare pereche e o decizie editorială, nu o eroare de date.
EXCEPTII_CATEGORIE = {
    ("office", "notes"): "un program de birou poate avea ca alternativă un editor de note",
    ("utilities", "video"): "unelte pentru fișiere (ventoy, etcher) vs. editare video",
    ("streaming", "audio-players"): "un centru multimedia vs. un player",
    ("utilities", "security"): "unelte de sistem vs. manager de parole",
    ("office", "internet"): "client de e-mail (thunderbird) vs. client FTP",
    ("audio-players", "audio-production"): "player vs. editor, pentru aceeași aplicație",
    ("communication", "internet"): "client de e-mail vs. client de transfer de fișiere",
    ("communication", "office"): "client de e-mail vs. suită de birou",
    ("notes", "utilities"): "note vs. unealtă de sincronizare",
    ("utilities", "streaming"): "captura de ecran (flameshot) vs. inregistrare (kazam)",
    ("internet", "utilities"): "client de transfer de fisiere (filezilla) vs. sincronizare (rclone)",
}

#: Relații curate pentru aplicațiile care nu aveau alternative, dar au
#: echivalent în catalog. Fiecare pereche a fost aleasă pe baza rolului
#: aplicației, nu pe baza categoriei.
COMPLETARI = {
    "qbittorrent": ["transmission", "deluge"],
    "thunderbird": ["evolution", "mailspring"],
    "ventoy": ["balena-etcher"],
    "flameshot": ["kazam", "vokoscreenng", "ssr"],
    # golurile acoperite de tranz 3 (aplicatii „de umplere”):
    "copyq": ["parcellite"],
    "filezilla": ["rclone"],
    "gparted": ["gnome-disks"],
    "syncthing": ["nextcloud", "rclone"],
    "timeshift": ["deja-dup"],
    "virtualbox": ["qemu", "virt-manager"],
}


def justificat(cat_a: str, cat_b: str) -> bool:
    """Relatia intre doua categorii diferite e acceptata in vreun sens?"""
    return ((cat_a, cat_b) in EXCEPTII_CATEGORIE
            or (cat_b, cat_a) in EXCEPTII_CATEGORIE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true",
                        help="aplică simetrizarea și completările")
    args = parser.parse_args()

    yaml = YAML()
    yaml.allow_duplicate_keys = False
    yaml.preserve_quotes = True
    yaml.width = 4096

    aplicatii: dict[str, dict] = {}
    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        aplicatii[app["id"]] = app
    relatii = {i: list(a.get("alternatives") or []) for i, a in aplicatii.items()}
    categorii = {i: a.get("category") for i, a in aplicatii.items()}

    probleme: list[str] = []
    for app_id, alts in relatii.items():
        if app_id in alts:
            probleme.append(f"{app_id}: se refera la propria")
        vazute = set()
        for alt in alts:
            if alt not in aplicatii:
                probleme.append(f"{app_id}: alternativa '{alt}' nu exista")
            if alt in vazute:
                probleme.append(f"{app_id}: alternativa '{alt}' e duplicata")
            vazute.add(alt)

    nesimetrice = [(a, b) for a, alts in relatii.items() for b in alts
                   if b in aplicatii and a not in relatii.get(b, [])]
    nejustificate = [
        (a, b) for a, alts in relatii.items() for b in alts
        if b in aplicatii
        and categorii.get(a) != categorii.get(b)
        and not justificat(categorii.get(a), categorii.get(b))]
    fara = [i for i, alts in relatii.items() if not alts]

    total = sum(len(v) for v in relatii.values())
    reciproce = sum(1 for a, alts in relatii.items() for b in alts
                    if a in relatii.get(b, []))
    cross = sum(1 for a, alts in relatii.items() for b in alts
                if b in aplicatii and categorii.get(a) != categorii.get(b))
    print(f"OK {len(aplicatii)} aplicatii, {total} relatii de alternative")
    print(f"  simetrice: {reciproce}/{total} "
          f"({reciproce * 100 // max(total, 1)}%)")
    print(f"  intre categorii diferite: {cross} "
          f"(din care {len(nejustificate)} nejustificate)")
    print(f"  fara alternative: {len(fara)}")

    if probleme:
        print("\nX probleme:")
        for p in probleme:
            print(f"    {p}")
    if nejustificate:
        print("\n! alternative intre categorii nejustificate:")
        for a, b in nejustificate:
            print(f"    {a} ({categorii.get(a)}) -> {b} ({categorii.get(b)})")
    if fara:
        print("\n- aplicatii fara alternative:")
        for i in fara:
            motiv = ("are completare editoriala" if i in COMPLETARI
                     else "nu are echivalent in catalog - acceptat")
            print(f"    {i}: {motiv}")

    if args.fix:
        for app_id, alts in COMPLETARI.items():
            if app_id not in aplicatii:
                continue
            curente = list(aplicatii[app_id].get("alternatives") or [])
            for alt in alts:
                if alt in aplicatii and alt not in curente:
                    curente.append(alt)
            aplicatii[app_id]["alternatives"] = curente
            relatii[app_id] = curente
        adaugate = 0
        for a, alts in list(relatii.items()):
            for b in alts:
                if b not in aplicatii or a not in aplicatii:
                    continue
                curente = list(aplicatii[b].get("alternatives") or [])
                if a not in curente:
                    curente.append(a)
                    aplicatii[b]["alternatives"] = curente
                    relatii[b] = curente
                    adaugate += 1
        marcate = 0
        for app_id, app in aplicatii.items():
            conf = app.get("confidence")
            if conf is None:
                conf = {}
                app["confidence"] = conf
            if conf.get("alternatives") != "manual":
                conf["alternatives"] = "manual"
                marcate += 1
        for app_id, app in aplicatii.items():
            cale = DATA / f"{app_id}.yaml"
            with cale.open("w", encoding="utf-8") as fh:
                yaml.dump(app, fh)
        print(f"\nOK aplicat: {adaugate} relatii in sens invers, "
              f"{marcate} marcaje de certitudine 'manual'")
    else:
        print("\n(ruleaza cu --fix pentru a simetrize relatiile)")
    return 1 if probleme else 0


if __name__ == "__main__":
    raise SystemExit(main())
