# -*- coding: utf-8 -*-
"""Katalog der verfuegbaren KI-Modelle - Parameter, Kontext, Preis, Plattenbedarf.

WOZU (Ansage Edgar, 11.08.2026)
-------------------------------
Fuer die Seite Hilfe > KI-Modelle: eine Uebersicht, welche Modelle als
Sparringspartner in Frage kommen - lokal auf diesem Rechner und online, kostenlos
und bezahlt. Die BEWERTUNG steht nicht hier, sondern in ``ki_messungen.py``;
diese Datei liefert nur die harten Katalogdaten.

WOHER DIE ZAHLEN KOMMEN - und wo sie unsicher sind
--------------------------------------------------
PREIS und KONTEXT  aus der OpenRouter-API (``/api/v1/models``). Belastbar, das
                   ist die Rechnungsgrundlage des Anbieters.
PLATTE lokal       aus der Ollama-API. Belastbar - echter Plattenplatz.
PARAMETERZAHL      aus dem MODELLNAMEN gelesen - siehe ``modellname.Modellname``.
PLATTE online      GESCHAETZT aus der Parameterzahl (``Modellname.gb``). In der
                   Anzeige mit ``~`` gekennzeichnet.

DREI DATEIEN SEIT DEM 30.08.2026. Hier stand alles zusammen und die Datei war
ueber 300 Zeilen lang. Getrennt ist jetzt, was getrennte Fehlerbilder hat:

    ``modelle.py``     der Onlinekatalog - eine Datei, ein Netzabruf, Preise
    ``ollama.py``      die lokale Installation - ein Dienst auf Port 11434
    ``modellname.py``  die Namensdeutung - reine Zeichenketten, kein Zugriff
"""
import json
import os
import time
import urllib.request

from .modellname import GB_JE_MRD, Modellname
from .ollama import OllamaModelle

MODELLE_URL = "https://openrouter.ai/api/v1/models"

#: Weitergereicht, damit ``from .modelle import GB_JE_MRD`` weiter geht - der
#: Wert und seine Herleitung stehen in ``modellname.py``.
__all__ = ["ModellKatalog", "GB_JE_MRD", "MODELLE_URL"]


class ModellKatalog:
    """Die Katalogdaten der Modelle - online (OpenRouter) und lokal (Ollama).

    Der Abruf geht ueber das Netz und dauert ~1 s. Damit die Hilfeseite nicht bei
    jedem Aufruf wartet - und damit sie auch OHNE Netz etwas anzeigt - wird die
    Antwort als Datei zwischengespeichert. Das Verzeichnis kommt von aussen
    (Django gibt ``output/KI_Modelle``); ohne Angabe wird nicht zwischengespeichert.
    """

    def __init__(self, cache_verzeichnis=None, cache_stunden=24, timeout=20):
        self.cache_verzeichnis = cache_verzeichnis
        self.cache_stunden = cache_stunden
        self.timeout = timeout
        self.quelle = "unbekannt"      #: "netz", "cache" oder "cache (Netz-Fehler)"
        self.stand = None              #: Unix-Zeit der gezeigten Daten
        #: Die lokale Seite. Eigenes Objekt, eigene Merker - siehe ``ollama.py``.
        self.ollama = OllamaModelle(timeout=timeout)
        #: Je Katalog EIN Zugriff auf die Datei. Siehe ``online_roh``:
        #: ``Bestenliste`` fragt sie je Messzeile erneut.
        self._roh_cache = None

    # ------------------------------------------------------------------- Quellen

    def _cache_datei(self):
        if not self.cache_verzeichnis:
            return None
        return os.path.join(str(self.cache_verzeichnis), "openrouter.json")

    def _aus_cache(self):
        pfad = self._cache_datei()
        if not pfad or not os.path.exists(pfad):
            return None, None
        try:
            with open(pfad, encoding="utf-8") as f:
                inhalt = json.load(f)
            return inhalt.get("data") or [], os.path.getmtime(pfad)
        except (OSError, ValueError):
            return None, None

    def _in_cache(self, daten):
        pfad = self._cache_datei()
        if not pfad:
            return
        try:
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            with open(pfad, "w", encoding="utf-8") as f:
                json.dump({"data": daten}, f)
        except OSError:
            pass

    def online_roh(self):
        """Die rohe Modell-Liste von OpenRouter - aus dem Cache, wenn frisch genug.

        FAELLT AUF DEN CACHE ZURUECK, wenn das Netz nicht antwortet: Eine
        Hilfeseite, die bei Netzausfall leer ist, ist schlechter als eine mit
        Zahlen von gestern - solange dransteht, dass sie von gestern sind.

        JE KATALOG NUR EINMAL (Messung 30.08.2026). ``Bestenliste._katalogdaten``
        durchsucht diese Liste je Messzeile - und rief damit je Zeile die Methode
        erneut auf. Auf ``/hilfe/ki-modelle/`` waren das 21 Aufrufe: die Datei mit
        396 Modellen wurde einundzwanzigmal gelesen und geparst, 326 der 664 ms
        der Bestenliste. Der Katalog lebt nur fuer die Dauer einer Anfrage - die
        Frische entscheidet weiterhin ``cache_stunden`` ueber der Datei, nicht
        dieser Merker."""
        if self._roh_cache is not None:
            return self._roh_cache
        daten, alter = self._aus_cache()
        if daten and alter and (time.time() - alter) < self.cache_stunden * 3600:
            self.quelle, self.stand = "cache", alter
            self._roh_cache = daten
            return daten
        try:
            with urllib.request.urlopen(MODELLE_URL, timeout=self.timeout) as r:
                frisch = json.loads(r.read().decode("utf-8"))["data"]
            self._in_cache(frisch)
            self.quelle, self.stand = "netz", time.time()
            self._roh_cache = frisch
            return frisch
        except Exception:                                        # noqa: BLE001
            if daten:
                self.quelle, self.stand = "cache (Netz-Fehler)", alter
                self._roh_cache = daten
                return daten
            self.quelle, self.stand = "nicht erreichbar", None
            self._roh_cache = []
            return []

    def lokal(self):
        """Die lokal installierten Modelle - siehe ``ollama.OllamaModelle``.

        Bleibt als Durchreicher stehen, weil ``Bestenliste`` und die Ansicht den
        Katalog halten und nicht wissen muessen, dass die lokale Seite ein
        eigenes Objekt ist."""
        return self.ollama.liste()

    # -------------------------------------------------------------------- Zeilen

    def _zeile(self, m):
        ges, aktiv = Modellname.parameter(m["id"])
        preise = m.get("pricing") or {}
        ein = float(preise.get("prompt") or 0) * 1e6
        aus = float(preise.get("completion") or 0) * 1e6
        # Dictionary gewollt: Tabellenzeile der Modell-Übersicht; die zehn Leser stehen in derselben Datei (geprüft mit werkzeug/dict_wege.py).
        return {
            "kennung": m["id"],
            "anbieter": m["id"].split("/")[0],
            "kontext": m.get("context_length") or 0,
            "param_gesamt": ges, "param_aktiv": aktiv,
            # AUS DEN GESAMT-PARAMETERN, nicht aus den aktiven (Fehler beim ersten
            # Bau): Bei einem MoE-Modell muessen ALLE Experten geladen sein, nur
            # gerechnet wird mit den aktiven. Beleg aus einem echten Download:
            # gemma4 26B-a4B belegt 16 GB - das sind 0,62 je Mrd. GESAMT, waehrend
            # 16 GB fuer 4 Mrd. aktive Parameter (4,0 je Mrd.) unsinnig waere.
            "gb": Modellname.gb(ges),
            "preis_ein": ein, "preis_aus": aus,
            # Ein Modell mit Parameterzahl im Namen hat in aller Regel offene
            # Gewichte - nur dann ist der Plattenbedarf ueberhaupt eine Frage.
            "offen": bool(ges),
        }

    def tabellen(self, anbieter=None):
        """(kostenlos, bezahlt) - zwei nach Preis bzw. Groesse sortierte Listen.

        ``anbieter`` filtert auf Namensbestandteile (z.B. ['qwen', 'gemini']);
        ohne Angabe kommt alles."""
        roh = self.online_roh()
        if anbieter:
            klein = [a.lower() for a in anbieter]
            roh = [m for m in roh if any(a in m["id"].lower() for a in klein)]
        frei, bezahlt = [], []
        for m in roh:
            z = self._zeile(m)
            # Die Batch-Varianten (":batch") sind dasselbe Modell mit Rabatt und
            # Wartezeit - sie verdoppeln die Tabelle ohne Erkenntnisgewinn.
            if z["kennung"].endswith(":batch") or z["kennung"].startswith("~"):
                continue
            # KOSTENLOS ENTSCHEIDET DER PREIS, NICHT DER NAME (22.08.2026).
            # Vorher stand hier ``endswith(":free")`` fuer die eine und
            # ``preis > 0`` fuer die andere Tabelle - ein Modell, das nichts
            # kostet und trotzdem kein ``:free`` im Namen traegt, fiel damit
            # durch BEIDE Raster und stand in keiner Tabelle. Aufgefallen an
            # ``stealth/ox-alpha`` (Preis 0/0, kein Suffix), das dadurch
            # unsichtbar blieb; von 288 Modellen im Filter war genau dieses eine
            # betroffen, fuer alle anderen aendert sich nichts.
            if z["preis_ein"] <= 0 and z["preis_aus"] <= 0:
                frei.append(z)
            else:
                bezahlt.append(z)
        frei.sort(key=lambda z: (-(Modellname.mrd(z["param_gesamt"]) or 0),
                                 z["kennung"]))
        bezahlt.sort(key=lambda z: (z["preis_ein"], z["preis_aus"]))
        return frei, bezahlt
