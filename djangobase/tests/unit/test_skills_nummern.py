# -*- coding: utf-8 -*-
u"""Fixer und Lehren nennen Nummern, die es in der Tabelle wirklich gibt.

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „passe noch an die Fix Werkzeuge, die erwähnen kriterien die es nicht
     gibt. sie sollen sich auf die Nummer der testcases beziehen"
    „auch die lehren sollen die testcases erwähnen (nummer)"

Die Fixer-Karten zeigten ``· Kr. 11``, ``· Kr. 16``, ``· Kr. 3``. Diese
Kriterien GIBT es — aber nicht auf dieser Seite: Die Werkzeug-Tabelle
darüber ist nach Rängen (1, 2, 3 …) und Bereichen geordnet. Wer ``Kr. 11``
las, suchte eine 11, die dort nirgends steht.

Jetzt nennt jeder Fixer die Prüfung, deren Befund er behebt — mit ihrer
Nummer aus der Tabelle. Dasselbe bei den Lehren.

DIE ZEHN OHNE PRÜFUNG SIND EIN ERGEBNIS
=======================================
Zwölf der 22 Lehren haben ein Werkzeug, zehn nicht. Diese zehn hängen
allein an der Sorgfalt dessen, der gerade schreibt — ``meta-ordering-
distinct``, ``kdtree-workers``, ``regressionsnetz-vorher`` und die anderen.
Das steht jetzt auf der Seite („prüft kein Werkzeug"), statt dass man es
vermuten muss.
"""
from djangobase.skills import fixer, werkzeuge
from djangobase.skills.lehren_review import LEHREN
from djangobase.skills.rangliste import rangliste

from ..base import BasisTest


def _raenge():
    u"""``{slug: rang}`` — so, wie die Tabelle sie zeigt."""
    aus = {}
    for abschnitt in rangliste().abschnitte(list(werkzeuge())):
        for rang, w in abschnitt['eintraege']:
            aus[w.slug] = rang
    return aus


class JederFixerNenntSeinePruefung(BasisTest):

    def test_jeder_nennt_ein_werkzeug(self):
        ohne = [f.slug for f in fixer() if not getattr(f, 'behebt', '')]
        self.assertEqual(ohne, [],
                         'Diese Fixer sagen nicht, welchen Befund sie '
                         'beheben: %s' % ohne)

    def test_das_genannte_werkzeug_gibt_es(self):
        da = {w.slug for w in werkzeuge()}
        falsch = [(f.slug, f.behebt) for f in fixer()
                  if getattr(f, 'behebt', '') and f.behebt not in da]
        self.assertEqual(falsch, [],
                         'Diese Fixer zeigen auf ein Werkzeug, das es nicht '
                         'gibt: %s' % falsch)

    def test_die_nummer_stimmt_mit_der_tabelle(self):
        raenge = _raenge()
        for f in fixer():
            with self.subTest(fixer=f.slug):
                p = f.nummer()
                self.assertIsNotNone(p, 'keine Nummer aufloesbar')
                self.assertEqual(p['nr'], raenge[f.behebt])

    def test_ohne_zuordnung_gibt_es_keine_nummer(self):
        u"""Lieber nichts als eine erfundene Zahl."""
        class Leer(type(fixer()[0])):
            behebt = ''
        self.assertIsNone(Leer().nummer())

    def test_ein_unbekanntes_werkzeug_ergibt_keine_nummer(self):
        class Falsch(type(fixer()[0])):
            behebt = 'gibt-es-nicht'
        self.assertIsNone(Falsch().nummer())


class DieLehrenNennenIhrePruefung(BasisTest):

    def test_jedes_genannte_werkzeug_gibt_es(self):
        da = {w.slug for w in werkzeuge()}
        falsch = [(l.slug, s) for l in LEHREN
                  for s in l.werkzeuge if s not in da]
        self.assertEqual(falsch, [],
                         'Diese Lehren zeigen auf Werkzeuge, die es nicht '
                         'gibt: %s' % falsch)

    def test_die_nummern_stimmen_mit_der_tabelle(self):
        raenge = _raenge()
        for l in LEHREN:
            if not l.werkzeuge:
                continue
            with self.subTest(lehre=l.slug):
                self.assertEqual([nr for nr, _t in l.nummern()],
                                 [raenge[s] for s in l.werkzeuge])

    def test_ohne_werkzeug_kommt_eine_leere_liste(self):
        u"""Kein Werkzeug ist eine AUSSAGE, kein Fehler — die Seite schreibt
        dann „prüft kein Werkzeug" hin."""
        ohne = [l for l in LEHREN if not l.werkzeuge]
        self.assertTrue(ohne, 'Wenn jede Lehre ein Werkzeug hat, ist dieser '
                              'Test ueberfluessig — dann bitte löschen.')
        for l in ohne:
            with self.subTest(lehre=l.slug):
                self.assertEqual(l.nummern(), [])

    def test_mindestens_die_haelfte_ist_gedeckt(self):
        u"""Ein Deckel gegen Verfall: Heute haben 12 von 22 ein Werkzeug.

        Fällt das unter die Haelfte, ist entweder eine Zuordnung verloren
        gegangen oder es sind Regeln dazugekommen, die niemand prüft.
        """
        mit = sum(1 for l in LEHREN if l.werkzeuge)
        self.assertGreaterEqual(
            mit * 2, len(LEHREN),
            'Nur %d von %d Lehren haben eine Prüfung.' % (mit, len(LEHREN)))


class KeineKriteriumsNummernMehrAufDenKarten(BasisTest):
    u"""Der Rückfall, gegen den diese Datei geschrieben ist."""

    def test_die_fixer_karte_zeigt_kein_kriterium(self):
        u"""OHNE KOMMENTARE GESUCHT (26.08.2026)

        Der erste Wurf fiel durch — an seiner EIGENEN Erklärung: Im
        ``{% comment %}``-Block über der Zeile steht der alte Ausdruck
        wörtlich, damit nachlesbar ist, was dort stand. Der Wächter fand
        ihn und meldete den Rückfall.

        Genau derselbe Fehler wie heute früh bei ``CacheBustingTest``, das
        drei Einbindungen aus Kommentarblöcken anmahnte. Deshalb hier
        derselbe Helfer.
        """
        from pathlib import Path

        from django.template.loader import get_template

        from djangobase.tests.konform.test_statik import ohne_kommentare
        markup = ohne_kommentare(
            Path(get_template('djangobase/hilfe/skills.html').origin.name
                 ).read_text(encoding='utf-8'))
        self.assertNotIn(
            '· Kr. {{ f.kriterium }}', markup,
            'Die Fixer-Karte zeigt wieder eine Kriteriums-Nummer — die steht '
            'in der Tabelle nirgends.')
