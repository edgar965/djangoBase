# -*- coding: utf-8 -*-
u"""FixVermerk - Anzeigeformate mit dem Vermerk versehen, der sie ausnimmt.

DER HAEUFIGSTE „FIX" IST KEIN UMBAU (16.08.2026)
================================================
134 von 204 Kriterium-11-Befunden waren Anzeigeformate: Woerterbuecher, deren
Schluessel woertlich im Frontend stehen. Der Auftrag nimmt sie ausdruecklich aus
(„geht es als JSON an den Browser, bleibt es ein Dictionary") - aber das
Pruefwerk kann es an der Fundstelle nicht wissen.

Die Loesung ist ein Vermerk IM CODE, direkt ueber der Rueckgabe:

    # Dictionary gewollt: geht als JSON an die Stunden-Seite (stunden.js liest
    # expected_end_of_day, expected_p5_eod …)

Das ist kein Grünstellen: Der Vermerk NENNT, wohin die Daten gehen, und ist
damit nachpruefbar. Und er zwingt dazu, die Frage einmal wirklich zu
beantworten, statt sie in einer Ausnahmeliste verschwinden zu lassen.

WAS DIESER FIXER TUT
====================
Er setzt den Vermerk dort, wo die Messung eindeutig ist: mindestens 70 % der
aussagekraeftigen Schluessel stehen im Frontend, und die Fundstelle nennt die
Dateien, in denen sie gefunden wurden. Alles darunter bleibt liegen - „gemischt"
heisst, ein Mensch muss hinsehen.
"""
import ast
import re
from collections import Counter

from .anlassfall import Anlassfall
from .fixer import Aenderung, Fixer, Vorschau

MARKER = "Dictionary gewollt"


class Fundstelle:
    """Ein Rueckgabe-Woerterbuch und wo seine Schluessel im Frontend stehen."""

    def __init__(self, pfad, knoten, schluessel, treffer, quellen):
        self.pfad = pfad
        self.knoten = knoten
        self.schluessel = schluessel
        #: Die Schluessel, die im Frontend vorkommen.
        self.treffer = treffer
        #: Die Frontend-Dateien, in denen sie stehen (hoechstens drei).
        self.quellen = quellen

    @property
    def anteil(self):
        return len(self.treffer) / len(self.schluessel) if self.schluessel else 0.0

    #: Belegstelle des Serialisierungswegs, falls es den gibt.
    serialisiert = ""

    @property
    def vermerk(self):
        """Der Kommentar, der gesetzt wird - er NENNT den Beleg."""
        if self.serialisiert:
            return ("        # Dictionary gewollt: verlässt das Programm als JSON "
                    "über %s — dort wird ein echtes Dictionary gebraucht "
                    "(geprüft mit Skills2 → Anzeigeformat)." % self.serialisiert)
        wo = ", ".join(self.quellen[:3]) or "der Oberfläche"
        return ("        # Dictionary gewollt: geht als JSON an %s (%d von %d "
                "Schlüsseln stehen dort wörtlich, geprüft mit Skills2 → "
                "Anzeigeformat)." % (wo, len(self.treffer), len(self.schluessel)))


class Serialisierungsweg:
    """Muendet diese Funktion nachweislich in ``JsonResponse``/``json.dumps``?

    DER ZWEITE, HAEUFIGERE BELEG (16.08.2026)
    =========================================
    Die Wortsuche im Frontend traegt nur, wenn die Schluessel dort woertlich
    stehen. Sehr oft reicht ein Zwischenschritt - ``{**basis, **zusatz}``, ein
    Umbenennen in JavaScript, eine Tabelle, die generisch ueber ``Object.keys``
    laeuft - und kein einziger Schluessel ist zu finden, obwohl die Daten
    zweifelsfrei den Prozess verlassen.

    Hier wird stattdessen der WEG belegt: Gibt ein Aufrufer das Ergebnis dieser
    Funktion an ``JsonResponse`` oder ``json.dumps`` weiter, ist es ein
    Ausgabeformat - nachpruefbar an Datei und Zeile, nicht behauptet.

    Geprueft werden zwei Formen, mehr nicht:

        return JsonResponse(_daten())          direkt
        d = _daten(); … JsonResponse(d)        ueber eine Variable
    """

    ZIELE = ("JsonResponse", "dumps", "HttpResponse")

    def __init__(self, baeume, importeure):
        self.baeume = baeume
        self.importeure = importeure

    def beleg(self, pfad, funktion):
        """``"views/x.py:88 (JsonResponse)"`` oder ``""``."""
        for datei in {pfad} | self.importeure.get(funktion, set()):
            baum = self.baeume.get(datei)
            if baum is None:
                continue
            treffer = self._in_baum(baum, funktion)
            if treffer:
                return "%s:%d (%s)" % (datei.name, treffer[0], treffer[1])
        return ""

    def _in_baum(self, baum, funktion):
        for f in ast.walk(baum):
            if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            namen = self._variablen_aus(f, funktion)
            for k in ast.walk(f):
                if not isinstance(k, ast.Call):
                    continue
                ziel = self._name(k.func)
                if ziel not in self.ZIELE or not k.args:
                    continue
                erstes = k.args[0]
                if isinstance(erstes, ast.Call) and \
                        self._name(erstes.func) == funktion:
                    return k.lineno, ziel
                if isinstance(erstes, ast.Name) and erstes.id in namen:
                    return k.lineno, ziel
        return None

    def _variablen_aus(self, funktion_knoten, funktion):
        """Namen, denen das Ergebnis von ``funktion`` zugewiesen wurde."""
        aus = set()
        for k in ast.walk(funktion_knoten):
            if isinstance(k, ast.Assign) and isinstance(k.value, ast.Call) and \
                    self._name(k.value.func) == funktion:
                for ziel in k.targets:
                    if isinstance(ziel, ast.Name):
                        aus.add(ziel.id)
        return aus

    @staticmethod
    def _name(knoten):
        if isinstance(knoten, ast.Name):
            return knoten.id
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        return ""


class FixVermerk(Fixer):
    slug = "fix-vermerk"
    #: Der Befund, den dieser Fixer behebt — als Kennung des
    #: Werkzeugs, das ihn meldet. Die Oberflaeche zeigt daraus die
    #: NUMMER der Pruefung in der Tabelle statt einer
    #: Kriteriums-Nummer, die dort nirgends steht.
    behebt = 'anzeigeformat'
    titel = "Anzeigeformate mit Vermerk versehen"
    tut = ("Setzt „# Dictionary gewollt: …“ über jede Rückgabe, deren Schlüssel "
           "nachweislich im Frontend stehen — mit Angabe der JS-Datei.")
    warum = ("134 von 204 Befunden waren Anzeigeformate. Der Auftrag nimmt sie "
             "aus; ohne Vermerk taucht jeder beim nächsten Lauf wieder auf und "
             "verdeckt die echten Fälle.")
    grenzen = ("Nur bei mindestens 70 % Trefferquote. „Gemischt“ bleibt liegen — "
               "dort muss ein Mensch entscheiden, ob das Dictionary unterwegs "
               "gelesen wird.")
    kriterium = 11
    dauer = "5–15 s"

    anlassfall = Anlassfall(
        # DREI Bedingungen muessen zugleich gelten, sonst schweigt der Fixer
        # mit gutem Grund:
        #   1. vier feste Schluessel im Rueckgabe-Dictionary,
        #   2. die Schluessel stehen woertlich in ZWEI Frontend-Dateien,
        #   3. die Funktion muendet nachweislich in `JsonResponse`.
        # Punkt 3 kam am 17.08.2026 dazu: Namensgleichheit allein hatte
        # einem Skript ohne jede Antwort „geht als JSON an audio.html"
        # in den Code geschrieben.
        {"kennzahlen.py":
            "from django.http import JsonResponse\n"
            "\n\n"
            "def kennzahlen(x):\n"
            "    return {'tagesquote': x, 'restposten': 0,\n"
            "            'laufzeitmittel': 0, 'fehlerquote': 0.0}\n"
            "\n\n"
            "def api_kennzahlen(request):\n"
            "    return JsonResponse(kennzahlen(1))\n",
         "tafel.html":
            "<div data-feld=\"tagesquote\"></div>\n"
            "<div data-feld=\"restposten\"></div>\n"
            "<div data-feld=\"laufzeitmittel\"></div>\n",
         "tafel.js":
            "export function zeichnen(d) {\n"
            "    return [d.tagesquote, d.restposten, d.fehlerquote];\n"
            "}\n"},
        mindestens=1, hoechstens=1, erwartet_in="kennzahlen.py",
        warum="Ein Rueckgabe-Dictionary, dessen Schluessel woertlich in der "
              "Oberflaeche stehen und das nachweislich als JSON hinausgeht — "
              "genau der Fall, den der Auftrag ausdruecklich ausnimmt")

    MIN_SCHLUESSEL = 4
    SCHWELLE = 0.7
    ZU_HAEUFIG = {"ok", "error", "name", "key", "value", "date", "id", "type",
                  "label", "data", "text", "url", "status", "title", "n", "count"}
    WORT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    RAUS = ("__pycache__", "node_modules", "venv", "pythonVENV", ".git",
            "sicherung", "backup", "archiv", "_web",
            # Fremdcode, der neben dem Projekt liegt - siehe werkzeug.AUSGESCHLOSSEN
            "virensuche_quarantine", "quarantine", "chrome-profile",
            "Extensions", "var", "vendor")
    #: Mitgelieferte Bibliotheken und Buendel. Ein Vermerk, der „geht an
    #: aws-sdk.js" behauptet, ist keine Begruendung, sondern ein Zufallstreffer:
    #: In einem 3-MB-Buendel steht JEDER kurze Bezeichner irgendwo.
    FREMDE_DATEI = ("min.js", "-sdk", "bundle", "compiler", "vendor", "polyfill",
                    "chunk", "runtime.", "jquery", "bootstrap", "htmx")
    #: Zeilen ab dieser Laenge heissen: minifiziert. Auch das ist Fremdcode.
    MINIFIZIERT_AB = 500
    #: Wie viele der gefundenen Schluessel EINE Datei enthalten muss, damit sie
    #: als Ziel genannt werden darf. Ohne diese Bedingung nannte der Fixer
    #: schlicht die groessten Dateien des Projekts: Jede Datei, die EINEN
    #: Schluessel enthielt, landete in der Begruendung — ein Verzeichnisvergleich
    #: bekam „geht als JSON an svelte_compiler.js" (17.08.2026).
    ANTEIL_JE_DATEI = 0.5

    def __init__(self):
        self._frontend = None
        self._baeume = None
        self._importeure = None

    @property
    def baeume(self):
        if self._baeume is None:
            aus = {}
            for pfad in self._pyquellen():
                try:
                    aus[pfad] = ast.parse(pfad.read_text(encoding="utf-8"))
                except (OSError, SyntaxError, ValueError):
                    continue
            self._baeume = aus
        return self._baeume

    @property
    def importeure(self):
        """{Name: {Dateien, die ihn importieren}} - einmal aufgebaut."""
        if self._importeure is None:
            aus = {}
            for pfad, baum in self.baeume.items():
                for k in ast.walk(baum):
                    if isinstance(k, ast.ImportFrom):
                        for a in k.names:
                            aus.setdefault(a.name, set()).add(pfad)
            self._importeure = aus
        return self._importeure

    @property
    def weg(self):
        return Serialisierungsweg(self.baeume, self.importeure)

    # ---- wo die Schluessel herkommen ---------------------------------------
    @property
    def frontend(self):
        """{Bezeichner: [Dateien, in denen er steht]} - einmal gelesen."""
        if self._frontend is None:
            aus = {}
            for muster in ("*.js", "*.mjs", "*.html"):
                for pfad in self.pfade(muster):
                    if not self.erlaubt(pfad):
                        continue
                    # AUCH AM DATEINAMEN, nicht nur am Ordner (16.08.2026): Der
                    # Ausschluss griff nur auf Verzeichnisse, und prompt belegte
                    # ein Vermerk sein „geht an die Oberfläche" mit
                    # ``backup_dax_handel_vor_modulen.html`` - einer Datei, die
                    # niemand mehr ausliefert. Ein Beleg auf totem Code ist
                    # genau die Sorte Begründung, die hier nichts verloren hat.
                    if any(t in pfad.stem.lower()
                           for t in ("backup", "_alt", "_vor_", ".bak", "kopie")):
                        continue
                    if any(t in pfad.name.lower() for t in self.FREMDE_DATEI):
                        continue
                    try:
                        text = pfad.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
                    # Minifiziert = fremdes Buendel. Dort steht jeder kurze
                    # Bezeichner irgendwo, und ein Treffer belegt nichts.
                    if any(len(z) > self.MINIFIZIERT_AB for z in text.split("\n")):
                        continue
                    for name in set(self.WORT.findall(text)):
                        aus.setdefault(name, []).append(pfad.name)
            self._frontend = aus
        return self._frontend

    def _pyquellen(self):
        for pfad in self.pfade("*.py"):
            if not self.erlaubt(pfad):
                continue
            yield pfad

    def _fundstellen(self):
        for pfad in self._pyquellen():
            try:
                text = pfad.read_text(encoding="utf-8")
                baum = ast.parse(text)
            except (OSError, SyntaxError):
                continue
            zeilen = text.split("\n")
            for k in ast.walk(baum):
                if not isinstance(k, ast.Return) or not isinstance(k.value, ast.Dict):
                    continue
                feste = [s.value for s in k.value.keys
                         if isinstance(s, ast.Constant) and isinstance(s.value, str)]
                if len(feste) < self.MIN_SCHLUESSEL:
                    continue
                aussage = [s for s in feste if s not in self.ZU_HAEUFIG]
                if not aussage:
                    continue
                # Steht der Vermerk schon da?
                von = max(0, k.lineno - 7)
                if any(MARKER in z for z in zeilen[von:k.lineno]):
                    continue
                treffer = [s for s in aussage if s in self.frontend]
                # NUR Dateien, die einen nennenswerten Teil der Schluessel
                # WIRKLICH enthalten, duerfen als Ziel genannt werden. Vorher
                # zaehlte jede Datei mit EINEM Treffer mit, und die Begruendung
                # nannte am Ende die groessten Dateien des Projekts.
                quellen = Counter(d for s in treffer for d in self.frontend[s])
                noetig = max(2, int(len(treffer) * self.ANTEIL_JE_DATEI))
                belegend = [d for d, n in quellen.most_common() if n >= noetig]
                fund = Fundstelle(pfad, k, aussage, treffer, belegend[:3])
                # ZWEI BELEGE, NICHT EINER (17.08.2026): Namensgleichheit allein
                # traegt nicht. ``bank/views/neu.py`` bekam „geht als JSON an
                # llm_settings.html" und ``compare_transcripts.py`` — ein
                # Skript ohne jede Antwort — „geht als JSON an audio.html".
                # Verlangt wird jetzt AUSSERDEM, dass die Rueckgabe nachweislich
                # als JSON hinausgeht (Serialisierungsweg). Lieber ein Fixer,
                # der wenig anfasst, als einer, der Behauptungen in den Code
                # schreibt.
                funktion_hier = self._funktion_um(baum, k.lineno)
                geht_hinaus = bool(funktion_hier
                                   and self.weg.beleg(pfad, funktion_hier))
                if (belegend and geht_hinaus
                        and len(treffer) / len(aussage) >= self.SCHWELLE):
                    yield fund
                    continue
                # ZWEITER WEG: Die Schluessel stehen nirgends woertlich, aber das
                # Ergebnis geht nachweislich als JSON hinaus.
                funktion = self._funktion_um(baum, k.lineno)
                beleg = funktion and self.weg.beleg(pfad, funktion)
                if beleg:
                    fund.serialisiert = beleg
                    yield fund

    @staticmethod
    def _funktion_um(baum, zeile):
        treffer = None
        for k in ast.walk(baum):
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
                    k.lineno <= zeile <= (k.end_lineno or k.lineno):
                if treffer is None or k.lineno > treffer.lineno:
                    treffer = k
        return treffer.name if treffer else ""

    # ---- Vorschau und Netz --------------------------------------------------
    def vorschau(self):
        je_datei = {}
        for f in self._fundstellen():
            je_datei.setdefault(f.pfad, []).append(f)
        aenderungen = []
        for pfad, funde in sorted(je_datei.items()):
            zeilen = pfad.read_text(encoding="utf-8").split("\n")
            # VON HINTEN einsetzen, sonst verschieben sich die Zeilennummern der
            # noch offenen Fundstellen (klassischer Fehler beim Mehrfach-Einfuegen).
            for f in sorted(funde, key=lambda x: -x.knoten.lineno):
                einzug = len(zeilen[f.knoten.lineno - 1]) - \
                    len(zeilen[f.knoten.lineno - 1].lstrip())
                zeilen.insert(f.knoten.lineno - 1,
                              " " * einzug + f.vermerk.strip())
            aenderungen.append(Aenderung(
                pfad, "%d Vermerk(e) setzen: %s" % (
                    len(funde), ", ".join(sorted(f.quellen[0] for f in funde
                                                 if f.quellen)[:2])),
                "\n".join(zeilen)))
        return Vorschau(aenderungen,
                        "Der Vermerk nennt die Frontend-Datei — er ist damit "
                        "nachprüfbar und kein bloßes Stummschalten.")

    def pruefen(self, aenderung):
        """Kompiliert die Datei noch, und steht der Vermerk wirklich drin?"""
        try:
            text = aenderung.pfad.read_text(encoding="utf-8")
            ast.parse(text)
        except SyntaxError as e:
            return ["kompiliert nicht mehr: %s" % e]
        except OSError as e:
            return ["nicht lesbar: %s" % e]
        if MARKER not in text:
            return ["der Vermerk steht nicht in der Datei"]
        return []
