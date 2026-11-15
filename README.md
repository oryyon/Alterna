# Alterna

Aplicație **desktop nativă pentru Kubuntu 24.04** (KDE Plasma) pentru descoperirea de **alternative la programe software** — un „AlternativeTo" offline, cu date locale și comparații detaliate între aplicații.

## ⚠️ Citește mai întâi

**[IDEI_PROIECT.md](IDEI_PROIECT.md) este sursa adevărului a proiectului.** Conține toate deciziile agreatate (16 secțiuni), roadmap-ul și istoricul complet. Orice contribuție (umană sau AI) trebuie să respecte deciziile de acolo. Pe scurt:

- **Stack:** PySide6 + Qt6 (Python), Qt Widgets — decizie finală, nu se redeschide.
- **Date:** fișiere YAML (sursa adevărului, în Git) → compilate automat în `catalog.db` (SQLite). Offline-first.
- **Etică:** fără rating subiectiv — doar indicatori obiectivi cu sursă citată.
- **Licențe:** cod GPLv3, date CC BY-SA 4.0; vezi [LICENSE](LICENSE), [LICENSE-DATA](LICENSE-DATA) și [NOTICE](NOTICE).
- **Contribuții:** doar prin GitHub Issues/PR, fără backend propriu — vezi [CONTRIBUTING.md](CONTRIBUTING.md).

## Stare curentă

🚀 **MVP funcțional cu 100 de aplicații în catalog.** Aplicația desktop pornește, citește `catalog.db` și reproduce macheta: căutare live, filtre, sortare, categorii, pagină de detalii, comparare cu tabel + matrice de funcționalități + export în 5 formate, teme comutabile.

**Funcțiile care promit, funcționează:** „Actualizează catalogul acum" descarcă catalogul nou de la release-urile publice și îl verifică cu SHA-256 (vechiul rămâne ca backup); asistentul AI generează propuneri de catalog validate cu validatorul proiectului, cu Ollama local sau Claude API și cheia ta proprie; butoanele de donație deschid pagini reale, centralizate în `app/links.py`. Nimic nu e buton decorativ.

**Fiecare valoare afișată e verificabilă:** sursele citate în `data/apps/<id>.yaml` apar în pagina de detalii ca linkuri clicabile (și sursa fiecărui indicator obiectiv), iar fiecare valoare poartă un **marcaj de certitudine** — `⟳` verificată automat, `✓` verificată manual, `≈` valoare estimată, `?` valoare necunoscută. Promisiunea „totul e verificabil" devine clicabilă și măsurabilă, nu declarativă.

| Ce există | Unde |
|---|---|
| Toate deciziile proiectului (viziune, stack, date, UI, licențe) | [IDEI_PROIECT.md](IDEI_PROIECT.md) |
| Machetă UI funcțională (referința vizuală agreată) | [mockup-ui/](mockup-ui) |
| Formatul YAML + **100 aplicații** pe cele 13 categorii | [data/](data) |
| Nivelurile de certitudine ale datelor (implicit per câmp) | [data/confidence.yaml](data/confidence.yaml) |
| Script de build YAML → `catalog.db` (SQLite), cu validări | [tools/build_catalog.py](tools/build_catalog.py) |
| Reîmprospătare automată indicatori (popcon / Ubuntu / GitHub) | [tools/refresh_indicators.py](tools/refresh_indicators.py) |
| 72 logo-uri reale (Simple Icons CC0 + Wikimedia Commons) + fallback inițiale | [data/logos/](data/logos), [tools/fetch_logos.py](tools/fetch_logos.py) |
| GitHub Actions: PR săptămânal cu indicatori reîmprospătați | [.github/workflows/refresh.yml](.github/workflows/refresh.yml) |
| Aplicația desktop (schelet PySide6/Qt Widgets) | [app/](app) |
| Suită de teste automate (183 teste: build, validări, interogări, comparație, export, GUI, surse, certitudine, actualizare, AI, licențiere, resurse, packaging, integrare GitHub) | [tests/](tests) |

> Indicatorii (popcon, stele, versiuni, „în repo Ubuntu") sunt acum **valori reale**, reîmprospătate automat săptămânal prin PR — aprobarea rămâne la maintainer (sec. 7).

## Licențe

- **Codul aplicației:** [GNU GPLv3](LICENSE) — text complet, nemodificat.
- **Datele originale ale catalogului:** [CC BY-SA 4.0](LICENSE-DATA).
- **Logo-uri și mărci:** au drepturi diferite și nu sunt incluse automat în
  licența CC BY-SA; vezi [`data/logos/README.md`](data/logos/README.md).
- **Aplicarea și delimitarea licențelor:** [NOTICE](NOTICE).

## Cum rulezi

```bash
pip install -r requirements.txt
python tools/build_catalog.py       # data/ → catalog.db (cu validări; eșuează la erori)
python -m app.main                  # pornește aplicația desktop
python -m pytest tests/             # rulează suita de teste (183)

# unelte de întreținere (rulate automat săptămânal prin GitHub Actions):
python tools/refresh_indicators.py  # popcon + repo Ubuntu + stele GitHub → YAML
python tools/fetch_logos.py         # logo-uri din Simple Icons + Wikimedia → data/logos/
```

### Distribuție Linux

Ambele pachete se construiesc din aceeași sursă:

```bash
./packaging/build_appimage.sh   # Alterna-<versiune>-x86_64.AppImage
./packaging/build_deb.sh        # alterna_<versiune>-1_amd64.deb
```

Pachetul Debian se instalează cu `sudo apt install ./alterna_*.deb` și
integrează aplicația în meniul sistemului. Detalii: [`packaging/README.md`](packaging/README.md).

## Cum vezi macheta

Deschide `mockup-ui/index.html` în orice browser. Este complet funcțională (date demo): căutare live, 12 categorii, filtre, sortare, teme (dark/light/ocean), comparare aplicații cu tabel + matrice de funcționalități (categoria „Securitate"), export în 5 formate.

## Pașii următori

1. ✅ Formatul YAML pentru fișierele-sursă ale catalogului → [data/README.md](data/README.md)
2. ✅ Scriptul de build YAML → `catalog.db` (SQLite) → [tools/build_catalog.py](tools/build_catalog.py)
3. ✅ Scheletul aplicației PySide6 care reproduce macheta → [app/](app)
4. ✅ Extinderea catalogului de la 8 la 100 aplicații (pragul minim al MVP-ului atins)
5. ✅ Automatizarea indicatorilor (script + GitHub Actions cu PR săptămânal) și logo-urile reale
6. ✅ Licențiere completă: GPLv3 pentru cod, CC BY-SA 4.0 pentru datele originale, `NOTICE` și excepția documentată pentru logo-urile terților.
7. ✅ Distribuție Linux AppImage: pipeline PyInstaller + AppDir + `appimagetool` verificat prin SHA-256.
8. ✅ Infrastructură GitHub: issue template pentru propuneri, etichete, workflow CI și workflow de release.
9. ✅ Pachet Debian (`.deb`) pentru integrare APT, cu pictograme la 9 dimensiuni, metadata AppStream și documentație.
10. Următorii pași (de agreat): detectarea aplicațiilor deja instalate, extinderea catalogului și roadmap-ul post-MVP din IDEI_PROIECT.md.

## Structura proiectului

```
kimi/
├── README.md            ← acest fișier (punctul de intrare)
├── IDEI_PROIECT.md      ← toate deciziile agreatate + istoric
├── LICENSE              ← GNU GPLv3 (codul aplicației)
├── LICENSE-DATA         ← CC BY-SA 4.0 (datele originale)
├── NOTICE               ← aplicarea și delimitarea licențelor
├── requirements.txt     ← dependențe (PyYAML, PySide6)
├── packaging/           ← AppImage: script build, AppRun, desktop entry, iconă
├── CONTRIBUTING.md      ← reguli pentru contribuitori
├── mockup-ui/           ← macheta UI (referință vizuală)
│   ├── index.html
│   ├── style.css
│   └── script.js
├── data/                ← catalogul-sursă YAML (sursa adevărului pentru date)
│   ├── README.md        ← specificația formatului (v1)
│   ├── categories.yaml  ← cele 13 categorii fixe
│   ├── taxonomy/        ← taxonomii de funcționalități (pilot: security)
│   ├── apps/            ← câte un fișier YAML per aplicație (100)
│   └── logos/           ← logo-uri reale (72 aplicații; restul primesc inițiale)
├── tests/               ← suita pytest (build, db, comparare/export, GUI offscreen)
├── tools/
│   ├── build_catalog.py      ← build YAML → catalog.db (generat, gitignored)
│   ├── refresh_indicators.py ← reîmprospătare indicatori (popcon/Ubuntu/GitHub)
│   └── fetch_logos.py        ← descărcare logo-uri SVG
├── .github/workflows/
│   └── refresh.yml      ← PR săptămânal automat cu indicatori actualizați
└── app/                 ← aplicația desktop (PySide6 / Qt Widgets)
    ├── main.py          ← punctul de intrare (python -m app.main)
    ├── db.py            ← stratul de date read-only peste catalog.db
    ├── theme.py         ← temele: Sistem / Breeze Dark / Light / Ocean (persistă)
    ├── widgets.py       ← carduri de aplicație, badge-uri, pictograme provizorii
    ├── main_window.py   ← fereastra principală: căutare, filtre, sortare, categorii
    ├── detail_view.py   ← pagina de detalii (5 carduri de fapte + alternative)
    ├── compare_view.py  ← tabelul de comparație + matrice + export (5 formate)
    └── dialogs.py       ← Setări (teme, indicatori, AI viitor) + Donații
```
