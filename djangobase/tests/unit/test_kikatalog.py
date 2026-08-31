# -*- coding: utf-8 -*-
u"""Der KI-Katalog fragt jede Quelle EINMAL — und liest die Namen richtig.

WARUM DIESE TESTS (30.08.2026)
==============================
``/hilfe/ki-modelle/`` brauchte 811 ms (Median über sieben Abrufe, gemessen über
``127.0.0.1``). Gemessen, nicht geschätzt, kam heraus:

    Bestenliste.zeilen(): 663,7 ms
      online_roh()  21x  ->  326,5 ms   openrouter.json mit 396 Modellen,
                                        einundzwanzigmal gelesen und geparst
      lokal()       12x  ->  294,0 ms   zwölf Abrufe von /api/tags für
                                        immer dieselben acht Modelle

``Bestenliste._katalogdaten`` sucht je Messzeile in beiden Quellen — und rief
dafür je Zeile die abrufende Methode erneut auf. Die STRUKTURZAHL, die nicht an
der Tageslast hängt: 21 Messzeilen × 396 Katalogeinträge, und 12 Netzabrufe, wo
einer reicht. Danach: 287 ms, das HTML Byte für Byte dasselbe (239.705).

Genau das prüfen die Fälle hier: nicht „schnell", sondern **wie oft**. Eine
Zeitmessung im Test wäre auf einem belasteten Rechner wertlos; eine Zählung ist
es nie.

DAZU DIE NAMENSDEUTUNG, weil sie beim Aufteilen aus ``ModellKatalog`` in
``Modellname`` gewandert ist. Die Erwartungswerte stehen nicht geraten hier,
sondern kommen aus der Kalibrierung im Docstring von ``modellname.py``
(27B = 17 GB, 26B = 16 GB) und aus echten Modellnamen dieses Rechners.
"""
from django.test import SimpleTestCase

from djangobase.ki.messungen import Bestenliste
from djangobase.ki.modelle import ModellKatalog
from djangobase.ki.modellname import GB_JE_MRD, Modellname
from djangobase.ki.ollama import OllamaModelle


class NamenTest(SimpleTestCase):
    u"""Was ``Modellname`` aus einer Kennung liest."""

    #: DB nicht angefasst — sonst öffnet jeder Fall eine Transaktion und kann
    #: einen laufenden Server blockieren (Regel ``testlauf-blockiert-server``).
    databases = []

    def test_moe_liefert_beide_zahlen(self):
        self.assertEqual(Modellname.parameter("qwen3.6:35b-a3b-q4_K_M"),
                         ("35B", "3B"))
        self.assertEqual(Modellname.parameter("deepseek/v4-550b-a55b"),
                         ("550B", "55B"))

    def test_einfaches_modell_hat_keine_aktive_zahl(self):
        self.assertEqual(Modellname.parameter("qwen3.8:27b"), ("27B", None))

    def test_geschlossene_modelle_bleiben_leer(self):
        u"""Keine Schätzung, wo nichts steht — lieber „k.A." als eine Zahl."""
        for kennung in ("openai/gpt-5", "anthropic/claude-opus-5",
                        "google/gemini-3-pro", "nomic-embed-text:latest"):
            self.assertEqual(Modellname.parameter(kennung), (None, None), kennung)

    def test_zahl_muss_auf_b_enden(self):
        u"""``qwen3.8`` ist eine Versionsnummer, keine Parameterzahl."""
        self.assertEqual(Modellname.parameter("qwen3.8"), (None, None))
        self.assertEqual(Modellname.parameter("modell-b32"), (None, None))

    def test_gb_trifft_die_kalibrierung(self):
        u"""Die drei echten Downloads aus dem Docstring von ``modellname.py``."""
        self.assertEqual(Modellname.gb("27B"), 17.0)
        self.assertEqual(Modellname.gb("26B"), 16.4)
        self.assertIsNone(Modellname.gb(None))
        self.assertIsNone(Modellname.gb("k.A."))

    def test_mrd_sortiert_und_faellt_nicht_um(self):
        self.assertEqual(Modellname.mrd("550B"), 550.0)
        self.assertIsNone(Modellname.mrd(None))
        self.assertIsNone(Modellname.mrd("groß"))

    def test_gb_je_mrd_bleibt_kalibriert(self):
        u"""Ändert jemand die Konstante, ändern sich alle Plattenangaben."""
        self.assertEqual(GB_JE_MRD, 0.63)


class ZaehlenderKatalog(ModellKatalog):
    u"""Ein Katalog, der mitschreibt, wie oft er die Datei anfasst."""

    def __init__(self, eintraege):
        super().__init__(cache_verzeichnis=None)
        self.eintraege = eintraege
        self.dateizugriffe = 0

    def _aus_cache(self):
        self.dateizugriffe += 1
        # Zeitstempel „jetzt", damit der Frischetest greift und kein Netzabruf
        # versucht wird — der Test soll nichts von diesem Rechner brauchen.
        import time
        return self.eintraege, time.time()


class ZaehlendeOllama(OllamaModelle):
    u"""Ollama-Attrappe: zählt die Abrufe, geht nie ins Netz."""

    def __init__(self, modelle, kontext=8192):
        super().__init__()
        self.modelle = modelle
        self.antwort_kontext = kontext
        self.abrufe = []

    def _holen(self, pfad, nutzlast=None):
        self.abrufe.append(pfad)
        if pfad == "/api/tags":
            return {"models": self.modelle}
        return {"model_info": {"qwen35.context_length": self.antwort_kontext}}


def _eintrag(kennung, preis=0.0):
    return {"id": kennung, "context_length": 32768,
            "pricing": {"prompt": preis, "completion": preis}}


def _lokal(name, groesse=1_000_000_000):
    return {"name": name, "size": groesse,
            "details": {"parameter_size": "27.3B", "quantization_level": "Q4_K_M"}}


class QuellenNurEinmalTest(SimpleTestCase):
    u"""Der eigentliche Befund: je Quelle EIN Zugriff, egal wie viele Zeilen."""

    databases = []

    def test_online_roh_liest_die_datei_nur_einmal(self):
        k = ZaehlenderKatalog([_eintrag("qwen/qwen3-27b")])
        for _ in range(5):
            self.assertEqual(len(k.online_roh()), 1)
        self.assertEqual(k.dateizugriffe, 1)

    def test_leerer_katalog_wird_auch_gemerkt(self):
        u"""Sonst liest eine leere Datei bei jeder Messzeile erneut."""
        k = ZaehlenderKatalog([])
        for _ in range(4):
            k.online_roh()
        self.assertEqual(k.dateizugriffe, 1)

    def test_ollama_fragt_je_modell_genau_einmal(self):
        o = ZaehlendeOllama([_lokal("a:27b"), _lokal("b:9b"), _lokal("c:3b")])
        for _ in range(4):
            self.assertEqual(len(o.liste()), 3)
        self.assertEqual(o.abrufe.count("/api/tags"), 1)
        self.assertEqual(o.abrufe.count("/api/show"), 3)

    def test_bestenliste_fragt_nicht_je_zeile_nach(self):
        u"""Der Fall, der die 620 ms ausgemacht hat.

        ``_katalogdaten`` läuft je Messzeile — mit einem Katalog, der nichts
        kennt, fällt JEDE Zeile bis in die Ollama-Liste durch. Vor dem
        30.08.2026 war das je Zeile ein Dateizugriff und ein Netzabruf."""
        k = ZaehlenderKatalog([])
        k.ollama = ZaehlendeOllama([_lokal("a:27b")])
        zeilen = Bestenliste(k).zeilen()
        self.assertGreater(len(zeilen), 10, "Messtabelle unerwartet kurz")
        self.assertEqual(k.dateizugriffe, 1)
        self.assertEqual(k.ollama.abrufe.count("/api/tags"), 1)

    def test_ollama_aus_wird_nicht_gemerkt(self):
        u"""Läuft der Dienst gleich wieder, soll die Seite ihn finden.

        Ein gemerktes „leer" sähe aus wie „nachgesehen, es gibt keine" — und
        bliebe für die Lebensdauer des Katalogs falsch."""
        o = ZaehlendeOllama([])
        self.assertEqual(o.liste(), [])
        self.assertEqual(o.liste(), [])
        self.assertEqual(o.abrufe.count("/api/tags"), 2)

    def test_liste_gibt_dieselben_woerterbuecher_zurueck(self):
        u"""Die Ansicht trägt Messwerte in die Zeilen ein (``zeile.update``).

        Käme beim zweiten Aufruf eine frische Kopie, wären sie weg — genau der
        Grund, aus dem in der Ansicht ``lokal()`` einmal geholt und
        weitergereicht wird."""
        o = ZaehlendeOllama([_lokal("a:27b")])
        erste = o.liste()
        erste[0]["note"] = "B"
        self.assertIs(o.liste()[0], erste[0])
        self.assertEqual(o.liste()[0]["note"], "B")


class OllamaZeilenTest(SimpleTestCase):
    u"""Was in einer lokalen Zeile steht — und woher."""

    databases = []

    def test_angabe_des_modells_schlaegt_den_namen(self):
        u"""``27b`` im Namen sind in Wahrheit 27,3 Mrd. Parameter."""
        o = ZaehlendeOllama([_lokal("qwen3.8:27b")])
        self.assertEqual(o.liste()[0]["param_gesamt"], "27.3B")

    def test_ohne_angabe_zaehlt_der_name(self):
        modell = _lokal("qwen3.6:35b-a3b-q4_K_M")
        modell["details"] = {}
        o = ZaehlendeOllama([modell])
        zeile = o.liste()[0]
        self.assertEqual(zeile["param_gesamt"], "35B")
        self.assertEqual(zeile["param_aktiv"], "3B")

    def test_groesste_zuerst(self):
        o = ZaehlendeOllama([_lokal("klein:3b", 3_000_000_000),
                             _lokal("gross:70b", 26_400_000_000),
                             _lokal("mittel:27b", 17_700_000_000)])
        self.assertEqual([z["kennung"] for z in o.liste()],
                         ["gross:70b", "mittel:27b", "klein:3b"])

    def test_kontext_kommt_aus_api_show(self):
        u"""Der Präfix wechselt je Modell — gesucht wird die ENDUNG."""
        o = ZaehlendeOllama([_lokal("a:27b")], kontext=262144)
        self.assertEqual(o.liste()[0]["kontext"], 262144)

    def test_kontext_fehlt_lieber_als_geraten(self):
        class OhneKontext(ZaehlendeOllama):
            def _holen(self, pfad, nutzlast=None):
                self.abrufe.append(pfad)
                if pfad == "/api/tags":
                    return {"models": self.modelle}
                return {"model_info": {"general.architecture": "qwen3"}}

        self.assertIsNone(OhneKontext([_lokal("a:27b")]).liste()[0]["kontext"])


class TabellenTest(SimpleTestCase):
    u"""Die Aufteilung in kostenlos und bezahlt."""

    databases = []

    def test_der_preis_entscheidet_nicht_der_name(self):
        u"""Befund 22.08.2026: ``stealth/ox-alpha`` kostet nichts und heißt
        nicht ``:free`` — es fiel durch beide Raster und stand in keiner
        Tabelle."""
        k = ZaehlenderKatalog([_eintrag("stealth/ox-alpha", 0.0),
                               _eintrag("openai/gpt-5", 0.000002)])
        frei, bezahlt = k.tabellen()
        self.assertEqual([z["kennung"] for z in frei], ["stealth/ox-alpha"])
        self.assertEqual([z["kennung"] for z in bezahlt], ["openai/gpt-5"])

    def test_batch_varianten_fliegen_raus(self):
        k = ZaehlenderKatalog([_eintrag("openai/gpt-5"),
                               _eintrag("openai/gpt-5:batch"),
                               _eintrag("~geplant/modell")])
        frei, bezahlt = k.tabellen()
        self.assertEqual([z["kennung"] for z in frei + bezahlt],
                         ["openai/gpt-5"])

    def test_filter_auf_anbieter(self):
        k = ZaehlenderKatalog([_eintrag("qwen/qwen3-27b"),
                               _eintrag("fremd/irgendwas")])
        frei, bezahlt = k.tabellen(anbieter=("qwen",))
        self.assertEqual([z["kennung"] for z in frei + bezahlt],
                         ["qwen/qwen3-27b"])

    def test_platte_aus_den_gesamtparametern(self):
        u"""Bei MoE zählt für den Plattenplatz die GESAMTzahl: Alle Experten
        müssen geladen sein, gerechnet wird nur mit den aktiven."""
        k = ZaehlenderKatalog([_eintrag("google/gemma4-26b-a4b")])
        frei, _ = k.tabellen()
        self.assertEqual(frei[0]["gb"], Modellname.gb("26B"))
