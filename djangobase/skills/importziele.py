# -*- coding: utf-8 -*-
u"""ImportZiele - ``from x import y``, wo es ``y`` gar nicht gibt.

DER ANLASS (03.09.2026, shortlongx)
===================================
``werkzeug/sparring.py`` verlor am 16.08.2026 beim Umbau auf ``ReviewPartner``
seine beiden Funktionen ``frage_lokal`` und ``frage_online``. **Sieben**
Werkzeuge importierten sie weiter. Sechs davon starteten ab diesem Tag gar nicht
mehr; das siebte importiert erst in der Methode und starb beim ersten Aufruf.
Aufgefallen ist es zweieinhalb Wochen spaeter, und nur, weil jemand die Aufrufer
von Hand durchsah.

Am selben Tag fanden sich drei weitere: ``ib_assets_deckung``,
``ib_fein_deckung`` und ``ib_historie_deckung`` holten ihre Pruefklassen aus
``tests_app.pruefungen`` - die waren nach ``tests_app.tests.broker.component``
umgezogen. Zehn tote Werkzeuge aus zwei Umbauten.

WARUM ES SONST NIEMAND MELDET
=============================
Der Language Server prueft fehlende Modul-*Attribute* nicht (er meldet nur
unaufloesbare MODULE), die Testsuite faehrt keine Werkzeuge, und ein Werkzeug,
das niemand startet, schweigt. Dabei ist es der billigste Befund ueberhaupt:
Man muss nur nachsehen, bevor es jemand ausfuehrt.

Der Unterschied zu ``tote-importe``: Dort geht es um Namen, die importiert und
nicht BENUTZT werden. Hier um Namen, die es am Ziel nicht GIBT.

Reine stdlib.
"""
import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug
from .modulindex import ModulIndex


class ImportZiele(BefundWerkzeug):

    slug = 'import-ziele'
    kriterium = 9
    titel = 'Importe ins Leere'
    zweck = ('Findet ``from x import y``, wo das Modul ``x`` zum Projekt gehoert '
             'und keinen Namen ``y`` definiert. Solche Dateien werfen beim '
             'Import einen ImportError - auf Modulebene starten sie gar nicht.')
    abhilfe = ('Nach jedem Umbau, der Namen verschiebt oder entfernt: Wer eine '
               'Funktion durch eine Klasse ersetzt, laesst die Aufrufer zurueck. '
               'Ein Werkzeug, das niemand taeglich startet, meldet das nie '
               'selbst.')
    befund = ('In shortlongx zehn tote Werkzeuge aus zwei Umbauten: sieben nach '
              'dem Wegfall von ``sparring.frage_online`` (16.08.2026), drei nach '
              'dem Umzug der Pruefklassen aus ``tests_app.pruefungen``. Keines '
              'davon fiel zweieinhalb Wochen lang auf.')
    dauer = 'Sekunden'

    anlassfall = Anlassfall(
        {"sparring.py": "class SparringLauf:\n    pass\n",
         "orb_dialog.py": "from sparring import frage_online\n\n\n"
                          "def haupt():\n    return frage_online(1, 2, 3, 4)\n",
         # Der AUSGENOMMENE Fall daneben: eine Tupel-Zuweisung bindet zwei
         # Namen. Die erste Fassung sah nur ``Name`` und meldete neun solcher
         # Importe, die alle in Ordnung waren.
         "richtungen.py": "LONG, SHORT = 1, -1\n",
         "nutzer.py": "from richtungen import LONG, SHORT\n"},
        mindestens=1, hoechstens=1, erwartet_in="frage_online",
        warum="Sieben Werkzeuge hingen an zwei Funktionen, die ein Umbau "
              "entfernt hatte - zweieinhalb Wochen lang unbemerkt")

    def pruefen(self, **_argumente):
        dateien = self.dateien(".py")
        index = ModulIndex(dateien, self.wurzel())
        befunde, undurchsichtig, rueckfall = [], 0, 0
        for d in dateien:
            if d.baum is None:
                continue
            for knoten, geschuetzt in self._importe(d):
                neue, u, r = self._urteil(index, d, knoten, geschuetzt)
                befunde.extend(neue)
                undurchsichtig += u
                rueckfall += r
        kopf = ["%d Dateien" % len(dateien), "%d Module" % len(index.je_name)]
        # AUSGENOMMENES WIRD GENANNT: Eine Pruefung, die still wegfiltert, sieht
        # aus wie eine, die nichts findet.
        if undurchsichtig:
            kopf.append("%d Ziele statisch nicht beurteilbar" % undurchsichtig)
        if rueckfall:
            kopf.append("%d mit try/except-Rueckfall" % rueckfall)
        return Befundsatz(self.titel, kopf, befunde)

    # ---------------------------------------------------------------- sammeln
    def _importe(self, datei):
        u"""``(Knoten, hat_rueckfall)`` aller ``from … import``-Stellen.

        ``hat_rueckfall``: Der Import steht in einem ``try``, dessen ``except``
        einen ``ImportError`` faengt - ein bewusster Weg fuer optionale
        Abhaengigkeiten und kein Befund."""
        aus = []
        self._sammeln(datei.baum, False, aus)
        return aus

    def _sammeln(self, knoten, im_rueckfall, aus):
        for kind in ast.iter_child_nodes(knoten):
            drin = im_rueckfall or (isinstance(knoten, ast.Try)
                                    and kind in knoten.body
                                    and self._faengt_importfehler(knoten))
            if isinstance(kind, ast.ImportFrom):
                aus.append((kind, drin))
            self._sammeln(kind, drin, aus)

    @staticmethod
    def _faengt_importfehler(versuch):
        for h in versuch.handlers:
            if h.type is None:
                return True
            namen = ([e.id for e in h.type.elts if isinstance(e, ast.Name)]
                     if isinstance(h.type, ast.Tuple)
                     else [h.type.id] if isinstance(h.type, ast.Name) else [])
            if {'ImportError', 'ModuleNotFoundError', 'Exception'} & set(namen):
                return True
        return False

    # ----------------------------------------------------------------- urteil
    def _urteil(self, index, datei, knoten, geschuetzt):
        u"""``(Befunde, undurchsichtig, rueckfall)`` fuer EINE Import-Zeile."""
        ziel = index.ziel(datei, knoten)
        if not ziel:
            return [], 0, 0
        modul = index.datei(ziel)
        if modul is None:
            return [], 0, 0                 # fremdes Paket - nicht unsere Sache
        grund = index.undurchsichtig(modul)
        vorhanden = index.namen(modul)
        befunde, u, r = [], 0, 0
        for a in knoten.names:
            if a.name == '*' or a.name in vorhanden:
                continue
            if index.ist_paketteil(ziel, a.name):
                continue                    # ein Untermodul, kein Attribut
            if grund:
                u += 1
            elif geschuetzt:
                r += 1
            else:
                befunde.append(self._befund(index, datei, knoten, modul, a.name))
        return befunde, u, r

    def _befund(self, index, datei, knoten, modul, name):
        return Befund(
            "%s:%d" % (datei.name, knoten.lineno),
            "%s gibt es in %s nicht" % (name, modul.name),
            self._hinweis(index, modul, name),
            Befund.FEHLER)

    def _hinweis(self, index, modul, name):
        u"""Konkret sagen, was es stattdessen gibt - sonst ist der Befund halb."""
        kurz = name.lower().lstrip('_')
        aehnlich = sorted(n for n in index.namen(modul)
                          if not n.startswith('_')
                          and (kurz in n.lower() or n.lower() in kurz))[:3]
        if aehnlich:
            return "%s bietet: %s" % (modul.name, ", ".join(aehnlich))
        wo = self._woanders(index, name)
        if wo:
            return "%s steht heute in %s" % (name, ", ".join(wo))
        return "Wirft beim Import einen ImportError - die Datei startet nicht"

    @staticmethod
    def _woanders(index, name):
        aus = []
        for punktname, d in index.je_name.items():
            if name in index.namen(d):
                aus.append(punktname)
            if len(aus) >= 3:
                break
        return aus
