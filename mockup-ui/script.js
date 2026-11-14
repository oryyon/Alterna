/* ============================================================
   Alterna — Machetă UI: date de exemplu + logică de interfață
   (Doar demonstrație vizuală — datele reale vor veni din SQLite)
   ============================================================ */

// ---------- Date de exemplu (simulează catalog.db) ----------
const APPS = [
  {
    id: "photoshop", nume: "Adobe Photoshop", icon: "Ps", culoare: "#31a8ff",
    descriere: "Editor profesional de imagini raster, standard în industrie.",
    categorie: "Grafică", licenta: "comercial", pret: "platit",
    platforme: ["windows", "macos"], tags: ["editare foto", "raster", "design"],
    popcon: null, stele: null, ultimaVersiune: "2026-09", inRepoUbuntu: false,
    alternative: ["gimp", "krita", "photopea", "affinity"],
  },
  {
    id: "gimp", nume: "GIMP", icon: "Gi", culoare: "#5c5543",
    descriere: "Editor de imagini liber și gratuit, cu plugin-uri și scripturi.",
    categorie: "Grafică", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["editare foto", "raster"],
    popcon: 120, stele: 4800, ultimaVersiune: "2026-10", inRepoUbuntu: true,
    alternative: ["krita", "photopea", "photoshop"], recomandareEditori: true,
  },
  {
    id: "krita", nume: "Krita", icon: "Kr", culoare: "#3b82f6",
    descriere: "Aplicație de pictură digitală, făcută de artiști pentru artiști.",
    categorie: "Grafică", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android"], tags: ["pictură", "desen", "tableta grafica"],
    popcon: 310, stele: 8200, ultimaVersiune: "2026-09", inRepoUbuntu: true,
    alternative: ["gimp", "photoshop", "photopea"],
  },
  {
    id: "photopea", nume: "Photopea", icon: "Pp", culoare: "#18a497",
    descriere: "Editor foto în browser, compatibil cu fișiere PSD.",
    categorie: "Grafică", licenta: "freemium", pret: "gratuit",
    platforme: ["web"], tags: ["editare foto", "browser", "psd"],
    popcon: null, stele: null, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["gimp", "photoshop"],
  },
  {
    id: "affinity", nume: "Affinity Photo", icon: "Af", culoare: "#7b5cf0",
    descriere: "Editor foto profesional, plată unică (fără abonament).",
    categorie: "Grafică", licenta: "comercial", pret: "platit",
    platforme: ["windows", "macos"], tags: ["editare foto", "raster"],
    popcon: null, stele: null, ultimaVersiune: "2026-08", inRepoUbuntu: false,
    alternative: ["photoshop", "gimp"],
  },
  {
    id: "msoffice", nume: "Microsoft Office", icon: "Of", culoare: "#d83b01",
    descriere: "Suită de birou: Word, Excel, PowerPoint. Pe bază de abonament.",
    categorie: "Birou", licenta: "comercial", pret: "platit",
    platforme: ["windows", "macos", "android", "web"], tags: ["documente", "foi de calcul", "prezentari"],
    popcon: null, stele: null, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["libreoffice", "onlyoffice", "wps"],
  },
  {
    id: "libreoffice", nume: "LibreOffice", icon: "Lo", culoare: "#18a303",
    descriere: "Suită de birou liberă și completă, compatibilă cu formatele MS Office.",
    categorie: "Birou", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["documente", "foi de calcul", "prezentari"],
    popcon: 15, stele: 3000, ultimaVersiune: "2026-10", inRepoUbuntu: true,
    alternative: ["onlyoffice", "msoffice"], recomandareEditori: true,
  },
  {
    id: "onlyoffice", nume: "ONLYOFFICE", icon: "Oo", culoare: "#ff6f3d",
    descriere: "Suită de birou cu compatibilitate excelentă cu formatele DOCX/XLSX.",
    categorie: "Birou", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "web"], tags: ["documente", "colaborare"],
    popcon: 890, stele: 5600, ultimaVersiune: "2026-09", inRepoUbuntu: false,
    alternative: ["libreoffice", "msoffice"],
  },
  {
    id: "wps", nume: "WPS Office", icon: "Wp", culoare: "#e84c3d",
    descriere: "Suită de birou cu interfață similară MS Office; versiune gratuită cu reclame.",
    categorie: "Birou", licenta: "freemium", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android"], tags: ["documente", "foi de calcul"],
    popcon: null, stele: null, ultimaVersiune: "2026-07", inRepoUbuntu: false,
    alternative: ["libreoffice", "msoffice"],
  },
  {
    id: "premiere", nume: "Adobe Premiere Pro", icon: "Pr", culoare: "#9999ff",
    descriere: "Editor video profesional, pe bază de abonament Creative Cloud.",
    categorie: "Video", licenta: "comercial", pret: "platit",
    platforme: ["windows", "macos"], tags: ["editare video", "montaj"],
    popcon: null, stele: null, ultimaVersiune: "2026-09", inRepoUbuntu: false,
    alternative: ["kdenlive", "davinci"],
  },
  {
    id: "kdenlive", nume: "Kdenlive", icon: "Kd", culoare: "#5271ff",
    descriere: "Editor video neliniar, liber, parte din proiectul KDE.",
    categorie: "Video", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["editare video", "montaj", "kde"],
    popcon: 210, stele: 2900, ultimaVersiune: "2026-10", inRepoUbuntu: true,
    alternative: ["davinci", "premiere"], recomandareEditori: true,
  },
  {
    id: "davinci", nume: "DaVinci Resolve", icon: "Dv", culoare: "#f0a500",
    descriere: "Editor video profesional cu etalonare cromatică de top; versiune gratuită generoasă.",
    categorie: "Video", licenta: "freemium", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["editare video", "color grading"],
    popcon: null, stele: null, ultimaVersiune: "2026-08", inRepoUbuntu: false,
    alternative: ["kdenlive", "premiere"],
  },
  {
    id: "vlc", nume: "VLC", icon: "Vc", culoare: "#ff7f00",
    descriere: "Player multimedia care redă aproape orice format, fără codecuri extra.",
    categorie: "Audio & Playere", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android"], tags: ["player", "video", "audio"],
    popcon: 25, stele: 14000, ultimaVersiune: "2026-06", inRepoUbuntu: true,
    alternative: ["mpv"],
  },
  {
    id: "mpv", nume: "mpv", icon: "Mp", culoare: "#6b21a8",
    descriere: "Player minimalist și extrem de configurabil, controlat din tastatură.",
    categorie: "Audio & Playere", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["player", "minimalist"],
    popcon: 340, stele: 31000, ultimaVersiune: "2026-09", inRepoUbuntu: true,
    alternative: ["vlc"],
  },
  {
    id: "vscode", nume: "VS Code", icon: "Vc", culoare: "#0078d4",
    descriere: "Editor de cod popular, cu extensii; build-ul Microsoft include telemetrie.",
    categorie: "Dezvoltare", licenta: "freemium", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["editor", "cod", "extensii"],
    popcon: 60, stele: 170000, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["vscodium", "kate"],
  },
  {
    id: "vscodium", nume: "VSCodium", icon: "Vs", culoare: "#2f80ed",
    descriere: "Build al VS Code fără telemetrie și 100% open source.",
    categorie: "Dezvoltare", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["editor", "cod", "fara telemetrie"],
    popcon: 980, stele: 27000, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["vscode", "kate"],
  },
  {
    id: "kate", nume: "Kate", icon: "Ka", culoare: "#1abc9c",
    descriere: "Editor de text avansat de la KDE, cu LSP și sesiuni de proiect.",
    categorie: "Dezvoltare", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows"], tags: ["editor", "cod", "kde"],
    popcon: 180, stele: 1500, ultimaVersiune: "2026-10", inRepoUbuntu: true,
    alternative: ["vscode", "vscodium"],
  },
  {
    id: "firefox", nume: "Mozilla Firefox", icon: "Ff", culoare: "#ff7139",
    descriere: "Browser independent, cu motor propriu și accent pe confidențialitate.",
    categorie: "Internet", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android"], tags: ["browser", "navigare", "privacidade"],
    popcon: 10, stele: 36000, ultimaVersiune: "2026-10", inRepoUbuntu: true,
    alternative: ["brave", "chromium"],
  },
  {
    id: "brave", nume: "Brave", icon: "Br", culoare: "#fb542b",
    descriere: "Browser bazat pe Chromium, cu blocare de reclame și trackere implicită.",
    categorie: "Internet", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android"], tags: ["browser", "adblock", "privacidade"],
    popcon: null, stele: 20000, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["firefox", "chromium"],
  },
  {
    id: "chromium", nume: "Chromium", icon: "Ch", culoare: "#4d8df5",
    descriere: "Versiunea open source a browserului Chrome, fără serviciile Google.",
    categorie: "Internet", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["browser", "navigare"],
    popcon: 150, stele: 21000, ultimaVersiune: "2026-10", inRepoUbuntu: true,
    alternative: ["firefox", "brave"],
  },
  {
    id: "telegram", nume: "Telegram Desktop", icon: "Tg", culoare: "#2aabee",
    descriere: "Mesagerie rapidă cu sincronizare în cloud; clientul desktop e open source.",
    categorie: "Comunicare", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["mesagerie", "chat"],
    popcon: 240, stele: 28000, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["signal"],
  },
  {
    id: "signal", nume: "Signal", icon: "Si", culoare: "#3a76f0",
    descriere: "Mesagerie cu criptare cap-la-cap implicită, administrată de o fundație non-profit.",
    categorie: "Comunicare", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android"], tags: ["mesagerie", "criptare", "privacidade"],
    popcon: 520, stele: 15000, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["telegram"],
  },
  {
    id: "keepassxc", nume: "KeePassXC", icon: "Kp", culoare: "#66bb6a",
    descriere: "Manager de parole local, offline, cu fișiere criptate .kdbx.",
    categorie: "Securitate", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["parole", "criptare", "offline"],
    popcon: 130, stele: 23000, ultimaVersiune: "2026-09", inRepoUbuntu: true,
    alternative: ["bitwarden"], recomandareEditori: true,
  },
  {
    id: "bitwarden", nume: "Bitwarden", icon: "Bw", culoare: "#175ddc",
    descriere: "Manager de parole cu sincronizare cloud; serverul poate fi auto-găzduit.",
    categorie: "Securitate", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android", "web"], tags: ["parole", "cloud", "sincronizare"],
    popcon: null, stele: 17000, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["keepassxc", "1password"],
  },
  {
    id: "1password", nume: "1Password", icon: "1P", culoare: "#0572ec",
    descriere: "Manager de parole comercial, cu aplicații native și extensii de browser mature.",
    categorie: "Securitate", licenta: "comercial", pret: "platit",
    platforme: ["linux", "windows", "macos", "android", "web"], tags: ["parole", "cloud", "echipe", "abonament"],
    popcon: null, stele: null, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["bitwarden", "keepassxc"],
  },
  {
    id: "obs", nume: "OBS Studio", icon: "Ob", culoare: "#302e31",
    descriere: "Înregistrare de ecran și streaming live, standardul de facto.",
    categorie: "Streaming & Captură", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["streaming", "inregistrare ecran", "twitch"],
    popcon: 95, stele: 66000, ultimaVersiune: "2026-09", inRepoUbuntu: true,
    alternative: ["ssr"],
  },
  {
    id: "ssr", nume: "SimpleScreenRecorder", icon: "Ss", culoare: "#e67e22",
    descriere: "Înregistrare simplă de ecran pentru Linux, ușoară și directă.",
    categorie: "Streaming & Captură", licenta: "foss", pret: "gratuit",
    platforme: ["linux"], tags: ["inregistrare ecran", "simplu"],
    popcon: 700, stele: 3400, ultimaVersiune: "2024-11", inRepoUbuntu: true,
    alternative: ["obs"],
  },
  {
    id: "audacity", nume: "Audacity", icon: "Au", culoare: "#0000cc",
    descriere: "Editor audio multipistă, clasic pentru podcasturi și curățare de înregistrări.",
    categorie: "Producție audio", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["audio", "editare", "podcast"],
    popcon: 140, stele: 13000, ultimaVersiune: "2026-05", inRepoUbuntu: true,
    alternative: ["tenacity"],
  },
  {
    id: "tenacity", nume: "Tenacity", icon: "Te", culoare: "#8e44ad",
    descriere: "Fork al Audacity, fără telemetrie, menținut de comunitate.",
    categorie: "Producție audio", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["audio", "editare", "fara telemetrie"],
    popcon: 1600, stele: 7500, ultimaVersiune: "2025-12", inRepoUbuntu: false,
    alternative: ["audacity"],
  },
  {
    id: "blender", nume: "Blender", icon: "Bl", culoare: "#ea7600",
    descriere: "Suită completă 3D: modelare, sculptură, animație, randare, VFX.",
    categorie: "3D & CAD", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["3d", "modelare", "animatie", "randare"],
    popcon: 160, stele: 14000, ultimaVersiune: "2026-09", inRepoUbuntu: true,
    alternative: ["freecad"],
  },
  {
    id: "freecad", nume: "FreeCAD", icon: "Fc", culoare: "#cb333b",
    descriere: "CAD parametric 3D pentru inginerie și design de produs.",
    categorie: "3D & CAD", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos"], tags: ["cad", "parametric", "inginerie", "3d print"],
    popcon: 420, stele: 25000, ultimaVersiune: "2026-08", inRepoUbuntu: true,
    alternative: ["blender"],
  },
  {
    id: "joplin", nume: "Joplin", icon: "Jo", culoare: "#2f80ed",
    descriere: "Notițe markdown cu criptare și sincronizare prin servicii la alegere.",
    categorie: "Notițe", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android"], tags: ["notite", "markdown", "criptare"],
    popcon: 350, stele: 50000, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["obsidian"], recomandareEditori: true,
  },
  {
    id: "obsidian", nume: "Obsidian", icon: "Os", culoare: "#7c3aed",
    descriere: "Notițe interconectate peste fișiere markdown locale; gratuit pentru uz personal.",
    categorie: "Notițe", licenta: "freemium", pret: "gratuit",
    platforme: ["linux", "windows", "macos", "android"], tags: ["notite", "markdown", "graf de cunostinte"],
    popcon: null, stele: null, ultimaVersiune: "2026-10", inRepoUbuntu: false,
    alternative: ["joplin"],
  },
  {
    id: "peazip", nume: "PeaZip", icon: "Pz", culoare: "#16a085",
    descriere: "Arhivator cu interfață prietenoasă, suportă peste 200 de formate.",
    categorie: "Utilitare", licenta: "foss", pret: "gratuit",
    platforme: ["linux", "windows"], tags: ["arhivare", "zip", "compresie"],
    popcon: 540, stele: 5600, ultimaVersiune: "2026-09", inRepoUbuntu: true,
    alternative: ["sevenzip"],
  },
  {
    id: "sevenzip", nume: "7-Zip", icon: "7z", culoare: "#c0392b",
    descriere: "Arhivator legendar cu rata de compresie excelentă (formatul .7z).",
    categorie: "Utilitare", licenta: "foss", pret: "gratuit",
    platforme: ["windows", "linux"], tags: ["arhivare", "7z", "compresie"],
    popcon: 88, stele: 5000, ultimaVersiune: "2026-04", inRepoUbuntu: true,
    alternative: ["peazip"],
  },
];

// ---------- Date suplimentare pentru comparație (demo) ----------
// site, dimMB (MB la instalare), an (prima versiune), formate, dev (dezvoltator), ro (interfață în română)
const EXTRA = {
  photoshop:  { site: "adobe.com/products/photoshop", dimMB: 4000, an: 1990, formate: "PSD, RAW, JPG, PNG, TIFF", dev: "Adobe Inc.", ro: false },
  gimp:       { site: "gimp.org", dimMB: 300, an: 1996, formate: "XCF, PSD, JPG, PNG, TIFF", dev: "Comunitatea GIMP", ro: true },
  krita:      { site: "krita.org", dimMB: 500, an: 2005, formate: "KRA, PSD, PNG, JPG", dev: "Fundația Krita / KDE", ro: true },
  photopea:   { site: "photopea.com", dimMB: 0, an: 2013, formate: "PSD, XCF, RAW", dev: "Ivan Kutskir", ro: true },
  affinity:   { site: "affinity.serif.com", dimMB: 700, an: 2015, formate: "AFPHOTO, PSD, RAW", dev: "Serif", ro: false },
  msoffice:   { site: "microsoft.com/microsoft-365", dimMB: 3000, an: 1990, formate: "DOCX, XLSX, PPTX", dev: "Microsoft", ro: true },
  libreoffice:{ site: "libreoffice.org", dimMB: 600, an: 2011, formate: "ODF, DOCX, XLSX, PPTX", dev: "The Document Foundation", ro: true },
  onlyoffice: { site: "onlyoffice.com", dimMB: 500, an: 2014, formate: "DOCX, XLSX, PPTX, ODF", dev: "Ascensio System", ro: true },
  wps:        { site: "wps.com", dimMB: 400, an: 1988, formate: "DOCX, XLSX, PPTX", dev: "Kingsoft", ro: false },
  premiere:   { site: "adobe.com/products/premiere", dimMB: 8000, an: 2003, formate: "MP4, MOV, ProRes, MXF", dev: "Adobe Inc.", ro: false },
  kdenlive:   { site: "kdenlive.org", dimMB: 200, an: 2003, formate: "MP4, MKV, MOV, WebM", dev: "Proiectul KDE", ro: true },
  davinci:    { site: "blackmagicdesign.com", dimMB: 3000, an: 2004, formate: "MP4, MOV, ProRes, BRAW", dev: "Blackmagic Design", ro: false },
  vlc:        { site: "videolan.org", dimMB: 80, an: 2001, formate: "aproape orice (MKV, MP4, FLAC…)", dev: "VideoLAN", ro: true },
  mpv:        { site: "mpv.io", dimMB: 30, an: 2013, formate: "orice suportă FFmpeg", dev: "Comunitatea mpv", ro: false },
  vscode:     { site: "code.visualstudio.com", dimMB: 350, an: 2015, formate: "orice fișier text / cod", dev: "Microsoft", ro: true },
  vscodium:   { site: "vscodium.com", dimMB: 350, an: 2018, formate: "orice fișier text / cod", dev: "Comunitatea VSCodium", ro: true },
  kate:       { site: "kate-editor.org", dimMB: 30, an: 2001, formate: "orice fișier text / cod", dev: "Proiectul KDE", ro: true },
  firefox:    { site: "mozilla.org/firefox", dimMB: 250, an: 2004, formate: null, dev: "Mozilla", ro: true },
  brave:      { site: "brave.com", dimMB: 300, an: 2016, formate: null, dev: "Brave Software", ro: true },
  chromium:   { site: "chromium.org", dimMB: 300, an: 2008, formate: null, dev: "Proiectul Chromium", ro: true },
  telegram:   { site: "telegram.org", dimMB: 150, an: 2013, formate: null, dev: "Telegram FZ-LLC", ro: true },
  signal:     { site: "signal.org", dimMB: 200, an: 2014, formate: null, dev: "Signal Foundation", ro: true },
  keepassxc:  { site: "keepassxc.org", dimMB: 50, an: 2016, formate: "KDBX", dev: "Comunitatea KeePassXC", ro: true },
  bitwarden:  { site: "bitwarden.com", dimMB: 250, an: 2016, formate: "import CSV / JSON", dev: "Bitwarden Inc.", ro: true },
  obs:        { site: "obsproject.com", dimMB: 300, an: 2012, formate: "MP4, MKV, FLV, MOV", dev: "OBS Project", ro: true },
  ssr:        { site: "maartenbaert.be/simplescreenrecorder", dimMB: 5, an: 2012, formate: "MP4, MKV, WebM", dev: "Maarten Baert", ro: false },
  audacity:   { site: "audacityteam.org", dimMB: 60, an: 2000, formate: "WAV, MP3, FLAC, OGG", dev: "Muse Group / comunitate", ro: true },
  tenacity:   { site: "tenacityaudio.org", dimMB: 60, an: 2021, formate: "WAV, MP3, FLAC, OGG", dev: "Comunitatea Tenacity", ro: false },
  blender:    { site: "blender.org", dimMB: 350, an: 1998, formate: "BLEND, OBJ, FBX, glTF, STL", dev: "Fundația Blender", ro: false },
  freecad:    { site: "freecad.org", dimMB: 500, an: 2002, formate: "FCStd, STEP, STL, IGES", dev: "Comunitatea FreeCAD", ro: false },
  joplin:     { site: "joplinapp.org", dimMB: 250, an: 2017, formate: "Markdown, JEX, ENEX", dev: "Laurent Cozic / comunitate", ro: true },
  obsidian:   { site: "obsidian.md", dimMB: 200, an: 2020, formate: "Markdown", dev: "Dynalist Inc.", ro: false },
  peazip:     { site: "peazip.github.io", dimMB: 20, an: 2006, formate: "7Z, ZIP, TAR + alte 200", dev: "Giorgio Tani", ro: true },
  sevenzip:   { site: "7-zip.org", dimMB: 2, an: 1999, formate: "7Z, ZIP, TAR (extragere: RAR)", dev: "Igor Pavlov", ro: true },
  "1password":{ site: "1password.com", dimMB: 400, an: 2006, formate: "import CSV / 1PUX", dev: "AgileBits", ro: false },
};
APPS.forEach(a => Object.assign(a,
  { site: "—", dimMB: null, an: "—", formate: null, dev: "—", ro: null },
  EXTRA[a.id] || {}));

// ---------- Telemetrie (fapt documentabil din politica de confidențialitate) ----------
const TEL = {
  photoshop: "da", gimp: "nu", krita: "nu", photopea: "optional", affinity: "nu",
  msoffice: "da", libreoffice: "nu", onlyoffice: "optional", wps: "da",
  premiere: "da", kdenlive: "nu", davinci: "optional",
  vlc: "nu", mpv: "nu", vscode: "da", vscodium: "nu", kate: "nu",
  firefox: "optional", brave: "optional", chromium: "optional",
  telegram: "nu", signal: "nu", keepassxc: "nu", bitwarden: "optional", "1password": "optional",
  obs: "nu", ssr: "nu", audacity: "optional", tenacity: "nu",
  blender: "optional", freecad: "nu", joplin: "nu", obsidian: "optional",
  peazip: "nu", sevenzip: "nu",
};
APPS.forEach(a => a.tel = TEL[a.id] || null);
const TEL_LABELS = {
  nu: "✓ Fără telemetrie",
  optional: "Opțională (se poate dezactiva)",
  da: "Da — colectează date",
};

// ---------- Taxonomie canonică de funcționalități per categorie ----------
// Aceeasi funcție = același rând, indiferent de denumirea comercială din fiecare aplicație.
const FEATURES = {
  "Securitate": {
    offline:           "Funcționare 100% offline",
    parole:            "Generator de parole",
    autofill:          "Completare automată în browser (autofill)",
    totp:              "Authenticator integrat (TOTP / 2FA)",
    passkeys:          "Suport passkeys",
    bio:               "Deblocare biometrică",
    partajare:         "Partajare seifuri / parole în echipă",
    audit:             "Audit parole (compromise / slabe / refolosite)",
    import_export:     "Import / export date",
    selfhost:          "Auto-găzduire server (self-hosting)",
    extensii_browser:  "Extensii de browser (Chrome / Firefox / Edge / Safari)",
    atasamente:        "Stocare fișiere criptate (atașamente)",
    acces_urgenta:     "Acces de urgență / recuperare prin contacte de încredere",
    chei_hardware:     "Chei hardware de securitate (YubiKey / WebAuthn)",
    monitorizare_brese:"Monitorizare breșe de date (dark web)",
    cli_api:           "CLI / API pentru automatizări",
    ssh_agent:         "Agent SSH integrat (gestionare chei SSH)",
    audit_independent: "Audit de securitate independent, cu raport public",
  },
};
// Valori posibile: "gratuit" | "platit" | "partial" | "nu" | lipsă (necunoscut → „—")
// Notă: la rânduri factuale (ex. audit_independent), „gratuit" = da, disponibil/public.
const FUNC = {
  keepassxc:  { offline: "gratuit", parole: "gratuit", autofill: "gratuit", totp: "gratuit", passkeys: "gratuit", bio: "gratuit", partajare: "nu", audit: "gratuit", import_export: "gratuit", selfhost: "gratuit",
                extensii_browser: "gratuit", atasamente: "gratuit", acces_urgenta: "nu", chei_hardware: "partial", monitorizare_brese: "nu", cli_api: "gratuit", ssh_agent: "gratuit", audit_independent: "gratuit" },
  bitwarden:  { offline: "partial", parole: "gratuit", autofill: "gratuit", totp: "platit", passkeys: "gratuit", bio: "gratuit", partajare: "platit", audit: "platit", import_export: "gratuit", selfhost: "gratuit",
                extensii_browser: "gratuit", atasamente: "platit", acces_urgenta: "platit", chei_hardware: "gratuit", monitorizare_brese: "gratuit", cli_api: "gratuit", ssh_agent: "nu", audit_independent: "gratuit" },
  "1password":{ offline: "partial", parole: "gratuit", autofill: "gratuit", totp: "platit", passkeys: "gratuit", bio: "gratuit", partajare: "platit", audit: "gratuit", import_export: "gratuit", selfhost: "nu",
                extensii_browser: "platit", atasamente: "platit", acces_urgenta: "platit", chei_hardware: "platit", monitorizare_brese: "platit", cli_api: "platit", ssh_agent: "platit", audit_independent: "gratuit" },
};
APPS.forEach(a => a.func = FUNC[a.id] || null);

// ---------- Stare ----------
const state = {
  search: "", categorie: "", licenta: "", platforma: "", pret: "", sort: "",
  compareMode: false, selected: new Set(),
};
const MAX_COMPARE = 4;

const LICENTE = { foss: "Open Source", freemium: "Freemium", comercial: "Comercial" };
const PLATFORME = { linux: "Linux", windows: "Windows", macos: "macOS", android: "Android", web: "Web" };
const byId = Object.fromEntries(APPS.map(a => [a.id, a]));

// ---------- Elemente DOM ----------
const $ = (id) => document.getElementById(id);
const appList = $("appList"), categoryList = $("categoryList");

// ---------- Categorii ----------
function renderCategories() {
  const cats = {};
  APPS.forEach(a => cats[a.categorie] = (cats[a.categorie] || 0) + 1);
  let html = `<li data-cat="" class="${state.categorie === "" ? "active" : ""}">
    <span>☰ Toate</span><span class="cat-count">${APPS.length}</span></li>`;
  for (const [cat, n] of Object.entries(cats)) {
    html += `<li data-cat="${cat}" class="${state.categorie === cat ? "active" : ""}">
      <span>${cat}</span><span class="cat-count">${n}</span></li>`;
  }
  categoryList.innerHTML = html;
  categoryList.querySelectorAll("li").forEach(li =>
    li.addEventListener("click", () => {
      state.categorie = li.dataset.cat;
      renderCategories();
      renderList();
    }));
}

// ---------- Filtrare ----------
function filtreaza() {
  const q = state.search.toLowerCase();
  return APPS.filter(a => {
    if (q && !(a.nume.toLowerCase().includes(q) ||
               a.descriere.toLowerCase().includes(q) ||
               a.tags.some(t => t.includes(q)))) return false;
    if (state.categorie && a.categorie !== state.categorie) return false;
    if (state.licenta && a.licenta !== state.licenta) return false;
    if (state.platforma && !a.platforme.includes(state.platforma)) return false;
    if (state.pret && a.pret !== state.pret) return false;
    return true;
  });
}

// ---------- Sortare ----------
function sorteaza(lista) {
  const copie = [...lista];
  switch (state.sort) {
    case "az":     return copie.sort((a, b) => a.nume.localeCompare(b.nume, "ro"));
    case "za":     return copie.sort((a, b) => b.nume.localeCompare(a.nume, "ro"));
    case "recent": return copie.sort((a, b) => b.ultimaVersiune.localeCompare(a.ultimaVersiune));
    case "mic":    return copie.sort((a, b) => (a.dimMB ?? Infinity) - (b.dimMB ?? Infinity));
    default:       return copie; // ordinea catalogului (populare)
  }
}

// ---------- Indicatori obiectivi (secțiunea 8 din decizii) ----------
function indicatori(a) {
  const p = [];
  if (a.popcon) p.push(`<span>Popcon: <b>#${a.popcon}</b></span>`);
  if (a.stele) p.push(`<span>★ GitHub: <b>${a.stele.toLocaleString("ro-RO")}</b></span>`);
  if (a.inRepoUbuntu) p.push(`<span style="color:var(--foss)">✓ în repo Ubuntu</span>`);
  p.push(`<span>Ultima versiune: <b>${a.ultimaVersiune}</b></span>`);
  return p.join("");
}

// ---------- Card aplicație ----------
function cardHTML(a) {
  const badgeClass = { foss: "badge-foss", freemium: "badge-freemium", comercial: "badge-comercial" }[a.licenta];
  const selectat = state.selected.has(a.id);
  return `
  <div class="app-card ${a.recomandareEditori ? "editors-pick" : ""} ${state.compareMode ? "comparing" : ""} ${selectat ? "selected" : ""}" data-id="${a.id}">
    ${state.compareMode ? `<input type="checkbox" class="compare-check" ${selectat ? "checked" : ""} tabindex="-1">` : ""}
    <div class="app-icon" style="background:${a.culoare}">${a.icon}</div>
    <div class="app-info">
      <div class="app-title-row">
        <span class="app-title">${a.nume}</span>
        <span class="badge ${badgeClass}">${LICENTE[a.licenta]}</span>
        ${a.pret === "platit" ? '<span class="badge badge-comercial">cu plată</span>' : ""}
      </div>
      <div class="app-desc">${a.descriere}</div>
      <div class="app-meta">${indicatori(a)}</div>
    </div>
    ${a.recomandareEditori ? '<span class="editors-pick-label">✎ Recomandarea editorilor</span>' : ""}
    <div class="alt-count"><strong>${a.alternative.length}</strong>alternative</div>
  </div>`;
}

// ---------- Listă ----------
function renderList() {
  const rez = sorteaza(filtreaza());
  $("resultCount").textContent = `${rez.length} rezultate`;
  $("listTitle").textContent = state.categorie || (state.search ? `Căutare: „${state.search}"` : "Aplicații populare");
  appList.innerHTML = rez.length
    ? rez.map(cardHTML).join("")
    : `<div class="empty-state"><div class="big">🔍</div>Nicio aplicație nu corespunde filtrelor.<br>Încearcă să le relaxezi sau propune o aplicație nouă.</div>`;
  appList.querySelectorAll(".app-card").forEach(c =>
    c.addEventListener("click", () => {
      if (state.compareMode) toggleSelect(c.dataset.id);
      else showDetail(c.dataset.id);
    }));

  // Butonul „Compară" apare doar în liste filtrate (categorie sau căutare), nu în „Toate"
  const inListaFiltrata = state.categorie !== "" || state.search !== "";
  $("compareBtn").style.display = inListaFiltrata ? "" : "none";
  if (!inListaFiltrata && state.compareMode) toggleCompareMode();

  $("statusText").textContent = state.compareMode
    ? `Mod comparație activ — ${state.selected.size} selectate.`
    : `Afișate ${rez.length} din ${APPS.length} aplicații.`;
}

// ---------- Mod comparație ----------
function toggleSelect(id) {
  if (state.selected.has(id)) {
    state.selected.delete(id);
  } else if (state.selected.size >= MAX_COMPARE) {
    $("statusText").textContent = `Poți compara maximum ${MAX_COMPARE} aplicații — deselectează una mai întâi.`;
    return;
  } else {
    state.selected.add(id);
  }
  renderList();
  updateCompareBar();
}

function updateCompareBar() {
  const n = state.selected.size;
  $("compareCount").textContent = `${n} selectate (max ${MAX_COMPARE})`;
  $("openCompareBtn").disabled = n < 2;
}

function toggleCompareMode() {
  state.compareMode = !state.compareMode;
  if (!state.compareMode) state.selected.clear();
  $("compareBtn").classList.toggle("active", state.compareMode);
  $("compareBtn").textContent = state.compareMode ? "✕ Anulează" : "⇄ Compară";
  $("compareBar").classList.toggle("hidden", !state.compareMode);
  updateCompareBar();
  renderList();
}

// ---------- Datele comparației (sursă comună pentru tabel + export) ----------
function fmtDimMB(n) {
  if (n == null) return "—";
  if (n === 0) return "0 (aplicație web)";
  if (n >= 1000) return `~${(n / 1000).toLocaleString("ro-RO")} GB`;
  return `~${n} MB`;
}
function fmtFuncText(v) {
  return v === "gratuit" ? "gratuit" : v === "platit" ? "doar în varianta plătită" : v === "partial" ? "parțial (cu limitări)" : v === "nu" ? "Nu" : "—";
}

function dateComparatie() {
  const apps = [...state.selected].map(id => byId[id]);
  const randuri = [
    ["Descriere", ...apps.map(a => a.descriere)],
    ["Dezvoltator", ...apps.map(a => a.dev)],
    ["Categorie", ...apps.map(a => a.categorie)],
    ["Licență", ...apps.map(a => LICENTE[a.licenta])],
    ["Preț", ...apps.map(a => a.pret === "gratuit" ? "Gratuit" : "Cu plată")],
    ["Platforme", ...apps.map(a => a.platforme.map(p => PLATFORME[p]).join(", "))],
    ["Site oficial", ...apps.map(a => a.site)],
    ["Dimensiune la instalare", ...apps.map(a => fmtDimMB(a.dimMB))],
    ["Anul primei versiuni", ...apps.map(a => String(a.an))],
    ["Ultima versiune", ...apps.map(a => a.ultimaVersiune)],
    ["Telemetrie", ...apps.map(a => TEL_LABELS[a.tel] || "—")],
    ["Limbă română", ...apps.map(a => a.ro === null ? "—" : a.ro ? "Da" : "Nu")],
    ["Formate de fișiere", ...apps.map(a => a.formate || "—")],
    ["Taguri", ...apps.map(a => a.tags.map(t => "#" + t).join(" "))],
  ];
  const taxonomie = FEATURES[apps[0].categorie];
  if (taxonomie && apps.every(a => a.categorie === apps[0].categorie)) {
    randuri.push(["FUNCȚIONALITĂȚI", ...apps.map(() => "")]);
    for (const [cheie, label] of Object.entries(taxonomie)) {
      randuri.push([label, ...apps.map(a => fmtFuncText(a.func?.[cheie]))]);
    }
  }
  return { apps, randuri };
}

// ---------- Rândurile de funcționalități (matrice normalizată) ----------
function fmtFunc(v) {
  if (v === "gratuit") return `<span class="func-free">✓ gratuit</span>`;
  if (v === "platit")  return `<span class="func-paid">💲 doar în varianta plătită</span>`;
  if (v === "partial") return `<span class="func-partial" title="Există, dar cu limitări (ex: doar citire offline)">⚠ parțial</span>`;
  if (v === "nu")      return `<span class="func-no">✗ Nu</span>`;
  return "—";
}

function renderFuncRows(apps) {
  const taxonomie = FEATURES[apps[0].categorie];
  if (!taxonomie || !apps.every(a => a.categorie === apps[0].categorie)) return "";
  const separator = `<tr class="feature-separator"><th class="row-label">Funcționalități</th>${apps.map(() => "<td></td>").join("")}</tr>`;
  const randuri = Object.entries(taxonomie).map(([cheie, label]) => `
    <tr>
      <th class="row-label">${label}</th>
      ${apps.map(a => `<td class="${a.func?.[cheie] === "gratuit" ? "cell-best" : ""}">${fmtFunc(a.func?.[cheie])}</td>`).join("")}
    </tr>`).join("");
  return separator + randuri;
}

// ---------- Tabel de comparație ----------
function renderCompare() {
  const apps = [...state.selected].map(id => byId[id]);
  const badgeClass = l => ({ foss: "badge-foss", freemium: "badge-freemium", comercial: "badge-comercial" })[l];

  // „Cel mai bun" pe fiecare rând (evidențiat cu verde)
  const bestDim = Math.min(...apps.map(a => a.dimMB ?? Infinity));
  const bestVers = apps.map(a => a.ultimaVersiune).sort().reverse()[0];
  const fmtMB = n => n == null ? "—" : n === 0 ? "0 (aplicație web)" : n >= 1000 ? `~${(n / 1000).toLocaleString("ro-RO")} GB` : `~${n} MB`;

  const rand = (label, valori, bestFn) => `
    <tr>
      <th class="row-label">${label}</th>
      ${apps.map((a, i) => `<td class="${bestFn && bestFn(a) ? "cell-best" : ""}">${valori[i]}</td>`).join("")}
    </tr>`;

  $("compareContent").innerHTML = `
    <div class="compare-table-wrap">
      <table class="compare-table">
        <thead>
          <tr>
            <th class="row-label"></th>
            ${apps.map(a => `
              <th><div class="compare-app-head" data-id="${a.id}">
                <div class="app-icon" style="background:${a.culoare}">${a.icon}</div>
                <span class="app-title">${a.nume}</span>
              </div></th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${rand("Descriere", apps.map(a => a.descriere))}
          ${rand("Dezvoltator", apps.map(a => a.dev))}
          ${rand("Categorie", apps.map(a => a.categorie))}
          ${rand("Licență", apps.map(a => `<span class="badge ${badgeClass(a.licenta)}">${LICENTE[a.licenta]}</span>`), a => a.licenta === "foss")}
          ${rand("Preț", apps.map(a => a.pret === "gratuit" ? "Gratuit" : "Cu plată"), a => a.pret === "gratuit")}
          ${rand("Platforme", apps.map(a => a.platforme.map(p => PLATFORME[p]).join(", ")), a => a.platforme.includes("linux"))}
          ${rand("Site oficial", apps.map(a => a.site))}
          ${rand("Dimensiune la instalare", apps.map(a => fmtMB(a.dimMB)), a => a.dimMB != null && a.dimMB === bestDim)}
          ${rand("Anul primei versiuni", apps.map(a => a.an))}
          ${rand("Ultima versiune", apps.map(a => a.ultimaVersiune), a => a.ultimaVersiune === bestVers)}
          ${rand("Telemetrie", apps.map(a => TEL_LABELS[a.tel] || "—"), a => a.tel === "nu")}
          ${rand("Limbă română", apps.map(a => a.ro === null ? "—" : a.ro ? "✓ Da" : "✗ Nu"), a => a.ro === true)}
          ${rand("Formate de fișiere", apps.map(a => a.formate || "—"))}
          ${rand("Taguri", apps.map(a => a.tags.map(t => "#" + t).join(" ")))}
          ${renderFuncRows(apps)}
        </tbody>
      </table>
    </div>
    <p class="compare-legend"><span class="swatch"></span> = cea mai bună valoare din selecție, pe acel criteriu. Click pe numele unei aplicații pentru pagina ei de detalii.<br>
    Funcționalitățile sunt <b>normalizate per categorie</b>: aceeași funcție apare pe același rând, indiferent de denumirea comercială din fiecare aplicație.<br>
    ⚠ <i>parțial</i> = funcția există, dar cu limitări (ex: doar citire offline, doar import fără export).</p>`;

  $("compareContent").querySelectorAll(".compare-app-head").forEach(h =>
    h.addEventListener("click", () => {
      $("compareView").classList.add("hidden");
      showDetail(h.dataset.id);
    }));

  $("listView").classList.add("hidden");
  $("compareView").classList.remove("hidden");
  document.querySelector(".main-panel").scrollTop = 0;
  $("statusText").textContent = `Comparație: ${apps.map(a => a.nume).join(" vs ")}`;
}

// ---------- Pagina de detalii ----------
function showDetail(id) {
  const a = byId[id];
  const badgeClass = { foss: "badge-foss", freemium: "badge-freemium", comercial: "badge-comercial" }[a.licenta];
  $("detailContent").innerHTML = `
    <div class="detail-header">
      <div class="detail-icon" style="background:${a.culoare}">${a.icon}</div>
      <div class="detail-info">
        <h1>${a.nume} <span class="badge ${badgeClass}">${LICENTE[a.licenta]}</span></h1>
        <div class="detail-desc">${a.descriere}</div>
        <div class="detail-tags">
          ${a.platforme.map(p => `<span class="tag">${PLATFORME[p]}</span>`).join("")}
          ${a.tags.map(t => `<span class="tag">#${t}</span>`).join("")}
        </div>
      </div>
    </div>
    <div class="detail-facts">
      <div class="fact"><div class="fact-label">Popcon Ubuntu</div>
        <div class="fact-value">${a.popcon ? "#" + a.popcon : "—"}</div>
        <div class="fact-source">sursa: popularity-contest</div></div>
      <div class="fact"><div class="fact-label">Stele GitHub</div>
        <div class="fact-value">${a.stele ? "★ " + a.stele.toLocaleString("ro-RO") : "—"}</div>
        <div class="fact-source">sursa: GitHub API</div></div>
      <div class="fact"><div class="fact-label">Ultima versiune</div>
        <div class="fact-value">${a.ultimaVersiune}</div>
        <div class="fact-source">sursa: catalog / Wikidata</div></div>
      <div class="fact"><div class="fact-label">În depozitele Ubuntu</div>
        <div class="fact-value ${a.inRepoUbuntu ? "ok" : ""}">${a.inRepoUbuntu ? "✓ Da — apt install" : "✗ Nu"}</div>
        <div class="fact-source">sursa: apt</div></div>
      <div class="fact"><div class="fact-label">Preț</div>
        <div class="fact-value">${a.pret === "gratuit" ? "Gratuit" : "Cu plată"}</div>
        <div class="fact-source">sursa: catalog</div></div>
    </div>
    <h3 class="alternatives-title">Alternative <span>— ${a.alternative.length} programe similare</span></h3>
    <div class="app-list">
      ${a.alternative.map(idAlt => byId[idAlt] ? cardHTML(byId[idAlt]) : "").join("")}
    </div>`;
  $("detailContent").querySelectorAll(".app-card").forEach(c =>
    c.addEventListener("click", () => showDetail(c.dataset.id)));
  $("listView").classList.add("hidden");
  $("detailView").classList.remove("hidden");
  document.querySelector(".main-panel").scrollTop = 0;
  $("statusText").textContent = `Detalii: ${a.nume}`;
}

// ---------- Rânduri funcționalități pentru export ----------
// (integrate în dateComparatie — secțiunea FUNCȚIONALITĂȚI)

// ---------- Evenimente ----------
$("backBtn").addEventListener("click", () => {
  $("detailView").classList.add("hidden");
  $("listView").classList.remove("hidden");
  renderList();
});

$("compareBtn").addEventListener("click", toggleCompareMode);
$("openCompareBtn").addEventListener("click", renderCompare);
$("compareBackBtn").addEventListener("click", () => {
  $("compareView").classList.add("hidden");
  $("listView").classList.remove("hidden");
  renderList();
});

// Exportul comparației în fișier — format ales de utilizator
// (în aplicația Qt: dialog de salvare nativ cu filtru pe extensii)
$("exportCompareBtn").addEventListener("click", () => {
  const { apps, randuri } = dateComparatie();
  const nume = apps.map(a => a.nume);
  const data = new Date().toLocaleDateString("ro-RO");
  const format = $("exportFormat").value;
  let continut, mime;

  if (format === "md") {
    const linie = (celule) => `| ${celule.join(" | ")} |`;
    continut = [
      `# Comparație: ${nume.join(" vs ")}`, "",
      `_Generat cu Alterna — ${data}_`, "",
      linie(["Criteriu", ...nume.map(n => `**${n}**`)]),
      linie(["---", ...apps.map(() => "---")]),
      ...randuri.map(linie), "",
    ].join("\n");
    mime = "text/markdown;charset=utf-8";
  } else if (format === "csv") {
    const celula = (v) => `"${String(v).replaceAll('"', '""')}"`;
    continut = [
      ["Criteriu", ...nume].map(celula).join(";"),
      ...randuri.map(r => r.map(celula).join(";")),
    ].join("\r\n");
    mime = "text/csv;charset=utf-8";
  } else if (format === "html") {
    const e = (v) => String(v).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    continut = [
      `<!DOCTYPE html><html lang="ro"><head><meta charset="utf-8">`,
      `<title>Comparație: ${e(nume.join(" vs "))}</title>`,
      `<style>body{font-family:sans-serif;margin:2em}table{border-collapse:collapse}th,td{border:1px solid #999;padding:6px 10px;text-align:left;vertical-align:top}th{background:#eee}</style></head><body>`,
      `<h1>Comparație: ${e(nume.join(" vs "))}</h1>`,
      `<p><em>Generat cu Alterna — ${data}</em></p>`,
      `<table><tr><th>Criteriu</th>${nume.map(n => `<th>${e(n)}</th>`).join("")}</tr>`,
      ...randuri.map(r => `<tr><th>${e(r[0])}</th>${r.slice(1).map(v => `<td>${e(v)}</td>`).join("")}</tr>`),
      `</table></body></html>`,
    ].join("\n");
    mime = "text/html;charset=utf-8";
  } else if (format === "txt") {
    const lat = Math.max(...randuri.map(r => r[0].length), 8);
    continut = [
      `COMPARAȚIE: ${nume.join(" vs ")}`,
      `Generat cu Alterna — ${data}`,
      "=".repeat(60), "",
      ...randuri.map(r => `${r[0].padEnd(lat)}  ${r.slice(1).join("  |  ")}`),
      "",
    ].join("\n");
    mime = "text/plain;charset=utf-8";
  } else { // json
    continut = JSON.stringify({
      generat: data, de: "Alterna (machetă)",
      aplicatii: nume,
      criterii: Object.fromEntries(randuri.map(r => [r[0], r.slice(1)])),
    }, null, 2);
    mime = "application/json;charset=utf-8";
  }

  const blob = new Blob([continut], { type: mime });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `comparatie-alterna.${format}`;
  link.click();
  URL.revokeObjectURL(link.href);
  $("statusText").textContent = `Comparația a fost salvată: comparatie-alterna.${format}`;
});

$("searchInput").addEventListener("input", (e) => {
  state.search = e.target.value.trim();
  $("clearSearch").classList.toggle("visible", state.search.length > 0);
  renderList();
});
$("clearSearch").addEventListener("click", () => {
  $("searchInput").value = "";
  state.search = "";
  $("clearSearch").classList.remove("visible");
  renderList();
});
$("filterLicense").addEventListener("change", e => { state.licenta = e.target.value; renderList(); });
$("filterPlatform").addEventListener("change", e => { state.platforma = e.target.value; renderList(); });
$("filterPrice").addEventListener("change", e => { state.pret = e.target.value; renderList(); });
$("sortSelect").addEventListener("change", e => { state.sort = e.target.value; renderList(); });

// ---------- Modale (Setări / Donații) ----------
function deschideModal(id) { $(id).classList.remove("hidden"); }
function inchideModal(id) { $(id).classList.add("hidden"); }

$("settingsBtn").addEventListener("click", () => deschideModal("settingsModal"));
$("donateBtn").addEventListener("click", () => deschideModal("donateModal"));
document.querySelectorAll(".modal-close").forEach(b =>
  b.addEventListener("click", () => inchideModal(b.dataset.close)));
document.querySelectorAll(".modal-overlay").forEach(m =>
  m.addEventListener("click", (e) => { if (e.target === m) m.classList.add("hidden"); }));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") document.querySelectorAll(".modal-overlay").forEach(m => m.classList.add("hidden"));
});

// ---------- Teme ----------
const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

function aplicaTema(alegere) {
  let tema = alegere;
  if (alegere === "system") tema = systemDark.matches ? "dark" : "light";
  document.documentElement.dataset.theme = tema;
  localStorage.setItem("alterna-tema", alegere);
  $("statusText").textContent = `Temă aplicată: ${
    { system: "a sistemului", dark: "Breeze Dark", light: "Breeze Light", ocean: "Ocean" }[alegere]
  }${alegere === "system" ? ` (${tema === "dark" ? "întunecată" : "luminoasă"})` : ""}`;
}

$("themeSelect").addEventListener("change", (e) => aplicaTema(e.target.value));
systemDark.addEventListener("change", () => {
  if ($("themeSelect").value === "system") aplicaTema("system");
});

// ---------- Pornire ----------
const temaSalvata = localStorage.getItem("alterna-tema") || "dark";
$("themeSelect").value = temaSalvata;
aplicaTema(temaSalvata);
renderCategories();
renderList();
$("statusText").textContent = "Gata.";
