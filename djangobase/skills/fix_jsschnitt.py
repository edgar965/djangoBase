# -*- coding: utf-8 -*-
u"""FixJsSchnitt - eine zu grosse JS-Datei teilen, mit Netz gegen acht Fallen.

WARUM DAS NETZ DER EIGENTLICHE INHALT IST (16.08.2026)
======================================================
Eine JS-Datei an einer Funktionsgrenze zu zerschneiden ist trivial. Was daran
schiefgeht, ist es nicht: An EINEM Tag sind bei genau diesem Handgriff acht
verschiedene Fehler passiert, und JEDER davon nimmt die ganze Seite mit - der
Browser verwirft ein Modul, das beim Laden wirft, komplett, samt aller Namen,
die es auf ``window`` legen wollte.

    1  Zirkel            beide Haelften brauchen einander
    2  super() fehlt     eine Klasse, die ploetzlich erbt
    3  Selbstbezug       ``Klasse.KONSTANTE`` in einer Methode, die wandert
    4  Duplicate export  ``export`` an der Definition UND in einer Liste
    5  geteilter Zustand ein freies ``let`` wandert mit, wird drueben geschrieben
    6  Modulebene-Global ``SeitenDaten.wert(…)`` ausserhalb jeder Funktion
    7  read-only Import  ein ``let`` ueber die Grenze ZUWEISEN
    8  Temporal Dead Zone der Rueck-Import holt ein ``const``, das es noch nicht gibt

Dazu zwei, die nicht das Laden treffen: ein Schnitt, der sich nicht LOHNT (beide
Haelften bleiben ueber der Grenze), und eine Datei, die IN SICH eine Klasse ist -
die teilt man ueber Vererbung, nicht mit einer Zeilennummer.

WAS ER TUT UND WAS NICHT
========================
Er schreibt die mechanische Haelfte: Importe beider Seiten ausrechnen, Exporte
setzen, den Rueckverweis legen. Die inhaltliche Ueberschrift - WAS beantwortet
die neue Datei? - bleibt Handarbeit; ohne sie steht ein Platzhalter drin, den
man nicht uebersehen kann.
"""
import re
from collections import Counter

from .fixer import Aenderung, Fixer, Vorschau

#: Namen, die eine Seite mitbringt. Ein Zugriff darauf auf Modulebene ist Falle 6.
SEITEN_GLOBALS = ("SeitenDaten", "OptZustand", "ErgSpalten", "LaufKopf", "ErgTab",
                  "WfUrteil", "WfGesamt", "LaufAnzeige", "LaufSperre", "Chart")


class Haelfte:
    """Ein Stueck JavaScript und was darin steht.

    ALLES HIER WIRD EINMAL GERECHNET UND GEMERKT (16.08.2026). ``_bester_schnitt``
    legt je Datei rund zwanzig Haelften-Paare an und fragt jedes mehrfach; als die
    Eigenschaften noch bei jedem Zugriff neu suchten, kostete ein Knopfdruck
    177.246 Regex-Laeufe und 73 Sekunden - gemessen mit ``cProfile``, nicht
    geschaetzt.
    """

    #: Ein Bezeichner, dem KEIN Punkt vorausgeht - ``a.name`` zaehlt also nicht.
    BEZEICHNER = re.compile(r"(?<![.\w])([A-Za-z_$][\w$]*)")

    def __init__(self, zeilen):
        self.zeilen = list(zeilen)
        self._merker = {}

    def _gemerkt(self, schluessel, bauen):
        if schluessel not in self._merker:
            self._merker[schluessel] = bauen()
        return self._merker[schluessel]

    @property
    def text(self):
        return self._gemerkt("text", lambda: "\n".join(self.zeilen))

    @property
    def bezeichner(self):
        """Jeder freistehende Name im Text - EINMAL gelesen.

        Der Ersatz fuer „je Name einmal den ganzen Text durchsuchen": Ein
        Durchlauf, danach beantwortet ein Mengenschnitt dieselbe Frage.
        """
        return self._gemerkt(
            "bezeichner", lambda: set(self.BEZEICHNER.findall(self.text)))

    @property
    def namen(self):
        return self._gemerkt("namen", lambda: set(re.findall(
            r"^(?:export )?(?:async )?(?:function|class|const|let|var) (\w+)",
            self.text, re.M)))

    @property
    def exportierte(self):
        def bauen():
            aus = set(re.findall(
                r"^export\s+(?:async\s+)?(?:function|class|const|let|var)\s+(\w+)",
                self.text, re.M))
            for m in re.finditer(r"^export\s*\{([^}]*)\}", self.text, re.M):
                for teil in m.group(1).split(","):
                    n = teil.strip().split(" as ")[-1].strip()
                    if n:
                        aus.add(n)
            return aus
        return self._gemerkt("exportierte", bauen)

    @property
    def freie_variablen(self):
        return self._gemerkt("freie", lambda: set(
            re.findall(r"^(?:let|var) (\w+)", self.text, re.M)))

    @property
    def modulebene_globals(self):
        def bauen():
            aus, tiefe = set(), 0
            for z in self.zeilen:
                nackt = z.strip()
                if tiefe == 0 and nackt and not nackt.startswith(("//", "*", "/*")):
                    # Einzeiler wie ``function f(){ Z.x = 1; }`` sind KEIN
                    # Modulebene-Zugriff - alles nach der Klammer ist Rumpf.
                    vor = z.split("{", 1)[0] if "{" in z else z
                    for g in SEITEN_GLOBALS:
                        if re.search(r"(?<![.\w])%s\s*\." % g, vor):
                            aus.add(g)
                tiefe = max(0, tiefe + z.count("{") - z.count("}"))
            return aus
        return self._gemerkt("globals", bauen)

    @property
    def zuweisungsziele(self):
        """Namen, die hier GESCHRIEBEN werden - fuer Falle 7 (read-only Import).

        Auch das lief vorher je Name einzeln ueber den ganzen Text.
        """
        return self._gemerkt("ziele", lambda: set(re.findall(
            r"(?<![.\w])([A-Za-z_$][\w$]*)\s*(?:=[^=]|\+\+|--|\+=)", self.text)))

    def benutzt(self, namen):
        """Welche dieser Namen kommen hier freistehend vor?

        Frueher eine Regex JE NAME ueber den ganzen Text - der Loewenanteil der
        73 Sekunden. Jetzt ein Mengenschnitt gegen die einmal gelesene
        Bezeichnerliste; dieselbe Antwort, ein Textdurchlauf statt N.
        """
        return set(namen) & self.bezeichner


class Schnitt:
    """Eine Datei, eine Trennlinie - und alles, was dagegen spricht."""

    GRENZE = 200

    def __init__(self, pfad, bei, neuer_name, versioniert=False, zeilen=None):
        self.pfad = pfad
        self.bei = bei                              # 0-basiert
        self.neuer_name = neuer_name
        #: Laedt eine Vorlage die Datei mit ``?v=`` (dann kein Rueck-Import)?
        self.versioniert = versioniert
        # ZEILEN HEREINREICHEN, nicht selbst lesen (16.08.2026): ``_bester_schnitt``
        # probiert je Datei rund zwanzig Trennlinien durch. Mit einem ``read_text``
        # im Konstruktor waren das siebenhundert Dateilesungen fuer einen
        # Knopfdruck - zweiundsiebzig Sekunden. Genau der Fall, den das
        # Nachbarwerkzeug „Arbeit in Schleifen" meldet, hier im Fixer selbst.
        if zeilen is None:
            zeilen = pfad.read_text(encoding="utf-8").split("\n")
        self.oben = Haelfte(zeilen[:bei])
        self.unten = Haelfte(zeilen[bei:])

    # ---- die acht Fallen ----------------------------------------------------
    def warnungen(self):
        aus = []
        if self.oben.benutzt(self.unten.namen) and self.unten.benutzt(self.oben.namen):
            aus.append("Zirkel: beide Hälften brauchen einander")
        doppelt = self.unten.exportierte & self.oben.exportierte
        if doppelt:
            aus.append("Duplicate export: %s" % ", ".join(sorted(doppelt)))
        geteilt = self.unten.freie_variablen & self.oben.benutzt(self.unten.freie_variablen)
        if geteilt:
            aus.append("geteilter Zustand: %s" % ", ".join(sorted(geteilt)))
        globs = self.unten.modulebene_globals
        if globs:
            aus.append("Global auf Modulebene: %s" % ", ".join(sorted(globs)))
        if re.search(r"class \w+ extends", self.unten.text) and \
                not re.search(r"super\s*\(", self.unten.text):
            aus.append("erbende Klasse ohne super()")
        beschrieben = sorted(self.oben.freie_variablen & self.unten.zuweisungsziele)
        if beschrieben:
            aus.append("read-only Import: %s wird unten zugewiesen" % beschrieben[0])
        konstanten = set(re.findall(r"^export const (\w+)", self.oben.text, re.M))
        tdz = self.unten.benutzt(konstanten)
        if tdz:
            aus.append("Temporal Dead Zone: %s ist oben ein const"
                       % ", ".join(sorted(tdz)))
        klassen_unten = re.findall(r"^export class (\w+)", self.unten.text, re.M)
        if klassen_unten and not self.oben.namen:
            aus.append("die Datei IST eine Klasse (%s) - über Vererbung teilen"
                       % ", ".join(klassen_unten))
        for wo, h in (("oben", self.oben), ("unten", self.unten)):
            if len(h.zeilen) + 8 > self.GRENZE:
                aus.append("lohnt nicht: %s bliebe bei ~%d Zeilen"
                           % (wo, len(h.zeilen) + 8))
        return aus

    # ---- der Text ------------------------------------------------------------
    def importzeilen(self, fuer):
        """``import {a as b} from 'x'`` - mit der VOLLEN Form, nicht nur dem Alias."""
        quelle = "\n".join(self.oben.zeilen + self.unten.zeilen)
        haelfte = self.oben if fuer == "oben" else self.unten
        ohne = re.sub(r"^import[^;]*;", "", haelfte.text, flags=re.M | re.S)
        je_modul = {}
        for m in re.finditer(r"import\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]",
                             quelle, re.S):
            for teil in m.group(1).split(","):
                voll = teil.strip()
                if not voll:
                    continue
                benutzt = voll.split(" as ")[-1].strip()
                if re.search(r"(?<![.\w])%s\b" % re.escape(benutzt), ohne):
                    je_modul.setdefault(m.group(2), []).append(voll)
        return ["import {%s} from '%s';" % (", ".join(sorted(v)), k)
                for k, v in sorted(je_modul.items())]

    def neuer_text(self):
        gebraucht = sorted(self.unten.benutzt(self.oben.namen))
        kopf = ["/* <WOFÜR ist diese Datei da? Ein Satz — HANDARBEIT.>",
                "   " + "=" * 72,
                "   Aus %s herausgelöst (%d Zeilen)."
                % (self.pfad.name, len(self.oben.zeilen) + len(self.unten.zeilen)),
                "   " + "=" * 72 + " */"]
        neu = kopf + self.importzeilen("unten")
        if gebraucht and self.versioniert:
            neu += ["// ACHTUNG: %s wird mit ?v= geladen - ein Rück-Import wäre eine"
                    % self.pfad.name,
                    "// ZWEITE Modul-URL. Diese Namen anders beschaffen: %s"
                    % ", ".join(gebraucht)]
        elif gebraucht:
            neu.append("import {%s} from './%s';" % (", ".join(gebraucht),
                                                     self.pfad.name))
        return "\n".join(neu + [""] + self.unten.zeilen)

    def resttext(self):
        gebraucht = sorted(self.unten.benutzt(self.oben.namen))
        text = self.oben.text
        for name in gebraucht:
            text = re.sub(r"^(function|class|const|let) %s\b" % re.escape(name),
                          r"export \1 %s" % name, text, flags=re.M)
        return text + ("\n\n// Herausgelöst am %s: %s\nimport './%s';\n"
                       % ("16.08.2026", self.neuer_name, self.neuer_name))


class FixJsSchnitt(Fixer):
    slug = "fix-jsschnitt"
    titel = "JS-Datei teilen (mit Fallen-Prüfung)"
    tut = ("Teilt jede zu große JS-Datei an ihrer besten Funktionsgrenze — aber "
           "nur, wenn keine der acht bekannten Fallen zuschlägt.")
    warum = ("Ein Modul, das beim Laden wirft, verwirft der Browser komplett — "
             "samt aller window-Namen, teils auch denen der Nachbardateien. "
             "Einmal waren acht Handler auf einen Schlag weg.")
    grenzen = ("Schreibt nur, wo alle acht Prüfungen halten. Der Kopfkommentar "
               "der neuen Datei bleibt ein Platzhalter — WAS sie beantwortet, "
               "weiß nur ein Mensch.")
    kriterium = 3
    dauer = "5–15 s"

    GRENZE = 200
    RAND = 40
    RAUS = ("__pycache__", "node_modules", "venv", "pythonVENV", ".git",
            "sicherung", "backup", "archiv", "_web")

    def _jsdateien(self):
        for pfad in self.pfade("*.js"):
            if not self.erlaubt(pfad):
                continue
            yield pfad

    @property
    def versionierte(self):
        """Alle JS-Dateien, die eine Vorlage mit ``?v=`` laedt - EINMAL gesucht.

        Die erste Fassung durchsuchte je JS-Datei alle Vorlagen: 35 mal denselben
        Text, 73 Sekunden fuer einen Knopfdruck. Genau der Fehler, den das
        Nachbarwerkzeug „Arbeit in Schleifen" meldet - hier im Fixer selbst
        (16.08.2026)."""
        if self._versionierte is None:
            aus = set()
            muster = re.compile(r"([\w.-]+\.js)['\"]?\s*\}?\}?\?v=")
            for pfad in self.pfade("*.html"):
                if not self.erlaubt(pfad):
                    continue
                try:
                    text = pfad.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                aus.update(m.group(1) for m in muster.finditer(text))
            self._versionierte = aus
        return self._versionierte

    def __init__(self):
        self._versionierte = None

    def _bester_schnitt(self, pfad):
        """Die mittigste fallenfreie Trennlinie - oder ``None`` und WARUM keine.

        Rueckgabe ist immer ein Paar ``(schnitt, diagnose)``. Der Diagnosesatz war
        anfangs fuer alle 35 Dateien derselbe („keine Trennlinie ohne Falle") und
        damit wertlos: Er verdeckte, dass 16 dieser Dateien gar keine
        Trennlinie HABEN - sie sind je EINE Klasse und gehoeren ueber Vererbung
        geteilt, nicht an einer Zeilennummer (16.08.2026).
        """
        zeilen = pfad.read_text(encoding="utf-8", errors="replace").split("\n")
        if len(zeilen) <= self.GRENZE:
            return None, ""
        mitte = len(zeilen) / 2
        versioniert = pfad.name in self.versionierte
        beste, blocker, kandidaten = None, Counter(), 0
        for i, z in enumerate(zeilen):
            if not re.match(r"^(?:export )?(?:async )?(?:function|class) \w+", z):
                continue
            if not (self.RAND < i < len(zeilen) - self.RAND):
                continue
            kandidaten += 1
            s = Schnitt(pfad, i, self._neuer_name(pfad, i), versioniert, zeilen)
            warnungen = s.warnungen()
            if warnungen:
                for w in warnungen:
                    blocker[w.split(":")[0].split(" (")[0]] += 1
                continue
            if beste is None or abs(i - mitte) < abs(beste.bei - mitte):
                beste = s
        if beste is not None:
            return beste, ""
        return None, self._diagnose(zeilen, kandidaten, blocker)

    @staticmethod
    def _diagnose(zeilen, kandidaten, blocker):
        """Ein Satz, der sagt, was STATTDESSEN zu tun ist."""
        if not kandidaten:
            klassen = re.findall(r"^(?:export )?class (\w+)", "\n".join(zeilen), re.M)
            if klassen:
                methoden = len(re.findall(r"^\s{2,4}(?:async )?\w+\s*\(",
                                          "\n".join(zeilen), re.M))
                return ("keine Trennlinie: die Datei IST %s (%d Methoden) — "
                        "über Vererbung teilen, nicht an einer Zeilennummer"
                        % (" und ".join(klassen), methoden))
            return ("keine Trennlinie: keine einzige Deklaration am Zeilenanfang "
                    "zwischen Zeile %d und %d" % (FixJsSchnitt.RAND,
                                                  len(zeilen) - FixJsSchnitt.RAND))
        haupt = ", ".join("%s (%dx)" % (w, n) for w, n in blocker.most_common(2))
        return "%d Trennlinien geprüft, alle blockiert — %s" % (kandidaten, haupt)

    @staticmethod
    def _neuer_name(pfad, bei):
        return "%s_teil%d.js" % (pfad.stem, bei)

    def vorschau(self):
        aenderungen = []
        for pfad in sorted(self._jsdateien()):
            zeilen = pfad.read_text(encoding="utf-8", errors="replace").split("\n")
            if len(zeilen) <= self.GRENZE:
                continue
            s, diagnose = self._bester_schnitt(pfad)
            if s is None:
                aenderungen.append(Aenderung(
                    pfad, "%d Zeilen — kein sauberer Schnitt" % len(zeilen),
                    None, [diagnose]))
                continue
            aenderungen.append(Aenderung(
                pfad, "bei Zeile %d teilen -> %s (%d / %d Zeilen)"
                % (s.bei + 1, s.neuer_name, len(s.oben.zeilen), len(s.unten.zeilen)),
                s.resttext(),
                begleiter=(pfad.parent / s.neuer_name, s.neuer_text())))
        return Vorschau(aenderungen,
                        "Der Kopfkommentar der neuen Datei ist ein Platzhalter — "
                        "bitte nach dem Anwenden füllen.")
