# -*- coding: utf-8 -*-
"""ReviewPartner — ein Modell als Gegenueber, mit Gedaechtnis.

WOZU (13.08.2026)
-----------------
Ein zweites Modell taugt als Kritiker nicht deshalb, weil es mehr wuesste,
sondern weil es die eigenen Schluesse NICHT kennt und sie deshalb unbefangen
angreifen kann. Genau daran ist in der Praxis mehrfach ein Befund gescheitert,
den der Autor fuer sicher hielt.

Diese Klasse spricht mit EINEM Modell und haelt den Gespraechsverlauf. Zwei
Ziele, eine Schnittstelle:

    lokal    Ollama auf diesem Rechner (kostenlos, nichts verlaesst ihn)
    online   ein OpenAI-kompatibler Endpunkt (OpenRouter u.a.)

ZWEI FALLEN, die hier bewusst behandelt sind:

* **Ollama schneidet still ab.** Ohne ``num_ctx`` nimmt Ollama ein kleines
  Kontextfenster an und wirft den ANFANG der Frage weg. Das Modell antwortet
  trotzdem — nur eben zu Code, den es nie gesehen hat. Deshalb wird ``num_ctx``
  gesetzt UND ``prompt_eval_count`` zurueckgemeldet, damit die Oberflaeche
  zeigen kann, wie voll das Fenster war.
* **OpenRouter meldet Fehler mit HTTP 200.** Bei Drosselung, unbekanntem Modell
  oder leerem Guthaben kommt ein ``error``-Objekt statt ``choices``. Ein nackter
  KeyError sieht dann wie ein Fehler im eigenen Werkzeug aus und ist eine
  Botschaft des Dienstes.

Der Schluessel steht in EINER Datei ausserhalb des Projekts (Vorgabe
``~/.sparring_key``) — nie im Repository, nie in einer Kommandozeile (die landet
in jedem Protokoll), nie in einer Fehlermeldung.
"""
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


class ReviewFehler(RuntimeError):
    """Der Dienst hat nicht geantwortet oder eine Absage geschickt."""


class ReviewPartner:
    """Ein Gespraechspartner: Modell + Verlauf + Zaehlwerk.

        p = ReviewPartner(slug="nemotron", name="Nemotron", ziel="online",
                          modell="nvidia/nemotron-3-ultra-550b-a55b", rolle=ROLLE)
        antwort = p.fragen("Warum haengt das hier?")
        p.verlauf   # [{'role': ..., 'content': ...}, ...]
    """

    #: Kontextfenster fuer Ollama. Ein Code-Paket sind schnell 8.000 Token, die
    #: Antworten kommen dazu — 32k laesst Luft fuer mehrere Runden.
    NUM_CTX = 32768

    def __init__(self, slug, name, ziel, modell, rolle, *, url=None,
                 schluessel_datei=None, timeout=1800, num_ctx=None):
        self.slug = slug
        self.name = name or slug
        self.ziel = ziel                      # "lokal" | "online"
        self.modell = modell
        self.url = url
        self.schluessel_datei = schluessel_datei
        self.timeout = timeout
        self.num_ctx = num_ctx or self.NUM_CTX
        self.verlauf = [{"role": "system", "content": rolle}]
        #: Je Runde: {"prompt": n, "antwort": n, "sekunden": s}
        self.verbrauch = []

    # ------------------------------------------------------------------ fragen

    def fragen(self, text):
        """Eine Runde: Frage anhaengen, Antwort holen, Verlauf fortschreiben."""
        self.verlauf.append({"role": "user", "content": text})
        try:
            antwort, zahlen = (self._lokal() if self.ziel == "lokal" else self._online())
        except urllib.error.URLError as e:
            self.verlauf.pop()                # Frage nicht im Verlauf lassen
            raise ReviewFehler(
                "Verbindung zu %s fehlgeschlagen: %s%s"
                % (self.ziel, e, "  (laeuft `ollama serve`?)" if self.ziel == "lokal" else "")
            ) from e
        except Exception:
            self.verlauf.pop()
            raise
        self.verlauf.append({"role": "assistant", "content": antwort})
        self.verbrauch.append(zahlen)
        return antwort

    # ------------------------------------------------------------------- lokal

    def _lokal(self):
        daten = {
            "model": self.modell,
            "messages": self.verlauf,
            "stream": False,
            "think": False,             # spart Zeit und haelt den Antworttext sauber
            "options": {"num_ctx": self.num_ctx, "temperature": 0.5},
        }
        a = self._senden(self.url or "http://127.0.0.1:11434/api/chat", daten)
        text = (a.get("message") or {}).get("content", "")
        return text, {"prompt": a.get("prompt_eval_count"),
                      "antwort": a.get("eval_count"),
                      "fenster": self.num_ctx}

    # ------------------------------------------------------------------ online

    def _online(self):
        kopf = {"Authorization": "Bearer %s" % self._schluessel()}
        a = self._senden(self.url or "https://openrouter.ai/api/v1/chat/completions",
                         {"model": self.modell, "messages": self.verlauf}, kopf)
        if "choices" not in a:
            fehler = a.get("error") or a
            raise ReviewFehler("Dienst meldet: %s"
                               % json.dumps(fehler, ensure_ascii=False)[:300])
        nutzung = a.get("usage") or {}
        return a["choices"][0]["message"]["content"], {
            "prompt": nutzung.get("prompt_tokens"),
            "antwort": nutzung.get("completion_tokens"),
            "fenster": None}

    # ------------------------------------------------------------------ Technik

    def _senden(self, url, daten, kopf=None):
        kopfzeilen = {"Content-Type": "application/json"}
        kopfzeilen.update(kopf or {})
        anfrage = urllib.request.Request(
            url, data=json.dumps(daten).encode("utf-8"), headers=kopfzeilen)
        with urllib.request.urlopen(anfrage, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _schluessel(self):
        pfad = Path(self.schluessel_datei or (Path.home() / ".sparring_key")).expanduser()
        try:
            wert = pfad.read_text(encoding="utf-8").strip()
        except OSError:
            wert = ""
        if not wert:
            raise ReviewFehler(
                "Kein API-Schluessel. Er gehoert in genau eine Datei ausserhalb des "
                "Projekts: %s (eine Zeile). Ueber DJANGOBASE['review_schluessel_datei'] "
                "aenderbar." % pfad)
        return wert
