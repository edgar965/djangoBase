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

ZWEI SCANNER WAREN ES — UND SIE WIDERSPRACHEN SICH
==================================================
Bis zum 29.08.2026 hatte `Codesicht` zwei getrennt ausgeschriebene Scanner
für dieselben Regeln: `_nichtcode` für `maske` und `_durchlauf` für `.code`.
Beim Schreiben dieser Tests kam heraus, dass sie nicht nur doppelt waren,
sondern verschiedene Antworten gaben:

    quelle : const s = `Wert: ${an ? 'fn.geheim' : 'Aus'} Ende`;
    maske  : const s =          an ? 'fn.geheim' : 'Aus'       ;
    code   : const s =  an ? '' : '' ;

`maske` ließ die Zeichenketten INNERHALB einer Vorlagen-Einsetzung stehen.
Wer mit ihr nach `fn.X` sucht — und genau dafür ist sie da — findet dort
einen Treffer, den es nicht gibt.

Jetzt liefert EIN Scanner (`_teile`) typisierte Bereiche; `maske` leert sie,
`.code` setzt je Art ihren Platzhalter. Eine Regel, zwei Sichten. Deshalb
prüft hier jeder Fall BEIDE Wege — sie können nicht mehr auseinanderlaufen,
aber sie können weiterhin verschieden falsch sein.

WARUM DIESE TESTS ERST JETZT ENTSTEHEN (29.08.2026)
===================================================
`_durchlauf` war ein handgeschriebener Scanner mit Rang C — der einzige
verbliebene „Echte Fehler" von `code-qualitaet` in djangoBase. Bevor man
einen Scanner umbaut, braucht man Fälle, die den Umbau bewachen.

DER ERSTE ANLAUF HAT DEN FALSCHEN BEWACHT: Er prüfte nur `maske` — und die
benutzte `_durchlauf` gar nicht. Zwei Sabotagen am umgebauten Scanner blieben
deshalb grün. Auch der Fingerabdruck über 389 echte JS-Dateien, mit dem der
Umbau belegt schien, war über den falschen Weg genommen.

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

#: Zeilenumbruch und Einsetzungsbeginn als Namen — so bleiben die
#: Zusicherungen unten lesbar und die Datei frei von Escapes.
NL = chr(10)
EIN = chr(36) + chr(123)


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

    def test_zeichenkette_in_einer_einsetzung_verschwindet_auch(self):
        u"""DER Widerspruch, an dem die Zusammenlegung haengt: Bis zum
        29.08.2026 liess `maske` genau diese Zeichenkette stehen, waehrend
        `.code` sie leerte. Ein Werkzeug, das hier nach `fn.X` sucht, fand
        einen Treffer, den es nicht gibt."""
        quelle = "const s = `Wert: ${an ? 'fn.geheim' : 'Aus'} Ende`;\n"
        maske = Codesicht.maske(quelle)
        self.assertNotIn('geheim', maske)
        self.assertIn('an ?', maske)          # der Code drumherum bleibt
        self.assertNotIn('geheim', Codesicht(quelle).code)

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
    u"""Derselbe Stoff über `Codesicht(quelle).code` — die zweite SICHT.

    Sie verdichtet, statt zu leeren: Eine Zeichenkette wird zu ihren beiden
    Anführungszeichen, ein Zeilenkommentar verschwindet ganz. Die Länge
    bleibt also NICHT erhalten — dafür gibt es `maske`.

    Seit dem 29.08.2026 kommen beide aus demselben Scanner; die Fälle hier
    unterscheiden sich von denen oben nur noch im Platzhalter.
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

    def test_die_platzhalter_stehen_fest(self):
        u"""Die genaue Form ist Vertrag, nicht Geschmack.

        Zwei Werkzeuge lesen `.code` mit regulären Ausdrücken
        (`exportlisten`, `unbekanntenamen`). Ob an der Stelle eines
        Kommentars nichts oder ein Leerzeichen steht, entscheidet darüber,
        ob zwei Namen zusammenkleben. Ohne diesen Fall bleibt eine Änderung
        daran unbemerkt — nachgestellt am 29.08.2026: Platzhalter vertauscht,
        alle anderen Fälle blieben grün.
        """
        self.assertEqual(self._code('a = 1; // weg' + NL + 'b = 2;' + NL),
                         'a = 1; ' + NL + 'b = 2;' + NL)
        self.assertEqual(self._code('a = /* weg */ 1;' + NL),
                         'a =   1;' + NL)
        self.assertEqual(self._code('a = /re/g;' + NL), 'a =  ;' + NL)
        self.assertEqual(self._code('a = `x' + EIN + 'b}y`;' + NL),
                         'a =  b ;' + NL)

    def test_leere_quelle(self):
        self.assertEqual(self._code(''), '')
