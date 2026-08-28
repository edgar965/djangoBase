# -*- coding: utf-8 -*-
u"""Welchen Namen darf ein View in der Endpunkt-Tabelle tragen?

DER ANLASS (28.08.2026)
=======================
``EndpunktProbe.test_jeder_endpunkt_ist_aufloesbar`` verglich schlicht
``treffer.func.__name__`` mit dem Namen aus der Tabelle. Solange jeder
View eine freie Funktion war, ging das auf.

Beim Bündeln freier Funktionen zu Klassen (Befund ``freie-funktionen``)
geht es nicht mehr auf. Aus::

    def midi_serve_file(request, filename): ...

wird::

    class MidiSeiten:
        @staticmethod
        def serve_file(request, filename): ...

    midi_serve_file = MidiSeiten.serve_file      # damit urls.py sie findet

Die Route zeigt danach auf ``serve_file``, die Tabelle nennt weiter
``midi_serve_file`` — und sieben Endpunkte galten als kaputt, obwohl
keiner es war.

DIE FALSCHE LÖSUNG, DIE FAST DRIN STAND
=======================================
Der erste Versuch verglich mit Namensähnlichkeit („endet auf
``_serve_file``"). Das hätte ``music_serve_file`` und
``midi_serve_file`` gegeneinander durchgehen lassen — eine vertauschte
Route wäre dann ein grüner Test gewesen. Genau der Fehlalarm-Typ, vor
dem ``analysewerkzeuge.md`` warnt, nur in die andere Richtung: kein
falscher Alarm, sondern ein verschwiegener.

Richtig ist die Frage: Hält das Modul, in dem die Funktion steht, unter
dem Namen aus der Tabelle GENAU DIESE Funktion? Das ist eine
Identitätsprüfung, kein Namensvergleich.

BDD - GEGEBEN / DANN
====================
    EineFreieFunktion       ... traegt ihren eigenen Namen
    EineGebuendelteMethode  ... darf unter dem Modulnamen stehen
    EineVertauschteRoute    ... faellt weiter auf
    EinModulOhneDenNamen    ... ebenfalls
"""
import sys
import types
import unittest

from djangobase.endpunkttests import EndpunktProbe


def _modul(name, **inhalt):
    u"""Ein Modul zum Anfassen, in ``sys.modules`` eingehaengt.

    Ohne den Eintrag findet ``_heisst_so`` das Modul nicht — es sucht
    ueber ``funktion.__module__``.
    """
    m = types.ModuleType(name)
    for k, v in inhalt.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


class _Lage(unittest.TestCase):
    def pruefen(self, funktion, ziel):
        return EndpunktProbe._heisst_so(funktion, ziel)


class EineFreieFunktion(_Lage):
    u"""Gegeben: Der Normalfall — ein View als Funktion auf Modulebene."""

    def setUp(self):
        def midi_serve_file(request):
            return None
        midi_serve_file.__module__ = 'probe_frei'
        _modul('probe_frei', midi_serve_file=midi_serve_file)
        self.f = midi_serve_file

    def tearDown(self):
        sys.modules.pop('probe_frei', None)

    def test_sie_traegt_ihren_namen(self):
        self.assertTrue(self.pruefen(self.f, 'midi_serve_file'))

    def test_ein_anderer_name_gilt_nicht(self):
        self.assertFalse(self.pruefen(self.f, 'music_serve_file'))


class EineGebuendelteMethode(_Lage):
    u"""Gegeben: Der Bereich ist zu einer Klasse gebuendelt.

    Die Methode heisst kurz, das Modul haelt den alten Namen als
    Zuweisung — sonst fände urls.py sie nicht mehr.
    """

    def setUp(self):
        class MidiSeiten:
            @staticmethod
            def serve_file(request):
                return None

            @staticmethod
            def stop(request):
                return None

        MidiSeiten.__module__ = 'probe_klasse'
        MidiSeiten.serve_file.__module__ = 'probe_klasse'
        MidiSeiten.stop.__module__ = 'probe_klasse'
        _modul('probe_klasse',
               MidiSeiten=MidiSeiten,
               midi_serve_file=MidiSeiten.serve_file,
               midi_stop=MidiSeiten.stop)
        self.K = MidiSeiten

    def tearDown(self):
        sys.modules.pop('probe_klasse', None)

    def test_der_modulname_gilt(self):
        u"""DER FALL, DER SIEBEN ENDPUNKTE ALS KAPUTT MELDETE."""
        self.assertTrue(self.pruefen(self.K.serve_file, 'midi_serve_file'))

    def test_der_methodenname_auch(self):
        self.assertTrue(self.pruefen(self.K.serve_file, 'serve_file'))

    def test_jede_methode_nur_ihr_eigener_name(self):
        u"""``midi_stop`` zeigt auf ``stop``, nicht auf ``serve_file``."""
        self.assertTrue(self.pruefen(self.K.stop, 'midi_stop'))
        self.assertFalse(self.pruefen(self.K.stop, 'midi_serve_file'))


class EineVertauschteRoute(_Lage):
    u"""Gegeben: Die Route zeigt auf den falschen View.

    DAS IST DER GRUND FÜR DIE GANZE PRÜFUNG. Sie darf nicht deshalb
    grün werden, weil zwei Namen ähnlich aussehen.
    """

    def setUp(self):
        class MidiSeiten:
            @staticmethod
            def serve_file(request):
                return None
        MidiSeiten.serve_file.__module__ = 'probe_midi'
        _modul('probe_midi', MidiSeiten=MidiSeiten,
               midi_serve_file=MidiSeiten.serve_file)

        def music_serve_file(request):
            return None
        music_serve_file.__module__ = 'probe_musik'
        _modul('probe_musik', music_serve_file=music_serve_file)

        self.midi = MidiSeiten.serve_file
        self.musik = music_serve_file

    def tearDown(self):
        for n in ('probe_midi', 'probe_musik'):
            sys.modules.pop(n, None)

    def test_aehnliche_namen_gelten_nicht(self):
        u"""Beide enden auf ``_serve_file``. Ein Vergleich über die
        Endung hätte das durchgelassen — und eine vertauschte Route
        wäre ein grüner Test geworden."""
        self.assertFalse(self.pruefen(self.midi, 'music_serve_file'))
        self.assertFalse(self.pruefen(self.musik, 'midi_serve_file'))

    def test_der_kurze_name_gilt_nicht_quer(self):
        u"""``serve_file`` ist der Methodenname der EINEN Klasse — die
        freie Funktion des anderen Bereichs heisst nicht so."""
        self.assertFalse(self.pruefen(self.musik, 'serve_file'))


class EinModulOhneDenNamen(_Lage):
    u"""Gegeben: Die Zuweisung fehlt (oder heisst anders)."""

    def setUp(self):
        class Seiten:
            @staticmethod
            def serve_file(request):
                return None
        Seiten.serve_file.__module__ = 'probe_leer'
        _modul('probe_leer', Seiten=Seiten)     # KEINE Zuweisung
        self.f = Seiten.serve_file

    def tearDown(self):
        sys.modules.pop('probe_leer', None)

    def test_der_modulname_gilt_dann_nicht(self):
        u"""Ohne Zuweisung fände urls.py den Namen auch nicht."""
        self.assertFalse(self.pruefen(self.f, 'midi_serve_file'))

    def test_der_methodenname_weiterhin_schon(self):
        self.assertTrue(self.pruefen(self.f, 'serve_file'))

    def test_ein_unbekanntes_modul_wirft_nicht(self):
        def irgendwas(request):
            return None
        irgendwas.__module__ = 'gibt_es_nicht'
        self.assertFalse(self.pruefen(irgendwas, 'egal'))
