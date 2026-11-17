
document.getElementById('data-azi').textContent =
  new Date().toLocaleDateString('ro-RO');
const caut = document.getElementById('caut');
const categorie = document.getElementById('categorie');
const rez = document.getElementById('rez');
const carduri = [...document.querySelectorAll('.card')];
function aplica() {
  const q = caut.value.trim().toLowerCase();
  const c = categorie.value;
  let n = 0;
  for (const card of carduri) {
    const t = (card.dataset.caut || '').toLowerCase();
    const viz = (!c || card.dataset.categorie === c) && (!q || t.includes(q));
    card.style.display = viz ? '' : 'none';
    if (viz) n++;
  }
  rez.textContent = n + ' din ' + carduri.length + ' aplicații';
}
caut.addEventListener('input', aplica);
categorie.addEventListener('change', aplica);
aplica();
