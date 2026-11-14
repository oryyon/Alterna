# Formatul YAML al catalogului — Specificație v1

> Sursa adevărului pentru datele Alterna (vezi [IDEI_PROIECT.md](../IDEI_PROIECT.md), secțiunile 4, 6–8, 14–15).
> `catalog.db` (SQLite) este generat automat din aceste fișiere — **nu se editează manual**.

## Licențierea catalogului

Datele originale din `data/apps/` și `data/taxonomy/` sunt licențiate conform
[Creative Commons Attribution-ShareAlike 4.0 International](../LICENSE-DATA).
Atribuirea recomandată: „Catalogul Alterna, contribuitorii Alterna, licențiat
CC BY-SA 4.0”.

Logo-urile din `data/logos/` sunt resurse ale unor terți, nu fac parte din
conținutul original licențiat CC BY-SA și au condiții distincte de utilizare
și atribuire. Vezi [`logos/README.md`](logos/README.md).

## Principii

- **Un fișier per aplicație:** `data/apps/<id>.yaml`. Numele fișierului = câmpul `id`.
- **Chei în engleză, valori de conținut în română** (descrieri, etichete) — ca să poată contribui oricine pe GitHub.
- **`id` unic, stabil:** litere mici, cifre, `-`. O dată publicat, nu se schimbă (e referențiat de `alternatives`).
- **Totul verificabil:** indicatorii obiectivi au surse citate în `sources`. Fără rating subiectiv.
- Validarea (chei obligatorii, referințe `alternatives` existente, categorii/valori legale) o face scriptul de build YAML → SQLite.

## Structura directoarelor

```
data/
├── README.md            ← acest fișier (specificația)
├── categories.yaml      ← cele 13 categorii fixe (slug → nume afișat)
├── taxonomy/            ← taxonomii de funcționalități per categorie (pilot: security)
│   └── security.yaml
└── apps/                ← câte un fișier YAML per aplicație
    ├── gimp.yaml
    └── ...
```

## Referința câmpurilor (`data/apps/<id>.yaml`)

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | string | ✅ | Identic cu numele fișierului. `[a-z0-9-]+` |
| `name` | string | ✅ | Numele oficial afișat |
| `description` | string | ✅ | 1–2 fraze, în română |
| `category` | slug | ✅ | Un slug din `categories.yaml` |
| `license` | enum | ✅ | `foss` \| `freemium` \| `commercial` |
| `price` | enum | ✅ | `free` \| `paid` |
| `developer` | string | ✅ | Companie / comunitate (ex. „Fundația Krita / KDE") |
| `website` | URL | ✅ | Site oficial |
| `platforms` | listă | ✅ | Din: `linux`, `windows`, `macos`, `android`, `web` |
| `tags` | listă | ✅ | Cuvinte-cheie în română (folosite la căutare) |
| `alternatives` | listă de `id` | ✅ | Poate fi goală `[]`; fiecare `id` trebuie să existe în catalog |
| `editors_choice` | bool | — | Implicit `false`. Max 1–2 per categorie; afișat marcat ca opinie |
| `popularity` | int | — | Ordinea editorială a catalogului (mic = mai popular); baza sortării „implicite". Multipli de 10, ca să poți insera între |
| `logo` | path | — | SVG în `data/logos/<id>.svg`, descărcat de `tools/fetch_logos.py`; dacă lipsește, aplicația afișează inițiale |
| `package` | string | — | Numele pachetului Debian/Ubuntu, doar dacă diferă de `id` (ex. `sevenzip` → `p7zip-full`); folosit de `tools/refresh_indicators.py` pentru popcon/repo |
| `details.install_size_mb` | int | ✅* | MB la instalare; `0` pentru aplicații web. \*„✅*" = completabil ≥90% din catalog (regula din sec. 14) |
| `details.first_release_year` | int | ✅* | Anul primei versiuni |
| `details.file_formats` | listă | ✅* | Formate principale; `[]` dacă nu are sens (ex. browser) |
| `details.telemetry` | enum | ✅* | `none` \| `optional` \| `yes` — fapt din politica de confidențialitate |
| `details.romanian_language` | bool | ✅* | Interfață disponibilă în română |
| `indicators.popcon_rank` | int \| `null` | — | Rang popcon Ubuntu/Debian; `null` dacă nu e în Debian/Ubuntu |
| `indicators.stars` | int \| `null` | — | Stele GitHub/GitLab; `null` dacă nu are repo public |
| `indicators.stars_url` | URL \| `null` | — | Repo-ul de unde provin stelele |
| `indicators.latest_release` | `YYYY-MM` | ✅ | Data ultimei versiuni (proiect viu vs abandonat) |
| `indicators.in_ubuntu_repos` | bool | ✅ | Prezent în depozitele oficiale Ubuntu |
| `features` | map | — | **Doar** dacă `category` are taxonomie în `taxonomy/`. Chei = taxonomia |
| `sources` | listă URL | ✅ | Surse oficiale pentru datele de mai sus |

### Valori `features` (matricea de funcționalități, sec. 15)

Cinci valori posibile: `free` (✓ gratuit) · `paid` (💲 doar în varianta plătită) · `partial` (⚠ parțial, cu limitări) · `"no"` (✗ nu) · `unknown` (— necunoscut).

> ⚠️ **Atenție — capcană YAML:** în YAML 1.1, `yes`/`no`/`on`/`off` fără ghilimele sunt interpretate ca booleeni. Scrie mereu `"yes"` și `"no"` cu ghilimele (în `features`, `details.telemetry` etc.). Validatorul din `tools/build_catalog.py` prinde aceste cazuri.

Formă scurtă sau lungă (cu explicație):

```yaml
features:
  offline: free
  chei_hardware:
    value: partial
    note: YubiKey doar prin HMAC-SHA1 challenge-response, nu FIDO2.
```

Convenție pentru rânduri factuale (ex. `audit_independent`): `free` = „da, public/disponibil tuturor".

## Exemplu complet

Vezi [apps/keepassxc.yaml](apps/keepassxc.yaml) — acoperă toate câmpurile, inclusiv `features`.

## Reguli de validare (aplicate de scriptul de build)

1. `id` == numele fișierului; unic în tot catalogul.
2. `category` există în `categories.yaml`; fiecare cheie din `features` există în taxonomia categoriei.
3. Fiecare `id` din `alternatives` există în catalog.
4. Toate câmpurile obligatorii sunt prezente; enum-urile au valori legale.
5. `features` este permis **doar** pentru categorii cu taxonomie definită (deocamdată: `security`).
6. Avertisment (nu eroare) dacă `sources` e gol sau dacă `latest_release` e mai veche de 2 ani.

## Automatizare

- `tools/refresh_indicators.py` — reîmprospătează `indicators.*` din surse publice (popcon Debian, packages.ubuntu.com, stele GitHub), rescriind fișierele YAML in-place (comentariile se păstrează). Rulează săptămânal prin GitHub Actions și deschide PR.
- `tools/fetch_logos.py` — descarcă logo-urile SVG (Simple Icons, CC0) în `data/logos/` și completează câmpul `logo`.
