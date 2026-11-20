"""Alterna — clienții pentru asistentul AI (sec. „Idei pentru viitor").

Regulile agreate (IDEI_PROIECT.md, secțiunea „Completare automată a datelor
cu AI"):

- sursa e **aleasă de utilizator**: local (Ollama) sau Claude API cu
  cheia personală a utilizatorului;
- aplicația **nu include nicio cheie API** și nu o trimite nicăieri;
- fără configurație, funcția nu apare — AI-ul e opțional prin
  construcție, nu doar dezactivat;
- **AI-ul propune, omul aprobă**: datele generate nu intră în catalog,
  ci ies ca o propunere pe care omul o poate revizui și trimite prin
  fluxul GitHub.

Implementarea face exact asta: generează o **propunere YAML** pentru o
aplicație nouă, o validează cu validatorul proiectului și o arată într-o
casetă de text — nu scrie nimic în catalog.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .net import USER_AGENT, NetworkError

#: Adresa implicită a serverului Ollama (local, implicit pe portul 11434).
#:
#: Folosim **127.0.0.1**, nu „localhost”: Ollama ascultă doar pe IPv4, iar
#: pe multe sisteme „localhost” rezolvă mai întâi la `::1` (IPv6). Atunci
#: conexiunea nu e refuzată, ci **expiră** — și utilizatorul vede „serverul
#: Ollama nu răspunde” deși serverul e perfect funcțional. Adresa rămâne
#: editabilă în Setări, pentru servere la altă adresă/port.
OLLAMA_DEFAULT_URL = "http://127.0.0.1:11434"

#: Modelul implicit sugerat pentru Ollama (un model de cod, bun la YAML).
OLLAMA_DEFAULT_MODEL = "llama3.1"

#: Modelul implicit pentru Claude.
CLAUDE_DEFAULT_MODEL = "claude-sonnet-4-5"

#: Endpointul Messages API pentru Claude.
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

#: Versiunea API-ului Anthropic folosită.
CLAUDE_API_VERSION = "2023-06-01"

#: Instrucțiunea dată modelului: ce trebuie să întoarcă.
PROPOSAL_SYSTEM_PROMPT = """\
Ești un contributor la catalogul Alterna, o aplicație desktop care descoperă
alternative software pe Linux. Propui fișiere YAML pentru aplicații noi.

Reguli STRICTE:
- Răspunde DOAR cu un singur bloc de cod YAML, fără explicații în afara lui.
- YAML-ul trebuie să respecte exact schema de mai jos (chei în engleză,
  valori în română).
- Folosește id-ul ca nume de fișier: doar [a-z0-9-], fără extensie.
- description: 1-2 fraze în română.
- category: unul dintre slug-urile: graphics, office, video, audio, development,
  internet, communication, security, streaming, audio-production, 3d-cad,
  notes, utilities.
- license: foss | freemium | commercial
- price: free | paid
- platforms: lista din: linux, windows, macos, android, web
- alternatives: lista de id-uri din catalog (pot fi goala: [])
- details.telemetry: none | optional | "yes"
- details.romanian_language: true | false
- sources: cel puțin o listă de URL-uri oficiale, din care se poate verifica
  fiecare valoare.
- Nu inventa indicatori (popcon, stele, dimensiune) care n-ai sursă reală:
  lasă install_size_mb și first_release_year cu valoarea 0 (necunoscut), iar
  în indicators lasă popcon_rank, stars, stars_url goale.

Schema (completează toate cheile):
id: example-app
name: Example App
description: O aplicație care face ceva util.
category: utilities
license: foss
price: free
developer: Numele dezvoltatorului
website: https://example.org
platforms: [linux, windows]
tags: [tag1, tag2]
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
- https://example.org
"""


INDICATORS_SYSTEM_PROMPT = """\
Ești un contributor la catalogul Alterna. Pentru o aplicație deja propusă,
trebuie să găsești **sursele** din care indicatorii ei se pot verifica
automat — nu valorile.

Reguli STRICTE:
- Răspunde DOAR cu un singur bloc YAML, fără explicații în afara lui.
- Pentru fiecare indicator, dă **URL-ul sursei** din care se poate citi
  valoarea, nu valoarea inventată:
    github_repo: URL-ul repository-ului (https://github.com/… sau
      https://gitlab.com/…) din care se citesc stelele și ultima versiune;
    ubuntu_package: numele pachetului din Ubuntu (dacă aplicația e
      ambalată acolo);
    releases_url: pagina de release-uri, dacă e alta decât repository-ul;
    website: site-ul oficial, dacă indicatorul se poate citi de acolo.
- Dacă nu ai o sursa sigură pentru un indicator, lasă valoarea vidă.
- Nu inventa URL-uri și nu inventa numere.

Schema:
github_repo: https://github.com/exemplu/exemplu
ubuntu_package: exemplu
releases_url:
website: https://exemplu.org
"""


class AiError(Exception):
    """Eroare de la backend-ul AI — mesajul e pregătit pentru UI.

    Marcajul `mesaj_pentru_ui` spune stratului de rețea că textul e deja
    scris pentru om: nu mai e prefixat cu „Eroare neașteptată” (o eroare
    explicată, cum e timeout-ul, nu e o surpriză tehnică).
    """

    mesaj_pentru_ui = True


def durata_text(seconds: int) -> str:
    """Durată în cuvinte: „10 minute”, „1 minut”, „45 de secunde”."""
    if seconds <= 0:
        return "fără așteptare"
    if seconds % 60 == 0:
        minute = seconds // 60
        return "1 minut" if minute == 1 else f"{minute} minute"
    return f"{seconds} de secunde"


def _post_json(url: str, payload: dict, headers: dict[str, str],
               timeout: int = 60) -> dict:
    """POST JSON și întoarce răspunsul parsat."""
    body = json.dumps(payload).encode("utf-8")
    all_headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    all_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=all_headers,
                                     method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise AiError(f"Serverul a răspuns {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AiError(f"Nu s-a putut contacta serverul: {exc.reason}") from exc
    except TimeoutError as exc:
        # Modelele mari pe CPU pot minute bune; mesajul spune ce s-a întâmplat
        # ȘI cât am așteptat, ca omul să știe dacă mai are rost să încerce.
        raise AiError(
            f"Serverul nu a răspuns în timp ({durata_text(timeout)}) — modelul "
            "e mare sau CPU-ul e lent. Poți încerca un model mai mic.") from exc
    except OSError as exc:
        raise AiError(f"Eroare de rețea: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AiError(f"Răspunsul serverului nu e JSON valid: {exc}") from exc


class OllamaClient:
    """Client pentru un server Ollama local — fără cheie, fără rețea externă."""

    def __init__(self, base_url: str = OLLAMA_DEFAULT_URL,
                 model: str = OLLAMA_DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self, timeout: int = 3) -> bool:
        """Serverul Ollama răspunde?"""
        try:
            request = urllib.request.Request(f"{self.base_url}/api/tags",
                                             headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def list_models(self, timeout: int = 5) -> list[str]:
        """Modelele disponibile pe server."""
        try:
            request = urllib.request.Request(f"{self.base_url}/api/tags",
                                             headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            raise AiError(f"Serverul Ollama nu răspunde: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AiError(f"Răspuns invalid de la Ollama: {exc}") from exc
        return [m.get("name", "") for m in data.get("models") or [] if m.get("name")]

    def loaded_models(self, timeout: int = 5) -> list[str]:
        """Modelele **încărcate în memorie** acum (nu doar descărcate).

        Ollama păstrează modelul în RAM cât timp e activ (keepalive); pot fi
        mai multe simultan. Utilizatorul vrea ca aplicația să folosească
        modelul pe care l-a încărcat el, nu unul implicit.
        """
        try:
            request = urllib.request.Request(f"{self.base_url}/api/ps",
                                             headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError):
            # serverul nu răspunde: nu e o eroare, doar nu avem model încărcat
            return []
        except json.JSONDecodeError as exc:
            raise AiError(f"Răspuns invalid de la Ollama: {exc}") from exc
        return [m.get("name", "") for m in data.get("models") or [] if m.get("name")]

    def generate(self, prompt: str, timeout: int = 600,
                 system: str = PROPOSAL_SYSTEM_PROMPT) -> str:
        """Cere o completare modelului."""
        payload = {
            "model": self.model,
            "prompt": f"{system}\n\n{user_prompt(prompt)}",
            "stream": False,
            "options": {"temperature": 0.2},
        }
        data = _post_json(f"{self.base_url}/api/generate", payload, {}, timeout)
        text = data.get("response")
        if not text:
            raise AiError("Ollama a răspuns fără text.")
        return text


#: Adresa implicită a serverului local LM Studio (portul standard 1234).
#:
#: IPv4 literal, ca la Ollama: „localhost” poate rezolva la ::1, iar serverul
#: LM Studio ascultă pe IPv4.
LMSTUDIO_DEFAULT_URL = "http://127.0.0.1:1234"

#: Modelul implicit pentru LM Studio (nimic implicit — se completează din
#: serverul local, ca la Ollama).
LMSTUDIO_DEFAULT_MODEL = ""


class LmStudioClient:
    """Client pentru serverul local al LM Studio (API compatibil cu OpenAI).

    LM Studio expune două interfețe:
      - `/v1/...` — compatibilă cu OpenAI (chat completions, listare modele);
      - `/api/v1/models` — internă, cu `loaded_instances` — de acolo știm
        care modele sunt **încărcate în RAM** (nu doar descărcate pe disc).
    """

    def __init__(self, base_url: str = LMSTUDIO_DEFAULT_URL,
                 model: str = LMSTUDIO_DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self, timeout: int = 3) -> bool:
        """Serverul LM Studio răspunde?"""
        try:
            request = urllib.request.Request(f"{self.base_url}/v1/models",
                                             headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def _get_json(self, url: str, timeout: int = 5) -> dict:
        """GET JSON de la serverul LM Studio."""
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise AiError(f"LM Studio a răspuns {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AiError(f"Serverul LM Studio nu răspunde: {exc.reason}") from exc
        except TimeoutError as exc:
            raise AiError(
                f"Serverul LM Studio nu a răspuns în timp "
                f"({durata_text(timeout)}).") from exc
        except json.JSONDecodeError as exc:
            raise AiError(f"Răspuns invalid de la LM Studio: {exc}") from exc

    def list_models(self, timeout: int = 5) -> list[str]:
        """Modelele disponibile în server (descărcate sau încărcate)."""
        data = self._get_json(f"{self.base_url}/v1/models", timeout)
        return [m.get("id", "") for m in data.get("data") or [] if m.get("id")]

    def loaded_models(self, timeout: int = 5) -> list[str]:
        """Modelele **încărcate în RAM** acum.

        API-ul intern (`/api/v1/models`) dă `loaded_instances` gol pentru
        modelele doar descărcate; `/v1/models` nu distinge încărcat de
        descărcat.
        """
        try:
            data = self._get_json(f"{self.base_url}/api/v1/models", timeout)
        except AiError:
            # serverul nu răspunde: nu e o eroare, doar nu avem model încărcat
            return []
        return [m.get("key", "") for m in data.get("models") or []
                if m.get("loaded_instances") and m.get("key")]

    def generate(self, prompt: str, timeout: int = 600,
                 system: str = PROPOSAL_SYSTEM_PROMPT) -> str:
        """Cere o completare modelului (API compatibil cu OpenAI)."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt(prompt)},
            ],
            "temperature": 0.2,
            "stream": False,
        }
        data = _post_json(f"{self.base_url}/v1/chat/completions", payload, {},
                          timeout)
        choices = data.get("choices") or []
        if not choices:
            raise AiError("LM Studio a răspuns fără alegere.")
        message = choices[0].get("message") or {}
        text = message.get("content") or ""
        if not text:
            # modelele cu „reasoning” pun răspunsul în reasoning_content
            text = message.get("reasoning_content") or ""
        if not text:
            raise AiError("LM Studio a răspuns fără text.")
        return text


class ClaudeClient:
    """Client pentru Claude API — cu cheia personală a utilizatorului.

    Aplicația nu include nicio cheie: e introdusă de utilizator și stocată
    local, în QSettings (niciun loc unde să fie furată). Cheia e trimisă
    doar către api.anthropic.com.
    """

    def __init__(self, api_key: str, model: str = CLAUDE_DEFAULT_MODEL):
        self.api_key = api_key.strip()
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, timeout: int = 120,
                 system: str = PROPOSAL_SYSTEM_PROMPT) -> str:
        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "system": system,
            "messages": [{"role": "user", "content": user_prompt(prompt)}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": CLAUDE_API_VERSION,
        }
        data = _post_json(CLAUDE_API_URL, payload, headers, timeout)
        if data.get("error"):
            raise AiError(f"Claude a răspuns cu eroare: {data['error']}")
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        if not text:
            raise AiError("Claude a răspuns fără text.")
        return text


def descriere_client(client) -> str:
    """Descrie sursa AI folosită, pentru afișare în interfață.

    De ex.: ``Ollama · model: qwen3:8b`` — utilizatorul vede mereu ce
    backend și ce model au răspuns, fără să se uite în Setări.
    """
    if isinstance(client, OllamaClient):
        return f"Ollama · model: {client.model}"
    if isinstance(client, LmStudioClient):
        return f"LM Studio · model: {client.model}"
    if isinstance(client, ClaudeClient):
        return f"Claude API · model: {client.model}"
    return "sursă AI necunoscută"


def user_prompt(request: str) -> str:
    """Cererea utilizatorului, încadrată ca sarcină de completare."""
    return (f"Propune o intrare de catalog pentru aplicația descrisă mai jos. "
            f"Răspunde strict cu blocul YAML, fără explicații.\n\n"
            f"{request.strip()}")


def indicators_prompt(request: str) -> str:
    """Cererea de **surse** pentru indicatorii unei aplicații."""
    return (f"Găsește sursele din care se pot verifica indicatorii aplicației "
            f"de mai jos. Răspunde strict cu blocul YAML, fără explicații.\n\n"
            f"{request.strip()}")


def extract_yaml(text: str) -> str:
    """Extrage blocul YAML din răspunsul modelului.

    Modelele pun adesea YAML-ul într-un bloc de cod; acceptăm și textul
    curat. Se ia primul bloc ```` ```yaml ... ``` ```` sau, lipsă, textul
    dintre primele linii `- ` / chei YAML.
    """
    text = text.strip()
    if "```" in text:
        part = text.split("```", 2)[1]
        if part.startswith("yaml"):
            part = part[4:]
        elif part.startswith("yml"):
            part = part[3:]
        text = part.strip()
    # elimină eventualele linii de explicație dinaintea primei chei YAML
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if line and not line[0].isspace() and ":" in line:
            start = i
            break
    return "\n".join(lines[start:]).strip()


class _FakePath:
    """Înlocuitor minim pentru `pathlib.Path` — validatorul folosește doar
    `.name` și `.stem`."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def stem(self) -> str:
        return self._name.rsplit(".", 1)[0]


def validate_proposal(yaml_text: str, known_categories: set[str]):
    """Validează o propunere YAML cu validatorul proiectului.

    Returnează (date, probleme). `date` e `None` dacă YAML-ul nu e valid
    sau nu respectă schema. Folosim exact validatorul din
    `tools/build_catalog.py` — deci AI-ul nu poate propune ceva ce build-ul
    ar respinge.
    """
    import yaml as _yaml

    from tools.build_catalog import Reporter, validate_app

    try:
        data = _yaml.safe_load(yaml_text)
    except _yaml.YAMLError as exc:
        return None, [f"YAML invalid: {exc}"]
    if not isinstance(data, dict):
        return None, ["Răspunsul nu e un mapping YAML."]

    reporter = Reporter()
    validate_app(_FakePath(f"{data.get('id', 'propunere')}.yaml"), data,
                 {}, reporter)
    probleme = list(reporter.errors) + list(reporter.warnings)
    if data.get("category") not in known_categories:
        probleme.append(f"Categorie necunoscută: {data.get('category')!r}")
    # Propunerea se întoarce oricum: problemele sunt lista de „de completat
    # manual", nu motiv de respingere. AI-ul propune, omul aprobă.
    return data, probleme
