# -*- coding: utf-8 -*-
"""JavaScript-Fallen, die auf djangoBase-Seiten still zuschlagen.

DER AUFTRAG (Edgar, 21.08.2026): „mach alle"
============================================
    * kein ``querySelector('form')``

DIE FALLE
=========
Aus ``~/.claude/rules/formular-selector.md``, nach einem echten Vorfall:

    Auf Seiten mit der djangoBase-Sidebar steht das LOGOUT-Formular früher im
    DOM als der Seiteninhalt. ``document.querySelector('form[action]')`` greift
    deshalb das Logout-Formular, und ``new FormData(form)`` sieht nur leere
    Felder.

Auf ``/bank/neu/`` meldete das jedes ausgefüllte Feld als „fehlt" — Logout-Form
bei DOM-Position ~11k, Bank-Form bei ~66k. Der Code war für sich richtig; er
wurde erst durch die geerbte Sidebar falsch. Genau deshalb gehört die Prüfung
hierher: Sie ist eine Folge der djangoBase-Konformität, kein allgemeiner
JS-Stil.

WAS GEMELDET WIRD
=================
Nur der generische Zugriff auf das ERSTE Formular:

    document.querySelector('form')          gemeldet
    document.querySelector('form[action]')  gemeldet
    document.querySelectorAll('form')       nicht — wer alle holt, wählt selbst
    el.closest('form')                      nicht — relativ zum Element, korrekt
    document.getElementById('meine-form')   nicht — das ist die Lösung

Dazu zwei verwandte Fallen derselben Bauart, die dieses Projekt schon getroffen
haben: ``document.forms[0]`` und ``querySelector('form')`` innerhalb eines
Submit-Handlers.
"""

import re

from django.test import SimpleTestCase

from djangobase.tests.konform.quellen import TABU, dateien, text_von  # noqa: F401

from .basis import KonformTest

#: ``querySelector('form')`` / ``querySelector("form[action]")`` — aber NICHT
#: ``querySelectorAll``, nicht ``closest``, und nicht ``form#id``/``form.klasse``:
#: die sind eindeutig und genau die empfohlene Lösung. Die erste Fassung des
#: Musters (``form\b[^"']*``) meldete sie mit — ein Prüfer, der die Lösung
#: anmeckert, wird abgeschaltet statt gelesen.
_ERSTES_FORM = re.compile(r"""(?<!All)\bquerySelector\s*\(\s*["']\s*form\s*(?:\[[^"']*\])?\s*["']\s*\)""")

#: ``document.forms[0]`` — dieselbe Wette auf die DOM-Reihenfolge.
_FORMS_INDEX = re.compile(r"""\bdocument\.forms\s*\[\s*\d+\s*\]""")


def _quellen():
    """Alle JS-Dateien und Vorlagen des Projekts (ohne djangoBase selbst).

    Welche Ordner draußen bleiben, entscheidet ``quellen.dateien`` — samt der
    Projekt-Ausnahmen aus ``DJANGOBASE_KONFORM_AUS``."""
    return dateien(".js", ".html")


def _treffer(muster):
    """[(datei, zeilennummer, zeile)] für ein Suchmuster."""
    aus = []
    for pfad in _quellen():
        text = text_von(pfad)
        if text is None or not muster.search(text):
            continue
        for nr, zeile in enumerate(text.splitlines(), 1):
            if muster.search(zeile) and not zeile.strip().startswith(("//", "*", "#")):
                aus.append((pfad, nr, zeile.strip()))
    return aus


class FormularSelektorTest(KonformTest):
    """Inhalts-Formulare nie über einen generischen Selektor."""

    def _melden(self, treffer, was, rat):
        zeilen = "\n".join("    %s:%d  %s" % (p.name, nr, z[:80]) for p, nr, z in treffer[:10])
        return "%d Stelle(n) %s:\n%s%s\n\n%s" % (
            len(treffer),
            was,
            zeilen,
            "\n    …" if len(treffer) > 10 else "",
            rat,
        )

    def test_kein_generischer_formular_zugriff(self):
        treffer = _treffer(_ERSTES_FORM)
        if treffer:
            self.fail(
                self._melden(
                    treffer,
                    "greifen das ERSTE Formular der Seite",
                    "Auf Seiten mit der djangoBase-Sidebar steht das "
                    "Logout-Formular früher im DOM — der Zugriff trifft es, und "
                    "FormData sieht nur leere Felder. Inhalts-Formulare immer über "
                    "eine eindeutige ID:\n"
                    "    document.getElementById('bank-form')",
                )
            )

    def test_kein_zugriff_ueber_forms_index(self):
        treffer = _treffer(_FORMS_INDEX)
        if treffer:
            self.fail(
                self._melden(
                    treffer,
                    "nutzen document.forms[n]",
                    "Dieselbe Wette auf die DOM-Reihenfolge wie querySelector"
                    "('form') — die Sidebar schiebt sie um. Über eine ID gehen.",
                )
            )

    def test_es_wurde_wirklich_gesucht(self):
        """Ohne durchsuchte Dateien wäre „0 Treffer" bedeutungslos."""
        anzahl = sum(1 for _ in _quellen())
        self.assertTrue(anzahl, "Keine JS-/HTML-Dateien gefunden — stimmt BASE_DIR?")


class GegenprobeTest(SimpleTestCase):
    """Trifft das Muster genau das Gemeinte?"""

    def test_generischer_zugriff_wird_erkannt(self):
        for zeile in (
            "const f = document.querySelector('form');",
            'document.querySelector("form[action]")',
            "el.querySelector( 'form' )",
        ):
            with self.subTest(zeile=zeile):
                self.assertTrue(_ERSTES_FORM.search(zeile), zeile)

    def test_erlaubte_schreibweisen_bleiben_still(self):
        for zeile in (
            "document.querySelectorAll('form')",
            "ev.target.closest('form')",
            "document.getElementById('bank-form')",
            "document.querySelector('#bank-form')",
            "document.querySelector('form#bank-form')",
        ):
            with self.subTest(zeile=zeile):
                self.assertIsNone(_ERSTES_FORM.search(zeile), zeile)

    def test_forms_index_wird_erkannt(self):
        self.assertTrue(_FORMS_INDEX.search("document.forms[0].submit()"))
        self.assertIsNone(_FORMS_INDEX.search("document.forms['meins']"))
