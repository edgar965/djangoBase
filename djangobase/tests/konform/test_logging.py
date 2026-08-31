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
liest dafür **eine Datei** an einem **erwarteten Ort** in einem **erwarteten
Format**:

    <Projekt>/logs/django.log      (oder eine Ebene über BASE_DIR)
    2026-08-20 16:30:45 [INFO] name: text

Weicht ein Projekt davon ab — anderer Dateiname, anderes Verzeichnis, anderer
Formatierer, nur Konsolen-Logging —, dann funktioniert die Aufzeichnung
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

#: Die Dateien, die djangoBase anlegt und auf die sich alles verlässt.
PFLICHT = ("django.log", "error.log")


def _handler_dateien():
    u"""{Dateiname: Handler-Definition} aus dem LOGGING dieses Projekts."""
    aus = {}
    for name, h in (settings.LOGGING or {}).get("handlers", {}).items():
        datei = h.get("filename")
        if datei:
            aus[Path(str(datei)).name] = (name, h)
    return aus


class LoggingKonformTest(SimpleTestCase):
    u"""Das Pflicht-Gerüst: zwei Dateien, ein Ort, ein Format."""

    def test_logging_ist_konfiguriert(self):
        u"""Ohne LOGGING-Dict schreibt niemand eine Datei — und die Aufzeichnung
        sammelt still null Log-Zeilen."""
        self.assertTrue(getattr(settings, "LOGGING", None),
                        u"Dieses Projekt hat kein LOGGING. djangoBase liefert es "
                        u"fertig: LOGGING = dblog.config(<pfad>/logs)")

    def test_beide_pflichtdateien_vorhanden(self):
        dateien = _handler_dateien()
        for name in PFLICHT:
            self.assertIn(name, dateien,
                          u"Es fehlt ein Datei-Handler für %r. djangoBase legt "
                          u"django.log (alles) und error.log (nur Fehler) an; "
                          u"Hilfe → Logs zeigt genau diese beiden Tabs." % name)

    def test_beide_liegen_im_selben_logs_verzeichnis(self):
        u"""``LogFenster`` sucht neben ``BASE_DIR`` — verteilte Log-Dateien
        findet es nicht."""
        dateien = _handler_dateien()
        ordner = {Path(str(h["filename"])).parent
                  for name, (_, h) in dateien.items() if name in PFLICHT}
        self.assertEqual(len(ordner), 1,
                         u"django.log und error.log müssen im selben Ordner "
                         u"liegen, gefunden: %s" % sorted(str(o) for o in ordner))
        ordner = ordner.pop()
        self.assertEqual(ordner.name, "logs",
                         u"Der Ordner muss „logs“ heißen (gefunden: %s) — "
                         u"LogFenster sucht <BASE_DIR>/logs und eine Ebene "
                         u"darüber." % ordner)

    def test_rotierend_und_mehrprozessfest(self):
        u"""Zwei Prozesse (Server plus ein Werkzeug) reichen, damit der
        Windows-Rollover scheitert: Ein Testlauf erzeugte 107
        PermissionError-Meldungen und verlor Logzeilen."""
        erwartet = handler_class()
        for name, (hname, h) in _handler_dateien().items():
            if name not in PFLICHT:
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
        dateien = _handler_dateien()
        if "error.log" not in dateien:
            self.skipTest("error.log fehlt - siehe test_beide_pflichtdateien")
        _, h = dateien["error.log"]
        self.assertEqual(str(h.get("level", "")).upper(), "ERROR",
                         u"error.log muss level=ERROR haben (hat: %r)"
                         % h.get("level"))


class LogFormatTest(SimpleTestCase):
    u"""Das Format, das ``LogFenster`` lesen kann."""

    @staticmethod
    def _filter_laufen_lassen(satz):
        u"""Die konfigurierten Filter über einen Satz laufen lassen.

        WARUM DAS DAZUGEHOERT (26.08.2026)
        ==================================
        Die Prüfung baute einen nackten ``LogRecord`` und schickte ihn
        durch den Formatierer — an CamTrack scheiterte sie mit::

            KeyError: 'job_str'

        Das Format ist djangoBase' eigenes::

            {asctime} [{levelname}] {name}: {job_str}{message}

        und ``{job_str}`` füllt :class:`djangobase.jobctx.JobContextFilter`,
        der in ``LOGGING['filters']`` steht. Im Betrieb läuft er vor jedem
        Formatieren; in der Prüfung lief er nicht. Sie prüfte also einen
        Weg, den es so nirgends gibt, und meldete einen Fehler, den kein
        Nutzer je sehen konnte.

        Ein Filter, der wirft, wird NICHT verschluckt: Er wirft im
        Betrieb genauso, und dann soll es hier auffallen.
        """
        from django.utils.module_loading import import_string
        for name, bau in ((settings.LOGGING or {}).get("filters", {})).items():
            if not isinstance(bau, dict) or "()" not in bau:
                continue          # z. B. django.utils.log.RequireDebugFalse
            klasse = bau["()"]
            if isinstance(klasse, str):
                klasse = import_string(klasse)
            argumente = {k: v for k, v in bau.items() if k != "()"}
            klasse(**argumente).filter(satz)

    def test_formatter_passt_zum_leser(self):
        u"""``LogFenster.KOPF`` erwartet „JJJJ-MM-TT HH:MM:SS [STUFE] name: text".

        Ein anderer Formatierer bricht die Aufzeichnung NICHT — er lässt sie
        still leer ausgehen. Deshalb wird hier eine echte Zeile durch den
        Formatierer geschickt und gegen den Leser gehalten, statt Zeichenketten
        zu vergleichen."""
        formatter = (settings.LOGGING or {}).get("formatters", {}).get("voll")
        self.assertIsNotNone(formatter,
                             u"Der Formatierer „voll“ fehlt — djangoBase legt "
                             u"ihn in dblog.config an")
        f = logging.Formatter(fmt=formatter.get("format"),
                              datefmt=formatter.get("datefmt"),
                              style=formatter.get("style", "%"))
        satz = logging.LogRecord("mein.modul", logging.INFO, "x", 1,
                                 "Testzeile", None, None)
        self._filter_laufen_lassen(satz)
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
        pfad = LogFenster().pfad
        self.assertTrue(pfad.exists(),
                        u"LogFenster sucht %s und findet dort nichts. Die "
                        u"Aufzeichnung würde jede Aufnahme ohne Log-Zeilen "
                        u"speichern — ohne Fehlermeldung." % pfad)

    def test_logfenster_liest_echte_zeilen(self):
        u"""Eine vorhandene, aber unlesbare Datei wäre derselbe stille Ausfall."""
        pfad = LogFenster().pfad
        if not pfad.exists() or pfad.stat().st_size == 0:
            self.skipTest("noch keine Log-Datei geschrieben")
        roh = pfad.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
        passend = [z for z in roh if LogFenster.KOPF.match(z)]
        self.assertTrue(passend,
                        u"Keine der letzten %d Zeilen in %s passt zum erwarteten "
                        u"Format. Beispiel: %r"
                        % (len(roh), pfad.name, roh[-1] if roh else ""))

    def test_die_datei_liegt_wo_das_projekt_sie_schreibt(self):
        u"""Sucht der Leser woanders als der Schreiber, ist beides für sich
        richtig und zusammen kaputt — die teuerste Sorte Fehler."""
        dateien = _handler_dateien()
        if "django.log" not in dateien:
            self.skipTest("kein django.log-Handler")
        geschrieben = Path(str(dateien["django.log"][1]["filename"])).resolve()
        gelesen = LogFenster().pfad.resolve()
        self.assertEqual(gelesen, geschrieben,
                         u"Geschrieben wird nach %s, gelesen aus %s."
                         % (geschrieben, gelesen))


class LogQuellenTest(SimpleTestCase):
    u"""Zeigt Hilfe -> Logs auch die Datei, die das Projekt WIRKLICH schreibt?

    DER FUND (HumanBodyWeb, 30.08.2026)
    ===================================
    ``DJANGOBASE["log_sources"]`` fuehrte weiter ``errors.log``, waehrend der
    Handler ``error_file`` seit der Umstellung auf ``dblog.config`` nach
    ``error.log`` schreibt. Gemessen an dem Tag:

        Quelle „Fehler (aggregiert)"  ->  errors.log   3.268 Bloecke,
                                          alle aus 19 Minuten des 27.08.
        error_file schreibt           ->  error.log      317 Bloecke des
                                          laufenden Tages - in KEINER Quelle

    Die Seite sah dabei vollstaendig aus. Sie zeigte nur alte Fehler, und die
    frischen standen nirgends. Das ist schlimmer als ein leerer Reiter: Ein
    leerer laesst nachfragen, ein gefuellter nicht.

    Geprueft wird die Richtung, die weh tut: Jede Datei, in die das Projekt
    schreibt, muss ueber die Logseite erreichbar sein. Die Gegenrichtung
    (eine Quelle, die kein Handler schreibt) bleibt erlaubt - Projekte
    fuehren dort auch Dateien fremder Prozesse.
    """

    def _quellen(self):
        konf = getattr(settings, "DJANGOBASE", {}) or {}
        return list(konf.get("log_sources") or [])

    def test_jede_geschriebene_datei_steht_in_den_quellen(self):
        quellen = self._quellen()
        if not quellen:
            self.skipTest("Projekt fuehrt keine log_sources")
        genannt = set()
        for eintrag in quellen:
            for name in eintrag[2:4]:
                if name:
                    genannt.add(Path(str(name)).name)
        fehlt = sorted(set(_handler_dateien()) - genannt)
        self.assertEqual(
            fehlt, [],
            u"Diese Dateien schreibt das Projekt, aber Hilfe -> Logs zeigt sie "
            u"nie: %s. In DJANGOBASE['log_sources'] eintragen." % ", ".join(fehlt))

    def test_jede_quelle_nennt_eine_datei(self):
        u"""Ein Eintrag ohne Dateinamen ist ein Reiter, der nie etwas zeigt.

        MIT DERSELBEN NACHSICHT WIE DER TEST DARUEBER (Befund CodeRabbit,
        31.08.2026): ``log_sources`` kommt aus dem Projekt. Feste Indizes
        ``e[2]``/``e[3]`` brachen bei einem kuerzeren Tupel mit IndexError ab —
        eine Konformitaetspruefung, die an einer plausibel aussehenden
        Konfiguration abstuerzt, verdeckt die Regel, die sie pruefen soll. Der
        Test darueber benutzt schon ``eintrag[2:4]``; beide waren sich also
        uneinig, welche Form erlaubt ist.
        """
        leer = [e[0] for e in self._quellen()
                if e and e[0] != "all" and not any(e[2:4])]
        self.assertEqual(leer, [], u"Quellen ohne Datei: %s" % ", ".join(leer))


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

    def test_veralteter_quellenname_faellt_auf(self):
        u"""Genau der Fall vom 30.08.2026: Quelle heisst ``errors.log``,
        geschrieben wird ``error.log``."""
        quellen = [("django", "Django", "django.log", None),
                   ("errors", "Fehler", "errors.log", None)]
        genannt = {Path(str(n)).name for e in quellen for n in e[2:4] if n}
        self.assertNotIn("error.log", genannt,
                         u"Die Regel muss den alten Namen als Luecke sehen - "
                         u"sonst prueft test_jede_geschriebene_datei nichts")
