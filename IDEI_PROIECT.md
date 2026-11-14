# Idei Agreate — Aplicație Desktop „AlternativeTo" pentru Kubuntu

> Fișier de lucru: conține deciziile asupra cărora am căzut de acord.
> Actualizat la fiecare idee nouă agreată în conversație.

**Ultima actualizare:** 2026-11-02

---

## 📍 Stare curentă și pasul următor

- **Faza proiectului:** MVP funcțional, cu catalogul la pragul minim agreat (100 aplicații; ținta sec. 6: 100–200). Cei trei pași agreati (YAML → build → schelet Qt) sunt finalizați.
- **Ce există concret:** acest fișier (sursa deciziilor) + `mockup-ui/` (referința vizuală) + `data/` (100 de aplicații pe toate cele 13 categorii) + `tools/build_catalog.py` (build YAML → `catalog.db`, cu validări) + `app/` (schelet PySide6/Qt Widgets; testat offscreen, cu screenshot-uri).
- **Indicatori reali, automatizați:** `tools/refresh_indicators.py` actualizează popcon / „în repo Ubuntu" / stele GitHub / data ultimei versiuni din sursele publice, in-place în YAML; GitHub Actions deschide PR săptămânal (aprobare la maintainer — sec. 7). Regula 6 (versiuni >2 ani) marchează deja 4 proiecte stagnante (Kazam, Stacer, SSR, Avidemux).
- **Logo-uri:** 55 de aplicații au SVG-uri reale (Simple Icons, CC0), restul primesc inițiale; multe branduri (Adobe, VLC, Edge) au fost scoase din Simple Icons la cererea deținătorilor — deciune documentată în istoric.
- **Pași următori propuși (de agreat):** crearea repo-ului GitHub „alterna" (sec. 9 — activează workflow-ul de refresh și butonul Propune), împachetare AppImage/deb, apoi roadmap-ul post-MVP.
- **Instrucțiune pentru orice AI care preia proiectul:** citește întâi acest fișier integral, apoi deschide `mockup-ui/index.html` ca referință vizuală. Nu propune stack-uri diferite de secțiunea 3 și nu reintroduce rating subiectiv (secțiunea 8).

---

## ✅ Decizii AGREATE

### 1. Scopul aplicației
- Aplicație **desktop nativă** (nu în browser) pentru **Kubuntu 24.04** (KDE Plasma).
- Rol: descoperirea de **alternative la programe software**, similar cu AlternativeTo.

### 2. Capabilități de bază (agreate ca direcție)
- Catalog de programe: nume, descriere, categorie, licență (open source / freemium / comercial), platforme, preț, **indicatori obiectivi de popularitate** (detalii: secțiunea 8; fără rating subiectiv; screenshot-uri doar post-MVP).
- Pentru fiecare program: listă de **alternative** cu comparații rapide.
- **Detectarea aplicațiilor instalate local** (deb / flatpak / snap) și sugestii de alternative — post-MVP (vezi „💡 Idei pentru viitor").
- Funcționare **offline-first**: bază de date locală SQLite, sincronizare opțională.

### 3. Stack tehnic — DECIZIE FINALĂ
- **PySide6 + Qt6** (Python) — confirmat definitiv pe 2026-10-24.
- Motivație: aspect 100% nativ pe KDE Plasma, un singur limbaj (Python) pentru UI + SQLite + scripturi de build/Wikidata, componente UI gata făcute pentru MVP, viteză mare de dezvoltare.
- Alternativa Tauri (Rust + web UI) a fost evaluată și respinsă: preț prea mare (stack dublu Rust + JS) pentru beneficii de care proiectul nu are nevoie.
- Notă: stratul de date (YAML/SQLite) rămâne independent de UI — o eventuală migrare viitoare nu pierde munca pe date.

### 4. Sursa datelor
- **Model hibrid:** bază de date proprie (JSON/SQLite în repo, contribuții tip Git „awesome list") + îmbogățire automată din **Wikidata / Wikipedia API**.
- Se evită scraping-ul AlternativeTo (încalcă termenii lor de utilizare).

### 5. Împachetare și distribuție
- **AppImage** ca format principal; `.deb` pentru integrare APT; Flatpak opțional, mai târziu.

### 6. MVP (produsul minim viabil)
1. **Fereastră principală:** bară de căutare live (nume + descriere + taguri) în stânga listă fixă cu cele **13 categorii** (lista: secțiunea 13); rezultate filtrate din SQLite local.
2. **Pagina unei aplicații:** detalii complete + lista de alternative (clickabile, navigare în lanț); marcaj „✓ instalat" rezervat pentru viitor.
3. **Filtre:** licență (open source / freemium / comercial), platformă (Linux / Windows / macOS / Android / Web), preț (gratuit / cu plată) — aplicate prin clauze WHERE în SQL.
4. **Fac parte din MVP și funcțiile agreatate ulterior:** compararea aplicațiilor (secțiunea 14), matricea de funcționalități — doar categoria Securitate (secțiunea 15), sortarea listelor (secțiunea 16), Setări cu teme (secțiunea 13).
5. **Bază de date SQLite locală** cu ~100–200 de aplicații populare, introduse manual, cu schemă minimă:
   - `applications` (id, nume, descriere, categorie, licență, preț, site, logo)
   - `platforms` (app_id, platformă)
   - `alternatives` (app_id, alternativă_id) — relația-cheie
   - `tags` (app_id, tag)

### 7. Modelul de întreținere a datelor
- **Sursa adevărului** = fișiere text simple (YAML/JSON, câte unul per aplicație) în repository-ul Git al proiectului.
- `catalog.db` (SQLite) este un **produs generat automat** din fișierele sursă (script de build), nu se editează manual.
- Contribuțiile comunității se fac prin **Pull Request** pe GitHub (adăugare/corectare aplicații), cu aprobare de la maintainer.
- Actualizări automate programate prin **GitHub Actions**: îmbogățire din Wikidata API, verificare linkuri moarte, PR-uri automate cu propuneri.
- Aplicația descarcă catalogul actualizat din repo (sincronizare opțională, inițiată de utilizator sau la pornire, dezactivabilă).
- Principiu anti-învechire: datele rămân portabile și lizibile — oricine poate face fork și continua proiectul.

### 8. Rating și popularitate — DECIZIE
- **Fără rating subiectiv (★ manual)** — respins ca falsă precizie; nedrept față de aplicații și de utilizatori.
- **Fără voturi de utilizatori la MVP** — necesită backend/conturi (rămâne în roadmap 6b).
- **Indicatori obiectivi, cu sursa citată:**
  - Rang `popcon` Ubuntu/Debian (câți îl au instalat real);
  - Stele GitHub/GitLab (interesul comunității);
  - Data ultimei versiuni (proiect viu vs abandonat);
  - „În depozitele oficiale Ubuntu ✓" (ușor de instalat, verificat).
- Opțional, marcat vizual clar ca **opinie**: „Recomandarea editorilor" (max 1–2 per categorie).

### 9. Numele aplicației — DECIZIE
- **Alterna** — scurt, clar internațional, descriptiv (alternative).
- De verificat la începutul dezvoltării: disponibilitatea repo-ului GitHub și a numelui de pachet (`alterna`).

### 10. Design UI — DECIZIE
- **Qt Widgets** pentru MVP: aplicația e în esență „căutare + liste + formulare" — punctul forte al Widgets; prototipare rapidă, documentație vastă, aspect nativ pe Plasma.
- Migrarea viitoare la QML/Kirigami: vezi secțiunea „💡 Idei pentru viitor".

### 11. Contribuții cu date — DECIZIE
- Contribuțiile se fac **exclusiv prin GitHub** (Issues/Pull Request), nu prin formular în aplicație.
- Implementare în aplicație: buton „Propune o aplicație" → deschide în browser pagina GitHub de issue nou, **precompletată cu un template** (câmpuri: nume, descriere, licență, platforme, alternative).
- Motivație: zero chei API în aplicație, zero backend, moderare și istoric asigurate nativ de GitHub.

### 12. Licențe — DECIZIE
- **Codul aplicației: GPLv3** — orice modificare distribuită trebuie publicată sub aceeași licență; nimeni nu poate face o clonă proprietară. Textul complet este în `LICENSE`.
- **Datele originale ale catalogului: CC BY-SA 4.0** — refolosire liberă cu atribuire și aceeași licență (modelul Wikipedia). Textul complet este în `LICENSE-DATA`.
- **Logo-urile și mărcile terților sunt excluse din licența CC BY-SA a catalogului**; condițiile lor sunt documentate separat în `data/logos/README.md`.
- Principiu: codul și conținutul sunt licențiate separat; delimitarea este formalizată în `NOTICE`.
- **Fără CLA (Contributor License Agreement)** — confirmat pe 2026-10-24: GPL pur. Consecință agreată: după primul contributor extern, o versiune viitoare cu sursă închisă nu va mai fi posibilă fără acordul tuturor contributorilor; rămâne legală doar vânzarea de binare GPL (cu sursă deschisă).

### 13. Machetă UI — DECIZIE (referință vizuală agreată)
- Există o machetă funcțională HTML/CSS/JS în folderul `mockup-ui/` (index.html + style.css + script.js), stil KDE Breeze, cu 34 de aplicații de exemplu. Ea servește ca **referință vizuală** pentru implementarea PySide6.
- **Bară de titlu:** butoane „＋ Propune", „♥ Donează", „⚙ Setări".
- **⚙ Setări (modal):**
  - *Aspect* — selector de temă: „A sistemului" (urmează Plasma), „Breeze Dark", „Breeze Light", „Ocean". Alegerea persistă între sesiuni.
  - *Catalog de date* — checkbox „verificare actualizări la pornire", data ultimei actualizări, buton „Actualizează acum".
  - *Indicatori afișați* — popcon, stele GitHub, ultima versiune, „în repo Ubuntu" — porniți/opriți individual.
  - *Asistent AI (viitor)* — selector dezactivat (Ollama / Claude cu cheie proprie), cu notă explicativă.
- **♥ Donează (modal):** text onest („absolut opțional — aplicația rămâne gratuită") + **3 opțiuni active** de plată, fiecare un link extern deschis în browser:
  - **Liberapay** — donații recurente, fără comisioane (card / SEPA);
  - **Ko-fi** — donații unice (card / PayPal);
  - **Revolut** — link revolut.me personal (instant, popular în România).
  - Rezervate pentru activare ulterioară (deja pregătite, comentate în cod): **GitHub Sponsors**, **PayPal (PayPal.Me)**.
  - Notă tehnică: plata cu cardul nu se face direct în aplicație, ci prin procesatori (Stripe/PayPal/Revolut) — aplicația doar deschide linkuri; zero cod de plată, zero date financiare atinse.
- **Categorii extinse la 13:** Grafică, Birou, Video, Audio & Playere, Dezvoltare, Internet, Comunicare, Securitate, Streaming & Captură, Producție audio, 3D & CAD, Notițe, Utilitare.
- **Pagina de detalii:** faptele (indicatori obiectivi) afișate în 5 carduri separate — layout agreat.
- Notă: butonul „♥ Donează" apare deja în machetă; implementarea efectivă rămâne în „💡 Idei pentru viitor" până există paginile de donații.

### 14. Compararea aplicațiilor — DECIZIE
- **Butonul „⇄ Compară"** apare în antetul listelor **filtrate** (categorie sau rezultat de căutare); NU apare în vizualizarea „Toate". Dacă utilizatorul revine la „Toate" cu modul activ, acesta se anulează automat.
- Activarea modului comparație: checkbox pe fiecare card; click pe card = selectare (nu deschide detaliile); cardurile selectate sunt evidențiate vizual.
- **Limită: max 4 aplicații** (limita e configurabilă / poate fi extinsă ulterior); mesaj în bara de stare la depășire.
- Bară plutitoare jos: „N selectate (max 4)" + butonul **„Vezi comparația"**, activ de la 2 selecții.
- **Pagina de comparație:** tabel — aplicațiile ca coloane, criteriile ca rânduri (14): Descriere, Dezvoltator, Categorie, Licență, Preț, Platforme, Site oficial, Dimensiune la instalare, Anul primei versiuni, Ultima versiune, **Telemetrie** (fără / opțională / da — fapt documentabil din politica de confidențialitate), Limbă română, Formate de fișiere, Taguri.
  - **Eliminate din tabel** (rămân doar pe pagina de detalii a aplicației): Popcon Ubuntu, Stele GitHub, În repo Ubuntu, Alternative cunoscute.
  - Evidențiere verde pe: Licență (FOSS), Preț (gratuit), Platforme (include Linux), Dimensiune (cea mai mică), Ultima versiune (cea mai recentă), Telemetrie (fără), Limbă română (Da).
  - Regulă de admitere a unui rând nou: valoarea trebuie completabilă pentru ≥90% din catalog.
- **Evidențierea verde** a celei mai bune valori din fiecare rând (păstrată, agreată) + legendă explicativă sub tabel.
- Click pe numele aplicației din antetul tabelului → pagina ei de detalii.
- **Export:** butonul „💾 Salvează în fișier" cu **selector de format**: Markdown (.md), CSV (.csv), HTML (.html), Text (.txt), JSON (.json). În aplicația Qt: dialog de salvare nativ cu filtru pe extensii.

### 15. Matricea de funcționalități normalizată — DECIZIE
- **Taxonomie canonică per categorie:** funcționalitățile sunt definite de proiect, o singură dată, per categorie — aceeași funcție apare pe același rând, indiferent de denumirea comercială din aplicații (rezolvă problema duplicatelor sub nume diferite).
- **Valori per aplicație (5):** ✓ gratuit / 💲 doar în varianta plătită / ⚠ parțial (există, dar cu limitări — ex: doar citire offline, doar import fără export; afișată portocaliu, cu explicație în legendă) / ✗ nu / — necunoscut.
- **Restricție:** matricea apare doar când toate aplicațiile comparate sunt din **aceeași categorie** cu taxonomie definită.
- **Domeniu:** doar categoria **Securitate** primește taxonomie deocamdată (pilot); nu se extinde la alte categorii.
- **Taxonomia „Securitate" (18 rânduri):** cele 10 inițiale (offline, generator parole, autofill, TOTP, passkeys, biometric, partajare, audit parole, import/export, self-hosting) + 8 adăugate în urma cercetării pe surse oficiale (bitwarden.com, 1password.com, keepassxc.org):
  - Extensii de browser (Chrome/Firefox/Edge/Safari);
  - Stocare fișiere criptate (atașamente);
  - Acces de urgență / recuperare prin contacte de încredere;
  - Chei hardware de securitate (YubiKey/WebAuthn) — *exemplu de „⚠ parțial": KeePassXC suportă YubiKey doar prin HMAC-SHA1 challenge-response, nu FIDO2*;
  - Monitorizare breșe de date (dark web) — *Bitwarden: scanare gratuită, rapoarte premium*;
  - CLI / API pentru automatizări;
  - Agent SSH integrat (KeePassXC și 1Password au, Bitwarden nu);
  - Audit de securitate independent cu raport public (toate cele 3 au — KeePassXC publică rapoartele pe keepassxc.org/audits).
- Convenție pentru rânduri factuale (ex. audit independent): „✓ gratuit" înseamnă „da, public/disponibil tuturor".
- **Plasare:** matricea apare **doar în pagina de comparație**, nu și pe pagina de detalii sau altundeva.
- Caz de utilizare principal: dezvoltatorii pot extrage lista completă de funcționalități ale concurenței (ex. 1Password vs Bitwarden) ca listă de cerințe pentru o alternativă nouă.

### 16. Sortarea listelor — DECIZIE
- Selector de sortare în bara de instrumente, aplicabil în orice listă (categorii, căutare, „Toate"):
  - **Implicită** — ordinea catalogului (aplicații populare);
  - **Nume A → Z** și **Nume Z → A** (alfabetică, cu reguli românești);
  - **Recent actualizate** — după data ultimei versiuni, descrescător;
  - **Dimensiune mică → mare** — aplicațiile fără dimensiune cunoscută la final.
- Sortarea se combină liber cu filtrele (licență / platformă / preț) și cu căutarea.

### 17. Formatul YAML al catalogului — DECIZIE
- **Specificația completă:** `data/README.md` (v1). Structură: `data/apps/<id>.yaml` (un fișier per aplicație), `data/categories.yaml`, `data/taxonomy/<categorie>.yaml`.
- **Chei în engleză, valori de conținut în română** — contributorii externi de pe GitHub pot edita fișierele.
- **`id` = numele fișierului**, unic și stabil; `alternatives` referă alte `id`-uri (validat la build).
- Acoperă toate câmpurile decise: schema minimă (sec. 6), indicatori obiectivi cu `sources` (sec. 8), rândurile tabelului de comparație (sec. 14), matricea de funcționalități prin `features` cu 5 valori, doar pentru categorii cu taxonomie (sec. 15).
- **Capcană descoperită la validare:** valoarea `no` din `features` trebuie scrisă `"no"` (YAML 1.1 o interpretează ca boolean). Documentat în specificație.
- **Set pilot validat (8 aplicații):** graphics — GIMP, Krita, Photoshop, Photopea, Affinity Photo; security — KeePassXC, Bitwarden, 1Password (cu matricea completă, 18 rânduri).
- Numerotarea categoriilor: corectată la 13 peste tot (sec. 6 și 13) — lista agreată a avut dintotdeauna 13 nume.

---

## 💡 Idei pentru viitor (roadmap)

> Funcționalități și direcții agreate ca valoroase, dar amânatе deliberat.
> Se implementează după validarea MVP-ului, în ordinea priorităților de la momentul respectiv.

### Funcționalități post-MVP
- Detectarea automată a pachetelor instalate local (deb / flatpak / snap) + sugestii de alternative.
- Sincronizarea catalogului din GitHub (buton „Actualizează catalogul").
- Screenshot-uri (la MVP: doar logo-uri mici).
- Îmbogățirea automată din Wikidata (GitHub Actions).
- Conturi, comentarii, voturi ale utilizatorilor (necesită backend — doar dacă proiectul crește).

### UI viitor
- Migrarea de la Qt Widgets la **QML/Kirigami** (aspect modern, stil Discover). Rescrierea ar afecta doar stratul UI — datele și logica rămân.

### Monetizare și susținere
- **Buton „Donații"** în aplicație (fereastra Despre / meniu) → deschide pagina de donații în browser. Platforme recomandate: Liberapay / Ko-fi / GitHub Sponsors. 100% compatibil cu GPLv3.
- **Versiune Windows/macOS plătită:** legal posibilă doar ca **GPL** (vânzare de binare, cu sursa deschisă — GPLv3 nu interzice vânzarea). Varianta cu sursă închisă a fost exclusă odată cu decizia „fără CLA" (secțiunea 12). Datele catalogului rămân oricum CC BY-SA (uz comercial permis, cu atribuire).

### Completare automată a datelor cu AI
- Opțiune de precompletare a câmpurilor la propunerea unei aplicații noi, cu model AI ales de utilizator: **local** (ex. Ollama — privat, gratuit) sau **Claude API** cu cheia personală a utilizatorului.
- Reguli de protecție: aplicația nu include nicio cheie API; fără configurare, funcția nu apare (offline-first rămâne implicit).
- **AI-ul propune, omul aprobă:** datele generate nu intră direct în catalog — trec prin fluxul agreat (verificare de utilizator → PR/issue pe GitHub → aprobare de maintainer).

---

## 🟡 În discuție (neagreate încă)

*(Momentan toate punctele deschise au fost rezolvate. Punctele noi de discuție vor fi adăugate aici.)*

---

## 📝 Istoric modificări

| Data | Modificare |
|---|---|
| 2026-10-24 | Crearea fișierului cu deciziile din prima discuție. |
| 2026-10-24 | Adăugată secțiunea 7: modelul de întreținere a datelor (sursă YAML/JSON în Git, DB generată automat, contribuții prin PR, automatizare GitHub Actions). |
| 2026-10-24 | Secțiunea 3 promovată la DECIZIE FINALĂ: PySide6 + Qt6 confirmat definitiv; Tauri respins oficial cu motivație. |
| 2026-10-24 | Detaliat MVP-ul (ecrane, schemă SQL, filtre); agreată lista „NU intră în MVP" și păstrată ca secțiunea 6b (roadmap post-MVP); adăugată propunerea privind ratingul obiectiv în „În discuție". |
| 2026-10-24 | Confirmată secțiunea 8: indicatori obiectivi de popularitate în loc de rating subiectiv; „Recomandarea editorilor" opțional, marcat ca opinie. |
| 2026-10-24 | Rezolvate toate punctele deschise: secțiunea 9 (nume: Alterna), 10 (Qt Widgets pentru MVP), 11 (contribuții doar prin GitHub cu template precompletat), 12 (GPLv3 cod + CC BY-SA 4.0 date). Lista „În discuție" golită. |
| 2026-10-24 | Creată secțiunea „💡 Idei pentru viitor": consolidat roadmap-ul post-MVP (fosta 6b), migrarea QML/Kirigami, butonul de donații, versiunea Win/Mac plătită (cu condiția CLA) și completarea datelor cu AI (local sau Claude, cu review uman). CLA adăugat la „În discuție". |
| 2026-10-24 | Creată macheta UI (`mockup-ui/`: HTML+CSS+JS, stil Breeze) și agreată ca referință vizuală — secțiunea 13: Setări cu teme comutabile (Sistem/Dark/Light/Ocean), modal Donații (Liberapay/Ko-fi/GitHub Sponsors), 12 categorii, layout cu 5 carduri pentru indicatori. |
| 2026-10-24 | Extinse opțiunile de donație de la 3 la 5: adăugate PayPal (PayPal.Me) și Revolut (revolut.me); documentată nota tehnică — plățile cu cardul trec prin procesatori externi, aplicația doar deschide linkuri. |
| 2026-10-24 | Donații restrânse la 3 active (Liberapay, Ko-fi, Revolut); GitHub Sponsors și PayPal păstrate în cod comentate, pentru activare ulterioară. |
| 2026-10-24 | Agreată secțiunea 14 — compararea aplicațiilor: buton doar în liste filtrate (nu în „Toate"), checkbox-uri, max 4 (extensibil), tabel cu evidențiere verde a celei mai bune valori, export în fișier Markdown. Rânduri suplimentare candidate trecute la „În discuție". |
| 2026-10-24 | Actualizat tabelul de comparație: eliminate popcon/stele/repo-ubuntu/nr-alternative (rămân pe pagina de detalii); adăugate Site oficial, Dimensiune la instalare, Anul primei versiuni, Formate de fișiere + 2 rânduri propuse (Dezvoltator, Limbă română). Schema datelor extinsă cu câmpurile aferente. |
| 2026-10-24 | Agreat rândul „Telemetrie" (14 rânduri în tabel) + regula de admitere ≥90% acoperire. Implementat demo pentru matricea de funcționalități normalizată (categoria Securitate: 1Password adăugat; valori gratuit/plătit/nu); trecută la „În discuție" pentru confirmarea designului. |
| 2026-10-24 | Agreată secțiunea 15 — matricea de funcționalități: doar aceeași categorie, doar în comparație, doar taxonomia „Securitate" (pilot). Exportul comparației extins la 5 formate (md/csv/html/txt/json) cu selector. „⚠ parțial" rămâne în discuție. |
| 2026-10-24 | Agreată valoarea „⚠ parțial" (a 5-a) în matricea de funcționalități. Agreată secțiunea 16 — sortarea listelor: implicită / A→Z / Z→A / recent actualizate / dimensiune mică→mare, combinabilă cu filtrele și căutarea. |
| 2026-10-24 | Reconfirmată secțiunea 12 (licențe). Extinsă taxonomia „Securitate" de la 10 la 18 rânduri în urma cercetării pe surse oficiale (Bitwarden, 1Password, KeePassXC): extensii browser, atașamente, acces de urgență, chei hardware, monitorizare breșe, CLI/API, agent SSH, audit independent. |
| 2026-10-24 | Pregătire predare proiect: reparate emoji-uri corupte la titluri, eliminate contradicții (secțiunea 2: rating/screenshot-uri actualizat; secțiunea 6: 12 categorii + funcțiile 14–16 incluse în MVP), adăugată secțiunea „📍 Stare curentă și pasul următor" + creat README.md ca punct de intrare pentru AI/dezvoltatori. |
| 2026-10-24 | Închis punctul CLA: GPL pur, fără CLA (secțiunea 12); lista „În discuție" golită definitiv — toate punctele sunt decise. |
| 2026-11-02 | Agreată secțiunea 17 — formatul YAML: specificația `data/README.md`, chei în engleză, structură `data/apps/` + `categories.yaml` + `taxonomy/`. Creat setul pilot de 8 aplicații (5 Grafică + 3 Securitate), validat prin parsare (zero erori). Descoperită și documentată capcana YAML `no` → boolean. Pasul următor: scriptul de build YAML → `catalog.db`. |
| 2026-11-02 | Creat `tools/build_catalog.py` (build YAML → `catalog.db` SQLite): schema relațională (applications, platforms, alternatives, tags, file_formats, sources, taxonomy, features, categories, metadata), toate cele 6 reguli de validare din specificație transformate în cod, exit code 1 la erori, avertismente neblocante (surse goale / versiune >2 ani). Testat pozitiv (query-uri pentru filtru+căutare, alternative, matrice, sortare) și negativ (9 erori intenționate, toate prinse). Prinsă și a doua capcană YAML: `yes` → boolean. Adăugate `requirements.txt` și `.gitignore` (`catalog.db` e produs generat, nu se comite). |
| 2026-11-02 | Creat scheletul aplicației PySide6 (`app/`: main, db, theme, widgets, main_window, detail_view, compare_view, dialogs) — reproduce macheta: căutare live, filtre, sortare, 13 categorii, detalii cu 5 carduri de fapte, comparare (max 4, doar în liste filtrate), tabel 14 rânduri + matrice Securitate (18 rânduri, tooltip la „parțial"), export md/csv/html/txt/json cu dialog nativ, teme Sistem/Dark/Light/Ocean persistente (QSettings), comutatoare indicatori funcționale, Donează/Propune prezente (Donează dezactivat până există paginile — sec. 13; Propune → GitHub, URL placeholder cu TODO sec. 9). Test de fum offscreen: 7 verificări + screenshot-uri (listă dark, comparație dark, detalii light/ocean). Depășiri agreate în implementare: pictograme provizorii generate (inițiale + culoare din id) până la logo-urile reale; sortarea „implicită" = rowid cu TODO pentru câmp de popularitate. |
| 2026-11-02 | Extins catalogul de la 8 la **100 aplicații**: migrate cele 27 rămase din machetă (date agreate) + 65 noi, acoperind toate cele 13 categorii (Grafică 11, Utilitare 12, Dezvoltare 10, Internet 10, Comunicare 8, Notițe 8, Securitate 6, Birou 6, Video 6, Audio & Playere 6, Producție audio 6, 3D & CAD 7, Streaming 4). Indicatorii noilor aplicații sunt instantanee aproximative din cunoștințele AI (de reîmprospătat automat — roadmap); valorile pentru cele 35 migrate sunt cele agreate în machetă. Validare build: 0 erori; 2 avertismente legitime (Kazam, Stacer — proiecte stagnante, prinse de regula 6). Smoke test pe catalogul mare: căutare, filtre combinate, sortări, comparație fără taxonomie (fără matrice, conform sec. 15). |
| 2026-11-02 | **Automatizarea indicatorilor:** `tools/refresh_indicators.py` (ruamel.yaml round-trip — comentariile din YAML se păstrează) din 3 surse publice fără chei: clasamentul popcon (o descărcare), packages.ubuntu.com, GitHub API + feed Atom releases. Prima rulare reală a corectat 71 de fișiere (ex. GIMP: popcon real #1860, stele 6561) și a scos la iveală date greșite din machetă (openoffice/pinta nu mai sunt în repo Ubuntu; tenacityteam/tenacity redenumit). Reguli anti-coliziune de nume documentate în cod: popcon doar pentru pachete confirmate; `in_ubuntu_repos` false→true nu se scrie automat (ex. „notion" = window manager neînrudit), ci se raportează în PR. Câmp nou opțional `package` (sec. 17 extins) + workflow `.github/workflows/refresh.yml` (PR săptămânal, aprobare la maintainer). |
| 2026-11-02 | **Logo-uri reale:** `tools/fetch_logos.py` + `data/logos/` — 55 SVG-uri din Simple Icons (CC0; sursă dublă CDN + raw GitHub, slug-map verificat manual). 45 de aplicații rămân pe inițiale — multe branduri (Adobe, VLC, Edge, Microsoft Office) au fost retrase din Simple Icons la cererea deținătorilor; e riscul acceptat al sursei unice, fallback-ul e automat. Aplicația Qt randează SVG-ul dacă există, altfel inițiale. |
| 2026-11-03 | **Reparat bug la comutarea temelor în timp de rulare** (semnalat cu capturi de pe Plasma reală): titlul h1 de pe pagina de detalii și pastilele de platforme/taguri păstrau culori din tema anterioară (invizibile: alb-pe-alb la „system", negru-pe-negru la dark/ocean). Cauză: Qt nu re-rezolvă culorile pe widgeturi deja construite la schimbarea stylesheet-ului. Fix: (1) `apply_theme` forțează unpolish/polish pe toate widgeturile, (2) regulile QSS h1/h2/tag au acum culori explicite, (3) vederea curentă se re-randează la comutare, (4) **tema se aplică acum instant la schimbarea selectorului din Setări** (previzualizare live ca în machetă, semnal `theme_changed`). Diagnostic notabil: pe Kubuntu 24.04 (Plasma 5.27) stilul Breeze nu există pentru Qt6 — aplicația rulează Fusion cu platformtheme gtk3; bug-ul nu se reproducea offscreen, doar cu fereastră reală. Verificat prin eșantionare de pixeli compoziți pe display real, toate cele 4 teme VIZIBILE, prin fluxul exact al dialogului. |
| 2026-11-03 | **Reparat DEFINITIV bug-ul textului invizibil în temele dark/ocean** (titlul h1 + descrierea din antetul paginii de detalii, semnalat cu a doua serie de capturi). Cauza reală, izolată prin reproducere minimală cu inspecție vizuală directă: `QWidget { color }` din QSS **nu ajunge la QLabel-urile din containere `QWidget` pure** (deși ajunge la cele din containere `QFrame` cu fundal QSS — de aceea cardurile erau OK, dar antetul nu); paletele widgeturilor erau corecte, dar randarea folosea culoarea paletei de sistem (închisă, din KubuntuLight). Fix: regulă explicită `QLabel { color }` per temă + corectat selectorul `QFrame#view` → `#view` (containerele de conținut sunt QWidget pur — regula nu se potrivea deloc). Verificat vizual pe display real în toate cele 4 teme (capturi înainte/după). Lecție: la buguri de randare Qt, reproducerea minimală + capturi reale bat inferența din inspecția paletelor. |
| 2026-11-03 | **Reparat bug-ul drop-down-urilor netematizate** (popup-urile QComboBox apăreau albe/netematizate în tema dark). Bisecție empirică: vinovatul era bucla manuală `unpolish/polish` din `apply_theme` (adăugată la fixul anterior) — după ea, popup-urile create ulterior pierdeau stylesheet-ul; `setStyleSheet` repetat, fără buclă, nu strică nimic. Fix: eliminată bucla; Qt re-polisează singur la StyleSheetChange, iar vederea curentă se re-randează oricum la comutare. Verificat vizual pe display real: popup corect în dark/light/system, fără regresie la texte (titlu/descriere vizibile în toate temele). Lecție înregistrată: fără unpolish/polish manual global în Qt. |
| 2026-11-03 | **Reparat bug-ul textului suprapus în QComboBox după schimbarea selecției** (după alegerea unui criteriu non-default, caseta desena textul vechi + cel nou suprapus; popup-ul se deschidea corect, sub casetă). Bisecție pe 4 variante de reguli QSS, cu capturi: `padding` și/sau `border-radius` pe QComboBox declanșează un bug de redesenare în Qt6/Fusion+QSS; doar `background+color+border` e sigur. Fix: regulă QComboBox separată, fără padding/radius (compensat cu min-height); QLineEdit nu e afectat (a rămas neschimbat). Verificat vizual: afișaj curat după selecție + popup tematizat sub casetă. |
| 2026-11-03 | **Reparată poziția popup-urilor drop-down** (după schimbarea criteriului, popup-ul „urca" sau „cobora" — se poziționa cu elementul curent suprapus peste casetă, comportamentul implicit Fusion; așteptarea, ca în machetă: mereu SUB casetă). Fix: subclasă `widgets.ComboBox(QComboBox)` cu `showPopup()` care repoziționează popup-ul sub casetă (fallback deasupra dacă nu încape pe ecran), folosită peste tot (filtre, sortare, Setări, export). Bonus: casetele au acum `AdjustToContents` — textul criteriului nu mai e trunchiat cu „...". Verificat vizual pe display real cu ultimul criteriu selectat (cazul extrem). |
| 2026-11-03 | **Bife lizibile în checkbox-uri** (bifa implicită Fusion era ștearsă în temele custom). Fix QSS: `QCheckBox::indicator` cu fundal + bordură tematizate; la bifare: fundal în culoarea de accent + bifă albă clară din `app/assets/check.svg` (cale absolută în QSS — QSS nu rezolvă căi relative). Se aplică automat și checkbox-urilor din modul comparație. Verificat vizual în ocean și light. |
| 2026-11-14 | **Prima distribuție AppImage funcțională:** adăugat `app/paths.py` (localizarea resurselor unitară pentru development și bundle PyInstaller), pipeline complet PyInstaller onedir → AppDir → AppImage în `packaging/`, cu metadata `.desktop` și AppStream, pictogramă proprie, licențe incluse, `appimagetool` descărcat doar după verificare SHA-256 și build fără FUSE (`--appimage-extract-and-run`). Bundle-ul a fost restrâns de la `--collect-all PySide6` la modulele Qt necesare (`QtCore`, `QtGui`, `QtWidgets`, `QtSvg`), reducând AppImage-ul de la 257 MB la 63 MB. Adăugat modul de diagnosticare `--selftest` (raport pe stdout + cod de ieșire) și utilitarul separat `Alterna-selftest` pentru CI. Artifact verificat: extragere reușită, selftest `REZULTAT: OK` (100 aplicații, 13 categorii, 72 logo-uri), pornire grafică offscreen fără crash. Total teste: 67 la acel moment. |
| 2026-11-14 | **Infrastructură GitHub pentru repository-ul „Alterna":** adăugat `app/links.py` (punct unic de definiție pentru URL-urile oficiale), issue template „Propunere aplicație" aliniat la formatul YAML, definiție de etichete, workflow CI (build + teste + validare metadata desktop/AppStream), workflow de release (AppImage la tag) și îmbunătățirea workflow-ului de refresh (rulează teste înainte de a deschide PR). Butonul „Propune" folosește acum linkul real, în locul URL-ului placeholder. Repository Git local inițializat pe branch `main`, cu remote `origin` → `github.com/alterna-app/Alterna` și istoric în 5 commituri tematice, fiecare validat prin worktree cu suita de teste verde. Total teste: 78. |
| 2026-11-14 | **Licențiere efectivă, delimitată corect:** adăugate textul complet GPLv3 (`LICENSE`), textul complet CC BY-SA 4.0 (`LICENSE-DATA`) și `NOTICE` cu scope-ul aplicării. Logo-urile terților au fost excluse explicit din licența CC BY-SA și documentate în `data/logos/README.md`. README, macheta, dialogul de donație și istoricul au fost sincronizate; adăugate 5 teste de licențiere (total: 52). |
| 2026-11-03 | **Mici datorii tehnice achitate (4/4):** (1) Câmp nou opțional `popularity` în YAML (sec. 17 extins) — ordinea editorială a catalogului, baza sortării „implicite" din sec. 16 (înlocuiește rowid-ul provizoriu; TODO din db.py închis); valori multiple de 10, avertisment la duplicate în build. (2) Logo-uri: a doua sursă în `fetch_logos.py` — Wikimedia Commons (Special:FilePath), 18 fișiere confirmate prin sondă → **72/100 aplicații au logo real** (Simple Icons 54 + Wikimedia 18); `IconLabel` acceptă și PNG. (3) Corectat „12 → 13 categorii" în sec. 6 și 13; notă eliminată din categories.yaml și sec. 17. (4) **Suită pytest în `tests/`** — 47 de teste verzi: build + toate cele 6 validări (inclusiv capcana `yes`→boolean), interogări/filtre/sortări (inclusiv popularity), comparație + matrice + cele 5 exporturi, GUI offscreen (regulile sec. 14: buton Compară doar în liste filtrate, max 4, anulare la „Toate"). |
