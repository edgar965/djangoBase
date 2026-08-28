# -*- coding: utf-8 -*-
u"""Funktionen, die ein Dekorator beim Rahmen ANMELDET.

DER FEHLALARM (28.08.2026, Projekt assistant)
=============================================
``freie-funktionen`` meldete ``mail/signals.py`` mit sechs freien
Funktionen. Alle sechs sind ``@receiver``-Signalhandler.

Wer dem Vorschlag folgt und sie in eine Klasse steckt, meldet sie nicht
mehr an: Django haelt Empfaenger ueber eine Referenz auf das
Funktionsobjekt, und ``dispatch_uid`` unterscheidet sie. An
``mail/signals.py`` haengt das automatische Einbetten, Einsortieren und
Verschlagworten JEDER neu angelegten Mail — der Umbau haette das still
abgeschaltet.

Dasselbe gilt fuer Templatetags: Django sucht sie beim Namen, den
``@register.filter`` eintraegt.

WAS NICHT DAZUGEHOERT
=====================
``require_POST``, ``csrf_exempt``, ``contextmanager`` und ``atomic``
wirken auch auf Methoden — sie melden nichts an, sie umhuellen nur den
Aufruf. Sie duerfen weiter gemeldet werden, sonst verschwinden echte
Befunde.

DIE REGEL ENTSCHAERFT GEZIELT, NICHT PAUSCHAL
=============================================
``schedule/signals.py`` hat zwei ``@receiver``-Handler und drei normale
Funktionen. Nach der Regel bleiben die drei gemeldet — die Datei
verschwindet NICHT aus den Befunden. Genau so soll es sein.

BDD - GEGEBEN / DANN
====================
    EinSignalhandler       ... wird nicht gemeldet
    EinTemplatetag         ... ebenfalls nicht
    EinUmhuellenderDekorator ... schon
    EineGemischteDatei     ... nur die echten
"""
import ast
import unittest

from djangobase.skills.rahmenvorschrift import Rahmenvorschrift


def _funktion(quelle: str):
    u"""Der erste Funktionsknoten aus einem Schnipsel."""
    for knoten in ast.parse(quelle).body:
        if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return knoten
    raise AssertionError('keine Funktion im Schnipsel')


class EinSignalhandler(unittest.TestCase):
    u"""Gegeben: Eine Funktion, die Django als Empfaenger anmeldet."""

    def test_mit_argumenten(self):
        knoten = _funktion(
            '@receiver(post_save, sender=Mail, dispatch_uid="x")\n'
            'def _auto_embed(sender, instance, created, **kw): pass\n')
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(knoten))

    def test_ohne_argumente(self):
        knoten = _funktion('@receiver\ndef f(): pass\n')
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(knoten))

    def test_ueber_ein_modul_geschrieben(self):
        u"""``@signals.receiver(...)`` — verglichen wird der letzte
        Namensteil."""
        knoten = _funktion(
            '@signals.receiver(post_save)\ndef f(s, i, **k): pass\n')
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(knoten))


class EinTemplatetag(unittest.TestCase):
    u"""Gegeben: Django sucht die Funktion beim Namen aus dem Register."""

    def test_ein_filter(self):
        knoten = _funktion('@register.filter\ndef kurz(wert): pass\n')
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(knoten))

    def test_ein_simple_tag_mit_argumenten(self):
        knoten = _funktion(
            '@register.simple_tag(takes_context=True)\n'
            'def x(context): pass\n')
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(knoten))

    def test_ein_inclusion_tag(self):
        knoten = _funktion(
            '@register.inclusion_tag("t.html")\ndef x(): pass\n')
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(knoten))

    def test_das_register_darf_heissen_wie_es_will(self):
        u"""``register`` ist ein Projektname, ``filter`` nicht."""
        knoten = _funktion('@meine_bibliothek.filter\ndef x(w): pass\n')
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(knoten))


class EineCeleryAufgabe(unittest.TestCase):
    u"""Gegeben: Ein Aufgabenplaner meldet die Funktion an."""

    def test_task(self):
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(
            _funktion('@app.task\ndef x(): pass\n')))

    def test_shared_task_mit_argumenten(self):
        self.assertTrue(Rahmenvorschrift.wird_angemeldet(
            _funktion('@shared_task(bind=True)\ndef x(self): pass\n')))


class EinUmhuellenderDekorator(unittest.TestCase):
    u"""Gegeben: Ein Dekorator, der nichts anmeldet.

    DIE ABGRENZUNG: Diese wirken auch auf Methoden. Wuerden sie
    mitausgenommen, verschwaenden echte Befunde — im Projekt assistant
    allein zehn ``@require_POST``-Views.
    """

    def test_require_post_zaehlt_nicht(self):
        self.assertFalse(Rahmenvorschrift.wird_angemeldet(
            _funktion('@require_POST\ndef x(request): pass\n')))

    def test_csrf_exempt_auch_nicht(self):
        self.assertFalse(Rahmenvorschrift.wird_angemeldet(
            _funktion('@csrf_exempt\ndef x(request): pass\n')))

    def test_contextmanager_nicht(self):
        self.assertFalse(Rahmenvorschrift.wird_angemeldet(
            _funktion('@contextmanager\ndef x(): pass\n')))

    def test_transaction_atomic_nicht(self):
        self.assertFalse(Rahmenvorschrift.wird_angemeldet(
            _funktion('@transaction.atomic\ndef x(): pass\n')))

    def test_ganz_ohne_dekorator_erst_recht_nicht(self):
        self.assertFalse(Rahmenvorschrift.wird_angemeldet(
            _funktion('def x(): pass\n')))


class EineGemischteDatei(unittest.TestCase):
    u"""Gegeben: Signalhandler UND normale Funktionen in einer Datei.

    So sieht ``schedule/signals.py`` aus: zwei ``@receiver`` und drei
    Helfer. Die Regel darf die Datei nicht als Ganzes freistellen — die
    drei Helfer sind echte Kandidaten.
    """

    QUELLE = (
        'def _compute_ctag(cal): pass\n'
        '@receiver(post_save, sender=Event)\n'
        'def event_saved(sender, instance, created, **kw): pass\n'
        'def _refresh_ctag(cal): pass\n'
    )

    def test_nur_der_handler_faellt_weg(self):
        angemeldet = [k.name for k in ast.parse(self.QUELLE).body
                      if isinstance(k, ast.FunctionDef)
                      and Rahmenvorschrift.wird_angemeldet(k)]
        self.assertEqual(angemeldet, ['event_saved'])

    def test_die_helfer_bleiben_kandidaten(self):
        offen = [k.name for k in ast.parse(self.QUELLE).body
                 if isinstance(k, ast.FunctionDef)
                 and not Rahmenvorschrift.wird_angemeldet(k)]
        self.assertEqual(offen, ['_compute_ctag', '_refresh_ctag'])


class DieListe(unittest.TestCase):
    u"""Gegeben: Die Liste der anmeldenden Dekoratoren."""

    def test_sie_enthaelt_die_django_faelle(self):
        for name in ('receiver', 'filter', 'simple_tag', 'inclusion_tag'):
            self.assertIn(name, Rahmenvorschrift.ANMELDENDE_DEKORATOREN, name)

    def test_und_nicht_die_umhuellenden(self):
        for name in ('require_POST', 'csrf_exempt', 'contextmanager',
                     'atomic', 'property', 'staticmethod'):
            self.assertNotIn(name, Rahmenvorschrift.ANMELDENDE_DEKORATOREN,
                             name)
