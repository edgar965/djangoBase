# -*- coding: utf-8 -*-
u"""Sammelzustand — Zustand, der einer Entitaet gehoert, aber gesammelt liegt.

AUFTRAG (Edgar, 23.08.2026): „Eigenschaften/Klassen, die einer anderen Klasse
gehoeren, sollen nicht global gehalten werden, sondern als Unterinstanz der
Klasse."

DER VORFALL, DER DAHINTERSTEHT
==============================
In CamTrack lagen die Zaehler zu elf Kameras verstreut, und die letzte Zeile
dieser Aufstellung ist der Fehler::

    Camera             models.py            die Einstellungen (DB-Zeile)
    CameraRegistry     camera_registry.py   Zwischenspeicher + Sperre je Kamera
    FrameProducer      producer.py          frames_produced, frames_motion_skipped
    LiveDetectorWorker detector_worker.py   frames_processed, errors_total
                                            — fuer ALLE Kameras zusammen

``LiveDetectorWorker`` holte die Bilder je Kamera aus einem Verzeichnis und
zaehlte flach. Die daran haengende Stillstands-Wache gab es genau EINMAL fuer
elf Kameras; sie setzt bei jeder gelungenen Sichtung zurueck. Damit setzte jede
funktionierende Kamera den Zaehler der blind gewordenen zurueck — vier Kameras
liefen am 09.05.2026 zehn Stunden blind, und die Wache, die genau dafuer gebaut
war, schlug kein einziges Mal an.

WARUM EIN EIGENES WERKZEUG
==========================
``GlobalerZustand`` fragt nach Zustand auf MODULEBENE — der war hier tadellos:
alles in einer Klasse, als Instanz-Attribut, genau wie Kriterium 18 es
verlangt. ``Klassenkandidat`` fragt, wo eine Klasse FEHLT — sie war da. Der
Fehler sitzt eine Ebene weiter: Es ist die falsche Klasse.

BEIDE RICHTUNGEN
================
Ein Pruefwerkzeug muss den Fall FINDEN und darf ihn nicht ERFINDEN. Die
Fehlalarm-Tests unten sind keine Kuer: Jeder einzelne steht fuer einen Befund,
der beim Lauf gegen das echte Projekt tatsaechlich kam und die echten Treffer
verdeckt haette. Gemessen an CamTrack (605 Klassen): 41 gemeldete Felder und
12 Warnungen im ersten Lauf, 12 und 5 nach dem Nachschaerfen — bei unveraendert
gefundenem Vorfall.
"""
import tempfile
from pathlib import Path

from djangobase.skills import kriterien, werkzeug_finden

from ..base import BasisTest


class SammelzustandTest(BasisTest):
    u"""Das Werkzeug gegen echte Dateien — findet und erfindet nicht."""

    SLUG = 'sammelzustand'

    def _lauf(self, dateien, **argumente):
        ordner = Path(tempfile.mkdtemp(prefix='sammel_'))
        for name, inhalt in dateien.items():
            (ordner / name).write_text(inhalt, encoding='utf-8')
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIsNotNone(werkzeug, '%s ist nicht registriert' % self.SLUG)
        # ``wurzel`` ist eine METHODE der Basisklasse. Als Attribut gesetzt
        # liefe die Pruefung still gegen das echte Projekt statt gegen die
        # Testdateien — und waere dann immer gruen.
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen(**argumente)

    def _namen(self, satz):
        return ' '.join(b.was for b in satz.befunde)

    # ------------------------------------------------------- Registrierung
    def test_werkzeug_ist_registriert_und_nennt_kriterium_18(self):
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIsNotNone(werkzeug)
        self.assertEqual(werkzeug.kriterium, 18)
        self.assertIn(18, kriterien())

    def test_es_traegt_seinen_anlassfall(self):
        u"""Ein Pruefer ohne Anlassfall meldet null und sieht dabei aus wie
        ein sauberes Projekt. Zweimal passiert am 17.08.2026."""
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIsNotNone(werkzeug.anlassfall)
        self.assertTrue(werkzeug.anlassfall.warum,
                        'der Anlassfall muss sagen, welcher Vorfall hier steht')

    # ------------------------------------------------------ findet den Fall
    def test_findet_den_vorfall(self):
        u"""DER FALL, FUER DEN DAS WERKZEUG GEBAUT IST.

        Je Kamera nachgesehen, gesammelt gezaehlt — und eine Wache fuer alle.
        Beide Haelften muessen kommen: der Zaehler UND die geteilte
        Unterinstanz. Nur die eine zu melden hiesse, den halben Umbau zu
        empfehlen."""
        satz = self._lauf({'detector_worker.py': (
            'class LiveDetectorWorker:\n'
            '    def __init__(self):\n'
            '        self._detektoren = {}\n'
            '        self._sperre = None\n'
            '        self.frames_processed = 0\n'
            '        self.stillstand = SilentFailureWatch()\n\n'
            '    def verarbeite(self, slug, frame):\n'
            '        det = self._detektoren[slug]\n'
            '        self.frames_processed += 1\n'
            '        self.stillstand.record(True)\n'
            '        return det\n')})
        namen = self._namen(satz)
        self.assertIn('frames_processed', namen,
                      'der gesammelte Zaehler wurde nicht gemeldet')
        self.assertIn('stillstand', namen,
                      'die geteilte Unterinstanz wurde nicht gemeldet — genau '
                      'sie liess vier Kameras zehn Stunden blind laufen')

    def test_der_vorfall_ist_eine_warnung_keine_randnotiz(self):
        u"""Zugriff je Entitaet und gesammeltes Schreiben in DERSELBEN Methode
        ist der harte Beweis — das darf nicht als Hinweis untergehen."""
        satz = self._lauf({'w.py': (
            'class Wache:\n'
            '    def __init__(self):\n'
            '        self._je_cam = {}\n'
            '        self.blind = 0\n\n'
            '    def bild(self, slug):\n'
            '        stand = self._je_cam[slug]\n'
            '        self.blind += 1\n'
            '        return stand\n')})
        self.assertTrue(satz.befunde)
        self.assertEqual(satz.befunde[0].gewicht, 'warnung')
        self.assertIn('slug', satz.befunde[0].warum,
                      'die Meldung muss sagen, WOMIT je Entitaet '
                      'nachgeschlagen wird')

    def test_die_abhilfe_nennt_die_unterinstanz(self):
        u"""Ein Befund ohne naechsten Schritt ist eine Beschwerde."""
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIn('Entitaet', werkzeug.abhilfe)
        self.assertIn('geteilt gewollt', werkzeug.abhilfe)

    def test_ein_befund_je_feld_nicht_je_fundstelle(self):
        u"""Ein Zaehler in vier Methoden ist EIN Umbau, nicht vier Baustellen.

        Vier Zeilen darueber liessen die schwerste Fundstelle zwischen den
        anderen untergehen."""
        satz = self._lauf({'v.py': (
            'class Vielfach:\n'
            '    def __init__(self):\n'
            '        self._je_cam = {}\n'
            '        self.zahl = 0\n\n'
            '    def a(self, k):\n'
            '        self._je_cam[k] = 1\n'
            '        self.zahl += 1\n\n'
            '    def b(self):\n'
            '        self.zahl += 1\n\n'
            '    def c(self):\n'
            '        self.zahl += 1\n')})
        self.assertEqual(len(satz.befunde), 1,
                         'ein Feld muss genau einmal im Bericht stehen')
        self.assertEqual(satz.befunde[0].gewicht, 'warnung',
                         'von mehreren Fundstellen muss die schwerste bleiben')

    # ------------------------------------------------- erfindet ihn NICHT
    def test_eine_instanz_je_kamera_ist_der_normalfall(self):
        u"""Der wichtigste Nicht-Befund ueberhaupt.

        Eine Klasse, von der es je Kamera eine gibt, gehoert ihre Zaehler
        selbst. Meldete das Werkzeug hier, waere JEDE saubere Loesung ein
        Befund — und der Bericht wertlos."""
        satz = self._lauf({'vorschau.py': (
            'class VorschauSchreiber:\n'
            '    def __init__(self, slug):\n'
            '        self.slug = slug\n'
            '        self.bilder = 0\n\n'
            '    def bild(self, frame):\n'
            '        self.bilder += 1\n')})
        self.assertFalse(satz.befunde,
                         'eine Klasse je Entitaet darf nie gemeldet werden')

    def test_fester_schluessel_ist_keine_verteilung(self):
        u"""``self._teile['kopf']`` ist eine Struktur mit benannten Faechern,
        keine Ablage je Entitaet."""
        satz = self._lauf({'bericht.py': (
            'class Bericht:\n'
            '    def __init__(self):\n'
            '        self._teile = {}\n'
            '        self.zeilen = 0\n\n'
            '    def fuege(self, text):\n'
            '        self._teile["kopf"] = text\n'
            '        self.zeilen += 1\n')})
        self.assertFalse(satz.befunde, 'fester Schluessel ist kein Beweis')

    def test_eigene_stelle_als_index_ist_keine_verteilung(self):
        u"""``self.punkte[self.stand]`` ist Buchfuehrung ueber die eigene
        Position — der Ringpuffer ``TrackCenters`` kam so in den ersten Lauf."""
        satz = self._lauf({'puffer.py': (
            'class Ringpuffer:\n'
            '    def __init__(self):\n'
            '        self.punkte = {}\n'
            '        self.stand = 0\n\n'
            '    def push(self, wert):\n'
            '        self.punkte[self.stand] = wert\n'
            '        self.stand += 1\n')})
        self.assertFalse(satz.befunde, 'ein Positionsindex ist kein Schluessel')

    def test_datensatz_wird_uebersprungen(self):
        u"""Ein ``@dataclass`` beschreibt EINE Sache. Haelt er ein Verzeichnis,
        sind das seine Daten — ``TrackLockState`` zaehlt darin nach Person aus
        und wurde im ersten Lauf trotzdem gemeldet."""
        satz = self._lauf({'sperre.py': (
            'from dataclasses import dataclass, field\n\n\n'
            '@dataclass\n'
            'class TrackLockState:\n'
            '    stimmen: dict = field(default_factory=dict)\n'
            '    frames_seen: int = 0\n\n'
            '    def add_vote(self, pk):\n'
            '        self.frames_seen += 1\n'
            '        self.stimmen[pk] = 1\n')})
        self.assertFalse(satz.befunde, 'ein Datensatz ist kein Verteiler')

    def test_kennungsfolge_bleibt_gemeinsam(self):
        u"""``next_id`` ist absichtlich geteilt — je Entitaet gefuehrt vergaebe
        sie doppelte Kennungen."""
        satz = self._lauf({'pool.py': (
            'class Pool:\n'
            '    def __init__(self):\n'
            '        self.pool = {}\n'
            '        self.next_id = 0\n\n'
            '    def neu(self, k, v):\n'
            '        self.pool[k] = v\n'
            '        self.next_id += 1\n'
            '        return self.next_id\n')})
        self.assertFalse(satz.befunde, 'eine Kennungsfolge gehoert allen')

    def test_sammelbehaelter_ist_das_ergebnis_nicht_der_zustand(self):
        u"""``self.to_keep.append(person)`` IST, was die Klasse liefert.
        In ``persons_cleanup`` standen gleich zwei davon unter den ersten
        zwoelf Warnungen."""
        satz = self._lauf({'aufraeumen.py': (
            'class Einteiler:\n'
            '    def __init__(self):\n'
            '        self.gruende = {}\n'
            '        self.behalten = []\n\n'
            '    def run(self, personen):\n'
            '        for p in personen:\n'
            '            self.behalten.append(p)\n'
            '            self.gruende[p.pk] = "x"\n')})
        self.assertFalse(satz.befunde, 'ein Ergebnis-Behaelter ist kein Befund')

    def test_alter_wert_als_vorgabe_ist_keine_rechnung(self):
        u"""``self.x = leser.zahl(..., self.x)`` nimmt den alten Wert als
        VORGABE. ``EngineThresholds`` kam mit drei solchen Zeilen."""
        satz = self._lauf({'schwellen.py': (
            'class Schwellen:\n'
            '    def __init__(self):\n'
            '        self._roh = {}\n'
            '        self.sim_high = 0.5\n\n'
            '    def apply(self, leser, key):\n'
            '        self._roh[key] = 1\n'
            '        self.sim_high = leser.zahl("a", self.sim_high, 0.1, 0.9)\n')})
        self.assertFalse(satz.befunde, 'eine Vorgabe ist keine Rechnung')

    def test_was_dem_dienst_selbst_gehoert(self):
        u"""Ein Dienst hat EINEN Faden und EINE Sperre. Das ist kein geteilter
        Zustand, das ist der Dienst."""
        satz = self._lauf({'dienst.py': (
            'class Dienst:\n'
            '    def __init__(self):\n'
            '        self._je_cam = {}\n'
            '        self._stop_event = None\n'
            '        self.laeuft = False\n\n'
            '    def start(self, cam):\n'
            '        d = self._je_cam[cam]\n'
            '        self.laeuft = True\n'
            '        return d\n')})
        self.assertFalse(satz.befunde, 'Lebenszyklus-Felder sind kein Befund')

    def test_vermerk_nimmt_den_gewollten_fall_heraus(self):
        u"""Eine Gesamtzahl fuer die Startseite IST gewollt — sie soll nur
        dastehen, weil jemand sie wollte."""
        ohne = self._lauf({'z.py': (
            'class Zaehlwerk:\n'
            '    def __init__(self):\n'
            '        self._je_cam = {}\n'
            '        self.gesamt = 0\n\n'
            '    def bild(self, slug):\n'
            '        d = self._je_cam[slug]\n'
            '        self.gesamt += 1\n'
            '        return d\n')})
        self.assertTrue(ohne.befunde, 'ohne Vermerk muss es ein Befund sein')

        mit = self._lauf({'z.py': (
            'class Zaehlwerk:\n'
            '    def __init__(self):\n'
            '        self._je_cam = {}\n'
            '        self.gesamt = 0\n\n'
            '    def bild(self, slug):\n'
            '        d = self._je_cam[slug]\n'
            '        # geteilt gewollt: Summe fuer die Startseite\n'
            '        self.gesamt += 1\n'
            '        return d\n')})
        self.assertFalse(mit.befunde,
                         'der Vermerk „geteilt gewollt" greift nicht mehr')

    def test_testdateien_bleiben_draussen(self):
        u"""Ein ``setUp`` legt je Pruefung ein Objekt an — das sieht aus wie
        der Befund und ist der Normalfall. Drei der zwoelf Warnungen im ersten
        Lauf kamen von dort."""
        satz = self._lauf({'test_etwas.py': (
            'class EtwasTest:\n'
            '    def __init__(self):\n'
            '        self._je_cam = {}\n'
            '        self.zahl = 0\n\n'
            '    def setUp(self, slug):\n'
            '        d = self._je_cam[slug]\n'
            '        self.zahl += 1\n'
            '        return d\n')})
        self.assertFalse(satz.befunde, 'Testdateien gehoeren nicht in den Bericht')

    def test_leeres_projekt_bleibt_still(self):
        u"""Wer im Leeren etwas meldet, sucht woanders."""
        satz = self._lauf({})
        self.assertFalse(satz.befunde)
        self.assertTrue(satz.kopf, 'auch ohne Befund gehoert eine Kennzahl hin')
