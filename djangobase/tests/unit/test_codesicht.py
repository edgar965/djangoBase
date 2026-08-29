# -*- coding: utf-8 -*-
u"""`Codesicht.maske`: JavaScript ohne Zeichenketten, Kommentare und Regexe.

WOZU DIESE MASKE
================
Mehrere Werkzeuge suchen in JavaScript nach Mustern — `fn.x = …`,
`class X extends Y`, `console.log(`. Wer das im ROHEN Text tut, findet sie
auch dort, wo sie nichts bedeuten: in einer Zeichenkette, in einem
auskommentierten Block, in einem regulären Ausdruck. `Codesicht.maske`
ersetzt genau diese Bereiche durch Leerraum und lässt die Zeilen- und
Spaltenzahlen stehen.

ZWEI SCANNER FÜR DIESELBEN REGELN
=================================
`Codesicht` hat davon ZWEI, und das ist beim Schreiben dieser Tests
aufgefallen:

    maske(s)   -> `_nichtcode`  liefert BEREICHE, die geleert werden;
                                die Länge bleibt, Zeilen stimmen weiter
    Codesicht(s).code -> `_durchlauf`  baut den Text neu, verdichtet

Beide kennen dieselben Regeln (`VOR_REGEX`, Escape, Vorlagen) und haben sie
getrennt ausgeschrieben. Wer eine Regel ändert, muss es zweimal tun.

WARUM DIESE TESTS ERST JETZT ENTSTEHEN (29.08.2026)
===================================================
`_durchlauf` ist ein handgeschriebener Scanner mit Rang C — der einzige
verbliebene „Echte Fehler" von `code-qualitaet` in djangoBase. Bevor man
einen Scanner umbaut, braucht man Fälle, die den Umbau bewachen.

DER ERSTE ANLAUF HAT DEN FALSCHEN BEWACHT: Er prüfte nur `maske` — und die
benutzt `_durchlauf` nicht. Zwei Sabotagen am umgebauten Scanner blieben
deshalb grün. Seither prüft jeder Fall BEIDE Wege.

DIE FÄLLE, DIE WEHTUN
=====================
* **Ein Schrägstrich ist zweideutig.** `a / b` ist eine Division, `/ab+/g`
  ein regulärer Ausdruck. Der Scanner entscheidet am letzten
  bedeutungstragenden Zeichen davor — und `)` gehört auf die Divisions-Seite
  (`(a+b) / 2`), obwohl danach durchaus ein Regex stehen könnte.
* **Zeichenketten mit Escape.** `'a\\'b'` endet NICHT am mittleren
  Anführungszeichen.
* **Vorlagen (Backticks)** dürfen ihre `${…}`-Einsetzungen behalten: Darin
  steht echter Code, den die Werkzeuge sehen sollen.
* **Die Zeilenzahl muss stimmen.** Ein Werkzeug meldet `datei.js:42`; wenn
  die Maske Zeilen schluckt, zeigt jeder Befund auf die falsche Stelle.
"""
from django.test import SimpleTestCase

from djangobase.umbau.codesicht import Codesicht


class MaskeTest(SimpleTestCase):

    def test_zeilenzahl_bleibt(self):
        u"""Ohne das zeigt jeder Befund auf die falsche Zeile."""
        quelle = ('const a = 1;\n'
                  '// ein Kommentar\n'
                  '/* mehrzeilig\n'
                  '   geht weiter */\n'
                  'const b = "text";\n')
        self.assertEqual(Codesicht.maske(quelle).count('\n'),
                         quelle.count('\n'))

    def test_zeichenkette_verschwindet(self):
        maske = Codesicht.maske('const a = "fn.geheim = 1";\n')
        self.assertNotIn('geheim', maske)
        self.assertIn('const a =', maske)

    def test_escape_beendet_die_zeichenkette_nicht(self):
        u"""`'a\\'b'` endet nicht am mittleren Anführungszeichen."""
        maske = Codesicht.maske("const a = 'x\\'geheim';\nconst b = 2;\n")
        self.assertNotIn('geheim', maske)
        self.assertIn('const b = 2;', maske)

    def test_zeilenkommentar_verschwindet(self):
        maske = Codesicht.maske('const a = 1; // fn.geheim = 1\n')
        self.assertNotIn('geheim', maske)
        self.assertIn('const a = 1;', maske)

    def test_blockkommentar_verschwindet(self):
        maske = Codesicht.maske('/* fn.geheim = 1 */\nconst a = 1;\n')
        self.assertNotIn('geheim', maske)
        self.assertIn('const a = 1;', maske)

    def test_regex_verschwindet(self):
        u"""Ein regulärer Ausdruck kann wie Code aussehen."""
        maske = Codesicht.maske('const r = /fn\\.geheim/g;\nconst a = 1;\n')
        self.assertNotIn('geheim', maske)
        self.assertIn('const a = 1;', maske)

    def test_division_ist_kein_regex(self):
        u"""DIE zweideutige Stelle: `(a+b) / 2` ist eine Division. Wer sie
        für einen Regex hält, frisst den Rest der Zeile."""
        maske = Codesicht.maske('const m = (a + b) / 2;\nfn.sichtbar = 1;\n')
        self.assertIn('fn.sichtbar = 1;', maske)

    def test_vorlage_behaelt_ihre_einsetzungen(self):
        u"""In `${…}` steht echter Code — den sollen die Werkzeuge sehen."""
        maske = Codesicht.maske('const s = `Text ${fn.sichtbar} Ende`;\n')
        self.assertIn('fn.sichtbar', maske)
        self.assertNotIn('Ende', maske)

    def test_zeichenkette_mit_schraegstrich(self):
        maske = Codesicht.maske('const p = "/api/geheim/";\nconst a = 1;\n')
        self.assertNotIn('geheim', maske)
        self.assertIn('const a = 1;', maske)

    def test_kommentarzeichen_in_einer_zeichenkette(self):
        u"""`"// kein Kommentar"` ist Text, kein Kommentar — und der Code
        dahinter muss stehen bleiben."""
        maske = Codesicht.maske('const s = "// kein Kommentar";\n'
                                'fn.sichtbar = 1;\n')
        self.assertIn('fn.sichtbar = 1;', maske)

    def test_leere_quelle(self):
        self.assertEqual(Codesicht.maske(''), '')


class CodeTest(SimpleTestCase):
    u"""Derselbe Stoff, aber über `Codesicht(quelle).code` — den ZWEITEN
    Scanner (`_durchlauf`).

    Er verdichtet statt zu leeren: Eine Zeichenkette wird zu ihren beiden
    Anführungszeichen, ein Kommentar verschwindet ganz. Die Länge bleibt
    also NICHT erhalten — dafür gibt es `maske`.
    """

    @staticmethod
    def _code(quelle):
        return Codesicht(quelle).code

    def test_zeichenkette_wird_zu_zwei_zeichen(self):
        self.assertEqual(self._code('const a = "geheim";\n'),
                         'const a = "";\n')

    def test_escape_beendet_die_zeichenkette_nicht(self):
        code = self._code("const a = 'x\\'geheim';\nconst b = 2;\n")
        self.assertNotIn('geheim', code)
        self.assertIn('const b = 2;', code)

    def test_zeilenkommentar_verschwindet(self):
        u"""DIE Stelle, an der die Reihenfolge der Fresser zählt: Wer den
        Regex-Fresser zuerst fragt, frisst `//` als leeren Ausdruck und
        lässt den Kommentartext als Code stehen."""
        code = self._code('const a = 1; // fn.geheim = 1\nconst b = 2;\n')
        self.assertNotIn('geheim', code)
        self.assertIn('const b = 2;', code)

    def test_blockkommentar_verschwindet(self):
        code = self._code('/* fn.geheim = 1 */\nconst a = 1;\n')
        self.assertNotIn('geheim', code)
        self.assertIn('const a = 1;', code)

    def test_regex_verschwindet(self):
        code = self._code('const r = /fn\\.geheim/g;\nconst a = 1;\n')
        self.assertNotIn('geheim', code)
        self.assertIn('const a = 1;', code)

    def test_division_ist_kein_regex(self):
        u"""`a / b / c` — ohne die Wache am letzten Zeichen frisst der
        Scanner `b` als regulären Ausdruck."""
        code = self._code('const m = a / bbb / c;\n')
        self.assertIn('bbb', code)

    def test_vorlage_behaelt_ihre_einsetzungen(self):
        code = self._code('const s = `Text ${fn.sichtbar} Ende`;\n')
        self.assertIn('fn.sichtbar', code)
        self.assertNotIn('Ende', code)

    def test_kommentarzeichen_in_einer_zeichenkette(self):
        code = self._code('const s = "// kein Kommentar";\n'
                          'fn.sichtbar = 1;\n')
        self.assertIn('fn.sichtbar = 1;', code)

    def test_leere_quelle(self):
        self.assertEqual(self._code(''), '')
