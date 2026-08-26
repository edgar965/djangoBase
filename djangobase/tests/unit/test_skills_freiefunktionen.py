# -*- coding: utf-8 -*-
u"""Freie Funktionen — und wohin die Klasse gehört, die aus ihnen wird.

DIE FRAGE (Edgar, 24.08.2026)
=============================
    „Warum haben sie die vielen globalen Funktionen nicht erfasst? die
     sollen als Klassen zusammengefasst werden, und dann möglichst in dem
     Baum der sie braucht."

Erfasst hatte das Werkzeug sie sehr wohl — an CamTrack **820 Funktionen
auf Modulebene in 283 Modulen**, davon 45 Module über der Schwelle. Was
fehlte, war die zweite Haelfte: WIE die Klasse heißt und WO sie hängt.

Ohne diese Auskunft scheitert der Umbau an derselben Stelle wie vorher:
Eine neue Klasse ohne Platz im Baum ist wieder eine Wurzel, und davon gibt
es schon zu viele (gemessen: 1023 Klassen, 72 gehalten).

DREI ANTWORTEN, NICHT EINE
==========================
    ruft eine Klasse sie?      -> dorthin hängen
    sind es Django-Ansichten?  -> klassenbasierte Ansicht (`View`)
    keins von beidem?          -> neue Wurzel, sparsam einsetzen

Die zweite ist der haeufigste Fall in einem Django-Projekt: Ansichten
werden vom URL-Router gerufen, nicht von einer Klasse. „Niemand ruft sie"
wäre dort die falsche Auskunft.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.befund import Befund

from ..base import BasisTest


class FreieFunktionenTest(BasisTest):

    def _lauf(self, dateien, **argumente):
        ordner = Path(tempfile.mkdtemp(prefix='ff_'))
        for name, inhalt in dateien.items():
            ziel = ordner / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding='utf-8')
        werkzeug = werkzeug_finden('freie-funktionen')
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen(**argumente)

    @staticmethod
    def _warum(satz, teil):
        for b in satz.befunde:
            if teil in b.warum:
                return b.warum
        raise AssertionError('%r steht in keinem Befund: %s'
                             % (teil, [b.warum for b in satz.befunde]))

    #: Fuenf Funktionen mit gemeinsamem Namensanfang — ein Buendel.
    BUENDEL = ''.join(
        'def person_%s(request):\n    return %d\n\n\n' % (w, i)
        for i, w in enumerate(('rename', 'ignore', 'delete', 'merge', 'split')))

    # ── dass es sie ueberhaupt findet ────────────────────────────
    def test_die_funktionen_werden_gezaehlt(self):
        satz = self._lauf({'a.py': self.BUENDEL}, ab='3')
        self.assertTrue(any('5 Funktionen auf Modulebene' in z
                            for z in satz.kopf), satz.kopf)

    def test_das_buendel_wird_als_klasse_vorgeschlagen(self):
        satz = self._lauf({'a.py': self.BUENDEL}, ab='3')
        self.assertIn('als Klasse `PersonVerwaltung`',
                      self._warum(satz, 'PersonVerwaltung'))

    # ── wohin die Klasse gehoert: drei Antworten ─────────────────
    def test_wer_sie_ruft_soll_sie_halten(self):
        satz = self._lauf({
            'a.py': self.BUENDEL,
            'b.py': ('from a import person_rename\n\n\n'
                     'class Personenpflege:\n'
                     '    def tu(self):\n'
                     '        person_rename(1)\n'
                     '        person_ignore(2)\n'),
        }, ab='3')
        self.assertIn('Personenpflege', self._warum(satz, 'Hängt an'))

    def test_django_ansichten_gehoeren_in_eine_view_klasse(self):
        u"""Der haeufigste Fall: Der URL-Router ruft sie, keine Klasse."""
        satz = self._lauf({
            'a.py': self.BUENDEL,
            'urls.py': ("from django.urls import path\n"
                        "from . import views\n"
                        "urlpatterns = [\n"
                        "    path('r/', views.person_rename),\n"
                        "    path('i/', views.person_ignore),\n"
                        "]\n"),
        }, ab='3')
        self.assertIn('klassenbasierte Ansicht',
                      self._warum(satz, 'Django-Ansichten'))

    def test_ohne_rufer_und_ohne_route_ist_es_eine_neue_wurzel(self):
        satz = self._lauf({'a.py': self.BUENDEL}, ab='3')
        self.assertIn('neue Wurzel', self._warum(satz, 'Wurzel'))

    def test_eine_klasse_im_selben_modul_ist_der_naechste_platz(self):
        satz = self._lauf({'a.py': self.BUENDEL + 'class Schon:\n    pass\n'},
                          ab='3')
        self.assertIn('selben Modul', self._warum(satz, 'selben Modul'))

    # ── was NICHT als Halter taugt ───────────────────────────────
    def test_eine_testklasse_haelt_keinen_produktionscode(self):
        u"""DER FEHLER AUS DEM ERSTEN LAUF (24.08.2026).

        Das Werkzeug schlug `ComputeAcceptThresholdTests` als Halter für
        drei Schwellen-Funktionen vor. Ein Test RUFT den Code, er BESITZT
        ihn nicht.
        """
        satz = self._lauf({
            'a.py': self.BUENDEL,
            'test_a.py': ('from a import person_rename\n\n\n'
                          'class PersonTests:\n'
                          '    def test_x(self):\n'
                          '        person_rename(1)\n'
                          '        person_ignore(2)\n'),
        }, ab='3')
        warum = self._warum(satz, 'Wurzel')
        self.assertNotIn('PersonTests', warum)

    def test_ein_mixin_ist_auch_kein_halter(self):
        satz = self._lauf({
            'a.py': self.BUENDEL,
            'b.py': ('from a import person_rename\n\n\n'
                     'class PersonMixin:\n'
                     '    def tu(self):\n'
                     '        person_rename(1)\n'),
        }, ab='3')
        self.assertNotIn('PersonMixin', self._warum(satz, 'Wurzel'))

    # ── die Schwelle ─────────────────────────────────────────────
    def test_unter_der_schwelle_wird_nichts_gemeldet(self):
        satz = self._lauf({'a.py': 'def eins():\n    pass\n'}, ab='3')
        self.assertFalse(satz.befunde)

    def test_ein_leeres_projekt_bleibt_still(self):
        satz = self._lauf({})
        self.assertFalse(satz.befunde)
        self.assertTrue(satz.kopf)

    # ── das Gewicht folgt der Rolle ──────────────────────────────
    VIELE = ''.join('def teil_%d(x):\n    return %d\n\n\n' % (i, i)
                    for i in range(8))

    def _gewicht(self, pfad):
        satz = self._lauf({pfad: self.VIELE}, ab='2')
        return satz.befunde[0].gewicht if satz.befunde else None

    def test_ein_dienst_ist_eine_warnung(self):
        self.assertEqual(self._gewicht('services/rechnen.py'),
                         Befund.WARNUNG)

    def test_eine_ansicht_ist_nur_ein_hinweis(self):
        u"""DIE FRAGE (Edgar, 26.08.2026)

            „wie kann es sein, dass die Code-Review-Tests alles grün
             melden, und du noch hunderte freier Funktionen hast usw??"

        Weil 59 % der Liste Dinge waren, die so gehören: `def
        meine_ansicht(request)` auf Modulebene IST die Django-Schreibweise.
        Gemessen an CamTrack: 101 der 285 Module sind Ansichten, 67 sind
        Prüfungen. Eine Liste, die zu 59 % aus Richtigem besteht, arbeitet
        niemand durch — und genau das ist passiert.
        """
        self.assertEqual(self._gewicht('views/seiten.py'), Befund.HINWEIS)

    def test_eine_testhilfe_ebenso(self):
        self.assertEqual(self._gewicht('tests/unit/test_hilfe.py'),
                         Befund.HINWEIS)

    def test_gemeldet_werden_sie_trotzdem(self):
        u"""Weglassen wäre schlimmer: Dann sähe niemand mehr, wie viele
        es sind."""
        satz = self._lauf({'views/seiten.py': self.VIELE}, ab='2')
        self.assertEqual(len(satz.befunde), 1)

    # ── der Name des Vorschlags ──────────────────────────────────
    def test_ein_verb_ist_kein_gegenstand(self):
        u"""DER BEFUND (24.08.2026): Für `path_resolver.py` kam
        `GetVerwaltung` heraus — gebündelt über `get_media_root`,
        `get_persons_dir`, `get_ffmpeg`. Das Verb hatten alle gemeinsam,
        den Gegenstand keine. So ein Vorschlag ist schlechter als keiner,
        weil er aussieht, als hätte jemand nachgedacht."""
        satz = self._lauf({'wege.py': (
            'def get_medien():\n    return 1\n\n\n'
            'def get_personen():\n    return 2\n\n\n'
            'def get_aufnahmen():\n    return 3\n')}, ab='3')
        self.assertNotIn('GetVerwaltung', self._warum(satz, 'als Klasse'))

    def test_ohne_buendel_gilt_der_dateiname(self):
        u"""`mqtt.py` hält `get_client`, `publish_sighting`,
        `publish_offline`: kein gemeinsames Wort, aber offensichtlich EINE
        Sache. Vorher stand hier „kein gemeinsamer Namensanfang — einzeln
        prüfen", also die Bankrotterklärung."""
        satz = self._lauf({'mqtt.py': (
            'def get_client():\n    x = 1\n    return x\n\n\n'
            'def publish_sichtung():\n    y = 1\n    return y\n\n\n'
            'def publish_offline():\n    z = 1\n    return z\n')}, ab='3')
        self.assertIn('`Mqtt`', self._warum(satz, 'als Klasse'))

    def test_ein_paketordner_gibt_den_namen_statt_init(self):
        satz = self._lauf({'kameras/__init__.py': (
            'def eins():\n    a = 1\n    return a\n\n\n'
            'def zwei():\n    b = 1\n    return b\n\n\n'
            'def drei():\n    c = 1\n    return c\n')}, ab='3')
        self.assertIn('`Kameras`', self._warum(satz, 'als Klasse'))

    # ── Fassade statt fehlender Klasse ───────────────────────────
    FASSADE = ('class Pfade:\n'
               '    @staticmethod\n'
               '    def medien():\n        return 1\n\n\n'
               'def get_medien():\n    return Pfade.medien()\n\n\n'
               'def get_personen():\n    return Pfade.medien()\n\n\n'
               'def get_aufnahmen():\n    return Pfade.medien()\n')

    def test_wo_die_klasse_schon_steht_fehlt_keine(self):
        u"""DER UNTERSCHIED, DER GEFEHLT HAT (24.08.2026)

        `app/integrations/` bekam sieben Mal „schreib eine Klasse".
        Gemessen: fünf der sechs Dateien HABEN sie — `Pfade`, `Dateien`,
        `FFmpeg`, `DiskSpace`, `Aufgabenplanung`. Davor stehen nur
        Einzeiler, und `get_media_root` allein wird an 146 Stellen
        gerufen. Abreissen kostet 146 Änderungen, die fehlende Klasse
        schreiben kostet eine — ohne die Unterscheidung sieht beides
        gleich dringend aus.
        """
        satz = self._lauf({'wege.py': self.FASSADE}, ab='2')
        self.assertIn('Klasse steht schon da',
                      self._warum(satz, 'Klasse steht schon da'))
        self.assertEqual([b.was for b in satz.befunde],
                         ['3 Weiterleitungen vor 1 Klasse(n)'])

    def test_echte_logik_bleibt_ein_auftrag(self):
        u"""Eine Klasse im Modul allein genügt nicht — die freien
        Funktionen müssen auch wirklich nur weitergeben."""
        satz = self._lauf({'wege.py': (
            'class Pfade:\n    pass\n\n\n'
            'def eins():\n    a = 1\n    b = 2\n    return a + b\n\n\n'
            'def zwei():\n    a = 1\n    b = 2\n    return a - b\n\n\n'
            'def drei():\n    a = 1\n    b = 2\n    return a * b\n')},
            ab='3')
        self.assertIn('als Klasse', self._warum(satz, 'als Klasse'))
