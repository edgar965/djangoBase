# -*- coding: utf-8 -*-
u"""Teststrom - einen Testlauf fahren und LIVE berichten.

    „live fortschritt in djangoBase einbauen" (Edgar, 17.08.2026)

:class:`~.testlauf.Testlauf` fährt ein Kommando und liefert am Ende alles auf
einmal. Bei 600 Tests sitzt man dann zehn Minuten vor einer Seite, die nichts
sagt — und weiß nicht, ob es läuft oder hängt. Dieser Läufer liest die Ausgabe
mit und gibt sie als JSON-Zeilen heraus:

    {"type": "start",    "cmd": "…", "name": "…"}
    {"type": "plan",     "tests": 173}                 sobald bekannt
    {"type": "log",      "line": "…"}                  jede sonstige Zeile
    {"type": "progress", "id": "app.tests…", "status": "pass"}
    {"type": "summary",  "total": 5, "passed": 5, …, "laeufe": {…}}

Das ``plan``-Ereignis ist die Grundlage des Fortschrittsbalkens: Vorher weiss
niemand, wie viele Tests kommen — auch der Aufrufer nicht, denn ein Label wie
``mail.tests.unit`` kann drei oder dreihundert Faelle bedeuten. ``manage.py
test`` sagt es selbst („Found 173 test(s)."), und zwar bevor der erste laeuft.
Bis dahin bleibt der Balken unbestimmt; das ist die Phase, in der die
Testdatenbank aufgebaut wird, und die dauert am laengsten.

Die Seite schreibt daraus ✓/✗ in die Zeilen und am Ende die Laufzeiten in die
Spalten „letzte", „Ø" und „letzte 4 Läufe" (dieselbe Historie wie der normale
Lauf, über :class:`~.testmitschrift.Mitschrift`).

DER SUBPROZESS MUSS STERBEN — UND ZWAR SICHER
============================================
Schließt der Browser die Verbindung (Tab zu, Reload, Netz weg), bricht der
Generator mit ``GeneratorExit`` ab, und das ``finally`` beendet den Lauf. Das
allein reicht NICHT, und zwar aus drei Gründen — alle drei sind hier abgedeckt:

1. **``readline()`` blockiert.** ``GeneratorExit`` kommt erst beim nächsten
   ``yield``. Ein Test, der hängt und nichts ausgibt, hielte den Prozess damit
   endlos. Deshalb läuft ein WÄCHTER-Thread mit, der nach Ablauf der Frist
   beendet, ohne auf die Ausgabe zu warten.
2. **Der Lauf hat Kinder.** ``manage.py test`` startet selbst Prozesse
   (``ProcessPoolExecutor``-Arbeiter). ``kill()`` auf den Elternprozess lässt sie
   stehen; auf Windows sterben sie NICHT mit ihm. Beendet wird deshalb der
   BAUM (:class:`~.testtoeter.Toeter`), und der Lauf startet auf POSIX in einer
   eigenen Prozessgruppe.
3. **Der Server kann selbst enden.** Bei einem Neustart mitten im Lauf wäre der
   Testprozess verwaist. ``atexit`` beendet ihn mit.

EIN LAUF ZUR ZEIT
=================
Über :class:`~.testsperre.Laufsperre` — eine Datei, keine Prozessvariable und
kein Cache: Sonst hätte bei mehreren Server-Arbeitern jeder seinen eigenen
„einen Lauf", und die zweite Testdatenbank läuft der ersten in die Quere.
"""
import atexit
import json
import logging
import re
import subprocess
import sys
import threading
import time

from django.conf import settings

from .testmitschrift import Mitschrift
from .testsperre import Laufsperre
from .testtoeter import Toeter
from .testzeilen import Testzeilen

__all__ = ["Teststrom"]

log = logging.getLogger("djangobase.tests")

#: Auf Windows kein Konsolenfenster je Lauf.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Teststrom:
    """Fährt ein Testkommando und liefert Ereignisse, solange es läuft."""

    #: Notbremse: Nach dieser Zeit wird der Lauf abgebrochen (Sekunden).
    FRIST = 3600
    #: „Found 173 test(s)." - die Gesamtzahl fuer den Fortschrittsbalken.
    #: Ohne Ankerung am Zeilenanfang: Projekte stempeln ihre Ausgabe.
    PLAN = re.compile(r"Found (\d+) test")

    def __init__(self, historie=None, sperre=None):
        self.mitschrift = Mitschrift(historie)
        self.sperre = sperre or Laufsperre()

    def fahren(self, cmd, name="", frist=None, ziele=(), alles=False):
        u"""Ereignis-Generator. ``cmd`` ist die geprüfte Kommandoliste.

        ``ziele`` sind die AUFGELÖSTEN Testlabels. Sie gehen ins ``start``-
        Ereignis, weil die Seite sie nicht kennen kann: Bei „Alles ausführen"
        oder „Kategorie ausführen" schickt sie den Slug eines Sammelbefehls
        („alles", „unit"), und was dahinter steckt, steht in der Konfiguration
        des Projekts. Die Seite hakt damit die passenden Kästchen an (Ansage
        18.08.2026).
        """
        cmd = list(self.mitschrift.option_setzen(cmd))
        frei, grund = self.sperre.belegen(name)
        if not frei:
            yield self._satz({"type": "error", "detail": grund, "belegt": True})
            return
        # `alles`: Der Lauf hat KEIN Label (ganzes Projekt) - die Seite hakt
        # dann jedes Kaestchen an, weil jeder Fall dabei ist.
        yield self._satz({"type": "start", "cmd": " ".join(cmd), "name": name,
                          "ziele": [str(z) for z in (ziele or [])],
                          "alles": bool(alles)})
        try:
            prozess = subprocess.Popen(
                cmd, cwd=str(settings.BASE_DIR),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
                creationflags=_NO_WINDOW,
                # POSIX: eigene Prozessgruppe, damit `os.killpg` die Kinder
                # trifft und NICHT den Server. Auf Windows tut der Parameter
                # nichts - dort erledigt `taskkill /T` dasselbe.
                start_new_session=not sys.platform.startswith("win"))
        except OSError as fehler:
            log.exception("Testlauf nicht startbar: %s", cmd)
            self.sperre.freigeben()
            yield self._satz({"type": "error", "detail": str(fehler)})
            return
        self.sperre.pid_merken(prozess.pid)
        leser = Testzeilen()
        zaehler = {"pass": 0, "fail": 0, "error": 0, "skip": 0}
        gesammelt = []
        plan = None
        start = time.time()
        ende = start + int(frist or self.FRIST)
        # Die drei Netze (siehe Modulkopf): Waechter gegen blockierende Ausgabe,
        # `atexit` gegen einen Server-Neustart, `finally` gegen den Abbruch.
        waechter = threading.Timer(max(1, ende - time.time()),
                                   self._notbremse, args=(prozess, name))
        waechter.daemon = True
        waechter.start()
        beim_ende = lambda: Toeter.prozess(prozess)          # noqa: E731
        atexit.register(beim_ende)
        try:
            while True:
                zeile = prozess.stdout.readline()
                if not zeile:
                    if prozess.poll() is not None:
                        break
                    if time.time() > ende:
                        yield self._satz({"type": "error",
                                          "detail": "Frist überschritten — "
                                                    "Lauf abgebrochen."})
                        break
                    continue
                zeile = zeile.rstrip()
                gesammelt.append(zeile)
                if plan is None:
                    treffer = self.PLAN.search(zeile)
                    if treffer:
                        plan = int(treffer.group(1))
                        yield self._satz({"type": "plan", "tests": plan})
                ereignis = leser.lesen(zeile)
                if ereignis:
                    zaehler[ereignis["status"]] = zaehler.get(
                        ereignis["status"], 0) + 1
                    yield self._satz({"type": "progress", **ereignis})
                else:
                    yield self._satz({"type": "log", "line": zeile})
            yield self._satz(self._abschluss(prozess, zaehler, gesammelt,
                                             time.time() - start, name))
        finally:
            # Siehe Modulkopf: Der Prozess darf NIE zurückbleiben.
            waechter.cancel()
            try:
                atexit.unregister(beim_ende)
            except Exception:  # noqa: BLE001
                pass
            if prozess.poll() is None:
                log.warning("Testlauf '%s' wird beendet (Verbindung beendet "
                            "oder Frist abgelaufen)", name or "?")
                Toeter.prozess(prozess)
            self.sperre.freigeben()

    # ------------------------------------------------------------- Bausteine

    def _abschluss(self, prozess, zaehler, gesammelt, dauer, name):
        try:
            laeufe = self.mitschrift.aufnehmen("\n".join(gesammelt))
        except Exception:  # noqa: BLE001
            # Der LAUF ist gelaufen — nur seine Zeiten fehlen. Das gehört ins
            # Log, nicht in einen Abbruch der Antwort.
            log.exception("Laufzeiten nicht in die Historie geschrieben")
            laeufe = {}
        gefahren = sum(zaehler.values())
        # Dictionary gewollt: geht als JSON-Zeile an die Seite.
        return {"type": "summary", "name": name,
                "total": gefahren, "passed": zaehler.get("pass", 0),
                "failed": zaehler.get("fail", 0),
                "errors": zaehler.get("error", 0),
                "skipped": zaehler.get("skip", 0),
                "rc": prozess.returncode,
                "ok": prozess.returncode == 0,
                # EIN UEBERSPRUNGENER TEST IST NIE GRUEN (23.08.2026)
                # =================================================
                #     „ein übersprungener Test soll nie grün melden!!!
                #      immer gelb"
                #
                # `returncode == 0` gilt auch dann, wenn kein einziger Test
                # gelaufen ist. An dem Abend meldeten 18 Vollbild-Pruefungen
                # „OK", von denen 11 uebersprungen waren — der Fehler, den
                # sie haetten finden sollen, war da.
                "zustand": ("rot" if prozess.returncode != 0
                            else "gelb" if (zaehler.get("skip", 0)
                                            or not gefahren)
                            else "gruen"),
                "dauer": round(dauer, 3), "laeufe": laeufe}

    @staticmethod
    def _notbremse(prozess, name):
        u"""Nach Ablauf der Frist beenden - ohne auf Ausgabe zu warten.

        Das ist der Fall, den das ``finally`` NICHT abdeckt: Haengt ein Test und
        schreibt nichts mehr, kommt der Generator nie zum naechsten ``yield`` und
        merkt weder Frist noch Abbruch.
        """
        if prozess.poll() is not None:
            return
        log.warning("Testlauf '%s' ueberschreitet die Frist - Prozessbaum %s "
                    "wird beendet", name or "?", prozess.pid)
        Toeter.prozess(prozess)

    @staticmethod
    def _satz(daten):
        u"""Eine JSON-Zeile. ``ensure_ascii=False``: Umlaute bleiben Umlaute."""
        return json.dumps(daten, ensure_ascii=False) + "\n"
