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
      r.push(`<tr class="grupa"><th colspan="${apps.length + 1}">FUNCȚIONALITĂȚI — ${esc(categorii[0])}</th></tr>`);
      for (const item of randuri) {
        const valori = apps.map((a) => {
          const f = (a.features || {})[item.key];
          const valoare = f ? f.value : "unknown";
          const nota = f && f.note ? `<div class="nota">${esc(f.note)}</div>` : "";
          return `${FEAT[valoare] || valoare}${nota}`;
        });
        const castig = valori.map((v, i) => v.startsWith("✓") ? i : -1).filter((i) => i >= 0);
        r.push(rand(item.label, valori, castig));
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
      deseneaza();
    });
  }
}

function csv() {
  const apps = alese.map((id) => DATE.aplicatii.find((a) => a.id === id)).filter(Boolean);
  if (apps.length < 2) return;
  const linii = [["Criteriu", ...apps.map((a) => a.name)]];
  const tabel = el("tbody").querySelectorAll("tr");
  for (const tr of tabel) {
    const celule = [...tr.children].map((c) => c.textContent.trim());
    if (celule.length) linii.push(celule);
  }
  const continut = linii.map((l) => l.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([continut], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "alterna-comparatie.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function markdown() {
  const apps = alese.map((id) => DATE.aplicatii.find((a) => a.id === id)).filter(Boolean);
  if (apps.length < 2) return;
  const out = [`# Comparație — ${apps.map((a) => a.name).join(" vs ")}`, ""];
  const tabel = el("tbody").querySelectorAll("tr");
  for (const tr of tabel) {
    const celule = [...tr.children].map((c) => c.textContent.trim().replace(/\|/g, "\\|"));
    out.push("| " + celule.join(" | ") + " |");
    if (tr.classList.contains("grupa")) out.push("|" + "---|".repeat(celule.length));
  }
  const url = URL.createObjectURL(new Blob([out.join("\n")], { type: "text/markdown" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "alterna-comparatie.md";
  a.click();
  URL.revokeObjectURL(url);
}

async function porneste() {
  DATE = await (await fetch("catalog.json")).json();
  el("categorie").innerHTML = `<option value="">Toate categoriile</option>` +
    DATE.categorii.map((c) => `<option value="${esc(c.slug)}">${esc(c.name)}</option>`).join("");
  el("categorie").addEventListener("change", listeaza);
  el("caut").addEventListener("input", listeaza);
  el("csv").addEventListener("click", csv);
  el("md").addEventListener("click", markdown);
  listeaza();
  deseneaza();
}
porneste();
