# -*- coding: utf-8 -*-
u"""`vorlagen-tags`: Ein umbrochenes ``{% … %}`` ist Text, kein Tag.

DER FALL (28.08.2026, 3DTools)
==============================
Fuenf Einstellungsseiten verloren gleichzeitig ihr Auswahlfeld fuer die
Standard-Animation - Status 200, keine Ausnahme, kein Logeintrag. Ursache war
ein der Lesbarkeit halber umbrochenes ``{% include %}``. Djangos Lexer kennt
kein ``DOTALL``; was ueber eine Zeilengrenze geht, ist fuer ihn Text.

ZWEI SEITEN, BEIDE WICHTIG
==========================
* Der echte Fall MUSS gemeldet werden - sonst faellt er wieder erst im
  Browser auf.
* Die Anleitung im ``{% comment %}``-Block darf NICHT gemeldet werden. Sie
  zeigt den Aufruf oft umbrochen, wirkt nie, und steht in jeder gut
  dokumentierten Vorlage. Ein Pruefer, der sie meldet, wird nach dem dritten
  Fehlalarm ignoriert.
"""
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.vorlagentags import Vorlagentags


ECHT = ('{% include "teil.html" with feld="a"\n'
        '   wert=b %}\n')

EINZEILIG = '{% include "teil.html" with feld="a" wert=b %}\n'

IM_KOMMENTAR = ('{% comment %}\nSo wird es aufgerufen:\n\n'
                '  {% include "teil.html" with feld="a"\n'
                '     wert=b %}\n{% endcomment %}\n'
                '{% include "teil.html" with feld="a" wert=b %}\n')

IM_VERBATIM = ('{% verbatim %}\n{% include "teil.html" with feld="a"\n'
               '   wert=b %}\n{% endverbatim %}\n')


class _Werkzeug(Vorlagentags):

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def wurzel(self):
        return self._ordner

    def pfade(self, muster="*.py", unter=None):
        return sorted(self._ordner.rglob(muster))

    def kurz(self, pfad):
        return Path(pfad).name


def _lauf(vorlagen):
    with tempfile.TemporaryDirectory(prefix="djb-vorlagentags-") as ordner:
        for name, inhalt in vorlagen.items():
            (Path(ordner) / name).write_text(inhalt, encoding="utf-8")
        return _Werkzeug(ordner).pruefen()


class FindetDenFallTest(SimpleTestCase):

    def test_umbrochenes_include_wird_gemeldet(self):
        satz = _lauf({"seite.html": ECHT})
        self.assertEqual(len(satz.befunde), 1, " | ".join(satz.kopf))
        self.assertIn("seite.html:1", satz.befunde[0].ort)

    def test_die_meldung_nennt_den_anfang_des_tags(self):
        u"""Ohne den Anfang muss man die Datei aufmachen, um zu wissen,
        welches der zwanzig Tags gemeint ist."""
        satz = _lauf({"seite.html": ECHT})
        self.assertIn('include "teil.html"', satz.befunde[0].was)

    def test_es_ist_ein_fehler_keine_anmerkung(self):
        from djangobase.skills.befund import Befund
        satz = _lauf({"seite.html": ECHT})
        self.assertEqual(satz.befunde[0].gewicht, Befund.FEHLER)


class KeineFehlalarmeTest(SimpleTestCase):

    def test_einzeiliges_tag_ist_in_ordnung(self):
        self.assertEqual(_lauf({"seite.html": EINZEILIG}).befunde, [])

    def test_anleitung_im_kommentarblock_zaehlt_nicht(self):
        satz = _lauf({"anleitung.html": IM_KOMMENTAR})
        self.assertEqual(satz.befunde, [],
                         "Fehlalarm: " + "; ".join(b.was for b in satz.befunde))

    def test_verbatim_zaehlt_nicht(self):
        self.assertEqual(_lauf({"beispiel.html": IM_VERBATIM}).befunde, [])

    def test_zeilennummer_stimmt_auch_nach_einem_kommentarblock(self):
        u"""Der Kommentar wird durch Leerzeichen ersetzt, NICHT geloescht —
        sonst zeigt jede Meldung dahinter auf die falsche Zeile."""
        satz = _lauf({"seite.html": IM_KOMMENTAR.replace(
            '{% include "teil.html" with feld="a" wert=b %}\n',
            '{% include "teil.html" with feld="a"\n   wert=b %}\n')})
        self.assertEqual(len(satz.befunde), 1)
        self.assertTrue(satz.befunde[0].ort.endswith(":7"),
                        satz.befunde[0].ort)


class KopfzeileTest(SimpleTestCase):

    def test_kopf_nennt_die_zahl_der_vorlagen(self):
        satz = _lauf({"a.html": EINZEILIG, "b.html": EINZEILIG})
        self.assertIn("2 Vorlagen", " ".join(satz.kopf))
