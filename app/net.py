"""Alterna — stratul HTTP (actualizare catalog, asistent AI).

Folosim `urllib` din biblioteca standard, nu `QtNetwork`, pentru două
 motive:
- bundle-ul AppImage rămâne la dimensiunea actuală (63 MB) — `QtNetwork`
  ar fi însă un modul Qt în plus, cu biblioteci de sistem noi;
- `.deb` nu ar necesita dependențe noi.

Cererile lungi rulează într-un `QThread`, ca interfața să nu se blocheze.
Principiul offline-first rămâne: rețeaua e folosită doar la cerere
explicită a utilizatorului, niciodată implicit la pornire.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

#: User-Agent identificabil — API-ul GitHub cere unul.
USER_AGENT = "Alterna/0.2 (+https://github.com/oryyon/Alterna)"

#: Timeout implicit pentru cererile HTTP (secunde).
DEFAULT_TIMEOUT = 15


class NetworkError(Exception):
    """Eroare de rețea, mesajul e deja gata de arătat utilizatorului."""


def http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """Descarcă un URL. Ridică NetworkError cu mesaj lizibil."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise NetworkError(f"Serverul a răspuns {exc.code} ({exc.reason})") from exc
    except urllib.error.URLError as exc:
        raise NetworkError(f"Nu s-a putut contacta serverul: {exc.reason}") from exc
    except OSError as exc:
        raise NetworkError(f"Eroare de rețea: {exc}") from exc


def http_get_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Descarcă un JSON. Ridică NetworkError la orice problemă."""
    raw = http_get(url, timeout=timeout)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NetworkError(f"Răspunsul serverului nu e JSON valid: {exc}") from exc


def http_download(url: str, dest: Path, timeout: int = DEFAULT_TIMEOUT) -> int:
    """Descarcă un URL într-un fișier. Returnează numărul de octeți."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            with tmp.open("wb") as handle:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
    except urllib.error.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        raise NetworkError(f"Serverul a răspuns {exc.code} ({exc.reason})") from exc
    except urllib.error.URLError as exc:
        tmp.unlink(missing_ok=True)
        raise NetworkError(f"Nu s-a putut contacta serverul: {exc.reason}") from exc
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise NetworkError(f"Eroare la descărcare: {exc}") from exc
    tmp.replace(dest)
    return dest.stat().st_size


class NetworkTask(QObject):
    """Rulează o funcție de rețea într-un thread și raportează rezultatul.

    Semnalele: `finished(object)` la succes, `failed(str)` la eșec.
    """

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._func(*self._args, **self._kwargs)
        except NetworkError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 — erori neașteptate, dar UI-ul nu trebuie să cadă
            self.failed.emit(f"Eroare neașteptată: {exc}")
        else:
            self.finished.emit(result)


def run_in_thread(parent, func, on_success, on_error, *args, **kwargs) -> None:
    """Rulează `func` într-un thread; apelează on_success / on_error.

    Thread-ul și task-ul sunt păstrate ca atribute pe `parent`, ca să nu
    fie colectate de garbage collector înainte de terminare (capcană clasică
    în Qt).
    """
    task = NetworkTask(func, *args, **kwargs)
    thread = QThread()
    task.moveToThread(thread)
    task.finished.connect(on_success)
    task.failed.connect(on_error)
    thread.started.connect(task.run)

    def _cleanup() -> None:
        thread.quit()
        thread.wait(2000)

    task.finished.connect(_cleanup)
    task.failed.connect(_cleanup)
    thread.finished.connect(task.deleteLater)

    parent._net_tasks = getattr(parent, "_net_tasks", [])
    parent._net_tasks.append((task, thread))
    thread.start()


def clear_threads(parent) -> None:
    """Oprește și eliberează thread-urile de rețea pornite de `parent`."""
    for task, thread in getattr(parent, "_net_tasks", []):
        try:
            thread.quit()
            thread.wait(1000)
        except RuntimeError:
            pass
    parent._net_tasks = []
