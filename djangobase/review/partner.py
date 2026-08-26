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

from ..ki.parameter import KiParameter

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

    #: Temperatur, wenn NICHTS anderes gesetzt ist.
    #:
    #: 0.5 statt der Herstellervorgabe (bei allen gemessenen Modellen 1.0):
    #: Ein Kritiker soll belegen, nicht ausschmuecken. Der Wert stand seit dem
    #: 13.08.2026 fest im Code und bleibt deshalb hier die Vorgabe - haette ich
    #: beim Umbau auf ``KiParameter`` auf Modellstandard umgestellt, haetten
    #: sich stillschweigend die Antworten in allen sechs djangoBase-Projekten
    #: geaendert. Wer es anders will, uebergibt ``parameter``.
    TEMPERATUR = 0.5

    def __init__(self, slug, name, ziel, modell, rolle, *, url=None,
                 schluessel_datei=None, timeout=1800, num_ctx=None,
                 parameter=None):
        self.slug = slug
        self.name = name or slug
        self.ziel = ziel                      # "lokal" | "online"
        self.modell = modell
        self.url = url
        self.schluessel_datei = schluessel_datei
        self.timeout = timeout
        self.num_ctx = num_ctx or self.NUM_CTX
        #: Die Stellschrauben dieser Anfrage (``ki/parameter.py``). Ohne Angabe
        #: die bisherige Einstellung - siehe :attr:`TEMPERATUR`.
        #:
        #: ``num_ctx`` bleibt getrennt fuehrbar: Es ist der einzige Wert, den
        #: diese Klasse selbst braucht (sie meldet ihn als ``fenster`` zurueck),
        #: und Aufrufer setzen ihn seit jeher ueber ``num_ctx=``. Ein
        #: uebergebener Parametersatz ohne eigenes ``kontext`` erbt ihn.
        self.parameter = parameter or self._aus_konfiguration(modell)
        if self.parameter.kontext is None:
            self.parameter = self.parameter.mit(kontext=self.num_ctx)
        else:
            self.num_ctx = self.parameter.kontext
        # ``parameter.system`` GREIFT HIER NICHT - und das ist kein Versehen:
        # Der System-Prompt dieser Klasse IST die ``rolle``, sie steht als
        # erste Nachricht im Verlauf. ``KiParameter.vor_verlauf`` verdoppelt
        # eine vorhandene System-Nachricht bewusst nicht, die vorhandene
        # gewinnt. Belegt am 25.08.2026: Ein Parametersatz mit „antworte
        # ausschliesslich auf Englisch" blieb wirkungslos, die Antwort kam auf
        # Deutsch - ohne jeden Hinweis. Genau diese stille Wirkungslosigkeit
        # bekommt deshalb eine Meldung; das Feld bleibt fuer Aufrufer nutzbar,
        # die ihren Verlauf selbst bauen (etwa werkzeug/gpu_nutzen.py).
        if self.parameter.system:
            logger.warning("ReviewPartner(%s): parameter.system wird ignoriert - "
                           "der System-Prompt dieser Klasse ist die 'rolle'.", slug)
        self.verlauf = [{"role": "system", "content": rolle}]
        #: Je Runde: {"prompt": n, "antwort": n, "sekunden": s}
        self.verbrauch = []

    @classmethod
    def _aus_konfiguration(cls, modell):
        u"""Die Einstellung fuer DIESES Modell aus ``DJANGOBASE["ki_parameter"]``.

        Aufbau (25.08.2026, Auftrag „Einstellungen pro KI"):

            DJANGOBASE["ki_parameter"] = {
                "*":            {"temperature": 0.5},      # gilt fuer alle
                "qwen3.8:27b":  {"temperature": 0.2, "top_k": 20},
                "gpt-oss":      {"max_tokens": 4000},      # ganze Familie
            }

        Gesucht wird vom Genauen zum Allgemeinen: voller Name, Name ohne
        Quantisierungs-Endung, Familie, dann ``*``. Der erste Treffer gewinnt -
        es wird NICHT zusammengemischt, weil sonst niemand mehr sagen kann,
        woher ein einzelner Wert stammt.

        OHNE KONFIGURATION bleibt es bei :attr:`TEMPERATUR` - dem Wert, der
        hier seit dem 13.08.2026 fest im Code stand. Das ist Absicht: djangoBase
        haengt in rund sechs Projekten, und keines davon soll durch diesen Umbau
        andere Antworten bekommen, solange es nichts einstellt.

        Django ist hier eine WEICHE Abhaengigkeit: Das Werkzeug
        ``sparring_vergleich.py`` benutzt diese Klasse ohne eingerichtetes
        Django. Faellt der Zugriff aus, gilt die Vorgabe.
        """
        grund = KiParameter(temperature=cls.TEMPERATUR)
        try:
            from ..conf import conf
            tabelle = conf().get("ki_parameter") or {}
        except Exception:                                       # noqa: BLE001
            return grund
        if not tabelle:
            return grund
        satz = KiParameter.fuer_modell(modell, tabelle, grund=grund)
        if satz is grund and tabelle.get("*"):
            satz = grund.mit(**{k: v for k, v in dict(tabelle["*"]).items()
                                if k in KiParameter._bekannt()})
        return satz

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
                % (self.ziel, e, "  (läuft `ollama serve`?)" if self.ziel == "lokal" else "")
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
            # Frueher fest ``{"num_ctx": ..., "temperature": 0.5}``. Jetzt aus
            # dem Parametersatz - leere Felder werden NICHT gesendet, dann
            # gilt, was das Modell selbst mitbringt (siehe ki/parameter.py).
            "options": self.parameter.als_optionen(),
        }
        a = self._senden(self.url or "http://127.0.0.1:11434/api/chat", daten)
        text = (a.get("message") or {}).get("content", "")
        return text, {"prompt": a.get("prompt_eval_count"),
                      "antwort": a.get("eval_count"),
                      "fenster": self.num_ctx}

    # ------------------------------------------------------------------ online

    def _online(self):
        kopf = {"Authorization": "Bearer %s" % self._schluessel()}
        # Bis zum 25.08.2026 gingen online GAR KEINE Einstellungen mit - die
        # Temperatur 0.5 galt nur lokal. Derselbe Partner antwortete online
        # also nachweislich anders eingestellt als lokal, ohne dass das
        # irgendwo stand. ``als_openai`` laesst weg, was das Schema nicht
        # kennt (top_k, min_p, repeat_penalty), statt Wirkung vorzutaeuschen.
        a = self._senden(self.url or "https://openrouter.ai/api/v1/chat/completions",
                         dict({"model": self.modell, "messages": self.verlauf},
                              **self.parameter.als_openai()), kopf)
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
                "Kein API-Schlüssel. Er gehört in genau eine Datei außerhalb des "
                "Projekts: %s (eine Zeile). Über DJANGOBASE['review_schlüssel_datei'] "
                "aenderbar." % pfad)
        return wert
