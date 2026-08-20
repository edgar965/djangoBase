# -*- coding: utf-8 -*-
u"""Aus einer Aufzeichnung eine Testdatei schreiben.

DAS ZIEL (Edgar, 20.08.2026)
===========================
    „Ziel ist es, dass du aus diesen Aufzeichnungen echte Tests erstellen
     kannst, die du dann in der Testsuite speicherst und ausführst"

    python manage.py testfall_aus_aufzeichnung --liste
    python manage.py testfall_aus_aufzeichnung auf_20260820_184215 \
        --ziel shortlongxWeb/tests_app/tests/oberflaeche/ui

WARUM EIN BEFEHL UND KEIN KNOPF
===============================
Was hier entsteht, ist QUELLTEXT im Projekt - eine Datei, die anschliessend bei
jedem Testlauf mitfaehrt. Das ist ein Schritt, den jemand bewusst tut und
danach liest; ein Knopf in der Oberflaeche wuerde dazu einladen, ihn
nebenbei zu druecken und die Datei nie anzusehen.

Der erzeugte Fall ist ein GERUEST: nachgefahren werden die aufgezeichneten
GET-Abrufe mit ihrem damaligen Status. Was der Nutzer dabei GEMEINT hat, steht
als Bedienung im Kopf - diese Zusicherungen ergaenzt ein Mensch.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ...aufzeichnung import Aufzeichnungen
from ...aufzeichnung_testfall import Testfall


class Command(BaseCommand):
    help = "Schreibt aus einer Aufzeichnung eine Testdatei."

    def add_arguments(self, p):
        p.add_argument("kennung", nargs="?", default="",
                       help="ID der Aufzeichnung (siehe --liste)")
        p.add_argument("--ziel", default="",
                       help="Zielverzeichnis; ohne Angabe wird nur ausgegeben")
        p.add_argument("--liste", action="store_true",
                       help="vorhandene Aufzeichnungen zeigen")

    def handle(self, *args, **o):
        bestand = Aufzeichnungen()
        if o["liste"] or not o["kennung"]:
            alle = bestand.alle()
            if not alle:
                self.stdout.write("Keine Aufzeichnungen (%s)" % bestand.pfad)
                return
            self.stdout.write("%-24s %-34s %8s %8s %6s" %
                              ("ID", "Name", "Schritte", "Logs", "Dauer"))
            for a in alle:
                self.stdout.write("%-24s %-34s %8d %8d %5.0fs" %
                                  (a.id, a.name[:34], len(a.schritte), len(a.logs),
                                   a.dauer_s))
            return

        a = bestand.holen(o["kennung"])
        if a is None:
            raise CommandError("Aufzeichnung %r nicht gefunden" % o["kennung"])
        fall = Testfall(a)
        quelltext = fall.quelltext()
        if not o["ziel"]:
            self.stdout.write(quelltext)
            return

        ordner = Path(o["ziel"])
        if not ordner.is_dir():
            raise CommandError("Zielverzeichnis gibt es nicht: %s" % ordner)
        pfad = ordner / fall.dateiname()
        if pfad.exists():
            # NICHT ueberschreiben: Die Datei kann von Hand ergaenzte
            # Zusicherungen tragen - genau die, die eine Aufnahme nicht kennt.
            raise CommandError("Es gibt schon %s - erst umbenennen oder loeschen."
                               % pfad)
        pfad.write_text(quelltext, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(
            "%s geschrieben (%d Abrufe geprueft)" % (pfad, len(fall.abrufe()))))
        self.stdout.write("Fahren mit:  manage.py test %s" %
                          str(pfad.with_suffix("")).replace("\\", ".").replace("/", "."))
