# -*- coding: utf-8 -*-
u"""Die Werkzeuge stehen EINMAL auf der Seite: in der Tabelle.

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „ich will keine neuen Bereich ohne tabelle die mit 17 anfangen,
     gliedere diese Bereiche ein in der Art und weise der Tabellen wie die
     vorherigen Bereiche. Was ist da so schwer zu verstehen???"

Unter der Tabelle standen zwei eigene Kästen — „Logging & Tests ·
Kriterium 16 und 17" und „Klassen & Zustand · Kriterium 18". Sie fingen
mit „16.", „17." und „18." an und sahen damit aus wie neue Bereiche.

Sie waren keine. Alle zehn Werkzeuge darin standen längst IN der Tabelle,
verteilt auf drei Abschnitte::

    Stille Fehler                    jsstumm, protokoll, schreibrouten
    Objektorientierung und Struktur  klassenreif, globaler-zustand, …
    Tests und Werkzeuge selbst       testaufbau, testdeckung, …

Zwei Darstellungen derselben Sache — und die zweite konnte weniger: kein
Häkchen, kein Rang, keine Ergebnis-Spalte. Kein Wunder, dass unklar war,
was das sein soll.

Das einzig Eigene war der Sammellauf-Knopf. Der sitzt jetzt in der
Abschnitts-Zeile und gilt für JEDEN Bereich.

Drei Vorläufer dieser Prüfung sind gescheitert, weil sie die Kästen
festhielten statt die Regel: Kein Werkzeug steht zweimal, und jeder
Abschnitt fährt genau seine eigenen.
"""
from djangobase.skills import werkzeuge
from djangobase.skills.rangliste import rangliste
from djangobase.views.skills import SkillsView

from ..base import BasisTest


def _abschnitte():
    return rangliste().abschnitte(list(werkzeuge()))


class JedesWerkzeugStehtGenauEinmal(BasisTest):

    def test_die_tabelle_zeigt_alle_werkzeuge(self):
        in_tabelle = [w.slug for a in _abschnitte()
                      for _rang, w in a['eintraege']]
        self.assertEqual(sorted(in_tabelle),
                         sorted(w.slug for w in werkzeuge()),
                         'Ein Werkzeug faellt aus der Tabelle — dann ist es '
                         'auf der Seite nicht mehr zu starten.')

    def test_keines_steht_in_zwei_abschnitten(self):
        in_tabelle = [w.slug for a in _abschnitte()
                      for _rang, w in a['eintraege']]
        doppelt = sorted({s for s in in_tabelle if in_tabelle.count(s) > 1})
        self.assertEqual(doppelt, [],
                         'Diese Werkzeuge stehen mehrfach: %s' % doppelt)


class DerKnopfFaehrtGenauSeinenAbschnitt(BasisTest):
    u"""Ein Knopf, der etwas anderes fährt als die Zeile darüber zeigt, ist
    schlimmer als kein Knopf."""

    def test_jeder_abschnitt_faehrt_seine_eigenen(self):
        for nummer, a in enumerate(_abschnitte()):
            if not a['eintraege']:
                continue
            with self.subTest(bereich=a['bereich']['name']):
                self.assertEqual(
                    sorted(SkillsView._bereich_slugs(nummer)),
                    sorted(w.slug for _rang, w in a['eintraege']))

    def test_jeder_abschnitt_hat_einen_knopf(self):
        for nummer, a in enumerate(_abschnitte()):
            if not a['eintraege']:
                continue
            kopf = SkillsView._gruppenkopf(nummer, a['bereich'],
                                           len(a['eintraege']))
            with self.subTest(bereich=a['bereich']['name']):
                self.assertIn('name="bereich" value="%d"' % nummer, kopf)
                self.assertIn(a['bereich']['name'], kopf)


class EineUnsinnigeNummerFaehrtNICHTS(BasisTest):
    u"""Die Nummer kommt aus der Anfrage — sie wird geprüft, nicht benutzt.

    Ohne das würde ein ``bereich=99`` entweder werfen (500) oder, schlimmer,
    versehentlich etwas fahren.
    """

    def test_zu_gross(self):
        self.assertEqual(SkillsView._bereich_slugs(999), [])

    def test_negativ(self):
        self.assertEqual(SkillsView._bereich_slugs(-1), [])

    def test_keine_zahl(self):
        self.assertEqual(SkillsView._bereich_slugs('alle'), [])

    def test_nichts_uebergeben(self):
        u"""Der Normalfall: Es wurde ein Werkzeug angehakt, kein Bereich."""
        self.assertEqual(SkillsView._bereich_slugs(None), [])


class KeineZWEITEDarstellungAufDerSeite(BasisTest):
    u"""Der Rückfall, gegen den diese Datei geschrieben ist."""

    VORLAGE = 'djangobase/hilfe/skills.html'

    def _markup(self):
        from django.template.loader import get_template
        from pathlib import Path
        return Path(get_template(self.VORLAGE).origin.name).read_text(
            encoding='utf-8')

    def test_die_kaesten_sind_weg(self):
        markup = self._markup()
        for rest in ('name="k1617"', 'name="k18"'):
            self.assertNotIn(
                rest, markup,
                'Der Kasten mit %s ist zurueck — dann stehen die Werkzeuge '
                'wieder doppelt, einmal koennend und einmal nicht.' % rest)
