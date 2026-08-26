# -*- coding: utf-8 -*-
u"""Seitenwurzeln — derselbe Massstab wie im Backend, andere Haelfte.

DIE FRAGE (Edgar, 23.08.2026)
=============================
    „mach eine Unterteilung, da viele Klassen aus js kommen, aus html seiten
     aufgerufen werden, die sollen ggf. an einer Klasse der seite hängen"

Nachgemessen an CamTrack::

    JS-Klassen im Projekt              175
      aus VORLAGEN erzeugt              16   <- die Wurzeln der Seite
      nur aus Modulen erzeugt          157   <- haengen an einem Ast

Die 157 sind in Ordnung. Das Problem sind die Vorlagen::

    form.html          18 Objekte
    base.html          10
    live_view.html      9   + zwei setTimeout

WARUM DIE WARTEZEITEN DER BEWEIS SIND
=====================================
``live_view.html`` erzeugt neun Objekte nebeneinander und raet ihre
Reihenfolge::

    setupZeitbereiche({...});                   // „ERST er, DANN die Leiste"
    setTimeout(() => setupStromWache(...), 2000);
    setTimeout(() => { setupGlobalTimeline({...}); }, 100);

Steht die Reihenfolge in einem ``setTimeout``, steht sie nirgends. Die
Fehler dazu sind belegt: Am 21.08.2026 liefen Zeitleiste und Kachel-Leisten
mit zwei getrennten Abrufen auseinander, am 23.08.2026 fiel der Sprung
zwischen Treffern an den Anfang zurueck, weil der Zustand am DOM hing.

WAS HIER GEPRUEFT WIRD
======================
1. Eine Vorlage, die mehrere Objekte erzeugt, wird gefunden.
2. Die Fabrik-Schreibweise (``setupX()``) zaehlt mit — ohne sie haette
   ``live_view.html`` zwei statt neun Wurzeln.
3. ``setTimeout`` macht daraus eine Warnung.
4. Browser-Bausteine zaehlen nicht. ``new Date()`` ist keine Wurzel eines
   Objektmodells — beim ersten Lauf standen drei davon in den Befunden.
5. Bausteine (``_teil_*.html``) sind keine Seiten.
"""
import tempfile
from pathlib import Path

from djangobase.skills import werkzeug_finden
from djangobase.skills.seitenwurzeln import Seite, Seitenwurzeln

from ..base import BasisTest


class SeitenwurzelnTest(BasisTest):

    SLUG = 'seitenwurzeln'

    def _lauf(self, dateien, **argumente):
        ordner = Path(tempfile.mkdtemp(prefix='seiten_'))
        for name, inhalt in dateien.items():
            (ordner / name).write_text(inhalt, encoding='utf-8')
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIsNotNone(werkzeug, '%s ist nicht registriert' % self.SLUG)
        werkzeug.wurzel = lambda: ordner
        return werkzeug.pruefen(**argumente)

    # ------------------------------------------------------- Registrierung
    def test_werkzeug_ist_registriert(self):
        werkzeug = werkzeug_finden(self.SLUG)
        self.assertIsNotNone(werkzeug)
        self.assertTrue(werkzeug.anlassfall)
        self.assertTrue(werkzeug.anlassfall.warum)

    def test_der_idealwert_steht_im_kopf(self):
        satz = self._lauf({'a.html': '<p>nichts</p>'}, ab='0')
        self.assertTrue(any('Idealwert' in z for z in satz.kopf))

    # ------------------------------------------------------ findet den Fall
    def test_mehrere_objekte_in_einer_vorlage(self):
        satz = self._lauf({'seite.html': (
            '<script type="module">\n'
            '  const a = new Gitter(document);\n'
            '  const b = new Leiste(document);\n'
            '</script>\n')}, ab='1')
        self.assertTrue(satz.befunde)
        self.assertIn('2 Objekte', satz.befunde[0].was)

    def test_die_fabrik_schreibweise_zaehlt_mit(self):
        """Ohne sie hätte `live_view.html` zwei statt neun Wurzeln — dort
        heißen sie `setupTrefferBar`, `setupGlobalTimeline`, …"""
        satz = self._lauf({'seite.html': (
            '<script type="module">\n'
            'setupZeitbereiche({});\n'
            'setupGlobalTimeline({});\n'
            'startDesktopKeepalive();\n'
            '</script>\n')}, ab='1')
        self.assertTrue(satz.befunde)
        self.assertIn('3 Objekte', satz.befunde[0].was)

    def test_wartezeiten_machen_daraus_eine_warnung(self):
        """DER KERN. Steht die Reihenfolge in einem `setTimeout`, steht sie
        nirgends."""
        satz = self._lauf({'seite.html': (
            '<script type="module">\n'
            '  const a = new Gitter(document);\n'
            '  const b = new Leiste(document);\n'
            '  setTimeout(() => setupSpaeter({}), 100);\n'
            '</script>\n')}, ab='1')
        self.assertTrue(satz.befunde)
        self.assertEqual(satz.befunde[0].gewicht, 'warnung')
        self.assertIn('setTimeout', satz.befunde[0].warum)

    def test_ohne_wartezeit_nur_ein_hinweis(self):
        satz = self._lauf({'seite.html': (
            '<script type="module">\n'
            '  const a = new Gitter(document);\n'
            '  const b = new Leiste(document);\n'
            '</script>\n')}, ab='1')
        self.assertEqual(satz.befunde[0].gewicht, 'hinweis')

    def test_die_zahl_steht_im_kopf(self):
        satz = self._lauf({
            'a.html': '<script>const x = new Eins(1);</script>',
            'b.html': '<script>const y = new Zwei(2);</script>'}, ab='0')
        self.assertTrue(any('2 Wurzeln insgesamt' in z for z in satz.kopf),
                        satz.kopf)

    # ------------------------------------------------- erfindet ihn NICHT
    def test_eine_seite_mit_EINER_wurzel_ist_das_ziel(self):
        satz = self._lauf({'seite.html': (
            '<script type="module">\n'
            '  new LiveAnsichtSeite(document).start();\n'
            '</script>\n')}, ab='1')
        self.assertFalse(satz.befunde,
                         'so soll es aussehen: eine Seiten-Klasse')

    def test_browser_bausteine_zaehlen_nicht(self):
        """`new Date()` ist keine Wurzel eines Objektmodells. Beim ersten
        Lauf standen `Date`, `URLSearchParams` und `CustomEvent` in den
        Befunden."""
        satz = self._lauf({'seite.html': (
            '<script type="module">\n'
            '  const t = new Date();\n'
            '  const p = new URLSearchParams(location.search);\n'
            '  const e = new CustomEvent("x");\n'
            '</script>\n')}, ab='0')
        self.assertFalse(satz.befunde)

    def test_bausteine_sind_keine_seiten(self):
        """`_teil_*.html` wird von einer Seite eingebunden — es IST keine."""
        satz = self._lauf({'_teil_frigate.html': (
            '<script>const a = new Eins(1); const b = new Zwei(2);</script>'
        )}, ab='0')
        self.assertFalse(satz.befunde)

    def test_eine_vorlage_ohne_skript_wird_uebergangen(self):
        satz = self._lauf({'a.html': '<h1>Nur Text</h1>'}, ab='0')
        self.assertFalse(satz.befunde)

    def test_leeres_projekt_bleibt_still(self):
        satz = self._lauf({})
        self.assertFalse(satz.befunde)
        self.assertTrue(satz.kopf)


class DieSeiteRechnetIhrGewicht(BasisTest):

    def test_ohne_wartezeit_hinweis(self):
        self.assertEqual(Seite('a.html', [('X', 1), ('Y', 2)], 0).gewicht,
                         'hinweis')

    def test_mit_wartezeit_warnung(self):
        self.assertEqual(Seite('a.html', [('X', 1)], 2).gewicht, 'warnung')

    def test_die_grenze_ist_einstellbar(self):
        self.assertEqual(Seitenwurzeln.eingabe[2], '1')
