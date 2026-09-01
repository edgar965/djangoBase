# -*- coding: utf-8 -*-
u"""Ablageumleitung — kein Prüflauf schreibt mehr in den System-Zwischenspeicher.

DER BEFUND (31.08.2026)
=======================
Im System-Zwischenspeicher lagen **1.761 Verzeichnisse** aus Prüfläufen
(`kr_*`, `kk_*`), das älteste fünf Tage alt. Die Ursache steht in djangoBase
selbst, und zwar breit: **79 Aufrufe von `tempfile.mkdtemp` & Co. ohne `dir=`
in 48 Dateien — 52 davon räumen nicht auf.**

`Wegwerfordner` löst das für jede Stelle, die ihn benutzt. Diese Klasse löst
es für alle anderen: Sie biegt `tempfile.tempdir` auf einen Ordner im Projekt
um, bevor der erste Prüffall läuft. Danach landet auch ein `mkdtemp()` ohne
`dir=` im Projekt — auf derselben Platte wie die Daten, nicht auf C:.

WARUM AN DIESER STELLE
======================
`djangobase/tests/__init__.py` wird beim Import JEDES Prüfmoduls ausgeführt,
egal von welcher Basisklasse der Fall erbt. Eine Basisklasse erreicht nur, wer
von ihr erbt — und ein neuer Prüffall, den jemand mit `unittest.TestCase`
schreibt, erbt sie nicht.

WAS SIE NICHT IST
=================
Kein Deckel über dem Befund. `systemablage` meldet die 79 Stellen weiter; der
Code bleibt falsch, auch wenn der Schaden abgefangen ist. Diese Klasse ist die
Sicherung, nicht die Reparatur.

DAS AUFRÄUMEN LÄUFT ZWEIMAL
===========================
Beim Start (was ein abgebrochener Lauf hinterlassen hat) und per `atexit`.
Ein `finally` allein hilft nur, solange der Prozess lebt — und gerade der
abgebrochene Lauf ist der, der etwas stehenlässt.
"""
import atexit
import os
import shutil
import tempfile
from pathlib import Path


class Ablageumleitung:
    u"""Lenkt `tempfile` für die Dauer des Prüflaufs ins Projekt."""

    #: Unterhalb von BASE_DIR. `_wegwerf` steht in `werkzeug.AUSGESCHLOSSEN`
    #: und in beiden `.gitignore` — siehe `Wegwerfordner.UNTER`.
    UNTER = ("_wegwerf", "system")

    #: Wohin `tempfile` zeigte, bevor wir es angefasst haben.
    _vorher = None

    #: Schon eingerichtet? Der Import läuft je Prüfmodul einmal.
    _steht = False

    @classmethod
    def einrichten(cls):
        u"""Einmal je Prozess. Ohne Django-Einstellungen passiert nichts.

        @returns {Path|None} der Ordner, oder None wenn nichts umgelenkt wurde
        """
        if cls._steht:
            return Path(tempfile.tempdir) if tempfile.tempdir else None
        wurzel = cls._wurzel()
        if wurzel is None:
            return None
        cls._steht = True
        cls._vorher = tempfile.tempdir
        cls._leeren(wurzel)
        tempfile.tempdir = str(wurzel)
        atexit.register(cls.zuruecknehmen)
        return wurzel

    @classmethod
    def zuruecknehmen(cls):
        u"""Ordner leeren und `tempfile` zurückstellen."""
        if not cls._steht:
            return
        wurzel = cls._wurzel()
        tempfile.tempdir = cls._vorher
        cls._steht = False
        if wurzel is not None:
            cls._leeren(wurzel)

    @classmethod
    def _wurzel(cls):
        u"""`BASE_DIR/_wegwerf/system`, angelegt falls nötig.

        Ohne konfigurierte Einstellungen (etwa beim blossen Import eines
        Moduls ausserhalb eines Prueflaufs) gibt es keine Wurzel — dann
        bleibt alles, wie es ist, statt zu werfen.
        """
        try:
            from django.conf import settings

            basis = settings.BASE_DIR
        except Exception:
            return None
        # JE PROZESS EIN EIGENER ORDNER (Befund CodeRabbit, 31.08.2026):
        # ``einrichten`` leert seine Wurzel beim ersten Import — bei
        # ``manage.py test --parallel`` oder ``pytest -n`` importiert JEDER
        # Worker die Pruefmodule und haette damit die Dateien der anderen
        # weggeraeumt, mitten im Lauf. Und ``atexit`` haette es am Ende noch
        # einmal getan. Mit der Prozessnummer im Pfad raeumt jeder nur sein
        # eigenes.
        pfad = Path(basis).joinpath(*cls.UNTER) / ("p%d" % os.getpid())
        try:
            pfad.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        cls._verwaiste_raeumen(pfad.parent, pfad)
        return pfad

    #: So lange darf ein fremder Prozessordner liegen bleiben, bevor er als
    #: Rest eines abgestuerzten Laufs gilt (Sekunden).
    VERFALL = 24 * 3600

    @classmethod
    def _verwaiste_raeumen(cls, eltern, eigener):
        u"""Reste abgestuerzter Laeufe — nie die eines laufenden Prozesses.

        ZWEI FRAGEN, IN DIESER REIHENFOLGE (31.08.2026):

        1. **Laeuft der Prozess noch, dessen Nummer der Ordner traegt?**
           Dann bleibt er, egal wie alt er ist — er koennte gerade
           schreiben. Das ist der Prozess-Check aus
           ``~/.claude/rules/rekursiv-loeschen.md``.
        2. Ist er tot, darf der Ordner sofort weg.

        DIE FRIST WAR VORHER DIE EINZIGE ANTWORT und damit zu langsam:
        Bei einem harten Abbruch laeuft ``atexit`` nicht, und der Rest
        lag dann einen vollen Tag im Projektbaum. Am 31.08.2026 waren es
        zwoelf Ordner aus drei abgebrochenen Laeufen desselben Tages;
        einer enthielt eine JS-Attrappe, die ``GrundtestEsModule`` als
        echten Projektcode las — vier gemeldete Importe ins Leere, jeder
        Gesamtlauf rot.

        Die Frist BLEIBT fuer Ordner ohne lesbare Prozessnummer: Ueber
        die weiss man nichts, und dann entscheidet wieder das Alter.
        """
        import time

        from ..skills.prozessfrage import Prozessfrage

        jetzt = time.time()
        try:
            eintraege = list(eltern.iterdir())
        except OSError:
            return
        for eintrag in eintraege:
            if eintrag == eigener or not eintrag.is_dir():
                continue
            nummer = Prozessfrage.nummer_aus(eintrag.name)
            if nummer is None:
                # Kein Prozessname — nur das Alter entscheidet.
                try:
                    if jetzt - eintrag.stat().st_mtime < cls.VERFALL:
                        continue
                except OSError:
                    continue
            elif Prozessfrage.lebt(nummer):
                continue
            shutil.rmtree(eintrag, ignore_errors=True)

    @staticmethod
    def _leeren(wurzel):
        u"""Alles unterhalb der eigenen Wurzel — Dateien wie Verzeichnisse.

        NUR UNTERHALB, und die Wurzel selbst bleibt stehen: Ein Aufräumer,
        der Elternpfade anfasst, ist die nächste Sorte Schaden.
        """
        for eintrag in wurzel.iterdir():
            if eintrag.is_dir():
                shutil.rmtree(eintrag, ignore_errors=True)
            else:
                try:
                    eintrag.unlink()
                except OSError:
                    pass
