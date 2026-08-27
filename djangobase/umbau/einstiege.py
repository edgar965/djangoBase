# -*- coding: utf-8 -*-
u"""Wo ein Workflow anfaengt — gefunden, nicht aufgeschrieben.

DIE ANSAGE (Edgar, 27.08.2026)
==============================
    „die workflows sollst du aber ermitteln, schau dir jede Seite durch
     und ermittle 20-50 Workflows"

Eine Liste von Hand waere beim naechsten neuen Endpunkt falsch. Hier wird
stattdessen gesucht, wo Code von aussen angestossen wird — und das sind
genau drei Stellen:

    Routen    ``path('live/kalender/', views.live_calendar_view)``
              -> jemand ruft eine Seite oder einen Endpunkt auf
    Befehle   ``app/management/commands/record_streams.py::handle``
              -> ein Dienst oder ein Cronjob startet
    Faeden    eine Klasse mit ``run()`` unter ``live/``
              -> laeuft von selbst weiter, ohne dass jemand klickt

Gemessen an CamTrack (27.08.2026): 271 Routen (113 Seiten, 158 unter
``api/``), 32 Befehle, 10 Faeden.

WARUM DIE ROUTE UND NICHT DIE VORLAGE
=====================================
Eine Seite ohne Route ruft niemand auf. Die Route ist ausserdem die
einzige Stelle, an der Adresse und Code beieinanderstehen — die Vorlage
weiss nicht, unter welcher Adresse sie haengt.
"""
import ast
import re
from pathlib import Path

from .klassenmodell import AUS

#: ``path('x/', views.y, name='z')`` — auch ``re_path``.
_ROUTE = re.compile(
    r'\b(?:path|re_path)\(\s*'
    r'[\'"](?P<pfad>[^\'"]*)[\'"]\s*,\s*'
    r'(?P<ziel>[\w.]+)'
    r'(?:[^)]*?name\s*=\s*[\'"](?P<name>[^\'"]+)[\'"])?')

#: Ordner, in denen ein ``run()`` als Faden gilt.
FADEN_ORTE = ('live', 'services', 'orchestrator')

#: Methodennamen, die einen Faden anzeigen.
FADEN_NAMEN = ('run', 'run_once', 'tick', 'einmal')


class Einstieg:
    u"""EIN Ort, an dem ein Workflow anfaengt."""

    __slots__ = ('adresse', 'art', 'ziel', 'datei', 'zeile', 'routenname')

    def __init__(self, adresse, art, ziel, datei, zeile, routenname=''):
        #: Was der Aufrufer angibt: eine URL, ein Befehlsname, ein Faden.
        self.adresse = adresse
        #: ``'seite'``, ``'api'``, ``'befehl'`` oder ``'faden'``
        self.art = art
        #: Der Name im Code, der angesprungen wird.
        self.ziel = ziel
        self.datei = datei
        self.zeile = zeile
        self.routenname = routenname

    @property
    def titel(self):
        u"""Was in der Liste steht."""
        if self.art in ('seite', 'api'):
            return '/%s' % self.adresse.lstrip('/')
        return self.adresse

    def als_dict(self):
        return {'adresse': self.adresse, 'art': self.art, 'ziel': self.ziel,
                'datei': str(self.datei), 'zeile': self.zeile,
                'routenname': self.routenname, 'titel': self.titel}

    def __repr__(self):
        return '<Einstieg %s %s>' % (self.art, self.titel)


class Einstiegssucher:
    u"""Durchsucht das Projekt nach Einstiegen."""

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)

    def alle(self):
        return self.routen() + self.befehle() + self.faeden()

    # ── Routen ──────────────────────────────────────────────────

    def routen(self):
        u"""Jede ``path(...)``-Zeile aus jeder ``urls.py``.

        Mit einem regulaeren Ausdruck und nicht ueber den AST: Eine
        ``urls.py`` ist eine Liste von Aufrufen, und der Ausdruck liest
        Pfad, Ziel und Namen in einem Zug. Der AST muesste dafuer
        Schluesselwort-Argumente einzeln auseinandernehmen.
        """
        aus = []
        for datei in sorted(self.wurzel.rglob('urls.py')):
            if any(teil in AUS for teil in datei.parts):
                continue
            try:
                text = datei.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                continue
            for treffer in _ROUTE.finditer(text):
                pfad = treffer.group('pfad')
                ziel = treffer.group('ziel')
                if ziel.endswith('as_view'):
                    ziel = ziel.rsplit('.', 2)[-2] if '.' in ziel else ziel
                else:
                    ziel = ziel.rsplit('.', 1)[-1]
                zeile = text.count('\n', 0, treffer.start()) + 1
                aus.append(Einstieg(
                    pfad, 'api' if pfad.startswith('api/') else 'seite',
                    ziel, datei, zeile, treffer.group('name') or ''))
        return aus

    # ── Befehle ─────────────────────────────────────────────────

    def befehle(self):
        u"""``manage.py <name>`` — je Datei genau ein ``handle``."""
        aus = []
        for datei in sorted(self.wurzel.rglob('management/commands/*.py')):
            if datei.name == '__init__.py':
                continue
            if any(teil in AUS for teil in datei.parts):
                continue
            zeile = self._zeile_von(datei, 'handle')
            if zeile:
                aus.append(Einstieg('manage.py %s' % datei.stem, 'befehl',
                                    'handle', datei, zeile))
        return aus

    # ── Faeden ──────────────────────────────────────────────────

    def faeden(self):
        u"""Was von selbst weiterlaeuft: eine Schleife in einer Klasse.

        Ein Faden hat keine Adresse, unter der ihn jemand aufruft — und
        gerade darum ist er im Bild wichtig: Er ist der Teil, den man beim
        Lesen der Routen NICHT findet.
        """
        aus = []
        for datei in sorted(self.wurzel.rglob('*.py')):
            teile = set(datei.parts)
            if any(t in AUS for t in datei.parts):
                continue
            if not teile & set(FADEN_ORTE):
                continue
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8'))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            for knoten in ast.walk(baum):
                if not isinstance(knoten, ast.ClassDef):
                    continue
                for kind in knoten.body:
                    if (isinstance(kind, (ast.FunctionDef,
                                          ast.AsyncFunctionDef))
                            and kind.name in FADEN_NAMEN):
                        aus.append(Einstieg(
                            '%s.%s' % (knoten.name, kind.name), 'faden',
                            kind.name, datei, kind.lineno))
        return aus

    @staticmethod
    def _zeile_von(datei, name):
        try:
            baum = ast.parse(datei.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError, OSError):
            return 0
        for knoten in ast.walk(baum):
            if (isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and knoten.name == name):
                return knoten.lineno
        return 0
