# -*- coding: utf-8 -*-
u"""Was `klassen-kandidat` melden soll — und was nicht.

DER FALL (30.08.2026, 3DTools)
==============================
Gemeldet wurde `core/templatetags/einstellungszeile.py`:

    Kontext-Klasse: Instanz "register" liegt frei, 2 Funktionen benutzen
    sie (zahl, kaestchen) — sie gehört in die EINE Kontext-Klasse des
    Projekts.

Dem Vorschlag zu folgen hätte das Modul zerstört. `register =
template.Library()` ist Djangos PFLICHTNAME: `import_library` sucht im
Modul das Attribut `register` und wirft `InvalidTemplateLibrary`, wenn es
fehlt — jede Seite mit `{% load %}` wäre danach tot. Es ist derselbe Fall
wie `Command` bei Management-Commands: ein Name, den nicht der Autor
vergibt, sondern das Rahmenwerk. Und es ist die teuerste Sorte Fehlalarm,
weil er wie Fortschritt aussieht.

Erkannt wird es AM GEBRAUCH, nicht am Ordnernamen: Wer als Dekorator
dient, sammelt Funktionen für ein Rahmenwerk ein. Eine Ordnerliste
(`templatetags/`) hätte beim nächsten Rahmenwerk danebengelegen.

DIE ANDERE HÄLFTE steht genauso hier: Eine Instanz, die zwei Funktionen
von Hand benutzen, MUSS weiterhin gemeldet werden. Ein Prüfer, der nach
einer Verschärfung nichts mehr findet, ist kein Prüfer mehr.
"""


from ..base import BasisTest
from ..wegwerfordner import Wegwerfordner

#: Die Bauart, die gemeldet gehört: eine Instanz, zwei Nutzer von Hand.
ZAEHLER = (
    "import collections\n\n"
    "zaehler = collections.Counter()\n\n\n"
    "def erhoehen(schluessel):\n"
    "    zaehler[schluessel] += 1\n\n\n"
    "def lesen(schluessel):\n"
    "    return zaehler[schluessel]\n"
)

#: Dieselbe Bauart — aber `register` ist Djangos Pflichtname, und die
#: Funktionen hängen als Dekorator daran.
TEMPLATETAG = (
    "from django import template\n\n"
    "register = template.Library()\n\n\n"
    "@register.simple_tag\n"
    "def eins(wert):\n"
    "    return wert\n\n\n"
    "@register.inclusion_tag('x.html')\n"
    "def zwei(wert):\n"
    "    return {'wert': wert}\n"
)

#: Flask/FastAPI bauen genauso — die Regel darf nicht auf Django zeigen.
ROUTEN = (
    "from fastapi import FastAPI\n\n"
    "app = FastAPI()\n\n\n"
    "@app.get('/eins')\n"
    "def eins():\n"
    "    return {}\n\n\n"
    "@app.post('/zwei')\n"
    "def zwei():\n"
    "    return {}\n"
)


def _orte(dateien):
    u"""Welche Dateien meldet das Werkzeug?"""
    werkzeug = Wegwerfordner.werkzeug('klassen-kandidat', dateien)
    return {b.ort for b in werkzeug.pruefen().befunde}


class RahmenwerkRegistrierung(BasisTest):
    u"""Ein Name, den das Rahmenwerk vergibt, ist kein freier Zustand."""

    def test_templatetag_register_wird_nicht_gemeldet(self):
        self.assertEqual(_orte({'marken.py': TEMPLATETAG}), set())

    def test_routen_dekorator_wird_nicht_gemeldet(self):
        u"""Erkannt am Dekorator, nicht am Ordner — sonst nur Django."""
        self.assertEqual(_orte({'web.py': ROUTEN}), set())

    def test_zaehler_wird_weiterhin_gemeldet(self):
        u"""Die Gegenprobe: ohne sie wäre die Verschärfung eine Blendung."""
        self.assertIn('zaehlwerk.py', _orte({'zaehlwerk.py': ZAEHLER}))

    def test_beide_nebeneinander(self):
        u"""Im selben Lauf: der eine gemeldet, der andere nicht."""
        orte = _orte({'zaehlwerk.py': ZAEHLER, 'marken.py': TEMPLATETAG})
        self.assertIn('zaehlwerk.py', orte)
        self.assertNotIn('marken.py', orte)
