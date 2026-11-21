/* Test de regresie pentru logica tabelului comparativ (rulat de
   `tests/test_site.py::TestComparatie`, prin node).
 *
 * Simulează DOM-ul minim și verifică fluxul: alegi două aplicații → se
 * desenează tabelul. Bugul prins aici: `rand()` referința o variabilă
 * `apps` inexistentă în scope → ReferenceError → tabelul rămâne gol, fără
 * nicio eroare vizibilă în interfață.
 */
const fs = require("fs");
const path = require("path");

/* Catalogul poate fi dat ca argument (CI-ul generează site-ul într-un
   director temporar); altfel se folosește cel din repo. */
const caleCatalog = process.argv[2]
  || path.join(__dirname, "..", "site", "catalog.json");
const catalog = JSON.parse(fs.readFileSync(caleCatalog, "utf-8"));

function element(id) {
  return {
    id,
    innerHTML: "",
    textContent: "",
    value: "",
    checked: false,
    dataset: {},
    classList: { add() {}, remove() {} },
    querySelectorAll() { return []; },
    addEventListener(ev, fn) { this["on_" + ev] = fn; },
  };
}

const elemente = {};
global.document = {
  getElementById(id) {
    if (!elemente[id]) elemente[id] = element(id);
    return elemente[id];
  },
  createElement() { return element("a"); },
  querySelectorAll() { return []; },
};
global.fetch = async () => ({ json: async () => catalog });
global.Blob = class { constructor() {} };
global.URL = { createObjectURL: () => "blob:x", revokeObjectURL() {} };

/* Codul aplicației + o punte care expune funcțiile — evaluate ÎN ACELAȘI
   scope (un `eval` separat nu ar vedea `let`/`const` din primul). */
const js = fs.readFileSync(path.join(__dirname, "compara.js"), "utf-8")
  + "\n;globalThis.__punte = { deseneaza, listeaza, "
  + "alege: (v) => { alese = v; } };";
eval(js);

setTimeout(() => {
  const lista = document.getElementById("lista");
  const tbody = document.getElementById("tbody");
  const rez = document.getElementById("rez");
  if (lista.innerHTML === "") {
    console.error("FAIL: lista nu s-a desenat");
    process.exit(1);
  }
  // alegem două aplicații din aceeași categorie (grafice)
  const grafice = catalog.aplicatii.filter((a) => a.category === "graphics").slice(0, 2);
  const ids = grafice.map((a) => a.id);
  // simulăm bifarea: apelăm direct funcțiile expuse prin eval
  globalThis.__punte.alege(ids);
  globalThis.__punte.listeaza();
  globalThis.__punte.deseneaza();

  const html = tbody.innerHTML;
  if (!html.includes("<tr")) {
    console.error("FAIL: tabelul nu s-a desenat (tbody gol)");
    process.exit(1);
  }
  if (!html.includes("FUNCȚIONALITĂȚI")) {
    console.error("FAIL: matricea de funcționalități lipsește");
    process.exit(1);
  }
  if (!html.includes("avantaj")) {
    console.error("FAIL: niciun avantaj evidențiat (criteriile verificate trebuie marcate)");
    process.exit(1);
  }

  /* Matricea de funcționalități: fiecare rând trebuie să aibă ETICHETA
     taxonomiei în prima celulă și VALORILE funcționalității în celulele
     aplicațiilor. Bugul prins aici: apelul `rand()` cu argumentele
     deplasate punea valorile în coloana etichetei și indicii (0, 1, 2…)
     în celule — tabelul arăa „corect” ca formă, dar cu conținut mutat. */
  const etichete = catalog.taxonomie[grafice[0].category].map((i) => i.label);
  for (const eticheta of etichete) {
    if (!html.includes(`<th>${eticheta}</th>`)) {
      console.error("FAIL: eticheta lipseste din matrice: " + eticheta);
      process.exit(1);
    }
  }
  const randuri = html.split("</tr>");
  for (const rand of randuri) {
    const celule = [...rand.matchAll(/<td[^>]*>(.*?)<\/td>/g)].map((m) => m[1]);
    for (const celula of celule) {
      if (/^[0-9]+$/.test(celula.trim())) {
        console.error("FAIL: celula contine un index, nu o valoare: " + celula);
        process.exit(1);
      }
    }
  }
  /* nicio eticheta de functionalitate nu trebuie sa arate ca valoare */
  if (/<th>[^<]*✓ (gratuit|parțial|nu)/.test(html)) {
    console.error("FAIL: valorile de functionalitati au ajuns in coloana etichetei");
    process.exit(1);
  }
  /* Cazul raportat de utilizator: 4 aplicații din Securitate, cu notele
     de pe funcționalități. Nota trebuie randată ca text în interiorul
     <div class="nota"> — nu ca marcaj afișat brut, nici ca entități
     HTML vizibile, și nici cu majuscule (stilul `th` din CSS). */
  const securitate = catalog.aplicatii
    .filter((a) => a.category === "security").slice(0, 4);
  globalThis.__punte.alege(securitate.map((a) => a.id));
  globalThis.__punte.listeaza();
  globalThis.__punte.deseneaza();
  const htmlSec = document.getElementById("tbody").innerHTML;
  if (!htmlSec.includes("FUNCȚIONALITĂȚI — Securitate")) {
    console.error("FAIL: antetul grupei nu arata numele categoriei (Securitate)");
    process.exit(1);
  }
  if (!/<div class="nota">Citire offline;/.test(htmlSec)) {
    console.error("FAIL: nota functionalitatii nu este randata corect");
    process.exit(1);
  }
  if (/&lt;div class=&quot;nota&quot;&gt;/.test(htmlSec)
      || /<div class="nota">&lt;/.test(htmlSec)) {
    console.error("FAIL: nota apare ca marcaj HTML brut");
    process.exit(1);
  }
  if (/<th>[^<]*<div class="nota">/.test(htmlSec)) {
    console.error("FAIL: functionalitatile au ajuns in coloana etichetei");
    process.exit(1);
  }

  const linii = html.split("<tr");
  console.log("OK: tabel comparativ desenat, matricea prezentă, avantajele marcate");
  if (process.env.DUMP) {
    console.log("--- randuri cu note (Securitate) ---");
    console.log(htmlSec.split("</tr>").filter((r) => r.includes("nota"))
      .slice(0, 3).join("</tr>").slice(0, 1400));
    console.log("--- primele randuri din matricea de functionalitati ---");
    console.log(linii.slice(14, 18).join("<tr").slice(0, 1200));
  }
}, 50);
