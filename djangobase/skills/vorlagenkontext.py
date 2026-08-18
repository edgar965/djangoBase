"""Vorlagenkontext — tote Kontextvariablen, fehlende Namen, verwaiste Vorlagen."""

import ast
import re
from pathlib import Path

from django.conf import settings
from django.template.base import FilterExpression, Variable
from django.template.loader import get_template

from .befund import Befund, Befundsatz, BefundWerkzeug

#: Namen, die aus Kontextprozessoren oder der Shell kommen, nicht aus der Ansicht.
VON_AUSSEN = {
    'request', 'user', 'perms', 'messages', 'csrf_token', 'settings', 'DEBUG',
    'True', 'False', 'None', 'block', 'forloop', 'djangobase', 'aktiv',
    'LANGUAGE_CODE', 'LANGUAGE_BIDI', 'TIME_ZONE', 'aktives_theme',
    'sidebar_initial_width', 'JS_VERSION', 'DJANGOBASE',
}

#: Ueber diese Attribute fuehrt der Weg aus der Vorlage heraus: jeder Knoten
#: kennt seine Herkunft, die ihren Lader, der die Engine — und deren Cache
#: enthaelt ALLE bereits geladenen Vorlagen. Ohne die Sperre sammelt die
#: Pruefung die Variablennamen des halben Projekts ein.
NICHT_ABSTEIGEN = {
    'origin', 'engine', 'loader', 'loaders', 'template', 'template_loaders',
    'libraries', 'builtins', 'get_template_cache', 'context',
}


def _ist_name(text):
    """Zahlen und Zeichenketten aussortieren: `{{ 1 }}` ist keine Variable."""
    return bool(re.match(r'^[A-Za-z_]\w*$', text or ''))


class Vorlagensicht:
    """Alle Variablennamen einer Vorlage samt eingebundener Bausteine."""

    def __init__(self, name):
        self.titel = name
        self.gelesen = set()
        self.lokal = set()
        self.eingebunden = set()
        self._sammeln(get_template(name).template)

    def _sammeln(self, vorlage):
        quelle = vorlage.source
        for treffer in re.finditer(r'{%\s*(?:extends|include)\s+"([^"]+)"', quelle):
            self.eingebunden.add(treffer.group(1))
        for muster in (r'{%\s*with\s+([^%]+)%}',
                       r'{%\s*include\s+"[^"]+"\s+with\s+([^%]+)%}'):
            for treffer in re.finditer(muster, quelle):
                for stueck in treffer.group(1).split():
                    if '=' in stueck:
                        self.lokal.add(stueck.split('=')[0].strip())
        for treffer in re.finditer(r'{%\s*for\s+([\w\s,]+?)\s+in\s', quelle):
            for teil in treffer.group(1).split(','):
                self.lokal.add(teil.strip())
        for treffer in re.finditer(r'\sas\s+(\w+)\s*%}', quelle):
            self.lokal.add(treffer.group(1))
        self._wert(vorlage.nodelist)

    def _wert(self, wert, gesehen=None, tiefe=0):
        """Alles absuchen, was Variablen enthalten koennte.

        Bewusst generisch statt nach Knotentypen: Die BEDINGUNGEN von
        `{% if %}` haengen als TemplateLiteral in Operator-Objekten
        (`.first`/`.second`) und sind weder Node noch FilterExpression. Wer nur
        die bekannten Typen abklappert, meldet dort gelesene Variablen faelsch-
        licherweise als tot.
        """
        if tiefe > 40:
            return
        gesehen = gesehen if gesehen is not None else set()
        if id(wert) in gesehen:
            return
        gesehen.add(id(wert))
        if isinstance(wert, FilterExpression):
            if isinstance(wert.var, Variable):
                self.gelesen.add(str(wert.var).split('.')[0].split('|')[0])
            else:
                self._wert(wert.var, gesehen, tiefe + 1)
            for _filter, argumente in wert.filters:
                for _, argument in argumente:
                    self._wert(argument, gesehen, tiefe + 1)
        elif isinstance(wert, Variable):
            self.gelesen.add(str(wert).split('.')[0])
        elif isinstance(wert, (str, bytes, int, float, bool, type(None))):
            return
        elif isinstance(wert, dict):
            for eintrag in wert.values():
                self._wert(eintrag, gesehen, tiefe + 1)
        elif isinstance(wert, (list, tuple, set, frozenset)):
            for eintrag in wert:
                self._wert(eintrag, gesehen, tiefe + 1)
        elif hasattr(wert, '__dict__'):
            for name, eintrag in vars(wert).items():
                if name not in NICHT_ABSTEIGEN:
                    self._wert(eintrag, gesehen, tiefe + 1)

    def namen(self, tiefe=0):
        """Gelesene Namen inklusive der eingebundenen Vorlagen."""
        alle = set(self.gelesen)
        if tiefe > 4:
            return alle
        for name in self.eingebunden:
            try:
                alle |= Vorlagensicht(name).namen(tiefe + 1)
            except Exception:  # noqa: BLE001 — fehlende Vorlage darf nicht stoppen
                pass
        return alle

    def alle_lokal(self, tiefe=0):
        alle = set(self.lokal)
        if tiefe > 4:
            return alle
        for name in self.eingebunden:
            try:
                alle |= Vorlagensicht(name).alle_lokal(tiefe + 1)
            except Exception:  # noqa: BLE001
                pass
        return alle


class Renderstelle:
    """Ein render()-Aufruf: Vorlage, uebergebene Schluessel, Ort im Quelltext."""

    __slots__ = ('datei', 'zeile', 'vorlage', 'schluessel', 'vollstaendig')

    def __init__(self, datei, zeile, vorlage, schluessel, vollstaendig):
        self.datei = datei
        self.zeile = zeile
        self.vorlage = vorlage
        self.schluessel = schluessel
        #: False, wenn der Kontext nicht nur aus Literalen besteht (`**extra`).
        #: Dann taugt die Gegenrichtung (FEHLEND) nicht.
        self.vollstaendig = vollstaendig

    @property
    def ort(self):
        return '%s:%d' % (self.datei, self.zeile)


class Vorlagenkontext(BefundWerkzeug):

    slug = 'vorlagen-kontext'
    titel = 'Vorlagen-Kontext'
    zweck = ('Vergleicht jeden render()-Aufruf mit seiner Vorlage: uebergebene, '
             'aber nie gelesene Schluessel (TOT), gelesene, aber nie gelieferte '
             'Namen (FEHLEND) und Vorlagen, die niemand rendert (VERWAIST).')
    abhilfe = ('Nach jedem groesseren Umbau und vor einem Review — findet stille '
            'Fehler, die kein Test bemerkt, weil Django fehlende Variablen '
            'kommentarlos als Leerstring rendert.')
    befund = ('Im Ursprungsprojekt: eine if-Bedingung, die seit vier Monaten auf '
             'einen nie gelieferten Namen zeigte (das Datei-Feld war dadurch '
             'immer Pflicht), zwei tote Kontextschluessel samt einem COUNT(*) '
             'je Aufruf und zwei unerreichbare Vorlagen.')
    dauer = 'wenige Sekunden'

    def pruefen(self, **_argumente):
        stellen = self._renderstellen()
        sicht, befunde = {}, []
        einbinde = self._einbindeparameter()
        for stelle in stellen:
            if stelle.vorlage not in sicht:
                try:
                    sicht[stelle.vorlage] = Vorlagensicht(stelle.vorlage)
                except Exception as fehler:  # noqa: BLE001
                    befunde.append(Befund(
                        stelle.ort, 'Vorlage %s nicht ladbar' % stelle.vorlage,
                        str(fehler), Befund.WARNUNG))
                    continue
            ansicht = sicht[stelle.vorlage]
            gelesen = ansicht.namen()
            ungenutzt = sorted(s for s in stelle.schluessel if s not in gelesen)
            for name in ungenutzt:
                befunde.append(Befund(
                    stelle.ort, 'TOT: %s (%s)' % (name, stelle.vorlage),
                    'wird uebergeben, aber von keiner beteiligten Vorlage gelesen',
                    Befund.WARNUNG))
            if stelle.vollstaendig:
                fehlend = sorted(n for n in gelesen - stelle.schluessel
                                 - ansicht.alle_lokal() - VON_AUSSEN - einbinde
                                 if _ist_name(n))
                for name in fehlend:
                    befunde.append(Befund(
                        stelle.ort, 'FEHLEND: %s (%s)' % (name, stelle.vorlage),
                        'die Vorlage liest den Namen, niemand liefert ihn — '
                        'Django rendert dafuer stillschweigend nichts',
                        Befund.FEHLER))
        befunde.extend(self._verwaiste(stellen))
        kopf = ['%d render()-Stellen, %d Vorlagen geprueft'
                % (len(stellen), len(sicht))]
        return Befundsatz(self.titel, kopf, befunde)

    # ------------------------------------------------------------------ intern

    def _renderstellen(self):
        gefunden = []
        for datei in self.projektdateien('.py'):
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
            except (SyntaxError, OSError):
                continue
            for knoten in ast.walk(baum):
                stelle = self._aus_aufruf(knoten, datei)
                if stelle is not None:
                    gefunden.append(stelle)
        return gefunden

    def _aus_aufruf(self, knoten, datei):
        if not (isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
                and knoten.func.id == 'render'):
            return None
        if len(knoten.args) < 2 or not isinstance(knoten.args[1], ast.Constant):
            return None
        schluessel, vollstaendig = set(), True
        wortliste = knoten.args[2] if len(knoten.args) > 2 else None
        for stichwort in knoten.keywords:
            if stichwort.arg == 'context':
                wortliste = stichwort.value
        if isinstance(wortliste, ast.Dict):
            for taste in wortliste.keys:
                if isinstance(taste, ast.Constant):
                    schluessel.add(taste.value)
                else:
                    vollstaendig = False
        elif wortliste is not None:
            vollstaendig = False
        return Renderstelle(self.kurz(datei), knoten.lineno,
                            knoten.args[1].value, schluessel, vollstaendig)

    def _einbindeparameter(self):
        """Namen, die irgendwo per `{% include … with name=… %}` gesetzt werden.

        Ein Baustein liest solche Namen, bekommt sie aber von der EINBINDENDEN
        Vorlage — aus Sicht des render()-Aufrufs saehen sie sonst wie fehlende
        Kontextvariablen aus.
        """
        namen = set()
        for ordner in self._vorlagenordner():
            for datei in Path(ordner).rglob('*.html'):
                quelle = datei.read_text(encoding='utf-8', errors='replace')
                for treffer in re.finditer(r'{%\s*(?:include|with)\s[^%]*?%}', quelle):
                    for stueck in treffer.group(0).split():
                        kopf = stueck.split('=')[0].strip()
                        if '=' in stueck and _ist_name(kopf):
                            namen.add(kopf)
        return namen

    @staticmethod
    def _vorlagenordner():
        """Alle DIRS aus der Template-Konfiguration, die es wirklich gibt."""
        ordner = []
        for eintrag in getattr(settings, 'TEMPLATES', []) or []:
            for verzeichnis in eintrag.get('DIRS', []) or []:
                if Path(str(verzeichnis)).is_dir():
                    ordner.append(str(verzeichnis))
        return ordner

    def _verwaiste(self, stellen):
        """Vorlagen, die niemand rendert und niemand einbindet."""
        befunde = []
        erreichbar = {s.vorlage for s in stellen}
        for ordner in self._vorlagenordner():
            for datei in Path(ordner).rglob('*.html'):
                quelle = datei.read_text(encoding='utf-8', errors='replace')
                for treffer in re.finditer(
                        r'{%\s*(?:extends|include)\s+"([^"]+)"', quelle):
                    erreichbar.add(treffer.group(1))
        for datei in self.projektdateien('.py'):
            quelle = datei.read_text(encoding='utf-8', errors='replace')
            for treffer in re.finditer(r'["\']([\w/_.-]+\.html)["\']', quelle):
                erreichbar.add(treffer.group(1))
        for ordner in self._vorlagenordner():
            for datei in Path(ordner).rglob('*.html'):
                titel = str(datei.relative_to(ordner)).replace('\\', '/')
                if name not in erreichbar:
                    befunde.append(Befund(
                        self.kurz(datei), 'VERWAIST (%d Byte)' % datei.stat().st_size,
                        'kein render(), kein include, kein extends verweist darauf',
                        Befund.HINWEIS))
        return befunde
