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
  console.log("OK: tabel comparativ desenat, matricea prezentă, avantajele marcate");
}, 50);
