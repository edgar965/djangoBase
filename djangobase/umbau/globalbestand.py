# -*- coding: utf-8 -*-
u"""Was auf Modulebene steht — und welche Seite welches Skript zieht.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „mach evtl. mehrere Bereiche, je einen pro Hauptast des Projektes.
     neuer Tab: Globale Funktionen, neuer Tab: Globale Klasse, neuer Tab
     Globale Variablen, neuer Tab HTML Seiten, darin je eine HTML Seite und
     deren JS code, auch als Abhängigkeiten falls verfügbar"

Das Klassenbild beantwortet „wer haelt wen". Diese vier Listen beantworten
die Frage davor: **Was haengt an gar keiner Klasse?**

Genau das ist der Massstab aus Kriterium 1 und 18 des Werkzeugkastens: Eine
freie Funktion auf Modulebene traegt ihren Zustand selbst, eine
veraenderliche Modulvariable ueberlebt jeden Aufruf und gehoert niemandem.
Beides sieht man im Klassenbild NICHT — dort ist nur, was schon eine Klasse
ist.

DIE HTML-SEITEN
===============
Eine Vorlage zieht Skripte (``{% static "…/x.js" %}``), und diese Skripte
ziehen weitere (``import { y } from './z.js'``). Damit steht neben jeder
Seite, welcher Code sie wirklich ausfuehrt — und wie tief das geht.
"""
import ast
import re
from pathlib import Path

#: Verzeichnisse, die nicht zum Bestand gehoeren.
#:
#: DIESELBE LISTE WIE IM KLASSENMODELL (24.08.2026)
#: ================================================
#: Hier stand zusaetzlich `tests`. Auf dem Reiter „Globale Klassen"
#: rechneten die Karten oben deshalb mit 1004 und die Gliederung darunter
#: mit 584 — zwei Zaehlungen auf EINEM Reiter, 420 Testklassen Unterschied.
#: Gemeldet als „struktur noch immer unklar".
#:
#: Tests gehoeren dazu: Die Gliederung nach Rolle stellt sie ohnehin
#: getrennt, und wer sie ausblenden will, klappt die Rolle zu. Sie
#: wegzulassen macht die Zahl kleiner, nicht wahrer.
from .klassenmodell import AUS

#: Namen, die zwar Listen sind, aber keinen Zustand tragen.
AUSFUHRLISTEN = {'__all__'}

#: ``{% static 'app/js/x.js' %}`` — so binden Django-Vorlagen Skripte ein.
STATIC = re.compile(r"""\{%\s*static\s+['"]([^'"]+\.js)['"]""")
#: ``<script src="/static/app/js/x.js">`` — der direkte Weg.
SRC = re.compile(r"""<script[^>]+src=['"]([^'"]+\.js)""")
#: ``import … from './x.js'`` innerhalb eines Moduls.
IMPORT = re.compile(r"""from\s+['"]([^'"]+\.js)['"]""")
#: ``{% extends "a/b.html" %}`` / ``{% include "a/b.html" %}``
VORLAGE = re.compile(r"""\{%\s*(?:extends|include)\s+['"]([^'"]+)['"]""")


class Eintrag:
    u"""Ein Fund auf Modulebene: Name, Ort, Kurzbeschreibung."""

    __slots__ = ('name', 'datei', 'zeile', 'zusatz')

    def __init__(self, name, datei, zeile, zusatz=''):
        self.name = name
        self.datei = datei
        self.zeile = zeile
        self.zusatz = zusatz


class Seite:
    u"""Eine HTML-Vorlage mit dem Code, den sie zieht."""

    __slots__ = ('pfad', 'skripte', 'eingebunden', 'zeilen')

    def __init__(self, pfad, skripte, eingebunden, zeilen):
        self.pfad = pfad
        #: ``[(js-pfad, [abhaengigkeit, …])]``
        self.skripte = skripte
        self.eingebunden = eingebunden
        self.zeilen = zeilen

    @property
    def abhaengigkeiten(self):
        return sum(len(a) for _s, a in self.skripte)


class Globalbestand:
    u"""Liest einen Bereich und sortiert, was auf Modulebene steht."""

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)
        self.funktionen = []
        self.klassen = []
        self.variablen = []
        self.seiten = []

    def lesen(self):
        for pfad in sorted(self.wurzel.rglob('*.py')):
            if any(teil in pfad.parts for teil in AUS):
                continue
            self._modul(pfad)
        for pfad in sorted(self.wurzel.rglob('*.html')):
            if any(teil in pfad.parts for teil in AUS):
                continue
            self._seite(pfad)
        self.funktionen.sort(key=lambda e: (e.datei, e.zeile))
        self.klassen.sort(key=lambda e: (e.datei, e.zeile))
        self.variablen.sort(key=lambda e: (e.datei, e.zeile))
        self.seiten.sort(key=lambda s: -s.abhaengigkeiten)
        return self

    # ── Python ──────────────────────────────────────────────────
    def _modul(self, pfad):
        try:
            baum = ast.parse(pfad.read_text(encoding='utf-8',
                                            errors='replace'))
        except (SyntaxError, OSError, ValueError):
            return
        kurz = self._kurz(pfad)
        for knoten in baum.body:
            if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                stellen = ', '.join(a.arg for a in knoten.args.args) or '—'
                self.funktionen.append(
                    Eintrag(knoten.name, kurz, knoten.lineno, stellen))
            elif isinstance(knoten, ast.ClassDef):
                basen = ', '.join(self._name(b) for b in knoten.bases)
                self.klassen.append(
                    Eintrag(knoten.name, kurz, knoten.lineno, basen))
            elif isinstance(knoten, (ast.Assign, ast.AnnAssign)):
                self._variable(knoten, kurz)

    def _variable(self, knoten, kurz):
        u"""Nur VERAENDERLICHE zaehlen — eine Konstante ist keine Last.

        ``MAX = 5`` ist eine Vorgabe und gehoert auf Modulebene. ``_cache =
        {}`` ist Zustand, der jeden Aufruf ueberlebt und niemandem gehoert
        — das ist der Fund.
        """
        ziele = knoten.targets if isinstance(knoten, ast.Assign) \
            else [knoten.target]
        for ziel in ziele:
            if not isinstance(ziel, ast.Name):
                continue
            wert = knoten.value
            if ziel.id in AUSFUHRLISTEN:
                # `__all__` ist eine Liste, aber kein Zustand — sie wird
                # beim Import einmal gelesen und nie geaendert. Ohne diese
                # Ausnahme stellte sie ein Viertel aller „veraenderlichen"
                # Modulvariablen und machte die Zahl wertlos.
                self.variablen.append(Eintrag(ziel.id, kurz, knoten.lineno,
                                              'Ausfuhrliste'))
                continue
            veraenderlich = isinstance(wert, (ast.Dict, ast.List, ast.Set)) or (
                isinstance(wert, ast.Call)
                and self._name(wert.func) in
                ('dict', 'list', 'set', 'defaultdict', 'OrderedDict',
                 'deque', 'Counter'))
            self.variablen.append(Eintrag(
                ziel.id, kurz, knoten.lineno,
                'veränderlich' if veraenderlich else 'Konstante'))

    # ── Vorlagen und Skripte ────────────────────────────────────
    def _seite(self, pfad):
        try:
            text = pfad.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return
        namen = sorted(set(STATIC.findall(text)) | set(SRC.findall(text)))
        if not namen and not VORLAGE.search(text):
            return
        skripte = [(n, self._abhaengig(n)) for n in namen]
        self.seiten.append(Seite(
            self._kurz(pfad), skripte,
            sorted(set(VORLAGE.findall(text))),
            text.count('\n') + 1))

    def _abhaengig(self, js_pfad):
        u"""Was dieses Skript selbst zieht — eine Stufe tief.

        Zwei Stufen waeren schon ein Netz, kein Baum: `live_view.js` zieht
        neun Module, die zusammen wieder dreissig ziehen. Wer das sehen
        will, klickt sich weiter.
        """
        datei = self._finden(js_pfad)
        if datei is None:
            return []
        try:
            text = datei.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return []
        return sorted({p.rsplit('/', 1)[-1] for p in IMPORT.findall(text)})

    def _finden(self, js_pfad):
        u"""Die Datei zu einem Skript-Pfad — der Name genuegt.

        Der Pfad in der Vorlage (`app/js/modules/live/x.js`) und der auf der
        Platte (`app/static/app/js/modules/live/x.js`) sind nicht dieselben.
        Gesucht wird deshalb ueber den Dateinamen; bei Gleichnamigkeit
        gewinnt der erste Treffer.
        """
        name = js_pfad.rsplit('/', 1)[-1]
        for gefunden in self.wurzel.rglob(name):
            if '__pycache__' not in gefunden.parts:
                return gefunden
        return None

    # ── Hilfen ──────────────────────────────────────────────────
    def _kurz(self, pfad):
        try:
            return str(pfad.relative_to(self.wurzel)).replace('\\', '/')
        except ValueError:
            return pfad.name

    @staticmethod
    def _name(knoten):
        if isinstance(knoten, ast.Name):
            return knoten.id
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        return ''

    def kennzahlen(self):
        return {
            'funktionen': len(self.funktionen),
            'klassen': len(self.klassen),
            'variablen': len(self.variablen),
            'veraenderlich': sum(1 for v in self.variablen
                                 if v.zusatz == 'veränderlich'),
            'seiten': len(self.seiten),
            'skripte': sum(len(s.skripte) for s in self.seiten),
        }


def hauptaeste(wurzel):
    u"""Die Hauptaeste eines Projekts — je eine Quelle zur Auswahl.

        „mach evtl. mehrere Bereiche, je einen pro Hauptast des Projektes"

    Das sind die obersten Verzeichnisse, die Python enthalten.

    GEZAEHLT WERDEN KLASSEN, NICHT DATEIEN (24.08.2026)
    ==================================================
    Vorher stand im Auswahlfeld die Zahl der `.py`-Dateien. Das las sich wie
    die Zahl der Klassen und war es nicht: `tools (14)` und `config (6)`
    sahen nach Inhalt aus und enthalten **null** Klassen. Wer sie waehlte,
    bekam ein leeres Bild ohne Erklaerung.
    """
    import ast as _ast

    # DIESELBE AUSSCHLUSSLISTE WIE DAS KLASSENMODELL (24.08.2026)
    # ==========================================================
    # `AUS` hier schliesst `tests` aus, `Klassenmodell.AUS` nicht. Das
    # Auswahlfeld sagte damit „app 615", das Ergebnis darunter „1004" —
    # zwei Zaehlweisen fuer dieselbe Sache, und keine Erklaerung dazu.
    basis = Path(wurzel)
    raus = []
    for eintrag in sorted(basis.iterdir()):
        if not eintrag.is_dir() or eintrag.name.startswith('.'):
            continue
        if (eintrag.name in AUS
                or eintrag.name in ('media', 'logs', 'db')):
            continue
        # VERSCHIEDENE NAMEN, NICHT DEFINITIONEN (24.08.2026)
        # ===================================================
        # `Klassenmodell` haelt seine Klassen in einem Woerterbuch nach
        # NAMEN — gleichnamige gewinnen einmal. In CamTrack heissen 82
        # Klassen doppelt: Das Auswahlfeld sagte „1086", das Ergebnis
        # darunter „1004". Wer zwei Zahlen fuer dieselbe Sache sieht,
        # glaubt keiner von beiden.
        namen = set()
        for datei in eintrag.rglob('*.py'):
            if any(t in datei.parts for t in AUS):
                continue
            try:
                baum = _ast.parse(datei.read_text(encoding='utf-8',
                                                  errors='replace'))
            except (SyntaxError, OSError, ValueError):
                continue
            namen.update(k.name for k in _ast.walk(baum)
                         if isinstance(k, _ast.ClassDef))
        if namen:
            raus.append({'name': eintrag.name, 'klassen': len(namen)})
    raus.sort(key=lambda e: -e['klassen'])
    return raus


__all__ = ['Globalbestand', 'Eintrag', 'Seite', 'hauptaeste']
