# Configurarea profilului GitHub Sponsors (pas manual al maintainerului)

Butonul „♥ Donează” din Alterna deschide `https://github.com/sponsors/oryyon`
(centralizat în `app/links.py`). Pentru ca pagina să **primească efectiv
donații**, contul GitHub trebuie să aibă Sponsors activat, cu niveluri și o
metodă de plată. GitHub face toată treaba din contul tău — de aceea e un pas
manual, de ~10 minute.

## 0. Primul pas: activezi profilul

În contul GitHub: **Settings → Sponsors → „Set up sponsors for myself”**.

GitHub cere: cont în regulă, 18+ ani, țară cu suport pentru plăți (România e
pe listă) și profilul completat (avatar + descriere). După acest pas apare
secțiunea „Manage tiers” (niveluri) și „Payment details” (metoda de plată).

## 1. Ce copiezi în formular

### Descriere scurtă (câmpul „Short description”, ~150 de caractere)

```
Alterna — aplicație desktop pentru alternative software pe Linux. Liberă, fără reclame, offline.
```

Varianta în engleză (pentru audiență mai largă):

```
Alterna — offline desktop app for discovering FOSS alternatives on Linux. Free, no ads, no tracking.
```

### Descriere lungă (secțiunea „About”, Markdown)

```markdown
**Alterna** e un „AlternativeTo" offline pentru Linux: un catalog de **214
aplicații libere** (13 categorii), fiecare cu indicatori obiectivi — stele
GitHub, rang popcon, ultima versiune, prezența în depozitele Ubuntu — și cu
**sursa citată** pentru fiecare valoare.

Ce o face diferită: comparația dintre aplicații folosește o **matrice de
funcționalități** (156 de rânduri canonice, pe toate cele 13 categorii), iar
„cea mai bună valoare" a fost înlocuită cu „avantaj obiectiv" — doar pe
criterii verificate, cu explicație la fiecare celulă.

- Aplicație desktop nativă (PySide6/Qt6), pentru Kubuntu 24.04 și Fedora 40+.
- Catalog complet offline, în SQLite, compilat din fișiere YAML din Git.
- Fără conturi, fără reclame, fără telemetrie.
- Cod GPLv3, date CC BY-SA 4.0.

Suportul lunar acoperă infrastructura (serverul de release-uri) și timpul de
dezvoltare: verificarea indicatorilor, actualizarea catalogului și funcțiile
noi.
```

## 2. Nivelurile (tiers)

În GitHub: **Settings → Sponsors → Manage tiers → New tier**. Creează cel
puțin unul; ideal trei, ca alegerea să fie reală (nu doar „1 € sau 2 €").

### Tier 1 — „Susținător" — 3 €/lună

```
Descriere:
Menține serverul de release-uri și catalogul actualizat.

Avantaje:
- Actualizare automată a catalogului (204 → 214 aplicații, lunar)
- Raport lunar pe noutăți: ce s-a adăugat, ce s-a corectat
- Numele tău în pagina de mulțumiri a proiectului
```

### Tier 2 — „Sponsor" — 8 €/lună

```
Descriere:
Susține dezvoltarea de funcții noi, nu doar întreținerea.

Avantaje:
- Tot ce are tier-ul „Susținător"
- Prioritate la cererile de funcții (ex.: comparație între categorii)
- Badge „Sponsor" în README-ul proiectului
```

### Tier 3 — „Sponsor Gold" — 20 €/lună

```
Descriere:
Finanțează următorul release: capturi de ecran, verificări automate și
documentație în română.

Avantaje:
- Tot ce are tier-ul „Sponsor"
- Credit în secțiunea „Mulțumiri" a README-ului, cu link opțional
- Discuție directă despre priorități (30 min/lună)
```

### Donație unică (opțional, dar recomandat)

GitHub permite și sume unice, fără abonament — pentru cei care nu vor o
recurență: **5 €** (un café ☕), **25 €**, **100 €**. activează opțiunea
„one-time" din setările profilului de Sponsors.

## 2-bis. Ce aleg la Stripe: „Business type”

Stripe (România) cere **entitatea legală** care primește banii — nu există
varianta „persoană fizică fără entitate”. Deci alegerea depinde de ce ai deja
(la pasul „Country: Romania"):

| Ce ai | Ce alegi | Documente cerute de Stripe |
|---|---|---|
| **PFA / AF** (CUI, întreprindere individuală) | **Persoană Fizică Autorizată / Întreprinderea individuală** | CUI, certificat de înregistrare fiscală (ANAF), certificat ONRC, cont bancar în numele PFA, CI/pașaport, CAEN |
| **SRL / societate** (CUI) | **Societate** | CUI, certificat ONRC, act constituire, cont bancar al firmei, CI/pașaport al administratorului |
| **ONG / fundație / asociație** (CIF) | **Non-profit** | CIF, act de înființare, cont bancar al organizației |
| **Nimic** | ⚠️ Stripe nu continuă | trebuie mai întâi un PFA (ANAF) — altfel nu se poate încasa |

**Atenție la „Non-profit”:** Alterna e liber (GPLv3) și fără scop lucrativ, dar
proiectul **nu e o entitate înregistrată** — opțiunea Stripe e pentru organizații
non-profit cu personalitate juridică (CIF). Nu se alege doar pentru că proiectul
e FOSS.

**PFA-ul pentru Alterna**: se înregistrează online la ANAF (portalul „Simplifică
factură"/SPV), cu un CAEN de programare (62101 — „activități de programare
informatizată” / 6201). Ca denumire poate fi „Alterna” (întreprinderea
individuală are denumire comercială). Atenție: venitul din Sponsors se declară
la ANAF și impozitează — pentru sume mici, consultă un contabil ce se aplică
(activități independente, declarație de venit). Nu e o sumă fără
consecințe fiscale.

**Dacă nu vrei o entitate fiscală pentru donații ocazionale**, alternativa mai
simplă e un canal care acceptă persoane fizice (Ko-fi, PayPal.me) — se adaugă
în `app/links.py` ca a doua țintă, într-o linie. GitHub Sponsors rămâne
opțional: se activează când vrei, butonul din aplicație poate indica ambele
canale.

## 3. Metoda de plată și datele fiscale

În **Settings → Sponsors → Payment details** (sau din pagina Stripe/PayPal):

1. **Stripe Connect** (recomandat) — GitHub te duce la onboarding: cont de
   business sau persoană fizică, date fiscale (CNP/CUI, adresă, cont
   bancar). România e pe lista țărilor cu suport.
2. **PayPal** — alternativă; GitHub o cere în unele țări.
3. GitHub reține **0% comision** pentru Sponsors; tu primești integral suma.

Dacă ai PFA sau firmă, poți folosi datele firmei; altfel, cele personale.

## 4. Publică

- Profilul devine live la `https://github.com/sponsors/oryyon`.
- Butonul „Sponsor" apare automat pe repo-ul Alterna (secțiunea „♥ Sponsor"
  din README e deja adăugată, cu badge-ul oficial).
- Verifică deschizând pagina **deconectat ca `oryyon`** (sau într-un
  browser privat): trebuie să apară butonul „Sponsor" și să poți alege o
  sumă. Dacă apare „Sponsor" și poți plăti — e gata.

## 5. Cum verificăm din linia de comandă

```bash
# doar existența paginii
python tools/check_sponsors.py

# + starea Sponsors prin API (necesită scope-ul read:user)
gh auth refresh -s read:user
GITHUB_TOKEN=$(gh auth token) python tools/check_sponsors.py
```

Instrumentul spune limpede „nu se poate confirma" dacă tokenul nu are
scope-ul potrivit — nu trage concluzii greșite dintr-un HTTP 200.

## 6. Dacă Stripe/PayPal nu merge

Nu lăsa butonul să conducă într-un loc mort. Două ieșiri:

1. **Alt canal de donații** — spune-mi ce folosești (Ko-fi, PayPal.me, Liberpay,
   monedă digitală) și îl adaug în `app/links.py` ca a doua țintă, cu text
   și tooltip proprii.
2. **Fără buton** — până când profilul e gata, butonul poate fi ascuns
   (lista din `app/links.py` se poate face goală), ca aplicația să nu
   promită ceva ce nu există.
