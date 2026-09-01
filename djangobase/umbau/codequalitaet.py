# -*- coding: utf-8 -*-
u"""Code-Qualität mit drei etablierten Werkzeugen messen.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „Dann brauche ich ein Tool zur Evaluierung der Code-Qualität, davon
     sollte es schon einige geben. Mach einen Button dazu der Code-Qualität
     mit 2-3 Methoden überprüft und eine Ausgabe auf der Seite macht"

„Davon sollte es schon einige geben" — richtig, und deshalb ist hier nichts
selbst gebaut. Drei Verfahren, die sich nicht überschneiden:

    Verfahren        Werkzeug      misst                       Fund
    ─────────────────────────────────────────────────────────────────────
    Komplexität      radon (cc)    Verzweigungen je Funktion   zu verwickelt
    Wartbarkeit      radon (mi)    Umfang + Verzweigung/Datei  zu viel drin
    Fehler           pyflakes      unbenutzt, undefiniert      echter Fehler
    Stil             pycodestyle   PEP 8                       Formsache

WARUM ALLE VIER UND NICHT EINES
===============================
Sie widersprechen einander regelmäßig, und das ist der Nutzen. Eine Datei
kann fehlerfrei nach pyflakes sein und trotzdem einen Wartbarkeitsindex im
Keller haben — dann ist nichts kaputt, aber niemand traut sich hinein.
Umgekehrt ist ein unbenutzter Import kein Komplexitätsproblem und wird von
radon nie gemeldet.

`pyflakes` findet ECHTE Fehler (ein Name, den es nicht gibt), `pycodestyle`
nur Formsachen (eine Zeile über 79 Zeichen). Beides in einen Topf zu werfen
ist der Grund, warum Leute solche Berichte wegklicken.

WAS NICHT GEMESSEN WIRD
=======================
JavaScript. Dafür wäre ESLint zuständig, das eine Node-Installation und
eine Konfigurationsdatei je Projekt braucht. Solange das nicht steht, sagt
die Seite lieber nichts, als etwas Halbes zu behaupten.
"""
import ast
from collections import Counter, defaultdict
from pathlib import Path

from .klassenmodell import AUS
from .codezahlen import DATEN, GROESSTE_QUELLDATEI

#: So viele Treffer je Verfahren werden gezeigt. Wer mehr will, ruft das
#: Werkzeug auf der Kommandozeile.
ZEIGEN = 15

#: Befunde, die BEREITS ein eigenes Werkzeug hat. Sie werden gezaehlt und
#: benannt, aber nicht noch einmal aufgelistet.
#:
#: KEINE DUPLIKATE (Edgar, 25.08.2026)
#: ===================================
#: `pyflakes` meldet unbenutzte Einfuhren — und genau die meldet
#: `tote-importe` seit Kriterium 5, mit Wissen, das `pyflakes` nicht hat
#: (Seiteneffekt-Module wie `signals`, `__all__`-Eintraege, Namen in
#: Zeichenketten). Zwei Werkzeuge fuer denselben Befund heisst: zwei
#: Listen, die auseinanderlaufen, und ein Nutzer, der zweimal dasselbe
#: abarbeitet.
#:
#: Der Befund bleibt sichtbar — als Zahl mit dem Namen des Werkzeugs, das
#: ihn fuehrt. Weglassen waere schlimmer als doppelt melden.
ANDERSWO = {
    'UnusedImport': 'tote-importe',
    'ImportStarUsed': 'tote-importe',
    'FStringMissingPlaceholders': 'fix-fzeichenkette',
}

#: Ab diesem Rang gilt eine Funktion als zu verwickelt. radon vergibt
#: A (1-5) bis F (>40); B ist noch gutmütig, ab C wird es Arbeit.
KOMPLEX_AB = 'C'

#: Unter diesem Wartbarkeitsindex (0-100) wird eine Datei zum Problem.
#: radon selbst nennt <10 rot, <20 gelb.
WARTBAR_UNTER = 20.0


def _ist_gewollt(zeilen, nummer):
    u"""Trägt die gemeldete Zeile ein ``# noqa``?

    ROHES PYFLAKES ACHTET NICHT DARAUF (24.08.2026)
    ===============================================
    Der erste Lauf meldete **299 Meldungen, davon 245 unbenutzte
    Einfuhren**. Nachgezählt trugen **211 davon ein ``# noqa``** — sie
    sind die öffentliche Schnittstelle der Pakete::

        from app.views._shared import (  # noqa: F401
            _analysis_jobs, _save_settings, …

    `flake8` achtet auf die Marke, die reine Bibliothek `pyflakes` nicht.
    Ohne diese Prüfung ertranken 19 echte Funde in 211 gewollten — darunter
    eine Testmethode, die zweimal denselben Namen trug und deshalb NIE lief.
    Ein Bericht, den niemand durchsieht, findet nichts.
    """
    if not 1 <= nummer <= len(zeilen):
        return False
    return 'noqa' in zeilen[nummer - 1].lower()


def _annotationsketten(baum):
    u"""Namen, die nur in einer Annotations-Zeichenkette stehen.

    PYFLAKES LIEST JEDE ZEICHENKETTE IN EINER ANNOTATION ALS TYP
    ============================================================
    In Python ist eine Annotation, die eine Zeichenkette ist, eine
    Vorwaertsreferenz: ``x: "MeineKlasse"``. pyflakes parst sie deshalb
    als Code — und zwar JEDE Zeichenkette im Annotationsteilbaum, auch
    die Argumente eines Aufrufs.

    Blender-Addons deklarieren ihre Eigenschaften seit 2.80 genau so::

        region: EnumProperty(name="Region", default="TORSO")

    Das ist dort keine Stilfrage, sondern Pflicht. pyflakes meldet
    daraufhin ``undefined name 'Region'`` und ``undefined name 'TORSO'``
    — und zwar als ECHTEN Fehler, die schwerste Kategorie dieses
    Werkzeugs. Gemessen am 01.09.2026 in ``HumanBodyBlender``: 110 von
    226 „Echten Fehlern" waren Beschriftungen wie ``Farbe``, ``Name``,
    ``Region``. Zum Vergleich derselbe Code als Zuweisung::

        region = EnumProperty(name="Region")   -> nur EnumProperty fehlt

    DIE TRENNLINIE IST DER AUFRUF: Verworfen werden nur Zeichenketten,
    die INNERHALB eines Aufrufs in der Annotation stehen. Die Annotation
    selbst (``x: "MeineKlasse"``) und Zeichenketten in einem Index
    (``Optional["MeineKlasse"]``) bleiben, was sie sind — echte
    Vorwaertsreferenzen, und ein fehlender Name dort ist ein Befund.

    ZWEI MELDUNGEN, EIN GRUND: Ist die Beschriftung ein einzelnes Wort
    (``"Region"``), parst pyflakes sie und meldet ``UndefinedName``. Hat
    sie ein Leerzeichen (``"Alpha Channel"``, ``"Material thickness
    (Solidify)"``), scheitert das Parsen und pyflakes meldet
    ``ForwardAnnotationSyntaxError``. Beide sind dasselbe Fehlurteil,
    und nach dem ersten Fix blieben allein in `properties.py` 40 der
    zweiten Sorte stehen. Deshalb kommen beide hier heraus.

    Zurueck kommt ``{(zeile, wert)}`` — der Wert ist genau das, was in
    ``m.message_args[0]`` steht: der Name bzw. die ganze Zeichenkette.
    """
    heraus = set()

    def namen_in(kette, zeile):
        try:
            innen = ast.parse(kette, mode='eval')
        except SyntaxError:
            heraus.add((zeile, kette))
            return
        for k in ast.walk(innen):
            if isinstance(k, ast.Name):
                heraus.add((zeile, k.id))

    def aus_aufruf(knoten):
        for k in ast.walk(knoten):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                namen_in(k.value, k.lineno)

    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.AnnAssign):
            continue
        for teil in ast.walk(knoten.annotation):
            if isinstance(teil, ast.Call):
                for arg in list(teil.args) + [k.value for k in teil.keywords]:
                    aus_aufruf(arg)
    return heraus


class Treffer:
    u"""Eine Fundstelle — dieselbe Form für alle vier Verfahren."""

    __slots__ = ('datei', 'zeile', 'name', 'wert', 'text')

    def __init__(self, datei, zeile, name, wert, text):
        self.datei = datei
        self.zeile = zeile
        self.name = name
        #: Die Zahl, nach der sortiert wird (Komplexität, MI, Anzahl).
        self.wert = wert
        self.text = text

    def als_dict(self):
        return dict((f, getattr(self, f)) for f in self.__slots__)


class Verfahren:
    u"""Ein Messverfahren mit seinem Ergebnis."""

    def __init__(self, name, werkzeug, misst, nachkomma=0):
        self.name = name
        self.werkzeug = werkzeug
        self.misst = misst
        #: Wie genau der Wert dieses Verfahrens ist. Der Wartbarkeitsindex
        #: misst 15,2 — mit null Nachkommastellen stuende dort „15", und
        #: die Zahl waere um genau den Teil aermer, der sie aussagt.
        #: Die Vorlage reicht das an `{{ t.wert|de:v.nachkomma }}` durch,
        #: statt das Format hier nachzubauen.
        self.nachkomma = nachkomma
        self.treffer = []
        self.zahlen = {}
        #: Gesetzt, wenn das Werkzeug fehlt — dann keine leere Liste zeigen,
        #: die wie „nichts gefunden" aussieht.
        self.fehlt = ''
        self.satz = ''

    def als_dict(self):
        return {
            'name': self.name, 'werkzeug': self.werkzeug,
            'misst': self.misst, 'fehlt': self.fehlt, 'satz': self.satz,
            'nachkomma': self.nachkomma,
            'zahlen': self.zahlen,
            'treffer': [t.als_dict() for t in self.treffer[:ZEIGEN]],
            'mehr': max(0, len(self.treffer) - ZEIGEN),
        }


class Codequalitaet:
    u"""Misst ein Projektverzeichnis mit allen vorhandenen Verfahren."""

    def __init__(self, wurzel, gitfilter=None, ausser=None):
        self.wurzel = Path(wurzel)
        #: Verzeichnisnamen, die nicht zum Projektcode gehoeren.
        #:
        #: EINE LISTE, NICHT ZWEI (29.08.2026): Diese Messung hatte mit
        #: ``klassenmodell.AUS`` eine eigene Meinung, und die kannte
        #: ``_anlassfall`` nicht — das Wegwerf-Verzeichnis des
        #: Anlassfall-Checks, in dem absichtlich kaputter Code steht. Drei
        #: „Echte Fehler" im Bericht kamen von dort. Wer einen Satz
        #: mitgibt (`Werkzeug.ausgeschlossen()`), misst dieselbe Menge wie
        #: jedes andere Werkzeug; ohne bleibt es bei ``AUS``.
        self.ausser = frozenset(ausser) if ausser else frozenset(AUS)
        #: Was ``.gitignore`` ausnimmt, ist nicht der Code des Projekts.
        #:
        #: DEN FILTER GAB ES SCHON (25.08.2026)
        #: ====================================
        #: `djangobase.skills.gitfilter.GitFilter` beantwortet genau diese
        #: Frage, und `Werkzeug.pfade()` geht seit dem 18.08. darüber —
        #: „der eine Weg ins Dateisystem". Dieses Modul hatte eine eigene
        #: Meinung und maß deshalb auch `_build_yolo_704.py`, ein
        #: ad-hoc-Skript, das git gar nicht kennt.
        #:
        #: Bleibt ``None``, wenn niemand einen mitgibt — dann misst es wie
        #: bisher alles. Ein Werkzeug ohne git soll nicht stehenbleiben.
        self.gitfilter = gitfilter
        self.dateien = []
        self.verfahren = []
        #: Was beim MESSEN schiefging — ``[(datei, verfahren, grund)]``.
        #:
        #: WARUM DAS EIN BEFUND IST UND KEIN `continue` (24.08.2026)
        #: ========================================================
        #: Jede Messung stand vorher hinter einem stummen
        #: ``except: continue``. Eine Datei, die nicht parst, verschwand
        #: damit aus der Statistik — und aus dem Bericht. Genau so hat
        #: `pycodestyle` einen ganzen Lauf lang „0 Abweichungen in 0
        #: Regeln" gemeldet, während jede einzelne Datei am
        #: ``assert not kwargs`` scheiterte.
        #:
        #: Eine Datei ohne gültige Syntax ist der schwerste Fund, den es
        #: gibt. Sie zu überspringen ist das Gegenteil von messen.
        self.pannen = []

    def _panne(self, datei, verfahren, grund):
        self.pannen.append((datei, verfahren,
                            '%s: %s' % (type(grund).__name__, grund)
                            if isinstance(grund, BaseException) else grund))

    # ── einlesen ────────────────────────────────────────────────
    def _quellen(self):
        u"""Jede ``.py``, die Quelltext ist — ohne Laufzeitdaten."""
        raus = []
        for pfad in sorted(self.wurzel.rglob('*.py')):
            # Nur der Teil INNERHALB des Projekts — siehe `Codezahlen._innen`.
            # Mit dem absoluten Pfad verschwand ein Projekt unter
            # `…\Temp\…` restlos, weil `temp` in `DATEN` steht.
            try:
                teile = pfad.relative_to(self.wurzel).parts
            except ValueError:
                teile = pfad.parts
            if any(t in self.ausser for t in teile):
                continue
            if any(t.lower() in DATEN for t in teile[:-1]):
                continue
            # Was git nicht kennt, ist nicht der Code des Projekts.
            # `erlaubt()` prüft selbst, ob git geantwortet hat, und lässt
            # ohne Antwort alles durch — hier also kein zweiter Wächter.
            if self.gitfilter is not None and not self.gitfilter.erlaubt(pfad):
                continue
            try:
                if pfad.stat().st_size > GROESSTE_QUELLDATEI:
                    continue
                text = pfad.read_text(encoding='utf-8', errors='replace')
            except OSError as exc:
                self._panne(str(pfad), 'Lesen', exc)
                continue
            raus.append((str(pfad.relative_to(self.wurzel)).replace('\\', '/'),
                         pfad, text))
        return raus

    def messen(self):
        self.dateien = self._quellen()
        self.verfahren = [
            self._komplexitaet(),
            self._wartbarkeit(),
            self._fehler(),
            self._stil(),
        ]
        return self

    # ── 1. Komplexität ──────────────────────────────────────────
    def _komplexitaet(self):
        v = Verfahren(u'Zyklomatische Komplexität', 'radon',
                      u'Wie viele Verzweigungen hat eine Funktion? '
                      u'Jedes if, jede Schleife, jedes except zählt eins.')
        try:
            from radon.complexity import cc_rank, cc_visit
        except ImportError:
            v.fehlt = 'radon'
            return v
        raenge = Counter()
        for kurz, _pfad, text in self.dateien:
            try:
                bloecke = cc_visit(text)
            except (SyntaxError, ValueError) as exc:
                self._panne(kurz, v.name, exc)
                continue
            for b in bloecke:
                rang = cc_rank(b.complexity)
                raenge[rang] += 1
                if rang >= KOMPLEX_AB:
                    v.treffer.append(Treffer(
                        kurz, b.lineno, b.name, b.complexity,
                        u'Rang %s — %d Verzweigungen' % (rang, b.complexity)))
        v.treffer.sort(key=lambda t: -t.wert)
        gesamt = sum(raenge.values())
        v.zahlen = {'gemessen': gesamt,
                    'raenge': [(r, raenge.get(r, 0)) for r in 'ABCDEF'],
                    'auffaellig': len(v.treffer)}
        v.satz = (u'%d von %d Funktionen liegen bei Rang %s oder schlechter'
                  % (len(v.treffer), gesamt, KOMPLEX_AB))
        return v

    # ── 2. Wartbarkeit ──────────────────────────────────────────
    def _wartbarkeit(self):
        v = Verfahren(u'Wartbarkeitsindex', 'radon',
                      u'Umfang, Verzweigung und Kommentaranteil einer Datei '
                      u'zu einer Zahl von 0 bis 100 verrechnet.',
                      nachkomma=1)
        try:
            from radon.metrics import mi_visit
        except ImportError:
            v.fehlt = 'radon'
            return v
        werte = []
        for kurz, _pfad, text in self.dateien:
            try:
                mi = mi_visit(text, True)
            except (SyntaxError, ValueError, ZeroDivisionError) as exc:
                self._panne(kurz, v.name, exc)
                continue
            werte.append(mi)
            if mi < WARTBAR_UNTER:
                v.treffer.append(Treffer(
                    kurz, 0, kurz.split('/')[-1], round(mi, 1),
                    u'Index %.1f von 100' % mi))
        v.treffer.sort(key=lambda t: t.wert)
        v.zahlen = {
            'gemessen': len(werte),
            'mittel': round(sum(werte) / max(1, len(werte)), 1),
            'auffaellig': len(v.treffer),
        }
        v.satz = (u'%d von %d Dateien unter %.0f; Mittel %.1f'
                  % (len(v.treffer), len(werte), WARTBAR_UNTER,
                     v.zahlen['mittel']))
        return v

    # ── 3. Echte Fehler ─────────────────────────────────────────
    def _fehler(self):
        v = Verfahren(u'Echte Fehler', 'pyflakes',
                      u'Namen, die es nicht gibt. Importe, die niemand '
                      u'benutzt. Zweimal dasselbe definiert.')
        try:
            from pyflakes.checker import Checker
        except ImportError:
            v.fehlt = 'pyflakes'
            return v
        arten = Counter()
        gewollt = 0
        kettennamen = 0
        fremd = Counter()
        for kurz, _pfad, text in self.dateien:
            try:
                baum = ast.parse(text, filename=kurz)
            except (SyntaxError, ValueError) as exc:
                self._panne(kurz, u'Syntax', exc)
                continue
            try:
                meldungen = Checker(baum, filename=kurz).messages
            except Exception as exc:
                # pyflakes stolpert an einzelnen Dateien. Das darf nicht
                # den ganzen Lauf kosten — aber auch nicht stumm bleiben.
                self._panne(kurz, v.name, exc)
                continue
            zeilen = text.splitlines()
            beschriftung = _annotationsketten(baum)
            for m in meldungen:
                if _ist_gewollt(zeilen, m.lineno):
                    gewollt += 1
                    continue
                art = type(m).__name__
                if (art in ('UndefinedName', 'ForwardAnnotationSyntaxError')
                        and m.message_args
                        and (m.lineno, m.message_args[0]) in beschriftung):
                    # Eine Beschriftung, kein Name — siehe
                    # `_annotationsketten`. Gezaehlt, nicht verschwiegen.
                    kettennamen += 1
                    continue
                if art in ANDERSWO:
                    fremd[ANDERSWO[art]] += 1
                    continue
                arten[art] += 1
                v.treffer.append(Treffer(
                    kurz, m.lineno, art, 1,
                    m.message % m.message_args))
        # Nach Häufigkeit der ART, damit gleiche Fälle beieinanderstehen.
        v.treffer.sort(key=lambda t: (-arten[t.name], t.datei, t.zeile))
        v.zahlen = {'gesamt': sum(arten.values()),
                    'arten': arten.most_common(8), 'gewollt': gewollt,
                    'kettennamen': kettennamen,
                    'anderswo': fremd.most_common()}
        v.satz = (u'%d Meldungen in %d Arten' % (sum(arten.values()),
                                                 len(arten)))
        if gewollt:
            v.satz += u' — dazu %d ausdrücklich erlaubt (# noqa)' % gewollt
        if kettennamen:
            v.satz += (u'; %d Beschriftungen in Annotationen (keine Namen)'
                       % kettennamen)
        for werkzeug, zahl in fremd.most_common():
            v.satz += u'; %d führt `%s`' % (zahl, werkzeug)
        return v

    #: Dateien, in denen ein Projekt seinen Stil festlegt — in der
    #: Reihenfolge, in der pycodestyle selbst sie liest.
    STILDATEIEN = ('setup.cfg', 'tox.ini', '.pycodestyle')

    def _stilkonfig(self):
        u"""Pfad zur Stil-Konfiguration des Projekts, oder ``None``."""
        for name in self.STILDATEIEN:
            pfad = self.wurzel / name
            if pfad.is_file():
                return str(pfad)
        return None

    # ── 4. Stil ─────────────────────────────────────────────────
    def _stil(self):
        v = Verfahren(u'Stil (PEP 8)', 'pycodestyle',
                      u'Formsachen: Zeilenlänge, Leerzeichen, Einrückung. '
                      u'Kein Fehler — aber die Grammatik der Sprache.')
        try:
            import pycodestyle
        except ImportError:
            v.fehlt = 'pycodestyle'
            return v

        gezaehlt = Counter()
        stellen = {}
        je_datei = defaultdict(Counter)
        wurzel = str(self.wurzel).replace('\\', '/').rstrip('/') + '/'

        class _Sammler(pycodestyle.BaseReport):
            u"""Sammelt statt zu drucken — je Regel Anzahl und ein Beispiel."""

            def error(self, zeilennummer, versatz, text, pruefung):
                schluessel = super(_Sammler, self).error(
                    zeilennummer, versatz, text, pruefung)
                if schluessel:
                    code = text[:4]
                    gezaehlt[code] += 1
                    kurz = str(self.filename).replace('\\', '/')
                    if kurz.startswith(wurzel):
                        kurz = kurz[len(wurzel):]
                    if code not in stellen:
                        stellen[code] = (kurz, zeilennummer, text)
                    # Je Regel zaehlen, IN WIE VIELEN Dateien sie steht.
                    je_datei[code][kurz] += 1
                return schluessel

        # DER DOKUMENTIERTE WEG (24.08.2026). Vorher stand hier
        # `Checker(pfad, quiet=True, options=wache.options)` — und
        # `Checker.__init__` hat ein `assert not kwargs`, sobald `options`
        # gesetzt ist. Jede Datei flog also in den `except`-Zweig, und der
        # Bericht meldete „0 Abweichungen in 0 Regeln" fuer einen
        # Quelltext mit reichlich langen Zeilen. Ein Verfahren, das bei
        # jedem Fehlschlag „alles gut" sagt, ist schlimmer als keines —
        # deshalb werden Fehlschlaege jetzt GEZAEHLT und angezeigt.
        # DAS PROJEKT SAGT, WIE LANG EINE ZEILE SEIN DARF (26.08.2026)
        # ============================================================
        # Hier stand `StyleGuide(quiet=True)` — also pycodestyles Vorgabe
        # von 79 Zeichen. Gemessen an CamTrack: von 3320 Abweichungen waren
        # **3009 genau diese eine Regel**. Das Projekt schreibt erkennbar
        # auf 100 (nur 438 Zeilen sind laenger, 233 ueber 120).
        #
        # Ein Bericht, der zu 91 % aus einer Regel besteht, die das Projekt
        # nie angenommen hat, ist unbrauchbar: Die 311 echten Befunde
        # daneben sieht niemand mehr. Dieselbe Sorte Fehler wie die
        # Fehlalarme aus `{% comment %}`-Bloecken — das Werkzeug misst
        # etwas, wonach niemand gefragt hat.
        #
        # `setup.cfg` / `tox.ini` im Projekt entscheiden jetzt. Ohne solche
        # Datei bleibt es bei pycodestyles Vorgabe.
        wache = pycodestyle.StyleGuide(quiet=True,
                                       config_file=self._stilkonfig())
        wache.init_report(_Sammler)
        gescheitert = 0
        try:
            wache.check_files([str(p) for _k, p, _t in self.dateien])
        except Exception as exc:                     # pragma: no cover
            gescheitert = len(self.dateien)
            v.fehlt = u'pycodestyle brach ab: %s' % exc
            return v

        # WIE VIELE DATEIEN, NICHT NUR WIE OFT (25.08.2026)
        # =================================================
        # Hier stand die Fundstelle des ERSTEN Vorkommens neben der
        # GESAMTZAHL. Der Bericht las sich damit als
        # „_build_yolo_704.py:45 — 2841x" — bei einer Datei mit 47 Zeilen.
        # Tatsaechlich verteilten sich die 2841 auf 513 Dateien.
        #
        # Eine Zahl neben einem Dateinamen wird als Zahl DIESER Datei
        # gelesen. Jetzt steht die Zahl der Dateien dabei, und der Ort ist
        # die Datei mit den MEISTEN Treffern statt der zufaellig ersten.
        for code, zahl in gezaehlt.most_common():
            wo = je_datei[code]
            schlimmste, dort = wo.most_common(1)[0] if wo else stellen[code][:1] + (0,)
            zeile = stellen[code][1] if schlimmste == stellen[code][0] else 0
            text = stellen[code][2]
            v.treffer.append(Treffer(
                schlimmste, zeile, code, zahl,
                u'%dx in %d Datei(en) — %s (hier %dx)'
                % (zahl, len(wo), text[5:], dort)))
        # NICHT `arten` nennen (24.08.2026): Bei „Echte Fehler" ist das eine
        # LISTE von Paaren, hier waere es eine Zahl. Die Vorlage lief mit
        # `{% for art, zahl in v.zahlen.arten %}` in ein
        # `TypeError: 'int' object is not iterable`. Gleicher Name, andere
        # Bauart — der Fehler wartet auf den, der es nicht nachliest.
        v.zahlen = {'gesamt': sum(gezaehlt.values()),
                    'regeln': len(gezaehlt), 'gescheitert': gescheitert}
        v.satz = (u'%d Abweichungen in %d Regeln'
                  % (sum(gezaehlt.values()), len(gezaehlt)))
        return v

    # ── Auskunft ────────────────────────────────────────────────
    def als_liste(self):
        return [v.als_dict() for v in self.verfahren]

    def kennzahlen(self):
        u"""Die Kopfzahlen — je Verfahren eine."""
        nach_name = dict((v.werkzeug + v.name, v) for v in self.verfahren)
        raus = {'dateien': len(self.dateien)}
        for v in self.verfahren:
            raus[v.name] = v.satz or (u'%s fehlt' % v.fehlt)
        raus['_'] = nach_name
        return raus


__all__ = ['Codequalitaet', 'Verfahren', 'Treffer', 'ZEIGEN']
