# -*- coding: utf-8 -*-
u"""Auch die Fixer müssen ihren eigenen Fall noch sehen.

DIE ANSAGE (Edgar, 25.08.2026)
==============================
    „mach alle die Verbesserungen"

DIE LÜCKE
=========
`anlassfall-check` lief über ``WERKZEUGE`` — und **nur** darüber. Die
sieben Fixer standen nicht in der Schleife, also genau die Werkzeuge, die
in Dateien **schreiben**. Von sieben hatte einer einen Anlassfall (und den
hatte ich einen Tag vorher selbst geschrieben).

Ein Fixer, der still aufhört seinen Fall zu finden, fällt niemandem auf:
Er meldet dann einfach „nichts zu tun", und das sieht aus wie ein sauberes
Projekt.

WAS DER ERSTE LAUF SOFORT FAND
==============================
    fix-ausnahme   im Anlassfall 32   im Leeren 32
    -> meldet im Leeren 32 — sucht nicht in der uebergebenen Wurzel

`FixAusnahme.pruefer()` baute sich sein Prüfwerk mit ``Protokoll()`` — mit
dessen EIGENER Wurzel, nicht der des Fixers. ``vorschau()`` durchsuchte
damit immer das ganze Projekt, gleichgültig worauf der Fixer gerichtet
war. Im gewöhnlichen Lauf fällt das nicht auf, weil beide Wurzeln dieselbe
sind — bei einem Werkzeug, das schreibt, ist es trotzdem der falsche
Zustand.
"""
from djangobase.skills import FIXER, WERKZEUGE

from ..base import BasisTest


class JederFixerHatSeinenFall(BasisTest):

    def test_keiner_ohne_anlassfall(self):
        ohne = [k.slug for k in FIXER if not getattr(k, 'anlassfall', None)]
        self.assertEqual(ohne, [], u'Fixer ohne Anlassfall: %s' % ohne)

    def test_jeder_fall_nennt_seinen_grund(self):
        u"""``warum`` steht im Bericht — ohne ihn ist der Fall eine
        Behauptung ohne Begründung."""
        for klasse in FIXER:
            fall = getattr(klasse, 'anlassfall', None)
            self.assertTrue(getattr(fall, 'warum', ''),
                            u'%s: Anlassfall ohne warum' % klasse.slug)

    def test_jeder_fall_bringt_dateien_mit(self):
        for klasse in FIXER:
            fall = getattr(klasse, 'anlassfall', None)
            self.assertTrue(getattr(fall, 'dateien', None),
                            u'%s: Anlassfall ohne Dateien' % klasse.slug)


class DerSammellaufSiehtSieAuch(BasisTest):

    def test_der_check_geht_ueber_werkzeuge_UND_fixer(self):
        u"""Die Schleife stand nur auf ``WERKZEUGE``."""
        import inspect

        from djangobase.skills.anlassfall_check import AnlassfallCheck
        quelle = inspect.getsource(AnlassfallCheck.laufen)
        self.assertIn('FIXER', quelle)
        self.assertIn('WERKZEUGE', quelle)

    def test_ein_fixer_meldet_ueber_vorschau_nicht_ueber_laufen(self):
        u"""Ein Fixer hat kein ``laufen()`` — dieselbe Bauart-Falle, die
        vorher schon den Läufer `tools/wartung/pruefen.py` abstürzen ließ
        (``'Altlast' object has no attribute 'pruefen'``)."""
        einer = FIXER[0]()
        self.assertTrue(hasattr(einer, 'vorschau'))
        self.assertFalse(hasattr(einer, 'laufen'))

    def test_der_probelauf_schreibt_nicht(self):
        u"""Ein Selbsttest, der Dateien ändert, ist kein Selbsttest mehr.

        Geprüft wird der RUMPF, nicht der Text: Im Docstring steht „nie
        ``anwenden()``" — eine Wortsuche über die Quelle schlug daran an
        und meldete das Gegenteil dessen, was der Fall ist.
        """
        import ast
        import inspect
        import textwrap

        from djangobase.skills.anlassfall_check import Probelauf
        baum = ast.parse(textwrap.dedent(
            inspect.getsource(Probelauf._fixerlauf)))
        gerufen = {k.func.attr for k in ast.walk(baum)
                   if isinstance(k, ast.Call)
                   and isinstance(k.func, ast.Attribute)}
        self.assertIn('vorschau', gerufen)
        self.assertNotIn('anwenden', gerufen)


class KeineKennungZweimal(BasisTest):
    u"""`tote-importe` war bis zum 25.08.2026 doppelt vergeben.

    Einmal als Prüfwerkzeug (``ToteImporte``), einmal als Fixer
    (``ImportFixer``). Folgen:

      * `werkzeug_finden("tote-importe")` war mehrdeutig,
      * der Werkzeugkatalog druckte zwei Zeilen mit demselben Namen,
      * und `anlassfall-check` legt sein Prüfverzeichnis nach dem Slug an
        — beide hätten in denselben Ordner geschrieben.
    """

    def test_jede_kennung_gehoert_einem(self):
        from collections import Counter
        alle = [w.slug for w in WERKZEUGE] + [k.slug for k in FIXER]
        doppelt = [s for s, n in Counter(alle).items() if n > 1]
        self.assertEqual(doppelt, [], u'doppelt vergeben: %s' % doppelt)

    def test_der_import_fixer_heisst_wie_seine_datei(self):
        from djangobase.skills.fix_importe import ImportFixer
        self.assertEqual(ImportFixer.slug, 'fix-importe')

    def test_das_pruefwerkzeug_behaelt_seine_kennung(self):
        u"""Auf `tote-importe` verweisen Texte und Prüfungen — die Kennung
        des PRÜFWERKZEUGS durfte sich nicht ändern."""
        from djangobase.skills.toteimporte import ToteImporte
        self.assertEqual(ToteImporte.slug, 'tote-importe')
