# -*- coding: utf-8 -*-
u"""Wegwerfordner - Prüfverzeichnisse, die nicht auf C: liegenbleiben.

DER BEFUND (31.08.2026, Projekt 3DTools)
========================================
Im Systemtemp lagen **1.761 Verzeichnisse** aus Prüfläufen:

    C:\\Users\\e\\AppData\\Local\\Temp\\kr_????????   1.717 Stück
    C:\\Users\\e\\AppData\\Local\\Temp\\kk_????????      44 Stück

Das älteste vom 26.08.2026, das neueste von derselben Minute, in der
gezählt wurde. Erzeugt hat sie `tempfile.mkdtemp(prefix='kr_')` in
`tests/unit/test_skills_klassenreif.py` - je einer pro Prüffall, keiner
je geräumt.

WARUM ES NIEMAND GESEHEN HAT: Das Werkzeug `systemablage` nimmt Prüfungen
aus, mit der Begründung „ein Wegwerf-Verzeichnis in einer Prüfung
verschwindet mit ihr". Das stimmt für `TemporaryDirectory` in einem
`with`-Block - und für `mkdtemp` gerade nicht. Die Ausnahme hat den
Schaden gedeckt, den das Werkzeug verhindern sollte.

Es ist dieselbe Klasse wie die 779 `mail_test_archive_*` im Projekt
`assistant` und die rund 100 GB Datenmüll auf C:, die dort dahinterstanden
(Edgars Regel: „keine Zwischendateien in System-Temp, besonders nicht auf
C: - ins Projektverzeichnis schreiben").

WAS DIESE KLASSE ANDERS MACHT
=============================
1. **Der Ort**: ``BASE_DIR/_wegwerf/pruef`` statt Systemtemp. Wer
   nachsehen will, findet die Reste im Projekt, nicht in einem
   Benutzerprofil auf einer anderen Platte.
2. **Aufräumen beim NÄCHSTEN Lauf**, nicht nur am Ende des eigenen.
   Ein `finally` hilft nur, solange der Prozess lebt; ein abgebrochener
   Lauf (Ctrl+C, Timeout, Absturz) lässt seinen Ordner stehen. Deshalb
   räumt der erste Aufruf jedes Laufs auf, was vorher liegengeblieben ist.
3. **`atexit`** zusätzlich, damit der Normalfall sofort sauber ist.
"""
import atexit
import os
import shutil
import tempfile
from pathlib import Path


class Wegwerfordner:
    u"""Prüfverzeichnisse unter dem Projekt, die sich selbst aufräumen."""

    #: Unterhalb von BASE_DIR - alles hier drin ist Wegwerfware.
    #:
    #: `_wegwerf` und NICHT `ProjektTemp`: Der Name steht in
    #: `werkzeug.AUSGESCHLOSSEN`, damit der normale Werkzeuglauf die
    #: Attrappen nicht als Projektbefunde meldet. `ProjektTemp` steht
    #: zusaetzlich in der `.gitignore` — und dann findet ein Werkzeug im
    #: Prueflauf GAR NICHTS mehr, weil `Werkzeug.pfade` beides siebt.
    #: Genau daran ist die erste Fassung gescheitert: jeder Prueffall
    #: meldete „keine Befunde", und das sah aus wie ein blindes Werkzeug.
    #: Dasselbe steht seit dem 19.08.2026 in `anlassfall_check` (ORDNER
    #: `_anlassfall`) — der Weg ist dort schon zu Ende gedacht.
    #:
    #: DER UNTERORDNER `pruef` IST NICHT ZIERDE (31.08.2026): Solange diese
    #: Klasse direkt auf `_wegwerf` zeigte, loeschte ihr `_reste_raeumen`
    #: auch `_wegwerf/system` — den Ordner der `Ablageumleitung`. Danach
    #: zeigte `tempfile.tempdir` auf einen Pfad, den es nicht mehr gab: 37
    #: Fehler mit `FileNotFoundError`, und zwar nur, wenn beide Module IM
    #: SELBEN LAUF drankamen. Einzeln war jedes gruen.
    #: Zwei Aufraeumer im selben Ordner raeumen einander weg.
    UNTER = ("_wegwerf", "pruef")

    #: Was dieser Lauf angelegt hat.
    _angelegt = []

    #: Wurde der Rest des letzten Laufs schon geräumt?
    _geraeumt = False

    @classmethod
    def wurzel(cls):
        u"""``BASE_DIR/_wegwerf/pruef`` - angelegt, falls es fehlt."""
        from django.conf import settings

        # JE PROZESS EIN EIGENER ORDNER (Befund CodeRabbit, 31.08.2026):
        # ``_reste_raeumen`` loeschte beim ersten Aufruf ALLES unter der
        # gemeinsamen Wurzel. Laeuft daneben ein zweiter Testprozess, ist das
        # sein Arbeitsordner — ``ignore_errors=True`` verhindert den Verlust
        # nicht, es verschweigt ihn nur.
        pfad = (Path(getattr(settings, "BASE_DIR", ".")).joinpath(*cls.UNTER)
                / ("p%d" % os.getpid()))
        pfad.mkdir(parents=True, exist_ok=True)
        return pfad

    @classmethod
    def neu(cls, praefix="pruef_"):
        u"""Ein leeres Verzeichnis für diesen Prüffall.

        @param praefix Namensanfang - er soll sagen, WER ihn angelegt hat
        @returns {Path} das Verzeichnis
        """
        wurzel = cls.wurzel()
        if not cls._geraeumt:
            cls._geraeumt = True
            cls._reste_raeumen(wurzel)
            atexit.register(cls.aufraeumen)
        ordner = Path(tempfile.mkdtemp(prefix=praefix, dir=str(wurzel)))
        cls._angelegt.append(ordner)
        return ordner

    @classmethod
    def aufraeumen(cls):
        u"""Alles wegräumen, was dieser Lauf angelegt hat."""
        for ordner in cls._angelegt:
            shutil.rmtree(ordner, ignore_errors=True)
        cls._angelegt = []

    @classmethod
    def werkzeug(cls, name, dateien, praefix=None):
        u"""Ein Werkzeug auf einen frischen Wegwerfordner ansetzen.

        Legt den Ordner an, schreibt die Dateien hinein und uebergibt an
        `ansetzen` — dort steht, warum beide Siebe aufgehen muessen.

        @param name     Kennung des Werkzeugs (`klassenreif`, …)
        @param dateien  {relativer Name: Inhalt}
        @param praefix  Namensanfang des Ordners; ohne Angabe der Kennung
        @returns das eingerichtete Werkzeug
        """
        from djangobase.skills import werkzeug_finden

        ordner = cls.neu(praefix or (name.replace("-", "_") + "_"))
        for pfadname, inhalt in dateien.items():
            ziel = ordner / pfadname
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding="utf-8")
        return cls.ansetzen(werkzeug_finden(name), ordner)

    @classmethod
    def ansetzen(cls, werkzeug, ordner):
        u"""Ein Werkzeug auf `ordner` als Projektwurzel ansetzen.

        BEIDE SIEBE MÜSSEN AUF: `Werkzeug.pfade` filtert über die
        Ausschlussliste UND über `.gitignore`. Für den Prüflauf ist der
        Ordner die WURZEL, kein ignorierter Teil des Projekts. Ohne diese
        drei Zeilen findet jedes Werkzeug null Dateien und jeder Prüffall
        meldet „keine Befunde" — was aussieht wie ein blindes Werkzeug.

        EIGENE METHODE, WEIL ES ZWEI AUFRUFER GIBT (31.08.2026):
        `Wegwerfprojekt.fahren` setzte nur die Wurzel. Das ging gut,
        solange sein Ordner im System-Zwischenspeicher lag — also
        AUSSERHALB des Projekts, wo kein Sieb greift. Seit die
        `Ablageumleitung` auch diese Ordner ins Projekt holt, greifen
        beide, und 13 Prüffälle in `test_systemablage` meldeten „keine
        Befunde". Zwei Fassungen derselben Einrichtung sind eine zu viel.

        @param werkzeug ein Werkzeug-Objekt
        @param ordner   die Wurzel für diesen Lauf
        @returns dasselbe Werkzeug, eingerichtet
        """
        werkzeug.wurzel = lambda: Path(ordner)
        offen = werkzeug.ausgeschlossen() - {cls.UNTER[0]}
        werkzeug.ausgeschlossen = lambda: offen
        werkzeug.gitfilter = lambda: _AllesErlaubt()
        return werkzeug

    @staticmethod
    def _reste_raeumen(wurzel):
        u"""Was ein früherer Lauf hinterlassen hat.

        NUR UNTERHALB DER EIGENEN WURZEL, und nur Verzeichnisse: Ein
        Aufräumer, der auch Dateien oder Elternpfade anfasst, ist die
        nächste Sorte Schaden. `ignore_errors` deckt den Fall ab, dass ein
        zweiter Lauf gleichzeitig arbeitet.
        """
        for eintrag in wurzel.iterdir():
            if eintrag.is_dir():
                shutil.rmtree(eintrag, ignore_errors=True)


class _AllesErlaubt:
    u"""Gitfilter-Ersatz für den Wegwerfordner: Er ist kein Projektbaum."""

    @staticmethod
    def erlaubt(_pfad):
        return True
