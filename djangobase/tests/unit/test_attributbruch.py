# -*- coding: utf-8 -*-
u"""Kein Anführungszeichen mitten in einem HTML-Attribut.

DER FUND (30.08.2026)
=====================
In ``testtabelle.py`` stand das deutsche SCHLUSSzeichen als ASCII-``"`` — mitten
in einem ``title``:

    title="… Ein-/ausblenden über … → „djangoBase-Testcases sichtbar".">

Der Parser beendet das Attribut bei ``sichtbar"``, liest ``.`` und ``"`` als
Anfang eines neuen Attributnamens und wirft den Rest weg. Im Browser stand dann
``<span class="…" title="… sichtbar" ."="">`` — das Element sitzt richtig, hat
die richtige Farbe, und der Tooltip zeigt die halbe Erklärung. Nichts daran
sieht nach einem Fehler aus.

Dasselbe zweimal in ``hilfe/review.html`` (Platzhalter der beiden Eingabefelder):

    placeholder="Bei „Einfache Frage" Pflicht. Bei den Dialog-Arten optional …"
    placeholder="… „Gegenprobe ergab X. Zieh zurück oder liefere einen Fall.""

Dort war der sichtbare Teil ``Bei „Einfache Frage`` — der Satz, der erklärt,
wann das Feld Pflicht ist, kam nie an.

WARUM ES GERADE HIER PASSIERT
=============================
Die Regel für deutsche Texte verlangt echte Anführungszeichen (``„…"``). Das
ÖFFNENDE ``„`` tippt man bewusst, das SCHLIESSENDE gerät leicht zum ASCII-``"``
— und genau dieses eine Zeichen ist im HTML das Ende des Attributs. Der Fehler
entsteht also aus dem Befolgen einer Regel, nicht aus Schlamperei.

WAS GEPRÜFT WIRD
================
Die Vorlagen und die HTML-bauenden Zeichenketten von djangoBase SELBST. Die
Konformitätsprüfungen (``tests/konform``) nehmen das Paket ausdrücklich aus —
sie prüfen die Konsumenten. Diese beiden Fälle hätte dort also niemand gesehen.

Geprüft wird mit dem Parser, nicht mit einem regulären Ausdruck: Ob ein Zeichen
ein Attribut aufbricht, entscheidet die Zustandsmaschine des Parsers, und die
kennt Fälle (unquotierte Werte, ``/`` vor ``>``), die ein Muster nicht trifft.
"""
import ast
import re
from html.parser import HTMLParser
from pathlib import Path

from django.test import SimpleTestCase

#: Wurzel des Pakets — geprüft wird djangoBase selbst.
PAKET = Path(__file__).resolve().parents[2]

#: Ein Attributname darf kein Anführungszeichen, keine spitze Klammer, keinen
#: Schrägstrich und kein Gleichheitszeichen enthalten. Steht dort eines davon —
#: oder beginnt der Name mit einem Satzzeichen —, ist davor ein Attribut
#: ungewollt zu Ende gegangen.
KAPUTT = re.compile(r"[\"'<>/=]|^[.,;:!?)]")

#: Vorlagen-Anweisungen stören den Parser. ``{% … %}`` fällt weg, ``{{ … }}``
#: wird zu einem harmlosen Platzhalter — sonst hielte der Parser ``{{`` und
#: ``}}`` für Attributnamen und meldete jede Vorlage.
_TAG = re.compile(r"{%.*?%}", re.S)
_VAR = re.compile(r"{{.*?}}", re.S)
#: KOMMENTARBLÖCKE SAMT INHALT. In ihnen steht Dokumentation — in
#: ``_nav_eintrag.html`` zum Beispiel ein Python-Wörterbuch als Beispiel. Nur
#: die Marken zu entfernen und den Inhalt stehen zu lassen ergab dort auf einen
#: Schlag vierzehn Fehlalarme (``<div {'label':=…>``).
_KOMMENTAR = re.compile(r"{%\s*comment.*?{%\s*endcomment\s*%}|{#.*?#}", re.S)

#: Die eigenen Testdateien. Sie führen den kaputten Fall ABSICHTLICH — der Fall
#: ``test_die_pruefung_findet_den_echten_fall`` besteht daraus. Ein Prüfer, der
#: seine eigene Gegenprobe anmeckert, ist eine Fehlalarm-Maschine
#: (Regel ``analysewerkzeuge``). Gerendert wird aus Tests ohnehin nichts.
_AUSSEN = ("tests",)


class _Sucher(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.befunde = []

    def handle_starttag(self, tag, attrs):
        for name, _wert in attrs:
            if KAPUTT.search(name or ""):
                self.befunde.append((self.getpos()[0], tag, name))


def _pruefen(text):
    u"""[(Zeile, Tag, Attributname)] der aufgebrochenen Attribute."""
    s = _Sucher()
    try:
        s.feed(text)
        s.close()
    except Exception:                                            # noqa: BLE001
        # Ein Fragment, das der Parser nicht zu Ende lesen kann, ist kein
        # Befund dieser Prüfung — es fehlt einfach der Rest der Datei.
        pass
    return s.befunde


def _dateien(endung):
    for p in sorted(PAKET.rglob("*" + endung)):
        teile = set(p.parts)
        if teile & {"__pycache__", "node_modules"} or teile & set(_AUSSEN):
            continue
        yield p


def _html_zeichenketten(quelle):
    u"""Alle Zeichenketten-Konstanten, die nach HTML mit Attributen aussehen.

    ``ast`` führt aneinandergereihte Literale (``'a' 'b'``) schon zu EINER
    Konstante zusammen — genau die Schreibweise, in der die Fragmente hier
    stehen. Die ``%s``-Platzhalter darin stören den Parser nicht.
    """
    try:
        baum = ast.parse(quelle)
    except SyntaxError:
        return
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
            wert = knoten.value
            if "<" in wert and '="' in wert:
                yield knoten.lineno, wert


class AttributbruchTest(SimpleTestCase):
    u"""Kein Attribut endet mitten im Satz."""

    #: Ohne Datenbank — die Prüfung liest Dateien (Regel
    #: ``testlauf-blockiert-server``).
    databases = []

    def _melden(self, funde):
        return "\n".join(
            "%s:%d  <%s %s=…>  — hier endet das Attribut zu früh"
            % (datei, zeile, tag, name) for datei, zeile, tag, name in funde)

    def test_vorlagen_haben_heile_attribute(self):
        funde = []
        for p in _dateien(".html"):
            roh = p.read_text(encoding="utf-8", errors="replace")
            text = _VAR.sub("x", _TAG.sub("", _KOMMENTAR.sub("", roh)))
            for zeile, tag, name in _pruefen(text):
                funde.append((p.relative_to(PAKET), zeile, tag, name))
        self.assertEqual(funde, [], "\n" + self._melden(funde))

    def test_html_aus_python_hat_heile_attribute(self):
        funde = []
        for p in _dateien(".py"):
            quelle = p.read_text(encoding="utf-8", errors="replace")
            for zeile, wert in _html_zeichenketten(quelle):
                for _z, tag, name in _pruefen(wert):
                    funde.append((p.relative_to(PAKET), zeile, tag, name))
        self.assertEqual(funde, [], "\n" + self._melden(funde))

    def test_die_pruefung_findet_den_echten_fall(self):
        u"""Gegenprobe mit genau dem Text, der am 30.08.2026 im Code stand."""
        kaputt = ('<span class="ts-kat-fest" title="Ein-/ausblenden über '
                  'Einstellungen → „djangoBase-Testcases sichtbar".">'
                  'DjangoBase</span>')
        self.assertTrue(_pruefen(kaputt), "der bekannte Fall bleibt unbemerkt")

        heil = kaputt.replace('sichtbar".', 'sichtbar“.')
        self.assertEqual(_pruefen(heil), [],
                         "mit typografischem Schlusszeichen ist nichts zu melden")

    def test_platzhalter_und_vorlagen_sind_kein_befund(self):
        u"""Kein Fehlalarm auf dem, was normal in diesen Dateien steht."""
        for heil in (
                '<a href="?run=%s" title="Diesen Test ausführen">Run</a>',
                '<input type="checkbox" value="%s" aria-label="auswählen">',
                '<td class="num" data-sort="0.379">379 ms</td>',
                '<span title="17.08.2026 22:33:24">17.08. 22:33 · 379 ms</span>',
                "<img src='x.png' alt='Bild'>",
                '<br/><hr />',
        ):
            self.assertEqual(_pruefen(heil), [], heil)
