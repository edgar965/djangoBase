# -*- coding: utf-8 -*-
u"""Freie Funktionen — und wohin die Klasse gehoert, die aus ihnen wird.

DIE FRAGE (Edgar, 24.08.2026)
=============================
    „Warum haben sie die vielen globalen Funktionen nicht erfasst? die
     sollen als Klassen zusammengefasst werden, und dann möglichst in dem
     Baum der sie braucht."

Erfasst hatte das Werkzeug sie sehr wohl — an CamTrack **820 Funktionen
auf Modulebene in 283 Modulen**, davon 45 Module ueber der Schwelle. Was
fehlte, war die zweite Haelfte: WIE die Klasse heisst und WO sie haengt.

Ohne diese Auskunft scheitert der Umbau an derselben Stelle wie vorher:
Eine neue Klasse ohne Platz im Baum ist wieder eine Wurzel, und davon gibt
es schon zu viele (gemessen: 1023 Klassen, 72 gehalten).

DREI ANTWORTEN, NICHT EINE
==========================
    ruft eine Klasse sie?      -> dorthin haengen
    sind es Django-Ansichten?  -> klassenbasierte Ansicht (`View`)
    keins von beidem?          -> neue Wurzel, sparsam einsetzen

Die zweite ist der haeufigste Fall in einem Django-Projekt: Ansichten
werden vom URL-Router gerufen, nicht von einer Klasse. „Niemand ruft sie"
waere dort die falsche Auskunft.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden

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
        self.assertIn('Personenpflege', self._warum(satz, 'Haengt an'))

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

        Das Werkzeug schlug `ComputeAcceptThresholdTests` als Halter fuer
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
