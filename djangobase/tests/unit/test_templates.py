# -*- coding: utf-8 -*-
"""Wächter über alle djangoBase-Templates.

WARUM DIESER TEST EXISTIERT (13.08.2026)
----------------------------------------
Ein mehrzeiliger `{# … #}`-Kommentar wird von Django NICHT entfernt — er steht
sichtbar auf der Seite. An Django 6.0.2 gemessen:

    django.template.base.tag_re   Flags 32, re.DOTALL NICHT gesetzt
    '{# eine Zeile #}'                    -> ''
    '{# Zeile eins\\n   Zeile zwei #}'     -> bleibt unverändert stehen

Dieser Fehler ist an einem Tag DREIMAL passiert (Sidebar-Navigation und zwei
Hilfe-Seiten) und jedes Mal erst im Screenshot aufgefallen — zweimal davon nur
in einem bestimmten Zustand der Seite (`{% if not partner %}`), also genau dann
nicht, wenn man hinschaut. Deshalb steht die Suche hier als Test und nicht als
gute Absicht: Die Kurzform gilt für EINE Zeile, alles andere ist
`{% comment %}`.
"""
import re
from pathlib import Path

import django
from django.template.base import tag_re
from django.test import SimpleTestCase

import djangobase

#: `{# … #}`, das über mindestens einen Zeilenumbruch geht.
MEHRZEILIG = re.compile(r"\{#(?:[^#]|#(?!\}))*?\n(?:[^#]|#(?!\}))*?#\}", re.S)


class TemplateKommentareTest(SimpleTestCase):

    def _templates(self):
        wurzel = Path(djangobase.__file__).resolve().parent / "templates"
        return sorted(wurzel.rglob("*.html"))

    def test_keine_mehrzeiligen_kurz_kommentare(self):
        funde = []
        for f in self._templates():
            text = f.read_text(encoding="utf-8")
            for m in MEHRZEILIG.finditer(text):
                zeile = text[: m.start()].count("\n") + 1
                funde.append("%s:%d  %s…" % (f.name, zeile,
                                             m.group(0)[:50].replace("\n", " / ")))
        self.assertEqual(funde, [], "Mehrzeilige {# #}-Kommentare stehen sichtbar "
                                    "auf der Seite — {% comment %} benutzen:\n  "
                                    + "\n  ".join(funde))

    def test_die_annahme_dahinter_gilt_noch(self):
        """Der Test darüber ist nur sinnvoll, solange Django das wirklich so macht.

        Setzt eine künftige Django-Fassung `re.DOTALL`, wäre die Regel überholt —
        dann soll DIESER Test anschlagen und nicht der andere stumm weiterlaufen."""
        self.assertFalse(tag_re.flags & re.DOTALL,
                         "Django %s entfernt mehrzeilige {# #} jetzt selbst — "
                         "test_keine_mehrzeiligen_kurz_kommentare kann weg."
                         % django.get_version())
