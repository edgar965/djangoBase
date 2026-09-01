# -*- coding: utf-8 -*-
u"""Die Modelle, die auf DIESEM Rechner liegen - gelesen ueber die Ollama-API.

Herausgeloest aus ``modelle.py`` (30.08.2026): Dort standen der Onlinekatalog
(OpenRouter, eine JSON-Datei, Preise) und die lokale Installation (ein Dienst auf
Port 11434, Plattenplatz, Quantisierung) in einer Klasse. Zwei Quellen, zwei
Fehlerbilder, ein Umbau - die Datei war ueber 300 Zeilen.

UEBER DIE HTTP-API, NICHT ueber ``ollama list`` (Befund 11.08.2026): Der
Django-Dienst laeuft als SYSTEM, und ``ollama.exe`` liegt im Benutzerprofil - im
Suchpfad von SYSTEM steht es nicht, der Aufruf lief ins Leere und die Seite
zeigte gar keine lokalen Modelle. Die API loest das nicht nur, sie liefert auch
mehr: die ECHTE Parameterzahl (27.8B) statt der gerundeten aus dem Namen (27b),
dazu die Quantisierungsstufe.

Ist Ollama nicht da, ist die Liste leer. Das ist kein Fehler, sondern der
Normalfall auf einem Rechner ohne lokale Modelle.
"""
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .modellname import Modellname

#: NICHT ``localhost`` (Regel ``zeit-messen``): Unter Windows loest der Name zu
#: ``['::1', '127.0.0.1']`` auf, Ollama lauscht nur auf IPv4 - der Aufschlag von
#: rund zwei Sekunden faellt JE VERBINDUNG an. Gemessen am 28.08.2026 in
#: ``assistant``: Median 2.923 ms gegen 840 ms.
BASIS = "http://127.0.0.1:11434"

#: So viele ``/api/show``-Abrufe gleichzeitig. Sie sind voneinander unabhaengig
#: und dauern je 6-30 ms; nacheinander summierten sich acht Modelle am
#: 30.08.2026 auf 105 ms. Vier statt acht Faeden, damit ein Rechner mit dreissig
#: Modellen den Dienst nicht mit dreissig Verbindungen bewirft.
FAEDEN = 4


class OllamaModelle:
    u"""Liste und Kontextlaenge der lokal installierten Modelle.

    Ein Objekt gilt fuer EINE Anfrage: Beide Merker leben nur, solange es lebt,
    danach wird wieder frisch gefragt. Ein prozessweiter Speicher waere schneller
    und wuerde nach einem ``ollama pull`` alte Zahlen zeigen, ohne dass man es
    der Seite ansieht.
    """

    def __init__(self, timeout=20):
        self.timeout = timeout
        #: Je Modell EIN ``/api/show``-Aufruf - der Kontext wird an zwei Stellen
        #: gebraucht (Katalog-Tabelle und Bestenliste).
        #: Je Modell EIN ``/api/show``-Ergebnis: Kontext, Familie,
        #: Expertenzahl. Frueher stand hier nur die Kontextlaenge -
        #: derselbe Abruf, zwei Drittel der Antwort weggeworfen.
        self._details = {}
        self._liste = None

    # ------------------------------------------------------------------- Abruf

    def _holen(self, pfad, nutzlast=None):
        u"""Die Antwort von ``pfad`` als Wörterbuch - oder ``{}``, wenn nichts kommt."""
        if nutzlast is None:
            ziel = BASIS + pfad
        else:
            ziel = urllib.request.Request(
                BASIS + pfad, data=json.dumps(nutzlast).encode("utf-8"),
                headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(ziel, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:                                        # noqa: BLE001
            return {}

    # ------------------------------------------------------------------ Zeilen

    def liste(self):
        u"""[{kennung, gb, param_gesamt, param_aktiv, quant, kontext}], groesste zuerst.

        IMMER DIESELBE Liste (Messung 30.08.2026). ``Bestenliste._katalogdaten``
        sucht hier jede Messzeile, die online nicht steht - auf
        ``/hilfe/ki-modelle/`` zwoelf Stueck, also zwoelf Abrufe von ``/api/tags``
        fuer immer dieselben acht Modelle: 294 der 664 ms. Dass es dieselben
        Wörterbücher sind, ist gewollt: Die Ansicht traegt die Messwerte in die
        Zeilen ein (``zeile.update(note=...)``), und ein zweiter Aufruf gab
        bisher frische Kopien ohne diese Werte zurueck.
        """
        if self._liste is not None:
            return self._liste
        roh = self._holen("/api/tags").get("models") or []
        if not roh:
            # NICHT merken: Ollama kann gleich laufen, und ein leerer Merker
            # saehe aus wie „nachgesehen, es gibt keine".
            return []
        self._details_vorholen([m.get("name", "") for m in roh])
        aus = [self._zeile(m) for m in roh]
        aus.sort(key=lambda z: -(z["gb"] or 0))
        self._liste = aus
        return aus

    def _zeile(self, m):
        einzel = m.get("details") or {}
        kennung = m.get("name", "")
        ges, aktiv = Modellname.parameter(kennung)
        bytes_ = m.get("size") or 0
        # Dictionary gewollt: Tabellenzeile der Seite Hilfe > KI-Modelle; gelesen
        # in ``ki_modelle.html`` und in ``Bestenliste._katalogdaten``.
        return {
            "kennung": kennung,
            "gb": round(bytes_ / 1e9, 1) if bytes_ else None,
            # Die Angabe des Modells schlaegt den Namen: ``27b`` im Namen sind
            # in Wahrheit 27,8 Mrd. Parameter.
            "param_gesamt": einzel.get("parameter_size") or ges,
            "param_aktiv": aktiv,
            "quant": einzel.get("quantization_level") or "",
            "kontext": self.kontext(kennung),
            # DIE ANGABEN, DIE DER NAME VERSCHWEIGT (01.09.2026, Ansage
            # Edgar: „welches Modell genau ist das? es gibt q4 usw."):
            # ``qwen3.8:27b`` ist Q4_K_M und dicht, ``qwen3.8:27b-q8_0``
            # dasselbe Modell in Q8_0. Am Namen ist das nicht zu sehen,
            # am Tempo dafuer sehr (44,6 gegen 26,0 Token/s).
            "familie": self._detail(kennung, "familie") or einzel.get("family") or "",
            "experten": self._detail(kennung, "experten"),
        }

    # ----------------------------------------------------------------- Kontext

    def _details_vorholen(self, kennungen):
        u"""Die ``/api/show``-Abrufe nebeneinander statt nacheinander."""
        offen = [k for k in kennungen if k and k not in self._details]
        if len(offen) < 2:
            return
        with ThreadPoolExecutor(max_workers=min(FAEDEN, len(offen))) as pool:
            for kennung, wert in zip(offen, pool.map(self._details_holen, offen)):
                self._details[kennung] = wert

    def kontext(self, kennung):
        u"""Kontextlaenge eines lokalen Modells - oder None."""
        return self._detail(kennung, "kontext")

    def _detail(self, kennung, feld):
        u"""Ein Feld aus dem gemerkten ``/api/show`` - notfalls nachholen."""
        if kennung not in self._details:
            self._details[kennung] = self._details_holen(kennung)
        return (self._details[kennung] or {}).get(feld)

    def _details_holen(self, kennung):
        u"""Kontext, Familie und Expertenzahl aus EINEM ``/api/show``.

        Die Laenge steht NICHT in ``/api/tags`` (Rueckfrage 11.08.2026: „der
        Kontext fehlt auch bei den lokalen"), sondern nur hier unter
        ``model_info.<architektur>.context_length``. Der Praefix wechselt je
        Modell (``qwen35.``, ``gemma4.``), deshalb wird nach der ENDUNG
        gesucht statt nach einem festen Schluessel - und aus demselben Grund
        auch die Expertenzahl (``*.expert_count``).

        DIE EXPERTENZAHL IST DIE ERKLAERUNG FUER DIE TEMPO-SPALTE: gemma4
        rechnet je Token 4 von 25,2 Mrd. Parametern und liegt bei 131,9
        Token/s, das gleich grosse dichte qwen3.8:27b bei 44,6. Ohne diese
        Angabe sieht die Tabelle so aus, als sei das eine Modell einfach
        besser gebaut.
        """
        antwort = self._holen("/api/show", {"model": kennung})
        info = antwort.get("model_info") or {}
        aus = {"kontext": None, "experten": None,
               "familie": (antwort.get("details") or {}).get("family") or ""}
        for schluessel, wert in info.items():
            if schluessel.endswith(".context_length"):
                aus["kontext"] = self._ganzzahl(wert)
            elif schluessel.endswith(".expert_count"):
                aus["experten"] = self._ganzzahl(wert)
        return aus

    @staticmethod
    def _ganzzahl(wert):
        try:
            return int(wert)
        except (TypeError, ValueError):
            return None
