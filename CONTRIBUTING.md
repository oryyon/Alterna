# Contribuție la Alterna

Bine ai venit! Alterna este un catalog local de alternative software pentru
Linux. Proiectul folosește **doar GitHub Issues și Pull Requests** — nu există
backend, conturi sau baze de date proprietare.

## Codul de conduită

- Fii respectuos și constructiv.
- Critică tehnică, nu persoane.
- Preferă surse verificabile la afirmații subiective.

## Fluxul de lucru

1. Verifică dacă ideea ta există deja în `IDEI_PROIECT.md` sau într-o issue
   deschisă.
2. Deschide o issue descriind schimbarea. Pentru aplicații noi, folosește
   template-ul **„Propunere aplicație”**, care generează direct câmpurile
   necesare pentru YAML.
3. Pentru modificări de cod: fork → ramură → pull request.
4. CI rulează automat buildul catalogului și suita de teste. Ambele trebuie să
   fie verzi înainte de merge.

## Formatul catalogului

Sursa de adevăr pentru date este `data/apps/<id>.yaml`. Formatul complet este
documentat în [`data/README.md`](data/README.md). Câteva reguli esențiale:

- `id` = numele fișierului fără extensie, doar `[a-z0-9-]`;
- `alternatives` conține doar `id`-uri care există în catalog;
- `sources` este obligatoriu — fără surse, datele nu pot fi verificate;
- pentru YAML 1.1, scrie `"yes"` și `"no"` cu ghilimele;
- `package` se declară **doar dacă numele pachetului Ubuntu diferă de `id`
  (ex. `openshot` → `openshot-qt`); altfel se presupune `id`;
- `confidence` (opțional) ridică nivelul de certitudine al unui câmp, când
  chiar ai verificat valoarea împotriva sursei — vezi
  [`data/confidence.yaml`](data/confidence.yaml).

Validează local înainte de a trimite:

```bash
python tools/build_catalog.py       # build + validări (eroare = blocat)
python tools/check_packages.py      # pachetele Ubuntu presupunute
python -m pytest tests/ -q          # include verificarea statică (pyflakes)
```

### Verificarea statică

`pytest` rulează și verificările statice proprii (doar biblioteca standardă,
deci nu depind de nimic instalat):

- **nicio variabilă nedefinită** — un `Path` folosit fără import în
  `app/dialogs.py` arunca `NameError` abia la apăsarea butonului „Actualizează
  catalogul acum”, în drum neacoperit de teste;
- **nicio clasă de test cu nume dublu** — Python păstrează doar a doua
  definiție, deci teste dispar din suita fără niciun semn;
- **nicio ocolire neregistrată** — vezi mai jos.

Dacă ai pyflakes instalat, verifică și el (prind importuri nefolosite):

```bash
pip install pyflakes
python -m pyflakes app tools tests
```

### Regula: niciun test nu ocolește codul pe care pretinde că îl verifică

O caracteristică **oprită printr-un steag de constructor** (ex.
`MainWindow(catalog, detecta=False)`) scindează suita în două: cea care
verifică și cea care nu verifică nimic. Așa a rămas nedetectat un segfault la
pornire: testele punctului 16 porneau fereastra cu detectarea oprită — adică
dezactivau exact drumul care crăpa.

Deci:

1. orice caracteristică oprită în teste trebuie declarată în `OCOLIRI`
   (`tests/test_lint.py`), cu **motivul** și cu **testul care acoperă calea
   pornită**;
2. orice modul al aplicației înlocuit cu `monkeypatch` se declară în
   `OCOLIRI_MONKEYPATCH`, tot cu motiv — înlocuirea e acceptabilă doar la
   *granița externă* (rețea, setări de utilizator);
3. testul care acoperă calea pornită nu poate ocoli el însuși caracteristica.

Verificările astea rulează în `pytest` și în CI — deci o ocolire nouă nu poate
trece neobservată.

## Corectitudinea datelor

Indicatoarele obiective (popcon, stele GitHub, ultima versiune, prezența în
depozitele Ubuntu) sunt actualizate automat săptămânal printr-un pull request.
**Nu edita manual valorile deja automatizate** — modificările manuale vor fi
suprascrise la următoarea rulare.

Pentru datele editoriale (descrieri, alternative, suport lingvistic,
telemetrie), citește sursele și folosește cea mai recentă informație
documentată.

**Dacă ai verificat o valoare împotriva sursei**, marcheaz-o: adaugă în
fișierul aplicației

```yaml
confidence:
  details.romanian_language: manual
```

Valoarea devine „✓ verificată manual" în interfață, în loc de „≈ estimată" —
exact cum se vede în pagina de detalii. Nivelul implicit per tip de câmp e în
[`data/confidence.yaml`](data/confidence.yaml).

**Un indicator nu poate fi fals:** `tools/check_packages.py` verifică că
pachetul presupus pentru fiecare aplicație există în arhiva Ubuntu și că
`in_ubuntu_repos` corespunde realității.

## Licențe

- Codul aplicației: GPLv3 — vezi [`LICENSE`](LICENSE).
- Datele originale ale catalogului: CC BY-SA 4.0 — vezi
  [`LICENSE-DATA`](LICENSE-DATA).
- Logo-urile terților au condiții distincte — vezi
  [`data/logos/README.md`](data/logos/README.md).

Prin contribution, ești de acord ca modificările tale de cod să fie licențiate
GPLv3, iar datele originale adăugate sub CC BY-SA 4.0.

## Limbă

- Cod, mesaje de eroare și documentație: română, cu excepția codului și a
  identificatorilor, care rămân în engleză.
- Descrierile din catalog: română.
- Commit-urile: începe cu un tip conventional (`feat:`, `fix:`, `docs:`,
  `chore:`, `test:`, `ci:`), urmat de un rezumat scurt în limba română.
