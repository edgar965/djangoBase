# -*- coding: utf-8 -*-
u"""Ist das Logging dieses Projekts djangoBase-konform — so dass die Aufzeichnung trägt?

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „Ist das Logging im projekt konform mit djangoBase Logging (also logfiles
     namen, directory, art des Logging) so dass die Testaufzeichnung
     funktioniert."

WARUM DAS ZUSAMMENHÄNGT
=======================
Die Testaufzeichnung schneidet am Ende die Server-Log-Zeilen ihres Zeitraums
mit (``LogFenster``) — sie sind die halbe Zusicherung des erzeugten Testfalls:
Was damals keine Ausnahme warf, darf auch jetzt keine werfen. ``LogFenster``
liest dafür **eine benannte Datei** in einem **erwarteten Format**:

    <Projekt>/logs/django.log      (dblog-Standard, oder eine Ebene über BASE_DIR)
    DJANGOBASE["aufzeichnung_log"] = [...]   (wer sein LOGGING selbst schreibt)
    2026-08-20 16:30:45 [INFO] name: text

Weicht ein Projekt davon ab — anderer Formatierer, nur Konsolen-Logging, oder
eine Datei, die niemand benannt hat —, dann funktioniert die Aufzeichnung
trotzdem, aber **still ohne Log-Zeilen**. Der erzeugte Testfall prüft dann nur
noch Abrufe, und niemand merkt, dass die Hälfte fehlt. Genau diese Sorte
stiller Lücke soll hier auffallen.

WAS GEPRÜFT WIRD — UND WAS NICHT
================================
Nicht, dass ein Projekt ``dblog.config`` *aufruft* (das ist eine Formalie),
sondern dass das Ergebnis stimmt: Gibt es die beiden Dateien, an der Stelle, wo
sie erwartet werden, mit dem Format, das gelesen werden kann, und findet
``LogFenster`` sie? Ein Projekt darf sein LOGGING gern selbst schreiben — es
muss nur passen.

Zusätzliche Handler (``aktionen.log`` in ShortLongX) sind ausdrücklich erlaubt.
Geprüft wird das Pflicht-Gerüst, nicht die Abwesenheit von Zusatz.
"""
import logging
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from djangobase.aufzeichnung_logs import LogFenster
from djangobase.logging import handler_class

#: Die Dateien, die ``dblog.config`` anlegt — die Vorgabe, wenn ein Projekt
#: nichts anderes benennt. Siehe ``_hauptlogs``.
PFLICHT = ("django.log", "error.log")


def _handler_dateien():
    u"""{Dateiname: Handler-Definition} aus dem LOGGING dieses Projekts."""
    aus = {}
    for name, h in (settings.LOGGING or {}).get("handlers", {}).items():
        datei = h.get("filename")
        if datei:
            aus[Path(str(datei)).name] = (name, h)
    return aus


def _hauptlog():
    u"""Die Datei, aus der die Aufzeichnung mitschneidet — als Dateiname.

    ZWEI ZULÄSSIGE ABLAGEN (Korrektur 21.08.2026): ``dblog.config`` legt
    ``logs/django.log`` an, und wer das nimmt, muss nichts angeben. Ein Projekt
    mit eigenem LOGGING benennt seine Hauptdatei über
    ``DJANGOBASE['aufzeichnung_log']`` — dann liest ``LogFenster`` genau die.

    Die erste Fassung dieser Prüfung kannte nur den ersten Weg und meldete den
    ``assistant`` mit vier Fehlschlägen, obwohl dessen sieben Logdateien
    rotieren, mehrprozessfest sind und im djangoBase-Format schreiben — sie
    heißen nur anders. Ohne die zweite Ablage hätte hier ein gewachsenes,
    dokumentiertes Logging-Schema umgebaut werden müssen, um eine Prüfung
    zufriedenzustellen."""
    return _hauptlogs()[0]


def _hauptlogs():
    u"""Alle Dateinamen, die die Aufzeichnung mitschneidet."""
    benannt = (getattr(settings, "DJANGOBASE", {}) or {}).get("aufzeichnung_log")
    if not benannt:
        return ["django.log"]
    roh = [benannt] if isinstance(benannt, (str, Path)) else list(benannt)
    return [Path(str(e)).name for e in roh] or ["django.log"]


def _fehlerlogs():
    u"""Alle Datei-Handler, die NUR Fehler aufnehmen (Tab „Exceptions")."""
    return {name: (hname, h) for name, (hname, h) in _handler_dateien().items()
            if str(h.get("level", "")).upper() == "ERROR"}


class LoggingKonformTest(SimpleTestCase):
    u"""Das Pflicht-Gerüst: zwei Dateien, ein Ort, ein Format."""

    def test_logging_ist_konfiguriert(self):
        u"""Ohne LOGGING-Dict schreibt niemand eine Datei — und die Aufzeichnung
        sammelt still null Log-Zeilen."""
        self.assertTrue(getattr(settings, "LOGGING", None),
                        u"Dieses Projekt hat kein LOGGING. djangoBase liefert es "
                        u"fertig: LOGGING = dblog.config(<pfad>/logs)")

    def test_beide_pflichtdateien_vorhanden(self):
        u"""Eine Datei für alles, eine für die Fehler — unter welchem Namen
        auch immer (siehe ``_hauptlog``)."""
        dateien = _handler_dateien()
        fehlend = [n for n in _hauptlogs() if n not in dateien]
        self.assertFalse(fehlend,
                         u"Es fehlt ein Datei-Handler für %s — genau diese "
                         u"Dateien schneidet die Aufzeichnung mit. Entweder "
                         u"LOGGING = dblog.config(<pfad>/logs) nehmen (legt "
                         u"django.log an) oder die eigenen Dateien über "
                         u"DJANGOBASE['aufzeichnung_log'] benennen."
                         % ", ".join(fehlend))
        self.assertTrue(_fehlerlogs(),
                        u"Kein einziger Datei-Handler mit level=ERROR. Der Tab "
                        u"„Exceptions“ in Hilfe → Logs bliebe dauerhaft leer — "
                        u"und das liest sich wie „keine Fehler“.")

    def test_beide_liegen_im_selben_logs_verzeichnis(self):
        u"""Haupt- und Fehlerdatei gehören in EIN Verzeichnis, und es muss da
        sein: Hilfe → Logs zeigt beide nebeneinander, und ein Handler auf einen
        Ordner, den es nicht gibt, wirft beim ersten Schreiben."""
        dateien = _handler_dateien()
        haupt = _hauptlog()
        if haupt not in dateien:
            self.skipTest("keine Hauptdatei - siehe test_beide_pflichtdateien")
        ordner = {Path(str(dateien[haupt][1]["filename"])).parent}
        ordner |= {Path(str(h["filename"])).parent
                   for _, (_, h) in _fehlerlogs().items()}
        self.assertEqual(len(ordner), 1,
                         u"Haupt- und Fehler-Log müssen im selben Ordner liegen, "
                         u"gefunden: %s" % sorted(str(o) for o in ordner))
        eins = ordner.pop()
        self.assertTrue(eins.is_dir(),
                        u"Das Log-Verzeichnis %s gibt es nicht." % eins)

    def test_rotierend_und_mehrprozessfest(self):
        u"""Zwei Prozesse (Server plus ein Werkzeug) reichen, damit der
        Windows-Rollover scheitert: Ein Testlauf erzeugte 107
        PermissionError-Meldungen und verlor Logzeilen."""
        erwartet = handler_class()
        pflicht = set(_hauptlogs()) | set(_fehlerlogs())
        for name, (hname, h) in _handler_dateien().items():
            if name not in pflicht:
                continue
            with self.subTest(datei=name):
                self.assertEqual(h.get("class"), erwartet,
                                 u"Handler %r nutzt %r statt %r — nimm "
                                 u"dblog.handler_class()"
                                 % (hname, h.get("class"), erwartet))
                self.assertTrue(h.get("maxBytes"),
                                u"Ohne maxBytes wächst die Datei unbegrenzt")
                self.assertTrue(h.get("backupCount"),
                                u"Ohne backupCount gibt es keine Rotation")

    def test_error_log_nimmt_nur_fehler(self):
        u"""Sonst ist der Tab „Exceptions" in Hilfe → Logs eine Kopie des
        anderen und taugt nicht zum Nachsehen."""
        fehler = _fehlerlogs()
        if not fehler:
            self.skipTest("kein Fehler-Log - siehe test_beide_pflichtdateien")
        self.assertNotIn(_hauptlog(), fehler,
                         u"Die Hauptdatei %r hat selbst level=ERROR — dann "
                         u"fehlt der Aufzeichnung alles unterhalb davon."
                         % _hauptlog())


class LogFormatTest(SimpleTestCase):
    u"""Das Format, das ``LogFenster`` lesen kann."""

    def test_formatter_passt_zum_leser(self):
        u"""``LogFenster.KOPF`` erwartet „JJJJ-MM-TT HH:MM:SS [STUFE] name: text".

        Ein anderer Formatierer bricht die Aufzeichnung NICHT — er lässt sie
        still leer ausgehen. Deshalb wird hier eine echte Zeile durch den
        Formatierer geschickt und gegen den Leser gehalten, statt Zeichenketten
        zu vergleichen."""
        formatierer = (settings.LOGGING or {}).get("formatters", {})
        dateien = _handler_dateien()
        # NICHT stur „voll" (Korrektur 21.08.2026): Geprüft gehört der
        # Formatierer, den die MITGESCHNITTENE Datei benutzt. Heißt er anders,
        # war die alte Fassung rot, obwohl das Format stimmte.
        name = "voll"
        if _hauptlog() in dateien:
            name = dateien[_hauptlog()][1].get("formatter") or "voll"
        formatter = formatierer.get(name)
        self.assertIsNotNone(formatter,
                             u"Der Formatierer %r ist nicht definiert — die "
                             u"Hauptdatei verweist auf ihn." % name)
        satz = logging.LogRecord("mein.modul", logging.INFO, "x", 1,
                                 "Testzeile", None, None)
        # Felder, die im Betrieb ein FILTER anhängt (``%(req_str)s`` und
        # Verwandte), gibt es an einem frisch gebauten Satz nicht — ohne sie
        # wirft der Formatierer, und die Prüfung meldete einen Formatfehler, wo
        # keiner ist. Sie werden leer gesetzt, weil sie für den Zeilenanfang,
        # um den es hier geht, keine Rolle spielen.
        for feld in set(re.findall(r"%\((\w+)\)", formatter.get("format") or "")):
            if not hasattr(satz, feld):
                setattr(satz, feld, "")
        # Ein Projekt darf eine eigene Formatierer-Klasse mitbringen („()“); die
        # wird gebaut wie im Betrieb, sonst prüft der Test etwas anderes als das,
        # was in der Datei landet.
        bauplan = dict(formatter)
        klasse = bauplan.pop("()", None)
        if klasse:
            from django.utils.module_loading import import_string
            klasse = import_string(klasse) if isinstance(klasse, str) else klasse
            try:
                f = klasse(**bauplan)
            except TypeError:
                # Wie logging.config es macht: Der Schlüssel heißt in der
                # Konfiguration „format", der Parameter aber „fmt". Ohne diesen
                # zweiten Versuch scheiterte die Prüfung an ihrem eigenen
                # Aufbau statt am Format des Projekts.
                bauplan["fmt"] = bauplan.pop("format", None)
                f = klasse(**bauplan)
        else:
            f = logging.Formatter(fmt=bauplan.get("format"),
                                  datefmt=bauplan.get("datefmt"),
                                  style=bauplan.get("style", "%"))
        zeile = f.format(satz)
        self.assertRegex(zeile, LogFenster.KOPF,
                         u"Die erzeugte Zeile %r passt nicht zu "
                         u"LogFenster.KOPF — die Aufzeichnung sammelt dann "
                         u"still NULL Log-Zeilen." % zeile)

    def test_leser_zerlegt_die_zeile_richtig(self):
        u"""Gegenprobe: Was der Formatierer schreibt, muss der Leser auch in
        seine vier Teile bekommen — sonst steht im Testfall Kraut und Rüben."""
        treffer = LogFenster.KOPF.match(
            "2026-08-21 16:30:45 [WARNING] dashboard.views: etwas ist schief")
        self.assertIsNotNone(treffer)
        self.assertEqual(treffer.group(2), "WARNING")
        self.assertEqual(treffer.group(3), "dashboard.views")
        self.assertEqual(treffer.group(4), "etwas ist schief")


class AufzeichnungFindetDasLogTest(SimpleTestCase):
    u"""Der eigentliche Zweck: Findet die Aufzeichnung die Datei WIRKLICH?

    Die Prüfungen oben lesen Einstellungen. Diese hier fragt das Werkzeug
    selbst — dieselbe Klasse, die beim Beenden einer Aufnahme läuft."""

    def test_logfenster_findet_die_datei(self):
        fehlend = [str(p) for p in LogFenster().pfade if not p.exists()]
        self.assertFalse(fehlend,
                         u"LogFenster sucht %s und findet dort nichts. Die "
                         u"Aufzeichnung würde jede Aufnahme ohne diese "
                         u"Log-Zeilen speichern — ohne Fehlermeldung."
                         % ", ".join(fehlend))

    def test_logfenster_liest_echte_zeilen(self):
        u"""Eine vorhandene, aber unlesbare Datei wäre derselbe stille Ausfall.

        Geprüft wird JEDE angegebene Datei: Ist eine davon in einem anderen
        Format, fehlt genau ihr Teil des Ablaufs — und nichts sagt es."""
        gelesen = 0
        for pfad in LogFenster().pfade:
            if not pfad.exists() or pfad.stat().st_size == 0:
                continue
            gelesen += 1
            roh = pfad.read_text(encoding="utf-8",
                                 errors="replace").splitlines()[-200:]
            passend = [z for z in roh if LogFenster.KOPF.match(z)]
            self.assertTrue(passend,
                            u"Keine der letzten %d Zeilen in %s passt zum "
                            u"erwarteten Format. Beispiel: %r"
                            % (len(roh), pfad.name, roh[-1] if roh else ""))
        if not gelesen:
            self.skipTest("noch keine Log-Datei geschrieben")

    def test_die_datei_liegt_wo_das_projekt_sie_schreibt(self):
        u"""Sucht der Leser woanders als der Schreiber, ist beides für sich
        richtig und zusammen kaputt — die teuerste Sorte Fehler."""
        dateien = _handler_dateien()
        if _hauptlog() not in dateien:
            self.skipTest("kein Handler für %s" % _hauptlog())
        geschrieben = Path(str(dateien[_hauptlog()][1]["filename"])).resolve()
        gelesen = LogFenster().pfad.resolve()
        self.assertEqual(gelesen, geschrieben,
                         u"Geschrieben wird nach %s, gelesen aus %s."
                         % (geschrieben, gelesen))


class GegenprobeTest(SimpleTestCase):
    u"""Schlagen die Regeln überhaupt an?

    Alle Prüfungen oben sind für ein konformes Projekt grün — das sagt für sich
    genommen nichts. Hier wird jede Regel gegen ein absichtlich kaputtes LOGGING
    gehalten: Was nicht rot wird, prüft nichts.
    """

    KAPUTT = {
        "version": 1,
        "formatters": {"voll": {"format": "{message}", "style": "{"}},
        "handlers": {
            "nur_konsole": {"class": "logging.StreamHandler", "formatter": "voll"},
            "woanders": {"class": "logging.FileHandler",
                         "filename": "/tmp/mein.log", "formatter": "voll"},
        },
        "root": {"handlers": ["nur_konsole"], "level": "INFO"},
    }

    @override_settings(LOGGING=KAPUTT)
    def test_fehlende_pflichtdateien_fallen_auf(self):
        dateien = _handler_dateien()
        self.assertNotIn("django.log", dateien)
        self.assertNotIn("error.log", dateien)

    @override_settings(LOGGING=KAPUTT)
    def test_falscher_formatter_faellt_auf(self):
        f = logging.Formatter(fmt="{message}", style="{")
        zeile = f.format(logging.LogRecord("m", logging.INFO, "x", 1,
                                           "Testzeile", None, None))
        self.assertIsNone(LogFenster.KOPF.match(zeile),
                          u"Ein Format ohne Zeitstempel MUSS am Leser scheitern - "
                          u"sonst prüft test_formatter_passt_zum_leser nichts")

    def test_nicht_rotierender_handler_faellt_auf(self):
        u"""``logging.FileHandler`` rotiert nicht und sperrt unter Windows."""
        self.assertNotEqual("logging.FileHandler", handler_class())
