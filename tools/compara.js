/* Alterna — tabel comparativ: aceleași criterii ca în aplicația desktop.
   Regula „avantaj obiectiv”: se evidențiază DOAR criteriile verificate
   (certitudine ⟳ automat / ✓ manual) — pe un criteriu estimat nu se
   declară niciun avantaj, pentru că ar fi o presupunere, nu un fapt. */
const MAX = 4;
let DATE = null;
let alese = [];

const el = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const LIC = { foss: "Open Source", freemium: "Freemium", commercial: "Comercial" };
const PLAT = { linux: "Linux", windows: "Windows", macos: "macOS",
  android: "Android", web: "Web" };
const TELE = { none: "✓ Fără telemetrie", optional: "Opțională",
  yes: "Da", unknown: "—" };
const FEAT = { free: "✓ gratuit", paid: "💲 doar în varianta plătită",
  partial: "⚠ parțial", no: "✗ nu", unknown: "— necunoscut" };
const CERT = { auto: "⟳", manual: "✓", estimated: "≈", unknown: "?" };

function cert(app, camp) {
  const nivel = (app.confidence || {})[camp];
  return nivel ? CERT[nivel] || "" : "";
}

/* Criteriul e „avantaj obiectiv” doar dacă toate aplicațiile comparate îl
   au ca valoare verificată (⟳ sau ✓) — ca în aplicația desktop: pe un
   criteriu estimat (≈) nu se declară niciun avantaj, pentru că ar fi o
   presupunere, nu un fapt. */
function verificat(camp, apps) {
  if (!camp) return false;
  return apps.every((a) => {
    const nivel = (a.confidence || {})[camp];
    return nivel === "auto" || nivel === "manual";
  });
}

/* rând: etichetă, valori, câștigătorii (indici), câmpul de certitudine */
function rand(apps, label, valori, castigatori, camp) {
  /* Gard: un apel cu argumentele deplasate (ca cel pentru matricea de
     funcționalități) ar desena valori în coloana etichetei și indici în
     celule — fără nicio eroare vizibilă. Aici devine explicit. */
  if (!Array.isArray(apps) || typeof label !== "string" || !Array.isArray(valori)) {
    throw new Error("rand(): argumente invalide (etichetă: "
      + typeof label + ", valori: " + Array.isArray(valori) + ")");
  }
  const ok = verificat(camp, apps);
  const td = valori.map((v, i) => {
    const cls = (ok && castigatori.includes(i)) ? " class=\"avantaj\"" : "";
    const c = camp ? `<span class="cert" title="certitudine">${cert(apps[i], camp)}</span>` : "";
    return `<td${cls}>${v}${c}</td>`;
  }).join("");
  return `<tr><th>${esc(label)}</th>${td}</tr>`;
}

function dimensiuniBaza(app) {
  return app.size_basis || "";
}

function deseneaza() {
  const tbody = el("tbody");
  if (!DATE) return;
  const apps = alese.map((id) => DATE.aplicatii.find((a) => a.id === id)).filter(Boolean);
  if (apps.length < 2) {
    tbody.innerHTML = `<tr><td colspan="${apps.length + 1}" class="gol">
      Alege cel puțin două aplicații din aceeași categorie.</td></tr>`;
    el("rez").textContent = "";
    return;
  }
  const r = [];
  r.push(rand(apps, "Descriere", apps.map((a) => esc(a.description)), [], "description"));
  r.push(rand(apps, "Dezvoltator", apps.map((a) => esc(a.developer)), [], "developer"));
  r.push(rand(apps, "Categorie", apps.map((a) => esc(a.category)), [], "category"));
  r.push(rand(apps, "Licență", apps.map((a) => LIC[a.license] || a.license),
    apps.map((a, i) => a.license === "foss" ? i : -1).filter((i) => i >= 0), "license"));
  r.push(rand(apps, "Preț", apps.map((a) => a.price === "free" ? "Gratuit" : "Cu plată"),
    apps.map((a, i) => a.price === "free" ? i : -1).filter((i) => i >= 0), "price"));
  r.push(rand(apps, "Platforme", apps.map((a) => (a.platforms || []).map((p) => PLAT[p] || p).join(", ")),
    apps.map((a, i) => (a.platforms || []).includes("linux") ? i : -1).filter((i) => i >= 0), "platforms"));
  r.push(rand(apps, "Site oficial", apps.map((a) => `<a href="${esc(a.website)}" rel="noopener">${esc(a.website)}</a>`), [], "website"));
  r.push(rand(apps, "Dimensiune la instalare", apps.map((a) => a.install_size_mb ? a.install_size_mb + " MB" : "—"), [], "details.install_size_mb"));
  r.push(rand(apps, "Anul primei versiuni", apps.map((a) => a.first_release_year || "—"), [], "details.first_release_year"));
  const ver = apps.map((a) => a.latest_release || "");
  const ceaMaiNoua = ver.filter(Boolean).sort().pop();
  r.push(rand(apps, "Ultima versiune", ver.map((v) => v || "—"),
    ver.map((v, i) => v && v === ceaMaiNoua ? i : -1).filter((i) => i >= 0), "indicators.latest_release"));
  r.push(rand(apps, "Telemetrie", apps.map((a) => TELE[a.telemetry] || "—"),
    apps.map((a, i) => a.telemetry === "none" ? i : -1).filter((i) => i >= 0), "details.telemetry"));
  r.push(rand(apps, "Limbă română", apps.map((a) => a.romanian_language === true ? "Da" : a.romanian_language === false ? "Nu" : "—"),
    apps.map((a, i) => a.romanian_language === true ? i : -1).filter((i) => i >= 0), "details.romanian_language"));
  r.push(rand(apps, "Formate de fișiere", apps.map((a) => (a.file_formats || []).join(", ") || "—"), [], "details.file_formats"));
  r.push(rand(apps, "Taguri", apps.map((a) => (a.tags || []).map((t) => "#" + t).join(" ")), [], "tags"));

  /* matricea de funcționalități — doar pentru aceeași categorie */
  const categorii = [...new Set(apps.map((a) => a.category))];
  if (categorii.length === 1) {
    const randuri = (DATE.taxonomie[categorii[0]] || []);
    if (randuri.length) {
      const numeCategorie = (DATE.categorii.find((c) => c.slug === categorii[0]) || {}).name
        || categorii[0];
      r.push(`<tr class="grupa"><th colspan="${apps.length + 1}">FUNCȚIONALITĂȚI — ${esc(numeCategorie)}</th></tr>`);
      for (const item of randuri) {
        const valori = apps.map((a) => {
          const f = (a.features || {})[item.key];
          const valoare = f ? f.value : "unknown";
          const nota = f && f.note ? `<div class="nota">${esc(f.note)}</div>` : "";
          return `${FEAT[valoare] || valoare}${nota}`;
        });
        const castig = valori.map((v, i) => v.startsWith("✓") ? i : -1).filter((i) => i >= 0);
        r.push(rand(apps, item.label, valori, castig, "features"));
      }
    }
  }
  tbody.innerHTML = r.join("");
  el("rez").textContent = `${apps.length} aplicații comparate`;
}

function listeaza() {
  const categorie = el("categorie").value;
  const cautare = (el("caut").value || "").trim().toLowerCase();
  const gasite = DATE.aplicatii.filter((a) => {
    if (categorie && a.category !== categorie) return false;
    if (!cautare) return true;
    return (a.name + " " + a.description + " " + (a.tags || []).join(" ")).toLowerCase().includes(cautare);
  });
  el("lista").innerHTML = gasite.map((a) => {
    const bifat = alese.includes(a.id);
    const plin = alese.length >= MAX && !bifat;
    return `<label class="app ${bifat ? "ales" : ""} ${plin ? "plin" : ""}">
      <input type="checkbox" data-id="${esc(a.id)}" ${bifat ? "checked" : ""} ${plin ? "disabled" : ""}>
      <span class="nume">${esc(a.name)}</span>
      <span class="cat">${esc(a.category)}</span>
    </label>`;
  }).join("");
  for (const cutie of el("lista").querySelectorAll("input")) {
    cutie.addEventListener("change", () => {
      const id = cutie.dataset.id;
      if (cutie.checked) {
        if (alese.length >= MAX) { cutie.checked = false; return; }
        alese.push(id);
      } else {
        alese = alese.filter((x) => x !== id);
      }
      listeaza();
      try {
        deseneaza();
      } catch (e) {
        /* o excepție nu trebuie să dispară: mesajul apare în pagină */
        console.error(e);
        el("tbody").innerHTML =
          `<tr><td class="gol">Eroare la desenarea tabelului: ${esc(e.message)}</td></tr>`;
      }
    });
  }
}

/* --- export: aceleași 5 formate ca în aplicația desktop ----------------
   (CSV, Markdown, HTML, Text, JSON). Marcajul de certitudine și
   evidențierea avantajului obiectiv ajung și în export: o comparație
   trimisă altcuva trebuie să fie la fel de onestă ca cea afișată. */

function tabelDate() {
  /* Randurile tabelului afișat, ca structură: etichetă + celule cu
     text, marcaj de certitudine și dacă e avantaj obiectiv. */
  const randuri = [];
  for (const tr of el("tbody").querySelectorAll("tr")) {
    const celule = [...tr.children];
    if (!celule.length) continue;
    if (tr.classList.contains("grupa")) {
      randuri.push({ grup: true, eticheta: celule[0].textContent.trim(), valori: [] });
      continue;
    }
    randuri.push({
      grup: false,
      eticheta: celule[0].textContent.trim(),
      valori: celule.slice(1).map((c) => ({
        text: c.textContent.trim(),
        avantaj: c.classList.contains("avantaj"),
        certitudine: (c.querySelector(".cert") || {}).textContent || "",
      })),
    });
  }
  return randuri;
}

function numeAplicatii() {
  return alese.map((id) => (DATE.aplicatii.find((a) => a.id === id) || {}).name || id);
}

function descarcă(nume, continut, tip) {
  const url = URL.createObjectURL(new Blob([continut], { type: tip }));
  const a = document.createElement("a");
  a.href = url;
  a.download = nume;
  a.click();
  URL.revokeObjectURL(url);
}

function areTabel() {
  if (numeAplicatii().length < 2) return false;
  return el("tbody").querySelectorAll("tr").length > 0;
}

function csv() {
  if (!areTabel()) return;
  const randuri = tabelDate();
  const linii = [["Criteriu", ...numeAplicatii()]];
  for (const r of randuri) {
    if (r.grup) continue;
    linii.push([r.eticheta, ...r.valori.map((v) => v.text)]);
  }
  const continut = linii.map((l) => l.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
  descarcă("alterna-comparatie.csv", continut, "text/csv;charset=utf-8");
}

function markdown() {
  if (!areTabel()) return;
  const out = [`# Comparație — ${numeAplicatii().join(" vs ")}`, ""];
  for (const r of tabelDate()) {
    if (r.grup) {
      out.push(`## ${r.eticheta}`, "");
      continue;
    }
    const celule = [r.eticheta, ...r.valori.map((v) => v.text.replace(/\|/g, "\\|"))];
    out.push("| " + celule.join(" | ") + " |");
    out.push("|" + "---|".repeat(celule.length));
  }
  descarcă("alterna-comparatie.md", out.join("\n"), "text/markdown");
}

function html() {
  if (!areTabel()) return;
  const nume = numeAplicatii();
  const randuri = tabelDate().map((r) => {
    if (r.grup) {
      return `<tr class="grupa"><th colspan="${nume.length + 1}">${esc(r.eticheta)}</th></tr>`;
    }
    const celule = r.valori.map((v) =>
      `<td${v.avantaj ? ' class="avantaj"' : ""}>${esc(v.text)}</td>`).join("");
    return `<tr><th scope="row">${esc(r.eticheta)}</th>${celule}</tr>`;
  }).join("\n");
  const continut = `<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8">
<title>Comparație — ${esc(nume.join(" vs "))}</title>
<style>
body{font-family:sans-serif;margin:2em;background:#111;color:#eee}
h1{font-size:1.4em}
table{border-collapse:collapse;width:100%}
th,td{border:1px solid #444;padding:6px 10px;text-align:left;vertical-align:top}
th{background:#222;color:#bbb}
tr.grupa th{color:#7fb3ff;text-transform:uppercase;letter-spacing:.04em}
td.avantaj{background:rgba(39,174,96,.22)}
p.meta{color:#999}
</style>
</head>
<body>
<h1>Comparație: ${esc(nume.join(" vs "))}</h1>
<p class="meta">Generat cu Alterna — site-ul catalogului FOSS</p>
<table>
<tr><th>Criteriu</th>${nume.map((n) => `<th>${esc(n)}</th>`).join("")}</tr>
${randuri}
</table>
</body>
</html>`;
  descarcă("alterna-comparatie.html", continut, "text/html;charset=utf-8");
}

function text() {
  if (!areTabel()) return;
  const randuri = tabelDate();
  const lățime = Math.max(...randuri.map((r) => r.eticheta.length), 8);
  const out = [`COMPARAȚIE: ${numeAplicatii().join(" vs ")}`,
               "Generat cu Alterna — site-ul catalogului FOSS",
               "=".repeat(60), ""];
  for (const r of randuri) {
    if (r.grup) {
      out.push("", r.eticheta, "-".repeat(60));
      continue;
    }
    out.push(r.eticheta.padEnd(lățime) + "  " +
             r.valori.map((v) => v.text).join("  |  "));
  }
  descarcă("alterna-comparatie.txt", out.join("\n"), "text/plain;charset=utf-8");
}

function json() {
  if (!areTabel()) return;
  const continut = JSON.stringify({
    generat: new Date().toISOString().slice(0, 10),
    de: "Alterna — site-ul catalogului FOSS",
    aplicatii: numeAplicatii(),
    criterii: tabelDate().map((r) => ({
      criteriu: r.eticheta,
      grup: r.grup,
      valori: r.valori.map((v) => ({
        valoare: v.text,
        avantaj_objectiv: v.avantaj,
        certitudine: v.certitudine,
      })),
    })),
  }, null, 2);
  descarcă("alterna-comparatie.json", continut, "application/json");
}

async function porneste() {
  DATE = await (await fetch("catalog.json")).json();
  el("categorie").innerHTML = `<option value="">Toate categoriile</option>` +
    DATE.categorii.map((c) => `<option value="${esc(c.slug)}">${esc(c.name)}</option>`).join("");
  el("categorie").addEventListener("change", listeaza);
  el("caut").addEventListener("input", listeaza);
  el("csv").addEventListener("click", csv);
  el("md").addEventListener("click", markdown);
  el("html").addEventListener("click", html);
  el("txt").addEventListener("click", text);
  el("json").addEventListener("click", json);
  listeaza();
  deseneaza();
}
porneste();
