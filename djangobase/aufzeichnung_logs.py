# -*- coding: utf-8 -*-
u"""Die Server-Log-Zeilen aus dem Zeitraum einer Aufzeichnung.

WOZU SIE ZUM TESTFALL GEHOEREN
==============================
Die Schritte sagen, was zu TUN ist. Was dabei herauskommen muss, steht im Log:
welcher Endpunkt lief, was er meldete, ob eine Ausnahme fiel. Ein Testfall, der
nur klickt und nichts prueft, meldet jeden Fehler als Erfolg.

WARUM AUS DER DATEI UND NICHT AUS EINEM RINGPUFFER
==================================================
Ein Puffer im Prozess kennt nur, was DIESER Prozess geschrieben hat - und die
Handels-Automatik, der Cron-Runner und die Werkzeuge laufen teils daneben. Die
rotierende Datei ist die vollstaendige Quelle, und sie liegt ohnehin da
(``dblog.config``: django.log neben error.log).

Gelesen wird vom ENDE her und nur so weit zurueck, wie der Zeitraum reicht: Eine
10-MB-Datei ganz einzulesen, um dreissig Sekunden herauszuschneiden, waere teuer
und bei jedem Beenden erneut.
"""
import logging
import re
from datetime import datetime
from pathlib import Path

from django.conf import settings

log = logging.getLogger("djangobase.tests")

__all__ = ["LogFenster"]


class LogFenster:
    u"""Log-Zeilen zwischen zwei Zeitpunkten."""

    #: Zeilenanfang der djangoBase-Formatierung: „2026-08-20 16:30:45 [INFO] name: text"
    KOPF = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+([^:]+):\s?(.*)$")

    #: So viele Zeilen werden hoechstens uebernommen. Ein langer Zeitraum mit
    #: einer gespraechigen Automatik haette sonst zehntausende - der Testfall
    #: wird davon nicht besser, die Datei nur gross.
    MAX_ZEILEN = 500

    #: So viele Bytes werden vom Dateiende her gelesen. Deckt bei der ueblichen
    #: Zeilenlaenge mehrere tausend Zeilen ab.
    RUECKBLICK_B = 3 * 1024 * 1024

    #: Diese Logger tragen nichts zum Testfall bei - sie protokollieren die
    #: Aufzeichnung selbst oder jeden HTTP-Zugriff.
    STILL = ("django.server", "djangobase.traffic")

    def __init__(self, pfad=None):
        self.pfade = ([Path(pfad)] if isinstance(pfad, (str, Path))
                      else [Path(p) for p in pfad] if pfad
                      else self._vorgabe())

    @property
    def pfad(self):
        u"""Die erste Datei - fuer Aufrufer, die nur eine erwarten."""
        return self.pfade[0]

    @staticmethod
    def _vorgabe():
        u"""Die Dateien, aus denen mitgeschnitten wird.

        DREI PROJEKTE, DREI ABLAGEN (21.08.2026): Wer ``dblog.config`` nimmt,
        hat ``<Projekt>/logs/django.log``. Wer sein LOGGING selbst schreibt,
        hat es woanders - der ``assistant`` etwa fuehrt sieben Dateien flach
        neben ``manage.py`` (``mail_action.log``, ``chat.log``, ``indexer.log``
        ...), im djangoBase-Format, nur unter anderen Namen und nach Bereichen
        getrennt. Fuer den bleibt die Aufzeichnung sonst dauerhaft OHNE
        Log-Zeilen, ohne dass es jemand sieht - und der erzeugte Testfall prueft
        danach nur noch Abrufe.

        Deshalb darf das Projekt seine Dateien benennen - eine oder mehrere::

            DJANGOBASE["aufzeichnung_log"] = "mail_action.log"
            DJANGOBASE["aufzeichnung_log"] = ["mail_action.log", "chat.log"]

        Mehrere werden nach Zeitstempel gemischt, wie der Reiter „Alle Quellen"
        unter Hilfe -> Logs. Ohne den Schluessel bleibt es beim dblog-Standard."""
        basis = Path(getattr(settings, "BASE_DIR", "."))
        benannt = (getattr(settings, "DJANGOBASE", {}) or {}).get("aufzeichnung_log")
        if benannt:
            roh = [benannt] if isinstance(benannt, (str, Path)) else list(benannt)
            aus = []
            for eintrag in roh:
                p = Path(str(eintrag))
                aus.append(p if p.is_absolute() else basis / p)
            return aus or [basis / "logs" / "django.log"]
        # Wie dblog.config es anlegt: <Projekt>/logs/django.log. Der Ordner liegt
        # bei manchen Projekten eine Ebene ueber BASE_DIR (Repo-Wurzel).
        for kandidat in (basis / "logs" / "django.log",
                         basis.parent / "logs" / "django.log"):
            if kandidat.exists():
                return [kandidat]
        return [basis / "logs" / "django.log"]

    # ------------------------------------------------------------------ Lesen
    def zeilen(self, von_iso, bis_iso=""):
        u"""Log-Zeilen im Zeitraum als Liste von Dictionaries.

        Ohne lesbare Datei oder Zeitangabe eine leere Liste - eine Aufzeichnung
        ohne Logs ist brauchbar, ein Absturz beim Beenden nicht."""
        von = self._zeit(von_iso)
        if von is None:
            return []
        bis = self._zeit(bis_iso) or datetime.now()
        aus = []
        for datei in self.pfade:
            try:
                roh = self._schwanz(datei)
            except OSError:
                log.warning("Log-Datei fuer die Aufzeichnung nicht lesbar: %s", datei)
                continue
            for zeile in roh:
                m = self.KOPF.match(zeile)
                if not m:
                    continue
                stempel, stufe, name, text = m.groups()
                try:
                    t = datetime.strptime(stempel, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                if t < von or t > bis:
                    continue
                if name.strip() in self.STILL:
                    continue
                aus.append({"zeit": stempel, "stufe": stufe,
                            "logger": name.strip(), "text": text[:400]})
        # Aus mehreren Dateien kommt die Reihenfolge sonst dateiweise - der
        # Testfall soll aber den ABLAUF zeigen, nicht die Ablage.
        aus.sort(key=lambda z: z["zeit"])
        return aus[-self.MAX_ZEILEN:]

    def _schwanz(self, datei=None):
        u"""Die letzten ``RUECKBLICK_B`` Bytes einer Datei als Zeilen."""
        datei = Path(datei) if datei else self.pfad
        groesse = datei.stat().st_size
        with open(datei, "rb") as f:
            if groesse > self.RUECKBLICK_B:
                f.seek(groesse - self.RUECKBLICK_B)
                f.readline()                     # angebrochene Zeile verwerfen
            roh = f.read()
        return roh.decode("utf-8", "replace").splitlines()

    @staticmethod
    def _zeit(iso):
        if not iso:
            return None
        try:
            # Die Aufzeichnung speichert mit Zeitzone, das Log ohne - fuer den
            # Vergleich zaehlt die lokale Wanduhr, also wird sie abgestreift.
            return datetime.fromisoformat(iso).replace(tzinfo=None)
        except (TypeError, ValueError):
            return None
