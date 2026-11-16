"""Teste pentru funcțiile puse la punct (review, datoriile 6, 7, 8):
actualizarea catalogului, asistentul AI și butoanele de donație.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import shutil
import sqlite3
import threading
from pathlib import Path

import pytest

from app import links
from app.ai import (CLAUDE_DEFAULT_MODEL, OLLAMA_DEFAULT_MODEL, ClaudeClient,
                    OllamaClient, extract_yaml, validate_proposal)
from app.catalog_update import (UpdateError, apply_catalog, check_schema,
                                parse_checksum, sha256_file, verify_checksum)

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def release_server(tmp_path, built_db):
    """Server local care imită release-ul GitHub (JSON + catalog + amprentă)."""
    catalog = tmp_path / "catalog.db"
    shutil.copy(built_db, catalog)
    amprenta = sha256_file(catalog)
    (tmp_path / "catalog.db.sha256").write_text(
        f"{amprenta}  catalog.db\n", encoding="utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):  # tăcă — nu vrem zgomot în teste
            pass

        def do_GET(self):  # noqa: N802 — numele impusă de http.server
            if self.path == "/releases/latest":
                base = f"http://127.0.0.1:{self.server.server_port}"
                body = json.dumps({
                    "tag_name": "v9.9.9",
                    "html_url": base + "/releases/tag/v9.9.9",
                    "assets": [
                        {"name": "catalog.db",
                         "browser_download_url": base + "/catalog.db"},
                        {"name": "catalog.db.sha256",
                         "browser_download_url": base + "/catalog.db.sha256"},
                    ],
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            fișier = tmp_path / self.path.lstrip("/")
            if fișier.exists():
                body = fișier.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    yield server
    server.shutdown()
    server.server_close()


class TestAmprenta:
    def test_parse_checksum_standard(self):
        assert parse_checksum("abc123  catalog.db\n") == "abc123"

    def test_parse_checksum_singur(self):
        assert parse_checksum("abc123") == "abc123"

    def test_parse_checksum_gol(self):
        assert parse_checksum("") == ""

    def test_sha256_file(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_bytes("conținut".encode("utf-8"))
        assert sha256_file(f) == hashlib.sha256("conținut".encode()).hexdigest()

    def test_verify_checksum_accepta(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_bytes(b"ok")
        verify_checksum(f, sha256_file(f))  # nu ridică

    def test_verify_checksum_respinge_si_sterge(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_bytes(b"ok")
        with pytest.raises(UpdateError):
            verify_checksum(f, "0" * 64)
        assert not f.exists(), "fișierul cu amprenta greșită nu trebuie păstrat"

    def test_verify_checksum_fara_amprenta_sterge(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_bytes(b"ok")
        with pytest.raises(UpdateError):
            verify_checksum(f, "")
        assert not f.exists()


class TestSchema:
    def test_schema_compatibila(self, built_db):
        assert check_schema(built_db) >= 1

    def test_schema_prea_noua_e_respinsa(self, tmp_path, built_db):
        nou = tmp_path / "nou.db"
        shutil.copy(built_db, nou)
        con = sqlite3.connect(nou)
        con.execute("UPDATE metadata SET value='99' WHERE key='schema_version'")
        con.commit()
        con.close()
        with pytest.raises(UpdateError) as exc:
            check_schema(nou)
        assert "versiune nouă" in str(exc.value)

    def test_fisier_inexistent(self, tmp_path):
        with pytest.raises(UpdateError):
            check_schema(tmp_path / "nu-exista.db")


class TestAplicare:
    def test_backup_se_pastreaza(self, tmp_path, built_db):
        curent = tmp_path / "catalog.db"
        shutil.copy(built_db, curent)
        nou = tmp_path / "catalog-nou.db"
        shutil.copy(built_db, nou)
        backup = apply_catalog(nou, curent)
        assert backup.exists()
        assert backup.read_bytes() == built_db.read_bytes()

    def test_catalogul_lipsa(self, tmp_path):
        with pytest.raises(UpdateError):
            apply_catalog(tmp_path / "nope.db", tmp_path / "catalog.db")


class TestDescarcare:
    def test_descarcare_completa(self, tmp_path, release_server, monkeypatch):
        """Flux complet: JSON release → catalog → amprentă → verificare."""
        from app import catalog_update

        monkeypatch.setattr(links, "LATEST_RELEASE_API",
                            f"{release_server.base_url}/releases/latest")
        rezultat = catalog_update.download_catalog(tmp_path / "out", timeout=15)
        assert rezultat.exists()
        assert rezultat.stat().st_size > 0
        con = sqlite3.connect(rezultat)
        assert con.execute("SELECT COUNT(*) FROM applications").fetchone()[0] >= 100
        con.close()

    def test_amprenta_greita_respinge_catalogul(self, tmp_path, release_server,
                                                  monkeypatch):
        from app import catalog_update

        monkeypatch.setattr(links, "LATEST_RELEASE_API",
                            f"{release_server.base_url}/releases/latest")
        (tmp_path / "catalog.db.sha256").write_text(
            "0" * 64 + "  catalog.db\n", encoding="utf-8")
        with pytest.raises(UpdateError):
            catalog_update.download_catalog(tmp_path / "out", timeout=15)
        assert not (tmp_path / "out" / "catalog.db").exists()

    def test_release_fara_catalog(self, tmp_path, monkeypatch):
        from app import catalog_update

        class Gol(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):  # noqa: N802
                body = json.dumps({"tag_name": "v1.0.0", "assets": []}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Gol)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            monkeypatch.setattr(
                links, "LATEST_RELEASE_API",
                f"http://127.0.0.1:{server.server_port}/releases/latest")
            with pytest.raises(UpdateError) as exc:
                catalog_update.download_catalog(tmp_path / "out", timeout=15)
            assert "nu publică un catalog" in str(exc.value)
        finally:
            server.shutdown()
            server.server_close()


PROPOZERIE_VALIDA = """id: krita
name: Krita
description: Editor de grafica vectoriala, liber si gratuit.
category: graphics
license: foss
price: free
developer: Fundația Krita / KDE
website: https://krita.org
platforms: [linux, windows]
tags: [desen, vectorial]
alternatives: []
details:
  install_size_mb: 0
  first_release_year: 0
  file_formats: []
  telemetry: none
  romanian_language: false
indicators:
  popcon_rank:
  stars:
  stars_url:
  latest_release:
  in_ubuntu_repos: false
sources:
- https://krita.org
"""


class TestPropunereAI:
    def test_extract_yaml_din_bloc_de_cod(self):
        text = "Iată propunerea:\n```yaml\n" + PROPOZERIE_VALIDA + "```\nSper să ajute."
        assert extract_yaml(text).startswith("id: krita")

    def test_extract_yaml_din_text_curat(self):
        assert extract_yaml(PROPOZERIE_VALIDA).startswith("id: krita")

    def test_extract_yaml_elimina_explicatia(self):
        text = "Sigur!\n" + PROPOZERIE_VALIDA
        assert extract_yaml(text).startswith("id: krita")

    def test_propunere_valida(self):
        date, probleme = validate_proposal(PROPOZERIE_VALIDA, {"graphics"})
        assert date is not None
        assert date["id"] == "krita"
        assert probleme == []

    def test_propunere_cu_categorie_invalida(self):
        """Propunerea e întoarsă, dar categoria greșită e raportată."""
        date, probleme = validate_proposal(
            PROPOZERIE_VALIDA.replace("category: graphics",
                                      "category: inexistent"),
            {"graphics"})
        assert date is not None
        assert any("Categorie necunoscută" in p for p in probleme)

    def test_propunere_cu_yaml_invalida(self):
        date, probleme = validate_proposal("id: [nevalid", {"graphics"})
        assert date is None
        assert probleme

    def test_campuri_lipsa_sunt_raportate(self):
        """Câmpurile lipsă apar ca „de completat manual", nu ca respingere."""
        incomplet = PROPOZERIE_VALIDA.replace("sources:\n- https://krita.org\n", "")
        date, probleme = validate_proposal(incomplet, {"graphics"})
        assert date is not None, "propunerea se întoarce oricum"
        assert probleme, "câmpurile lipsă trebuie raportate"


class TestClientiAI:
    def test_ollama_fara_cheie(self):
        client = OllamaClient()
        assert not hasattr(client, "api_key"), "Ollama nu are cheie"

    def test_claude_necheie(self):
        assert not ClaudeClient("").is_configured()
        assert ClaudeClient("sk-ant-x").is_configured()

    def test_claude_trimite_cheia_ca_header(self, monkeypatch):
        """Cheia e trimisă în header, nu în corp — și nu e inclusă în aplicație."""
        captat = {}

        def fake_post(url, payload, headers, timeout=60):
            captat["url"] = url
            captat["headers"] = headers
            captat["payload"] = payload
            return {"content": [{"type": "text", "text": "id: x\n"}]}

        monkeypatch.setattr("app.ai._post_json", fake_post)
        ClaudeClient("sk-ant-secreta").generate("test")
        assert captat["headers"]["x-api-key"] == "sk-ant-secreta"
        assert "sk-ant-secreta" not in str(captat["payload"])

    def test_promptul_include_schema(self):
        from app.ai import PROPOSAL_SYSTEM_PROMPT

        for cheie in ("id:", "name:", "category:", "license:", "price:",
                      "platforms:", "sources:", "indicators:"):
            assert cheie in PROPOSAL_SYSTEM_PROMPT, cheie

    def test_modele_implicite(self):
        assert OLLAMA_DEFAULT_MODEL
        assert CLAUDE_DEFAULT_MODEL


class TestDonatii:
    def test_exista_cel_putin_un_canal(self):
        assert links.donation_targets(), "niciun canal de donații configurat"

    def test_url_uri_sunt_https_si_reale(self):
        for target in links.donation_targets():
            assert target["url"].startswith("https://"), target
            assert target["label"], target
            assert target["note"], target

    def test_destinatiile_sunt_in_repository(self):
        """Butoanele de donație nu pot duce în afara proiectului."""
        for target in links.donation_targets():
            assert "oryyon" in target["url"], target

    def test_api_url_este_json(self):
        """Regresie: endpointul trebuie să fie API-ul JSON, nu pagina HTML."""
        assert links.LATEST_RELEASE_API.startswith("https://api.github.com/")
        assert links.LATEST_RELEASE_API.endswith("/releases/latest")

    def test_assetele_catalogului_sunt_definite(self):
        assert links.CATALOG_ASSET == "catalog.db"
        assert links.CATALOG_CHECKSUM_ASSET == "catalog.db.sha256"


class TestDialoguri:
    """Butoanele din interfață trebuie să fie funcționale, nu decorative."""

    @pytest.fixture
    def setari(self, tmp_path):
        from PySide6.QtCore import QSettings

        return QSettings(str(tmp_path / "test.ini"), QSettings.IniFormat)

    def test_butonul_de_actualizare_e_activ(self, catalog, setari, qapp):
        from app.dialogs import SettingsDialog

        dialog = SettingsDialog(setari, catalog)
        assert dialog.update_btn.isEnabled(), "butonul de actualizare e inert"
        assert "Actualizează" in dialog.update_btn.text()
        dialog.close()

    def test_sectiunea_ai_nu_e_dezactivata_cu_tota_la(self, catalog, setari, qapp):
        """Sursa AI poate fi aleasă — funcția e la punct, nu scoasă din UI."""
        from app.dialogs import SettingsDialog

        dialog = SettingsDialog(setari, catalog)
        assert dialog.ai_combo.count() == 3
        assert dialog.ai_combo.isEnabled()
        dialog.close()

    def test_ai_neconfigurat_nu_permite_generarea(self, catalog, setari, qapp):
        from app.dialogs import SettingsDialog

        dialog = SettingsDialog(setari, catalog)
        # implicit: sursa „none" → butonul de propunere e dezactivat
        assert dialog.ai_combo.currentData() == "none"
        assert not dialog.ai_propose_btn.isEnabled()
        dialog.close()

    def test_ai_ollama_activat_duce_la_butoane(self, catalog, setari, qapp):
        from app.dialogs import SettingsDialog

        dialog = SettingsDialog(setari, catalog)
        dialog.ai_combo.setCurrentIndex(1)  # „Model local (Ollama)"
        assert dialog.ai_combo.currentData() == "ollama"
        assert dialog.ai_propose_btn.isEnabled()
        assert dialog.ai_ollama_url.isEnabled()
        assert not dialog.ai_claude_key.isEnabled()
        dialog.close()

    def test_butoanele_donatie_sunt_activate(self, qapp):
        """Niciun buton de donație dezactivat — niciun buton decorativ."""
        from PySide6.QtWidgets import QPushButton

        from app.dialogs import DonateDialog

        dialog = DonateDialog()
        butoane = [b for b in dialog.findChildren(QPushButton)
                   if "♥" in b.text() and "Donează" not in b.text()]
        assert butoane, "nu există butoane de donație"
        for btn in butoane:
            assert btn.isEnabled(), btn.text()
            assert btn.toolTip().startswith("https://"), btn.text()
        dialog.close()

    def test_donatie_deschide_pagina_reala(self, qapp, monkeypatch):
        from PySide6.QtGui import QDesktopServices

        from app.dialogs import DonateDialog

        deschise = []
        monkeypatch.setattr(QDesktopServices, "openUrl",
                            lambda url: deschise.append(url.toString()) or True)
        dialog = DonateDialog()
        dialog._open("https://github.com/sponsors/oryyon")
        assert deschise == ["https://github.com/sponsors/oryyon"]
        dialog.close()


class TestImporturiDialoguri:
    """Dialogurile trebuie să folosească doar nume importate (Pylance)."""

    def test_actualizarea_catalogului_nu_arunca_name_error(self, catalog):
        """Regresie: `Path` lipsea din importuri — butonul arunca NameError.

        Fluxul e simulat (fără rețea): se verifică doar că `Path` e definit
        și că ținta descărcării e calculată corect.
        """
        from app import dialogs

        assert hasattr(dialogs, "Path"), "Path nu e importat în app/dialogs.py"
        țintă = dialogs.Path(catalog.db_path).parent / "catalog-nou.db"
        assert țintă.name == "catalog-nou.db"

    def test_salvarea_propunerii_are_path_importat(self):
        """Aceeași verificare pentru salvarea propunerii AI."""
        from app import dialogs

        assert hasattr(dialogs, "Path")

