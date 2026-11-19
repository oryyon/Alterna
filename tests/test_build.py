"""Teste pentru tools/build_catalog.py — validări și schemă (sec. 17)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.build_catalog import build

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _copy_data(tmp_path: Path) -> Path:
    import shutil
    dest = tmp_path / "data"
    shutil.copytree(DATA, dest)
    return dest


class TestBuildReal:
    def test_build_ok(self, built_db):
        assert built_db.exists()

    def test_counts(self, built_db):
        con = sqlite3.connect(built_db)
        apps = con.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        cats = con.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        tax = con.execute("SELECT COUNT(*) FROM taxonomy").fetchone()[0]
        meta = dict(con.execute("SELECT key, value FROM metadata"))
        con.close()
        assert apps >= 100 and int(meta["app_count"]) == apps
        assert cats == 13
        # taxonomiile cresc (Securitate + Video) — verificăm proprietatea,
        # nu un număr înghețat
        assert tax >= 18, tax
        assert meta["schema_version"] == "3"

    def test_coloanele_de_instalare_sunt_populate(self, built_db):
        """Numele de pachet / snap / Flatpak sunt în catalog (punctul 16)."""
        con = sqlite3.connect(built_db)
        coloane = {r[1] for r in con.execute("PRAGMA table_info(applications)")}
        assert {"package", "snap", "flatpak"} <= coloane
        fara_pachet = con.execute(
            "SELECT COUNT(*) FROM applications WHERE package IS NULL").fetchone()[0]
        cu_snap = con.execute(
            "SELECT COUNT(*) FROM applications WHERE snap IS NOT NULL").fetchone()[0]
        cu_flatpak = con.execute(
            "SELECT COUNT(*) FROM applications WHERE flatpak IS NOT NULL").fetchone()[0]
        con.close()
        assert fara_pachet == 0, "fiecare aplicație are un nume de pachet"
        assert cu_snap > 20 and cu_flatpak > 10

    def test_popularity_column(self, built_db):
        con = sqlite3.connect(built_db)
        rows = con.execute(
            "SELECT COUNT(*) FROM applications WHERE popularity IS NULL").fetchone()
        dup = con.execute(
            "SELECT popularity, COUNT(*) c FROM applications "
            "GROUP BY popularity HAVING c > 1").fetchall()
        con.close()
        assert rows[0] == 0, "toate aplicațiile trebuie să aibă popularity"
        assert not dup, f"popularity duplicate: {dup}"


class TestValidari:
    """Fiecare regulă din data/README.md trebuie să blocheze build-ul."""

    def _fail(self, tmp_path, nume, continut):
        data = _copy_data(tmp_path)
        (data / "apps" / nume).write_text(continut, encoding="utf-8")
        return build(data, tmp_path / "out.db")

    def test_categorie_invalida(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("category: graphics", "category: nu-exista")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_alternativa_inexistenta(self, tmp_path):
        import re

        # stilul YAML poate fi bloc sau flux — înlocuim rândul, nu o secvență
        text = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8")
        bad = re.sub(r"^alternatives:.*$",
                     "alternatives: [fantoma-app, krita]", text, count=1,
                     flags=re.M)
        assert bad != text, "nu s-a putut modifica lista de alternative"
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_id_diferit_de_fisier(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("id: gimp", "id: altceva")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_camp_obligatoriu_lipsa(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("license: foss", "")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_capcana_boolean_yaml(self, tmp_path):
        """telemetry: yes fără ghilimele → boolean True → eroare (regula 4)."""
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("telemetry: none", "telemetry: yes")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_features_fara_taxonomie(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
            + "\nfeatures:\n  offline: free\n"
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_fisierele_logo_sunt_imagini_valide(self):
        """Fiecare logo trebuie să fie o imagine reală — altfel Qt afișează
        un pătrat gol în locul pictogramei."""
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent / "data" / "logos"
        for f in sorted(root.iterdir()):
            if f.suffix == ".svg":
                assert b"<svg" in f.read_bytes()[:500], f.name
            elif f.suffix == ".png":
                assert f.read_bytes()[:8].startswith(b"\x89PNG"), f.name
            elif f.suffix == ".jpg":
                assert f.read_bytes()[:3] == b"\xff\xd8\xff", f.name

    def test_campul_logo_din_yaml_exista_pe_disc(self):
        """Câmpul `logo:` trebuie să indice un fișier prezent.

        Altfel aplicația cade pe pictograma de rezervă (inițiale) fără să
        apară niciun motiv în interfață.
        """
        from pathlib import Path

        from ruamel.yaml import YAML

        root = Path(__file__).resolve().parent.parent / "data"
        yaml = YAML()
        lipsa = []
        for f in sorted((root / "apps").glob("*.yaml")):
            app = yaml.load(f.read_text(encoding="utf-8"))
            logo = app.get("logo")
            if logo and not (root / logo).exists():
                lipsa.append(f"{f.name}: {logo}")
        assert not lipsa, "logo-uri lipsă de pe disc: " + ", ".join(lipsa)
