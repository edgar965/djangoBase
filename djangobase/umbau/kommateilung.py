# -*- coding: utf-8 -*-
"""Kommateilung — eine Deklarationsliste an den Kommas der obersten Ebene teilen.

WARUM (16.08.2026): `let a = 1, b = 2;` deklariert zwei Namen, und beide
Scanner splitten die Liste dafuer am Komma. Nur steht in

    const hSegs = Math.max(4, segments >> 1);

ebenfalls ein Komma — eines INNERHALB der Klammern. Naiv geteilt ergibt der
zweite Abschnitt ` segments >> 1)`, dessen fuehrender Name `segments` faelschlich
als deklariert gilt. Genau daran ist js_freie_namen.py an der Stelle
vorbeigelaufen, fuer die es gebaut wurde.

Hier wird nur geteilt, wo die Klammerbilanz null ist.
"""


class Kommateilung:
    """Teilt Text an Kommas, die nicht in Klammern stehen."""

    AUF = '([{'
    ZU = ')]}'

    @staticmethod
    def teile(text):
        abschnitte, tiefe, letzte = [], 0, 0
        for i, c in enumerate(text):
            if c in Kommateilung.AUF:
                tiefe += 1
            elif c in Kommateilung.ZU:
                tiefe -= 1
            elif c == ',' and tiefe == 0:
                abschnitte.append(text[letzte:i])
                letzte = i + 1
        abschnitte.append(text[letzte:])
        return abschnitte
