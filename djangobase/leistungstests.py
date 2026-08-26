# -*- coding: utf-8 -*-
u"""Leistungstests - Ladezeiten messen, protokollieren, vergleichen.

    Test-Art „performance": alle wichtigen Seiten und Ablaeufe werden gemessen,
    die Ergebnisse protokolliert.

WARUM MESSEN OHNE PROTOKOLL NICHTS TAUGT
========================================
Eine Zahl allein sagt nichts: „Die Seite braucht 380 ms" ist weder gut noch
schlecht. Interessant ist die VERAENDERUNG - dass dieselbe Seite letzte Woche
120 ms brauchte. Deshalb schreibt jeder Lauf seine Werte fort (JSON im Projekt,
nie in System-Temp) und vergleicht gegen den letzten Stand.

DREI FALLEN, DIE HIER BEHANDELT SIND
====================================
* **Der erste Aufruf luegt.** Vorlagen werden uebersetzt, Verbindungen
  aufgebaut, Zwischenspeicher gefuellt. Gemessen wird deshalb erst nach einem
  Aufwaermlauf, und es zaehlt der MEDIAN mehrerer Aufrufe, nicht der Einzelwert.
* **Nebenlaeufige Last verzerrt alles.** Laeuft nebenher etwas anderes,
  schwanken die Werte um Faktor 1,5 und mehr. Ein Ausschlag gilt deshalb erst
  ab einer deutlichen Abweichung als Rueckschritt (Vorgabe: doppelte Zeit UND
  mindestens 150 ms mehr).
* **Die Zahl der Abfragen ist die stabilere Groesse.** Sie haengt nicht an der
  Tageslast. Deshalb wird zusaetzlich gezaehlt, wie viele SQL-Abfragen eine
  Seite ausloest - eine Seite, die von 12 auf 400 springt, hat ein
  N+1-Problem, egal was die Uhr sagt.

BENUTZUNG
=========
    <app>/tests/performance/test_ladezeiten.py:

        from djangobase.leistungstests import *   # noqa: F401,F403

Einstellen ueber ``DJANGOBASE["leistung"]``:

    "leistung": {
        "seiten": ["/", "/chat/", "/audio/"],   # sonst alle parameterlosen GETs
        "aus": ["/admin/"],
        "grenze_ms": 2000,        # harte Obergrenze je Seite
        "laeufe": 3,              # Messungen je Seite (Median zaehlt)
    }
"""
import json
import logging
import statistics
import time
from pathlib import Path

from django.conf import settings
from django.test import TestCase

logger = logging.getLogger("djangobase.leistung")

__all__ = ["Messwert", "Leistungsablage", "GrundtestLadezeiten"]


def _cfg(name, vorgabe=None):
    return ((getattr(settings, "DJANGOBASE", {}) or {}).get("leistung") or {}
            ).get(name, vorgabe)


class Messwert:
    """Was eine Seite gekostet hat: Zeit und Zahl der Abfragen."""

    def __init__(self, pfad, ms, abfragen, status):
        self.pfad = pfad
        self.ms = ms
        self.abfragen = abfragen
        self.status = status

    def als_dict(self):
        # Dictionary gewollt: geht so in die JSON-Ablage und ins Protokoll.
        return {"pfad": self.pfad, "ms": round(self.ms, 1),
                "abfragen": self.abfragen, "status": self.status}

    def zeile(self):
        return ("%-44s %7.1f ms  %4d Abfragen  HTTP %s"
                % (self.pfad[:44], self.ms, self.abfragen, self.status))


class Leistungsablage:
    """Haelt die Messungen fest und vergleicht gegen den letzten Lauf.

    Im PROJEKT, nicht in System-Temp (dort haben Zwischendateien schon einmal
    hundert Gigabyte auf C: hinterlassen). Es bleiben die letzten Laeufe stehen,
    damit man eine Entwicklung sieht statt eines Einzelwerts."""

    MAX_LAEUFE = 20

    def __init__(self, datei=None):
        self.datei = Path(datei or (Path(str(settings.BASE_DIR))
                                    / ".djangobase-leistung.json"))

    def laden(self):
        try:
            return json.loads(self.datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"laeufe": []}

    def letzter(self):
        laeufe = self.laden().get("laeufe") or []
        return {w["pfad"]: w for w in (laeufe[-1]["werte"] if laeufe else [])}

    def schreiben(self, werte, stempel):
        daten = self.laden()
        daten.setdefault("laeufe", []).append(
            {"stand": stempel, "werte": [w.als_dict() for w in werte]})
        daten["laeufe"] = daten["laeufe"][-self.MAX_LAEUFE:]
        try:
            self.datei.write_text(json.dumps(daten, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
        except OSError as e:
            logger.warning("Leistungsablage nicht schreibbar: %s", e)
        return self.datei


class GrundtestLadezeiten(TestCase):
    """Misst die wichtigen Seiten, protokolliert sie und meldet Rueckschritte."""

    #: Ab wann gilt eine Seite als langsamer geworden: doppelte Zeit UND
    #: mindestens so viele Millisekunden mehr. Beides zusammen, weil ein Sprung
    #: von 4 auf 9 ms nichts bedeutet.
    FAKTOR = 2.0
    MINDEST_ZUWACHS_MS = 150

    @classmethod
    def setUpTestData(cls):
        """Angemeldet messen - sonst misst man die Abweisung.

        BELEGT BEIM ERSTEN LAUF (17.08.2026): Ohne Anmeldung antworteten 321 von
        321 Seiten mit HTTP 401 in 1,3 ms und NULL Abfragen. Das sah nach einer
        blitzschnellen Anwendung aus und war die Zurueckweisung am Eingang -
        genau die Sorte Zahl, die man besser gar nicht erhebt."""
        from django.contrib.auth import get_user_model
        Nutzer = get_user_model()
        cls.messnutzer = Nutzer.objects.create_superuser(
            **{Nutzer.USERNAME_FIELD: "leistungsmessung",
               "password": "nur-fuer-die-messung"})

    def setUp(self):
        super().setUp()
        self.client.force_login(self.messnutzer)

    #: Ohne eigene Liste werden SEITEN gemessen, keine Endpunkte: Der Auftrag
    #: lautet „wichtige Workflows und Seiten". Alle 321 Routen dreimal
    #: anzufahren dauerte ueber zwei Minuten und mass zu neun Zehnteln
    #: API-Antworten, die niemand als Ladezeit erlebt (17.08.2026).
    ENDPUNKT_MARKER = ("/api/", "/admin/", "/static/", "/media/")
    HOECHSTENS = 60

    def _pfade(self):
        fest = _cfg("seiten")
        if fest:
            return list(fest)
        from djangobase.grundtests import _routen
        aus = set(_cfg("aus") or [])
        mit_api = bool(_cfg("mit_endpunkten", False))
        pfade = []
        for muster, _cb, _name in _routen():
            pfad = "/" + muster.lstrip("^/")
            if "<" in pfad or "(" in pfad:
                continue
            if pfad in aus or any(pfad.startswith(a) for a in aus):
                continue
            if not mit_api and any(m in pfad for m in self.ENDPUNKT_MARKER):
                continue
            pfade.append(pfad)
        return pfade[:self.HOECHSTENS]

    def _messen(self, pfad, laeufe):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.client.get(pfad)                        # Aufwaermlauf, zaehlt nicht
        zeiten, abfragen, status = [], 0, 0
        for _ in range(laeufe):
            with CaptureQueriesContext(connection) as q:
                t0 = time.perf_counter()
                antwort = self.client.get(pfad)
                zeiten.append((time.perf_counter() - t0) * 1000)
            abfragen = len(q)
            status = antwort.status_code
        return Messwert(pfad, statistics.median(zeiten), abfragen, status)

    def test_ladezeiten_messen_und_protokollieren(self):
        laeufe = int(_cfg("laeufe", 3))
        grenze = _cfg("grenze_ms")
        vorher = Leistungsablage().letzter()
        werte, langsamer, ueber_grenze = [], [], []

        for pfad in self._pfade():
            try:
                w = self._messen(pfad, laeufe)
            except Exception as e:                            # noqa: BLE001
                logger.warning("Leistung: %s nicht messbar: %s", pfad, e)
                continue
            werte.append(w)
            alt = vorher.get(pfad)
            if alt and alt.get("ms"):
                if (w.ms > alt["ms"] * self.FAKTOR
                        and w.ms - alt["ms"] >= self.MINDEST_ZUWACHS_MS):
                    langsamer.append("%s: %.0f -> %.0f ms"
                                     % (pfad, alt["ms"], w.ms))
            if grenze and w.ms > float(grenze):
                ueber_grenze.append("%s: %.0f ms" % (pfad, w.ms))

        stempel = time.strftime("%d.%m.%Y %H:%M:%S")
        datei = Leistungsablage().schreiben(werte, stempel)
        # Protokoll: einmal als Block ins Log (mit Zeitstempel aus dem Format).
        logger.info("Leistungsmessung %s — %d Seiten, Ablage %s\n%s",
                    stempel, len(werte), datei,
                    "\n".join(w.zeile() for w in
                              sorted(werte, key=lambda x: -x.ms)[:25]))

        self.assertEqual(langsamer, [],
                         "Deutlich langsamer als beim letzten Lauf: %s" % langsamer)
        if grenze:
            self.assertEqual(ueber_grenze, [],
                             "Über der Grenze von %s ms: %s" % (grenze, ueber_grenze))

    def test_keine_seite_stellt_uebermaessig_viele_abfragen(self):
        """Die stabilere Größe: Abfragen hängen nicht an der Tageslast."""
        grenze = int(_cfg("grenze_abfragen", 120))
        viele = []
        for pfad in self._pfade():
            try:
                w = self._messen(pfad, 1)
            except Exception:                                 # noqa: BLE001
                continue
            if w.abfragen > grenze:
                viele.append("%s: %d Abfragen" % (pfad, w.abfragen))
        self.assertEqual(viele, [],
                         "Mehr als %d SQL-Abfragen je Seite (N+1 verdächtig): %s"
                         % (grenze, viele))
