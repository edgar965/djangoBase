# -*- coding: utf-8 -*-
u"""`doppelcode` meldet keine reinen Importbloecke mehr.

DER FEHLALARM (27.08.2026, 3DTools)
===================================
Vier Module bekamen eine Warnung fuer diesen Block::

    import json
    import logging
    import os
    import re

    from django.conf import settings

Er IST in allen vier gleich — und muss es sein. Wer `json` braucht, importiert
`json`; zusammenfassen laesst sich daran nichts. Von 187 gemeldeten Stellen
waren 20 von dieser Sorte, und sie standen ganz oben, weil sie in den meisten
Dateien vorkommen.

WAS HIER GEPRUEFT WIRD
======================
Beide Richtungen: Der Fehlalarm muss weg sein UND echter doppelter Code muss
bleiben — auch dann, wenn er mit Importen ANFAENGT.
"""

import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.doppelcode import Doppelcode

NUR_IMPORTE = '''import json
import logging
import os
import re

from django.conf import settings
from django.http import JsonResponse
'''

ECHTER_CODE = '''def preis_pruefen(betrag):
    if betrag < 0:
        raise ValueError('negativ')
    if betrag > 1000:
        raise ValueError('zu gross')
    return round(betrag, 2)
'''


class _Werkzeug(Doppelcode):
    u"""Ein `Doppelcode`, der in einem Wegwerf-Verzeichnis sucht."""

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def projektdateien(self, endung='.py', **_weitere):
        u"""Nur die Dateien DIESER Endung.

        Bis zum 28.08.2026 lieferte der Helfer immer alle `.py`-Dateien,
        egal wonach gefragt wurde — und das dreimal, weil `Doppelcode` je
        Endung einmal fragt. Ein `.js`-Fall waere hier stumm durchgelaufen
        („0 Dateien geprueft"), und der Test haette nichts gemessen.
        """
        return sorted(self._ordner.rglob('*' + endung))

    def kurz(self, datei):
        return Path(datei).name


def _lauf(dateien):
    with tempfile.TemporaryDirectory() as ordner:
        for name, inhalt in dateien.items():
            (Path(ordner) / name).write_text(inhalt, encoding='utf-8')
        return _Werkzeug(ordner).pruefen()


class ImportbloeckeTest(SimpleTestCase):

    def test_gleiche_importbloecke_sind_kein_befund(self):
        ergebnis = _lauf({'eins.py': NUR_IMPORTE, 'zwei.py': NUR_IMPORTE})
        self.assertEqual(ergebnis.befunde, [],
                         'ein Importblock laesst sich nicht zusammenfassen')

    def test_die_zahl_steht_in_der_kopfzeile(self):
        u"""Eine Ausnahme, die niemand sieht, ist eine Hintertuer."""
        ergebnis = _lauf({'eins.py': NUR_IMPORTE, 'zwei.py': NUR_IMPORTE})
        text = ' '.join(' '.join(ergebnis.kopf).split())
        self.assertIn('reine Importbloecke', text)

    def test_echter_doppelter_code_bleibt_ein_befund(self):
        u"""DIE GEGENPROBE: Der Waechter muss weiter anschlagen."""
        ergebnis = _lauf({'eins.py': ECHTER_CODE, 'zwei.py': ECHTER_CODE})
        self.assertEqual(len(ergebnis.befunde), 1, ' | '.join(ergebnis.kopf))

    def test_importe_PLUS_code_bleiben_ein_befund(self):
        u"""Streng gezaehlt: Nur ein Fenster, das NUR Importe enthaelt, faellt raus."""
        gemischt = 'import os\nimport re\n' + ECHTER_CODE
        ergebnis = _lauf({'eins.py': gemischt, 'zwei.py': gemischt})
        self.assertGreaterEqual(len(ergebnis.befunde), 1,
                                ' | '.join(ergebnis.kopf))


class ImportblockMitKommentarkopfTest(SimpleTestCase):
    u"""Importe PLUS die oeffnende Zeile des Modulkopfs (28.08.2026).

    Drei Module im BVH-Studio (3DTools) bekamen eine Warnung fuer genau das:
    fuenf gleiche Importzeilen, dann `/**`. Die Ausnahme griff um EINE Zeile
    nicht weit genug — und ein Befund, der nichts zu tun gibt, verdeckt die,
    die etwas zu tun geben.
    """

    KOPF = ("import { state } from './state.js';\n"
            "import { fn } from '../gemeinsam/registrierung.js';\n"
            "import { Clip } from './models.js';\n"
            "import { pushUndo } from './undo.js';\n"
            "import { Protokoll } from '../gemeinsam/protokoll.js';\n"
            "\n"
            "/**\n"
            " * Was dieses Modul macht.\n"
            " */\n")

    def test_gleiche_importe_und_kommentaranfang_sind_kein_befund(self):
        satz = _lauf({'a.js': self.KOPF + 'export function eins() { return 1; }\n',
                      'b.js': self.KOPF + 'export function zwei() { return 2; }\n'})
        self.assertEqual(satz.befunde, [],
                         'Fehlalarm: ' + '; '.join(b.was for b in satz.befunde))

    def test_die_ausnahme_sagt_wie_viel_sie_schluckt(self):
        u"""Eine Ausnahme, die schweigt, ist ein blinder Fleck."""
        satz = _lauf({'a.js': self.KOPF + 'export function eins() { return 1; }\n',
                      'b.js': self.KOPF + 'export function zwei() { return 2; }\n'})
        self.assertIn('Importbl', ' '.join(satz.kopf))

    def test_echter_code_hinter_den_importen_bleibt_ein_befund(self):
        u"""Gegenprobe: Die Ausnahme darf nicht anfangen, Code zu schlucken."""
        rumpf = ('const a = 1;\nconst b = 2;\nconst c = 3;\n'
                 'const d = 4;\nconst e = 5;\nconst f = 6;\n')
        satz = _lauf({'a.js': self.KOPF + rumpf, 'b.js': self.KOPF + rumpf})
        self.assertTrue(satz.befunde, 'echte Dublette nicht mehr gefunden')


class DocstringBlockTest(SimpleTestCase):
    u"""Ein wiederholter DOCSTRING ist kein wiederholter Code (29.08.2026).

    In 3DTools erklären vier Modellklassen in vier Dateien mit demselben
    Absatz, woher sie kommen — und das ist richtig so: Jede Datei soll für
    sich sprechen. Ein Befund, der verlangt, Dokumentation zusammenzufassen,
    gibt nichts zu tun.

    DER MODULKOPF IST BEIDES, und daran ist der erste Wurf gescheitert: vier
    Zeilen Erklärung, die schließenden Anführungszeichen, dann `import uuid`.
    Getrennt gefragt („nur Importe?" ODER „nur Docstring?") ist kein Fenster
    darüber rein das eine oder das andere.
    """

    KOPF = ('# -*- coding: utf-8 -*-\n'
            '"""Ein Modell dieser Anwendung.\n'
            '\n'
            'Aus models.py herausgeloest (Umbau 16.08.2026). Die Datei hatte\n'
            '383 Zeilen mit vier Modellklassen; die Regel im Projekt ist eine\n'
            'Klasse je Datei. Django findet die Modelle weiter ueber\n'
            'models/__init__.py — Migrationen bleiben unveraendert.\n'
            '"""\n'
            '\n'
            'import uuid\n'
            '\n'
            'from django.db import models\n'
            '\n'
            '\n')

    def test_gleicher_modulkopf_ist_kein_befund(self):
        satz = _lauf({'auftrag.py': self.KOPF + 'class Auftrag:\n    a = 1\n',
                      'datei.py': self.KOPF + 'class Datei:\n    b = 2\n'})
        self.assertEqual(satz.befunde, [],
                         'Fehlalarm: ' + '; '.join(b.was for b in satz.befunde))

    def test_die_ausnahme_sagt_wie_viel_sie_schluckt(self):
        satz = _lauf({'auftrag.py': self.KOPF + 'class Auftrag:\n    a = 1\n',
                      'datei.py': self.KOPF + 'class Datei:\n    b = 2\n'})
        self.assertIn('Docstring', ' '.join(satz.kopf))

    def test_echter_code_hinter_dem_kopf_bleibt_ein_befund(self):
        u"""Gegenprobe: Die Ausnahme darf nicht anfangen, Code zu schlucken."""
        rumpf = ('class X:\n    def m(self):\n        a = 1\n'
                 '        b = 2\n        c = 3\n        return a + b + c\n')
        satz = _lauf({'auftrag.py': self.KOPF + rumpf,
                      'datei.py': self.KOPF + rumpf})
        self.assertTrue(satz.befunde, 'echte Dublette nicht mehr gefunden')

    def test_eine_zeichenkette_mitten_im_code_ist_kein_docstring(self):
        u"""`ast` weiß den Unterschied — ein Muster wüsste ihn nicht."""
        rumpf = ('def eins():\n'
                 '    text = """Vier gleiche Zeilen\n'
                 '    stehen hier als WERT,\n'
                 '    nicht als Docstring \u2014 und\n'
                 '    zaehlen deshalb mit."""\n'
                 '    return text\n')
        satz = _lauf({'a.py': rumpf, 'b.py': rumpf})
        self.assertTrue(satz.befunde,
                        'Zeichenkette im Code faelschlich als Docstring geschluckt')


class NurSchliessendesMarkupTest(SimpleTestCase):
    u"""Fenster, die nur zumachen (31.08.2026, assistant).

    Jede Tabelle im Projekt endet gleich::

        </td>
        </tr>
        {% endfor %}
        </tbody>
        </table>
        </div>

    Sechs Zeilen, in dieser Reihenfolge, in jeder Vorlage mit einer
    Tabelle — und nichts davon laesst sich zusammenfassen. Solche
    Fenster stellten acht der damals 53 HTML-Befunde und gaben nichts
    zu tun.
    """

    NUR_ZU = ('                    </td>\n'
              '                </tr>\n'
              '                {% endfor %}\n'
              '            </tbody>\n'
              '        </table>\n'
              '    </div>\n')

    def test_ein_reines_tabellenende_ist_kein_befund(self):
        satz = _lauf({'a.html': self.NUR_ZU, 'b.html': self.NUR_ZU})
        self.assertEqual(satz.befunde, [], ' | '.join(satz.kopf))

    def test_die_zahl_steht_in_der_kopfzeile(self):
        u"""Eine Ausnahme, die niemand sieht, ist eine Hintertuer."""
        satz = _lauf({'a.html': self.NUR_ZU, 'b.html': self.NUR_ZU})
        self.assertIn('schliessen nur Markup',
                      ' '.join(' '.join(satz.kopf).split()))

    def test_eine_einzige_inhaltszeile_macht_es_zum_befund(self):
        u"""DIE GEGENPROBE: streng gezaehlt, nicht ungefaehr.

        Steht im Fenster auch nur EINE Zeile, die etwas sagt, ist es
        wieder ein Befund — dort gaebe es etwas zu teilen.
        """
        gemischt = ('                    <td>{{ zeile.summe }}</td>\n'
                    + self.NUR_ZU)
        satz = _lauf({'a.html': gemischt, 'b.html': gemischt})
        self.assertTrue(satz.befunde, ' | '.join(satz.kopf))
