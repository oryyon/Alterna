# Traducere — glosar și convenții

Proiectul e în română: interfața, catalogul, documentația și mesajele
instrumentelor sunt în română. Acest document e puntea de legătură pentru
contribuitorii care lucrează în engleză (cod, mesaje de commit, nume de
fișiere) și pentru traducătorii care trebuie să păstreze **un singur termen**
pentru același lucru.

## Principii

1. **Termenii tehnici rămân în engleză** când sunt folosiți în ecosistem:
   *telemetry*, *build*, *commit*, *release*, *snapshot*, *flatpak*, *snap*,
   *AppImage*, *CI*, *workflow*.
2. **Termenii de interfață se traduc** — sunt textul pe care utilizatorul îl
   citește: „Actualizează catalogul acum”, „Doar instalate”, „În depozitele
   Ubuntu”, „Certitudine”.
3. **Un termen, o formă** — nu „descărcat” și „descărcat” în două locuri.
   Tabelul de mai jos e autoritatea.
4. **Nume proprii, neschimbate**: GIMP, VLC, KDE, GNOME, Firefox, GitHub.

## Glosar

| English | Română | Unde apare |
|---|---|---|
| application | aplicație | catalog, interfață |
| app (as în „My App”) | aplicație | UI |
| alternative (to another app) | alternative | `alternatives` în YAML |
| bookmark | marcaj | marcajele de certitudine |
| build | compilare / construire | `tools/build_catalog.py` |
| category | categorie | `category` |
| certitude / confidence | certitudine | `confidence:` din YAML |
| CLI | linie de comandă | documentație |
| comparison | comparație | pagina de comparație |
| data (as în „the data”) | date | documentație |
| desktop app | aplicație desktop | README |
| developer | dezvoltator | `developer` |
| disclosure (as în „we disclose”) | dezvăluire | politici de confidențialitate |
| distribution | distribuție | README, AppImage |
| download | descărcare | instrumentele |
| draft (as in a proposal) | propunere | chestionarul de propuneri |
| entry (in a catalog) | intrare | `data/apps/*.yaml` |
| feature (in a comparison matrix) | funcționalitate | `features` |
| filter | filtru | bara de filtre |
| flatpak | Flatpak | `flatpak:` |
| fork | fork | documentație |
| gate (as in „quality gate”) | poartă de calitate | CI |
| indicator | indicator | `indicators` |
| install | instalare | `comanda_instalare` |
| license | licență | `license` |
| maintenance (as in „under maintenance”) | în întreținere | indicatori |
| matrix (comparison) | matrice | `data/taxonomy/` |
| metadata | metadate | AppStream, catalog |
| open source | open source | etichete, badge „Open Source” |
| owner (of a repo) | responsabil | documentație |
| package | pachet | `package:` |
| packaging | împachetare | `packaging/` |
| pipeline | flux | CI, `tools/refresh_all.sh` |
| privacy policy | politică de confidențialitate | telemetrie |
| release | lansare / release | AppStream, GitHub |
| repository | repository | README |
| roadmap | hartă de drum | README |
| rule (as in a validation rule) | regulă | build |
| run (as in „run the tool”) | rulează | documentație |
| sample (as in “a sample”) | exemplu | documentație |
| seed (as in „seed data”) | semință | `tools/seminte/` |
| server | server | aplicații |
| site (official) | site oficial | `website` |
| snapshot | captură | `screenshot` |
| source (as in „the source”) | sursă | `sources` |
| stable (as in a release channel) | stabil | documentație |
| store (as in Snap Store) | magazin | linkuri `snap://` |
| submit (a proposal) | trimite | chestionar |
| support (a format) | format | `file_formats` |
| tag | etichetă | `tags` |
| telemetry | telemetrie | `details.telemetry` |
| upstream | amonte | documentație |
| usage | utilizare | indicatori |
| validation | validare | build, teste |
| value | valoare | catalog |
| verified | verificat | marcaj `✓` |
| website | site web | `website` |

## Marcajele de certitudine

| Nivel | Etichetă | Ce înseamnă |
|---|---|---|
| `auto` | ⟳ automat | valoarea vine dintr-o sursă publică, sincronizată automat |
| `manual` | ✓ verificat | omul a verificat valoarea și sursa e citată |
| `estimated` | ≈ estimat | valoare editorială, fără dovezi verificabile |
| `unknown` | ? necunoscut | valoarea lipsește — nu se poate verifica ce nu există |

## Verbe la imperativ

În README și în mesajele instrumentelor se folosește forma **la imperativ**
 („Rulează”, „Deschide”, „Verifică”) — concis și direct.

## Commit-uri

Mesajele sunt în română, în formatul `<tip>(<zonă>): <descriere>`:

- `feat(catalog):` — funcționalitate nouă
- `fix(detalii):` — corectură de comportament
- `chore(data):` — actualizare de date, fără schimbare de cod
- `docs:` — documentație
- `test:` — teste
- `release:` — pregătirea unei lansări

Exemplu: `feat(catalog): extinderea de la 100 la 168 de aplicații, cu import din Wikidata`
