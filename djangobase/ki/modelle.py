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
PLATTE lokal       aus ``ollama list``. Belastbar - echter Plattenplatz.
PARAMETERZAHL      aus dem MODELLNAMEN gelesen (``27b``, ``550b-a55b``). Sie steht
                   dort nur, wenn der Hersteller die Gewichte veroeffentlicht;
                   bei geschlossenen Modellen (Gemini, GPT, Claude, qwen-max)
                   gibt es sie nicht - dort steht ``k.A.`` und NICHT eine
                   Schaetzung. Ein Modell ohne Parameterzahl im Namen gilt hier
                   deshalb als geschlossen. Das ist eine Faustregel, keine
                   Garantie: ``llama-4-scout`` etwa ist offen und traegt trotzdem
                   keine Zahl im Namen.
PLATTE online      GESCHAETZT aus der Parameterzahl, siehe ``gb_aus_parametern``.
                   In der Anzeige mit ``~`` gekennzeichnet.

MoE-SCHREIBWEISE ``550b-a55b`` = 550 Mrd. Parameter gesamt, davon 55 Mrd. je Token
aktiv. Fuer Tempo und Speicherbedarf zaehlt die zweite Zahl, fuer die Faehigkeiten
eher die erste. Deshalb stehen beide.
"""
import json
import os
import re
import time
import urllib.request

MODELLE_URL = "https://openrouter.ai/api/v1/models"

#: Plattenbedarf je Mrd. Parameter in der ueblichen 4-Bit-Quantisierung (Q4_K_M).
#: NICHT aus der Bit-Rechnung hergeleitet, sondern an drei echten Ollama-Downloads
#: kalibriert: 27B = 17 GB (0,63), 26B = 16 GB (0,62), 9B = 6,6 GB (0,73). Kleine
#: Modelle liegen darueber, weil Einbettungstabellen und Vokabular kaum mit der
#: Modellgroesse schrumpfen - die Formel unterschaetzt sie also.
GB_JE_MRD = 0.63


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
        #: Je Modell EIN ``/api/show``-Aufruf - die Seite fragt den Kontext sonst
        #: mehrfach ab (Katalog-Tabelle und Bestenliste).
        self._kontext_cache = {}

    # ---------------------------------------------------------------- Bausteine

    @staticmethod
    def parameter_aus_name(kennung):
        """('550B', '55B') aus einem Modellnamen - oder (None, None).

        Die zweite Zahl ist nur bei MoE-Modellen gesetzt (aktive Parameter)."""
        name = (kennung or "").lower()
        moe = re.search(r"(\d+(?:\.\d+)?)b-a(\d+(?:\.\d+)?)b", name)
        if moe:
            return "%sB" % moe.group(1), "%sB" % moe.group(2)
        einfach = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)b(?![a-z0-9])", name)
        if einfach:
            return "%sB" % einfach[-1], None
        return None, None

    @staticmethod
    def gb_aus_parametern(param):
        """Geschaetzter Plattenbedarf in GB aus '27B' - oder None."""
        if not param:
            return None
        try:
            mrd = float(param.rstrip("Bb"))
        except ValueError:
            return None
        return round(mrd * GB_JE_MRD, 1)

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
        Zahlen von gestern - solange dransteht, dass sie von gestern sind."""
        daten, alter = self._aus_cache()
        if daten and alter and (time.time() - alter) < self.cache_stunden * 3600:
            self.quelle, self.stand = "cache", alter
            return daten
        try:
            with urllib.request.urlopen(MODELLE_URL, timeout=self.timeout) as r:
                frisch = json.loads(r.read().decode("utf-8"))["data"]
            self._in_cache(frisch)
            self.quelle, self.stand = "netz", time.time()
            return frisch
        except Exception:                                        # noqa: BLE001
            if daten:
                self.quelle, self.stand = "cache (Netz-Fehler)", alter
                return daten
            self.quelle, self.stand = "nicht erreichbar", None
            return []

    def lokal(self):
        """[{kennung, gb, param_gesamt, param_aktiv, quant}] der Ollama-Modelle.

        UEBER DIE HTTP-API, nicht ueber ``ollama list`` (Befund 11.08.2026): Der
        Django-Dienst laeuft als SYSTEM, und ``ollama.exe`` liegt im Benutzerprofil
        - im Suchpfad von SYSTEM steht es nicht, der Aufruf lief ins Leere und die
        Seite zeigte gar keine lokalen Modelle. Die API loest das nicht nur, sie
        liefert auch mehr: die ECHTE Parameterzahl des Modells (27.8B) statt der
        gerundeten aus dem Namen (27b), dazu die Quantisierungsstufe.

        Leer, wenn Ollama nicht laeuft - das ist kein Fehler, sondern der
        Normalfall auf einem Rechner ohne lokale Modelle."""
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags",
                                        timeout=self.timeout) as r:
                roh = json.loads(r.read().decode("utf-8")).get("models") or []
        except Exception:                                        # noqa: BLE001
            return []
        aus = []
        for m in roh:
            einzel = m.get("details") or {}
            ges, aktiv = self.parameter_aus_name(m.get("name", ""))
            bytes_ = m.get("size") or 0
            kennung = m.get("name", "")
            aus.append({
                "kennung": kennung,
                "gb": round(bytes_ / 1e9, 1) if bytes_ else None,
                # Die Angabe des Modells schlaegt den Namen: ``27b`` im Namen sind
                # in Wahrheit 27,8 Mrd. Parameter.
                "param_gesamt": einzel.get("parameter_size") or ges,
                "param_aktiv": aktiv,
                "quant": einzel.get("quantization_level") or "",
                "kontext": self.kontext(kennung),
            })
        aus.sort(key=lambda z: -(z["gb"] or 0))
        return aus

    def kontext(self, kennung):
        """Kontextlaenge eines lokalen Modells - oder None.

        Steht NICHT in ``/api/tags`` (Rueckfrage 11.08.2026: „der Kontext fehlt
        auch bei den lokalen"), sondern nur in ``/api/show`` unter
        ``model_info.<architektur>.context_length``. Der Praefix wechselt je
        Modell (``qwen35.``, ``gemma4.``), deshalb wird nach der Endung gesucht
        statt nach einem festen Schluessel."""
        if kennung in self._kontext_cache:
            return self._kontext_cache[kennung]
        wert = None
        try:
            daten = json.dumps({"model": kennung}).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/show", data=daten,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                info = json.loads(r.read().decode("utf-8")).get("model_info") or {}
            for schluessel, v in info.items():
                if schluessel.endswith(".context_length"):
                    wert = int(v)
                    break
        except Exception:                                        # noqa: BLE001
            wert = None
        self._kontext_cache[kennung] = wert
        return wert

    # -------------------------------------------------------------------- Zeilen

    def _zeile(self, m):
        ges, aktiv = self.parameter_aus_name(m["id"])
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
            "gb": self.gb_aus_parametern(ges),
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
            if z["kennung"].endswith(":free"):
                frei.append(z)
            elif z["preis_ein"] > 0 or z["preis_aus"] > 0:
                bezahlt.append(z)
        frei.sort(key=lambda z: (-(_mrd(z["param_gesamt"]) or 0), z["kennung"]))
        bezahlt.sort(key=lambda z: (z["preis_ein"], z["preis_aus"]))
        return frei, bezahlt


def _mrd(param):
    """'550B' -> 550.0; None -> None. Nur zum Sortieren."""
    if not param:
        return None
    try:
        return float(param.rstrip("Bb"))
    except ValueError:
        return None
