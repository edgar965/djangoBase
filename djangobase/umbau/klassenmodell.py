# -*- coding: utf-8 -*-
u"""Das Klassenmodell eines Projekts — wer haelt wen, wer erbt von wem.

WOZU (Edgar, 24.08.2026)
========================
    „erstelle eine Seite in djangoBase hilfe - werkzeug Klassenmodell, das
     soll einen Button enthalten, der so eine Übersicht des Codes erstellt"

Dazu ein UML-Klassendiagramm als Vorlage: Kaesten mit Name, Feldern und
Methoden, dazwischen Linien mit Vielfachheiten (``1``, ``0..*``) und
Vererbungspfeile.

`objektwurzeln` misst dasselbe Verhaeltnis bereits — aber als ZAHL („74 von
548 Klassen haengen als self.x an einer anderen"). Eine Zahl sagt, wie gut
das Modell ist; sie zeigt nicht, WIE es aussieht. Dafuer ist das Bild da.

WAS GELESEN WIRD
================
Aus dem Syntaxbaum, ohne das Projekt zu starten:

    class Kachel(Basis):          -> erbt von Basis
        def __init__(self):
            self.zeiger = Zeiger()      -> haelt genau eine (1)
            self.balken = []            -> Sammlung, Vielfachheit 0..*
            self.balken.append(Balken())

Ein Feld gilt als Beziehung, wenn ihm eine ERKENNBARE eigene Klasse
zugewiesen wird. `self.name = 'x'` ist ein Attribut, `self.zeiger =
Zeiger()` eine Beziehung — der Unterschied ist genau der zwischen einem
Kasten-Eintrag und einer Linie.

WARUM NICHT ALLES AUF EINMAL
============================
Ein Projekt mit 548 Klassen ergibt ein Bild, das niemand liest. Gezeigt
wird deshalb eine NACHBARSCHAFT: eine Wurzel und alles, was von ihr aus in
`tiefe` Schritten erreichbar ist. Ohne Angabe waehlt das Werkzeug die
Klasse, die am meisten haelt — dort ist am meisten zu sehen.
"""
import ast
from pathlib import Path

#: Verzeichnisse, die nicht zum Modell gehoeren.
AUS = ('migrations', '__pycache__', 'node_modules', '.git', 'venv',
       'staticfiles', 'site-packages')

#: Sammlungen: Ein Feld dieser Bauart haelt VIELE.
SAMMLUNGEN = {'list', 'dict', 'set', 'tuple', 'defaultdict', 'OrderedDict',
              'deque', 'frozenset'}

#: Was Python selbst mitbringt — keine eigene Klasse des Projekts.
FREMD = {
    'Exception', 'ValueError', 'TypeError', 'KeyError', 'OSError',
    'RuntimeError', 'Path', 'Decimal', 'Enum', 'Thread', 'Lock', 'RLock',
    'Event', 'Queue', 'Popen', 'Counter', 'True', 'False', 'None',
}


class Feld:
    u"""Ein Eintrag im Kasten: ``- name : art``."""

    __slots__ = ('name', 'art', 'oeffentlich')

    def __init__(self, name, art='', oeffentlich=False):
        self.name = name
        self.art = art
        self.oeffentlich = oeffentlich

    @property
    def zeile(self):
        zeichen = '+' if self.oeffentlich else '-'
        return '%s %s%s' % (zeichen, self.name,
                            ' : %s' % self.art if self.art else '')


class Beziehung:
    u"""Eine Linie zwischen zwei Kaesten."""

    #: Vererbung wird als Dreieckspfeil gezeichnet, Besitz als Linie.
    ERBT = 'erbt'
    HAELT = 'haelt'

    __slots__ = ('von', 'nach', 'art', 'name', 'vielfachheit')

    def __init__(self, von, nach, art, name='', vielfachheit='1'):
        self.von = von
        self.nach = nach
        self.art = art
        self.name = name
        self.vielfachheit = vielfachheit


class Klasse:
    u"""Ein Kasten: Name, Felder, Methoden — und woher er stammt."""

    __slots__ = ('name', 'datei', 'zeile', 'basen', 'felder', 'methoden',
                 'haelt', 'dekorateure', 'nur_statisch', 'methodenzahl')

    def __init__(self, name, datei, zeile):
        self.name = name
        self.datei = datei
        self.zeile = zeile
        self.basen = []
        self.felder = []
        self.methoden = []
        #: ``[(feldname, klassenname, vielfachheit)]``
        self.haelt = []
        #: ``@dataclass`` und Verwandte — sie machen die Art der Klasse aus.
        self.dekorateure = []
        #: Nur ``@staticmethod``/``@classmethod``: eine Werkzeugklasse.
        self.nur_statisch = False
        #: Auch die privaten — fuer die Unterscheidung Datenklasse/Dienst.
        self.methodenzahl = 0


class Klassenmodell:
    u"""Liest ein Projekt und liefert Kaesten und Linien."""

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel)
        self.klassen = {}

    # ── Einlesen ────────────────────────────────────────────────
    def lesen(self):
        for pfad in sorted(self.wurzel.rglob('*.py')):
            if any(teil in pfad.parts for teil in AUS):
                continue
            try:
                baum = ast.parse(pfad.read_text(encoding='utf-8',
                                                errors='replace'))
            except (SyntaxError, OSError, ValueError):
                continue
            kurz = str(pfad.relative_to(self.wurzel)).replace('\\', '/')
            for knoten in ast.walk(baum):
                if isinstance(knoten, ast.ClassDef):
                    self._klasse(knoten, kurz)
        return self

    def _klasse(self, knoten, datei):
        k = Klasse(knoten.name, datei, knoten.lineno)
        for basis in knoten.bases:
            name = self._name(basis)
            if name and name not in FREMD:
                k.basen.append(name)
        k.dekorateure = [self._name(d) for d in knoten.decorator_list]
        eigene, statisch = 0, 0
        for teil in knoten.body:
            if isinstance(teil, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not teil.name.startswith('_') or teil.name == '__init__':
                    k.methoden.append(teil.name)
                eigene += 1
                marken = {self._name(d) for d in teil.decorator_list}
                if marken & {'staticmethod', 'classmethod'}:
                    statisch += 1
        k.methodenzahl = eigene
        k.nur_statisch = bool(eigene) and statisch == eigene
        self._felder(knoten, k)
        # Gleichnamige Klassen in mehreren Dateien: die erste gewinnt, die
        # zweite waere im Bild ohnehin nicht unterscheidbar.
        self.klassen.setdefault(k.name, k)

    def _felder(self, knoten, k):
        u"""``self.x = …`` einsammeln — Attribut oder Beziehung."""
        gesehen = set()
        for teil in ast.walk(knoten):
            if not isinstance(teil, (ast.Assign, ast.AnnAssign)):
                continue
            ziele = teil.targets if isinstance(teil, ast.Assign) else [teil.target]
            for ziel in ziele:
                if not (isinstance(ziel, ast.Attribute)
                        and isinstance(ziel.value, ast.Name)
                        and ziel.value.id == 'self'):
                    continue
                name = ziel.attr
                if name in gesehen:
                    continue
                gesehen.add(name)
                art, gehalten, viele = self._art(teil.value)
                if gehalten:
                    k.haelt.append((name, gehalten, '0..*' if viele else '1'))
                else:
                    k.felder.append(Feld(name, art,
                                         not name.startswith('_')))

    def _art(self, wert):
        u"""``(Art fuers Etikett, gehaltene Klasse oder None, viele?)``."""
        if isinstance(wert, ast.Call):
            name = self._name(wert.func)
            if name in SAMMLUNGEN:
                return (name, self._in_sammlung(wert), True)
            if name and name[:1].isupper() and name not in FREMD:
                return (name, name, False)
            return (name or '', None, False)
        if isinstance(wert, (ast.List, ast.Set, ast.Tuple)):
            return ('list', self._erste_klasse(wert.elts), True)
        if isinstance(wert, ast.Dict):
            return ('dict', self._erste_klasse(wert.values), True)
        if isinstance(wert, ast.Constant):
            return (type(wert.value).__name__, None, False)
        return ('', None, False)

    def _in_sammlung(self, ruf):
        return self._erste_klasse(list(ruf.args))

    def _erste_klasse(self, knoten):
        for eintrag in knoten or []:
            if isinstance(eintrag, ast.Call):
                name = self._name(eintrag.func)
                if name and name[:1].isupper() and name not in FREMD:
                    return name
        return None

    @staticmethod
    def _name(knoten):
        if isinstance(knoten, ast.Name):
            return knoten.id
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        return ''

    # ── Auswerten ───────────────────────────────────────────────
    def beziehungen(self):
        raus = []
        for k in self.klassen.values():
            for basis in k.basen:
                if basis in self.klassen:
                    raus.append(Beziehung(k.name, basis, Beziehung.ERBT))
            for feld, ziel, viel in k.haelt:
                if ziel in self.klassen:
                    raus.append(Beziehung(k.name, ziel, Beziehung.HAELT,
                                          feld, viel))
        return raus

    def dickster_ast(self):
        u"""Die Klasse, die am meisten haelt — dort ist am meisten zu sehen."""
        beste, zahl = None, -1
        for k in self.klassen.values():
            eigene = len({z for _f, z, _v in k.haelt if z in self.klassen})
            if eigene > zahl:
                beste, zahl = k.name, eigene
        return beste

    def nachbarschaft(self, start=None, tiefe=2):
        u"""Die Wurzel und alles, was in `tiefe` Schritten erreichbar ist.

        Ein Bild mit 548 Kaesten liest niemand. Diese Grenze ist der
        Unterschied zwischen einer Uebersicht und einer Tapete.
        """
        start = start or self.dickster_ast()
        if not start or start not in self.klassen:
            return [], []
        drin = {start}
        rand = {start}
        for _ in range(max(0, int(tiefe))):
            neu = set()
            for name in rand:
                k = self.klassen.get(name)
                if not k:
                    continue
                for _f, ziel, _v in k.haelt:
                    if ziel in self.klassen:
                        neu.add(ziel)
                for basis in k.basen:
                    if basis in self.klassen:
                        neu.add(basis)
            neu -= drin
            if not neu:
                break
            drin |= neu
            rand = neu
        kaesten = [self.klassen[n] for n in sorted(drin)]
        linien = [b for b in self.beziehungen()
                  if b.von in drin and b.nach in drin]
        return kaesten, linien

    #: Die Kategorien in der Reihenfolge, in der sie geprueft werden.
    #: Die erste passende gewinnt — sonst zaehlte eine Model-Klasse mit
    #: statischen Methoden zweimal.
    KATEGORIEN = (
        ('model', 'Django-Model', 'Vom ORM erzeugt, nicht vom Quelltext'),
        ('ansicht', 'Django-Ansicht', 'Der URL-Router ruft sie'),
        ('formular', 'Django-Formular', 'Django erzeugt und bindet sie'),
        ('test', 'Test', 'Prueft anderen Code, gehoert nicht ins Modell'),
        ('ausnahme', 'Ausnahme', 'Wird geworfen, nicht gehalten'),
        ('aufzaehlung', 'Aufzaehlung', 'Feste Werte statt Verhalten'),
        ('daten', 'Datenklasse', 'Nur Felder — ein Wert mit Namen'),
        ('werkzeug', 'Werkzeugklasse', 'Nur statische Methoden, kein Zustand'),
        ('im_baum', 'Baustein im Baum', 'Haengt als self.x an einer anderen'),
        ('oberklasse', 'Oberklasse', 'Wird beerbt, aber nicht gehalten'),
        ('frei', 'Freistehend', 'Haengt an nichts — der eigentliche Befund'),
    )

    #: Woran eine Django-Klasse zu erkennen ist. Ueber die Oberklasse, nicht
    #: ueber den Namen: `PersonListPage` ist keine Ansicht, `SkillsView(View)`
    #: schon.
    DJANGO_BASEN = {
        'model': ('Model',),
        'ansicht': ('View', 'TemplateView', 'ListView', 'DetailView',
                    'APIView', 'ViewSet'),
        'formular': ('Form', 'ModelForm', 'FormSet'),
        'test': ('TestCase', 'TransactionTestCase', 'SimpleTestCase',
                 'BasisTest', 'LiveServerTestCase'),
        'ausnahme': ('Exception', 'Error', 'BaseException'),
        'aufzaehlung': ('Enum', 'IntEnum', 'StrEnum', 'TextChoices',
                        'IntegerChoices'),
    }

    def kategorien(self):
        u"""Jede Klasse in genau einen Topf.

        DIE FRAGE (Edgar, 24.08.2026)
        =============================
            „bei Klassenmodell steht 1004 Klassen, wenn ich aber die
             Bereiche aufzähle die gelistet sind, komme ich auf unter 50.
             Wo ist der Rest? Kategorisiere sie alle"

        Das Bild zeigt eine NACHBARSCHAFT — Wurzel plus n Schritte. Am
        groessten Ast von CamTrack sind das 17 Kaesten, und tiefer wird es
        nicht. Der Rest fehlt nicht im Bild, er haengt an nichts::

            Klassen gesamt        1004
            irgendwo gehalten       71
            als Oberklasse          26
            weder noch             908

        908 von 1004 — das ist die Antwort auf „wo ist der Rest", und sie
        ist unangenehm. Aber nicht jede davon ist ein Versaeumnis: Ein
        Django-Model wird vom ORM erzeugt, eine Ansicht vom URL-Router,
        eine Ausnahme wird geworfen. Diese Einteilung trennt, was
        SYSTEMBEDINGT frei steht, von dem, was frei steht, weil niemand es
        eingehaengt hat.
        """
        gehalten = {z for k in self.klassen.values()
                    for _f, z, _v in k.haelt if z in self.klassen}
        basen = {b for k in self.klassen.values() for b in k.basen
                 if b in self.klassen}
        toepfe = {schluessel: [] for schluessel, _l, _e in self.KATEGORIEN}
        for name in sorted(self.klassen):
            toepfe[self._topf(self.klassen[name], gehalten, basen)].append(name)
        return [{'key': schluessel, 'label': etikett, 'erklaerung': erklaerung,
                 'namen': toepfe[schluessel], 'zahl': len(toepfe[schluessel])}
                for schluessel, etikett, erklaerung in self.KATEGORIEN]

    def _topf(self, k, gehalten, basen):
        for schluessel, endungen in self.DJANGO_BASEN.items():
            if any(b.endswith(endungen) for b in k.basen):
                return schluessel
        if 'test' in k.datei.lower() or '/tests/' in '/' + k.datei:
            return 'test'
        if k.name.endswith(('Error', 'Exception')):
            return 'ausnahme'
        if any(d in ('dataclass',) for d in k.dekorateure):
            return 'daten'
        # Eine Klasse ohne jede Methode ist ein Wert mit Namen. Mit genau
        # einer (`__init__`) auch — sie tut nichts, sie haelt nur.
        if k.methodenzahl <= 1 and not k.haelt:
            return 'daten'
        if k.nur_statisch:
            return 'werkzeug'
        if k.name in gehalten:
            return 'im_baum'
        if k.name in basen:
            return 'oberklasse'
        return 'frei'

    def kennzahlen(self):
        alle = len(self.klassen)
        gehalten = {z for k in self.klassen.values()
                    for _f, z, _v in k.haelt if z in self.klassen}
        erben = {b for k in self.klassen.values() for b in k.basen
                 if b in self.klassen}
        return {
            'klassen': alle,
            'im_baum': len(gehalten),
            'oberklassen': len(erben),
            'beziehungen': len(self.beziehungen()),
        }


__all__ = ['Klassenmodell', 'Klasse', 'Feld', 'Beziehung']
