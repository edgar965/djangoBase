# -*- coding: utf-8 -*-
u"""Aus einer Test-Kennung einen deutschen Satz machen.

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „verbessere meine testcases, so dass es die Gherkin BDD Anforderungen
     erfüllt, z. B. Wer kann es lesen: auch Nicht-Programmierer"

Das ist die eine Eigenschaft, die Gherkin wirklich voraus hatte. Eine
``.feature``-Datei liest jeder:

    Szenario: Eine ausgeblendete Person bleibt ausgeblendet

Auf ``/hilfe/tests/`` stand dagegen dies:

    AliasVerbundTest.test_falte_behaelt_reihenfolge_und_einzelne

Derselbe Satz — nur in Maschinenschrift. Unterstriche statt Leerzeichen,
``test_`` davor, und der Gegenstand steckt ungetrennt im Klassennamen.

WARUM DAS REICHT, UND KEINE ZWEITE DATEI NÖTIG IST
===================================================
Der Satz ist bereits da. Er steht nur in der Schreibweise, die Python für
Bezeichner verlangt. Eine ``.feature``-Datei daneben wäre eine ZWEITE
Fassung desselben Satzes — und zwei Fassungen laufen auseinander, sobald
jemand die eine ändert und die andere vergisst.

Hier wird stattdessen gelesen, was ohnehin dasteht:

    AliasVerbundTest.test_falte_behaelt_reihenfolge_und_einzelne
    -> „Alias Verbund: Falte behaelt reihenfolge und einzelne"

Damit gilt dieselbe Zusage wie bei Gherkin — lesbar ohne Code — ohne ein
zweites Rahmenwerk, einen zweiten Testläufer und eine zweite Liste.

WAS DER LESER NICHT SIEHT — UND WARUM DAS IN ORDNUNG IST
=========================================================
Gherkin trennt „Gegeben / Wenn / Dann". Diese drei Teile stehen hier im
Docstring der Prüfung, nicht im Namen. Der Name trägt das ERGEBNIS, und
das ist der Teil, den man beim roten Balken braucht: Was sollte stimmen
und stimmt jetzt nicht?
"""
from __future__ import annotations

import re

#: KEINE UMLAUT-LISTE (26.08.2026)
#: ================================
#:     „ich brauche keine umlaute in den testcases"
#:
#: Hier stand eine Zuordnung von 230 Wörtern: ``behaelt`` -> ``behält``,
#: ``groesse`` -> ``Größe`` … Sie machte die Sätze eine Spur hübscher und
#: kostete dafür Pflege bei JEDER neuen Prüfung — ein Wort, das nicht
#: darin steht, bleibt ohnehin, wie es ist.
#:
#: Der wertvolle Teil bleibt: aus ``AliasVerbundTest.test_falte_behaelt_
#: reihenfolge`` wird „Alias Verbund: Falte behaelt reihenfolge". Der Satz
#: ist lesbar, auch ohne ä — der Bezeichner selbst kann ohnehin keins
#: tragen.

#: Wortanfaenge, die im Klassennamen keine eigene Trennung verdienen —
#: sonst wird aus ``JsBefunde`` ein „Js Befunde".
ZUSAMMEN = ('Js', 'Ui', 'Roi', 'Api', 'Db', 'Ki')

#: KLEIN GESCHRIEBEN, auch wenn sie im Bezeichner groß stehen.
#:
#: Nur die geschlossene Klasse der Füllwörter — Hauptwörter und Verben
#: bleiben, wie sie dastehen. Bei einem unbekannten Wort lieber groß
#: lassen: Ein falsch großes Hauptwort stört weniger als ein falsch
#: kleines.
KLEIN = {
    'und', 'oder', 'aber', 'sondern', 'denn',
    'der', 'die', 'das', 'den', 'dem', 'des',
    'ein', 'eine', 'einer', 'einen', 'einem', 'eines',
    'kein', 'keine', 'keinen', 'keiner',
    'in', 'im', 'an', 'am', 'auf', 'aus', 'bei', 'beim', 'mit', 'nach',
    'seit', 'von', 'vom', 'zu', 'zum', 'zur', 'ueber', 'über', 'unter',
    'vor', 'hinter', 'neben', 'zwischen', 'ohne', 'gegen', 'fuer', 'für',
    'durch', 'um', 'als', 'wie', 'wenn', 'dann', 'weil', 'dass', 'ob',
    'nicht', 'nur', 'auch', 'noch', 'schon', 'sehr', 'mehr', 'immer',
    'ist', 'sind', 'war', 'waren', 'wird', 'werden', 'wurde', 'hat',
    'haben', 'kann', 'koennen', 'können', 'muss', 'muessen', 'müssen',
    'darf', 'duerfen', 'dürfen', 'soll', 'sollen', 'bleibt', 'bleiben',
    'steht', 'stehen', 'laeuft', 'läuft', 'laufen', 'geht', 'gehen',
    'kommt', 'kommen', 'macht', 'machen', 'gibt', 'geben',
    'meldet', 'melden', 'traegt', 'trägt', 'zaehlt', 'zählt',
    'sie', 'er', 'es', 'ihn', 'ihm', 'ihr', 'sich', 'selbst',
    'voll', 'leer', 'ganz', 'halb', 'gleich', 'anders',
}

_LEERE = re.compile(r'\s+')


class Testsatz:
    u"""EINE Test-Kennung, gelesen als Satz.

        >>> Testsatz('app.tests.unit.test_a.AliasVerbundTest'
        ...          '.test_falte_behaelt_reihenfolge').satz()
        'Alias Verbund: Falte behaelt reihenfolge'
    """

    #: Was am Anfang einer Prüfmethode wegfällt.
    VORSATZ = 'test_'

    #: Was am Ende eines Klassennamens wegfällt — es sagt nichts über den
    #: Gegenstand, nur dass es eine Prüfung ist.
    NACHSATZ = ('Tests', 'Test', 'TestCase', 'Case')

    def __init__(self, kennung):
        self.kennung = str(kennung or '')
        teile = self.kennung.split('.')
        self.methode = teile[-1] if teile else ''
        self.klasse = teile[-2] if len(teile) >= 2 else ''

    # ── Der Satz ────────────────────────────────────────────────

    def satz(self):
        u"""``'Gegenstand: das erwartete Ergebnis'`` — oder nur eines davon."""
        links = self.gegenstand()
        rechts = self.ergebnis()
        if links and rechts:
            return '%s: %s' % (links, rechts)
        return rechts or links or self.kennung

    def gegenstand(self):
        u"""Der Klassenname als Wortfolge: ``AliasVerbundTest`` -> ``Alias Verbund``."""
        name = self.klasse
        for nach in self.NACHSATZ:
            if name.endswith(nach) and len(name) > len(nach):
                name = name[:-len(nach)]
                break
        if not name:
            return ''
        woerter = self._trennen(name)
        return ' '.join(self._klein(w, i) for i, w in enumerate(woerter))

    def ergebnis(self):
        u"""Der Methodenname als Satz: ``test_falte_prueft_x`` -> ``Falte prueft x``."""
        name = self.methode
        if name.startswith(self.VORSATZ):
            name = name[len(self.VORSATZ):]
        if not name:
            return ''
        woerter = [w for w in name.split('_') if w]
        if not woerter:
            return ''
        satz = ' '.join(woerter)
        return _LEERE.sub(' ', satz[:1].upper() + satz[1:]).strip()

    # ── Kleinteile ──────────────────────────────────────────────

    @classmethod
    def _trennen(cls, name):
        u"""``AliasVerbund`` -> ``['Alias', 'Verbund']``, ``JsBefunde`` -> eines."""
        roh = re.findall(r'[A-Z][a-z0-9]*|[a-z0-9]+', name)
        aus = []
        for wort in roh:
            if aus and aus[-1] in ZUSAMMEN:
                aus[-1] = aus[-1] + wort
            else:
                aus.append(wort)
        return aus

    @staticmethod
    def _klein(wort, stelle):
        u"""Füllwörter klein — aber nie das erste Wort eines Satzes.

        In ``KameraUndPerson`` steht jedes Wort groß, weil CamelCase es
        verlangt, nicht weil es ein Hauptwort wäre. Ohne diesen Schritt
        liest sich der Satz wie ein englischer Titel: „Kamera Und Person".
        """
        if stelle and wort.lower() in KLEIN:
            return wort.lower()
        return wort

