"""Teste pentru completarea indicatorilor cu ajutorul AI.

Regula pe care o verifică aici: **AI-ul propune surse, nu valori**. Numai
valorile confirmate de uneltă (API-ul GitHub, arhiva Ubuntu) ajung în
catalog — o valoare nesurprinsă de nicaieri nu se scrie niciodată.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


class TestVerificareSurse:
    def test_repo_goleste_stelele_si_versiunea(self, monkeypatch):
        import complete_indicators as ci

        def fake_json(url, token=""):
            if url.endswith("/releases/latest"):
                return {"published_at": "2026-11-03T10:00:00Z"}
            return {"stargazers_count": 1234}

        monkeypatch.setattr(ci, "github_json", fake_json)
        rezultat = ci.verifica_repo("GNOME/gimp")
        assert rezultat["stars"] == 1234
        assert rezultat["stars_url"] == "https://github.com/GNOME/gimp"
        assert rezultat["latest_release"] == "2026-11"

    def test_repo_inaccesibil_nu_produce_valori(self, monkeypatch):
        import complete_indicators as ci

        monkeypatch.setattr(ci, "github_json", lambda url, token="": None)
        assert ci.verifica_repo("nope/nope") == {}

    def test_pachet_existent_in_arhiva(self):
        import complete_indicators as ci

        rezultat = ci.verifica_pachet("gimp")
        assert rezultat.get("in_ubuntu_repos") is True

    def test_pachet_inexistent(self):
        import complete_indicators as ci

        assert ci.verifica_pachet("pachet-inexistent-xyz") == {}

    def test_aplica_scrie_doar_valori_verificate(self, monkeypatch):
        import complete_indicators as ci

        monkeypatch.setattr(ci, "github_json", lambda url, token="": None)
        rezultat = ci.aplica({"sources": []},
                             {"github_repo": "x/y", "ubuntu_package": "gimp"})
        assert "stars" not in rezultat
        assert rezultat.get("in_ubuntu_repos") is True


class TestPromptSurse:
    def test_promptul_cere_surse_nu_valori(self):
        from app.ai import INDICATORS_SYSTEM_PROMPT

        text = INDICATORS_SYSTEM_PROMPT.lower()
        assert "surs" in text
        assert "github_repo" in INDICATORS_SYSTEM_PROMPT
        assert "ubuntu_package" in INDICATORS_SYSTEM_PROMPT

    def test_user_prompt_specific(self):
        from app.ai import indicators_prompt

        text = indicators_prompt("Aplicație: Exemplu")
        assert "Exemplu" in text
        assert "yaml" in text.lower()

    def test_backendul_accepta_prompt_de_sistem(self):
        """`generate()` trebuie să poată folosi promptul de surse."""
        import inspect

        from app.ai import OllamaClient

        parametru = inspect.signature(OllamaClient.generate).parameters
        assert "system" in parametru
