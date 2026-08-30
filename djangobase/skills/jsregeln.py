# -*- coding: utf-8 -*-
u"""Die Regeln der Frontend-Befunderhebung - eine Klasse je Auffaelligkeit.

Jede Regel prueft EINE Sache und sagt, warum sie ein Befund ist. Regeln, die
nicht sicher entscheidbar sind (etwa „diese Funktion ist zu komplex"), stehen
nicht drin: Eine Zahl, die falsche Treffer enthaelt, ist schlimmer als eine
kleinere ehrliche.

VIER FEHLALARME, die beim Bau aufgefallen sind und hier behoben sind
====================================================================
1. ``==`` in Django-Vorlagen: ``{% if job.status == 'complete' %}`` ist die
   einzige richtige Schreibweise. JavaScript-Regeln gelten in HTML deshalb nur
   innerhalb von ``<script>``-Bloecken (`nur_javascript`).
2. ``== null`` ist die uebliche Pruefung auf null ODER undefined und mit
   ``===`` gerade falsch - ausgenommen.
3. Das Fenster fuer die ok-Pruefung zaehlt ab dem ENDE der fetch-Anweisung.
   Bei einem mehrzeiligen Optionsobjekt liegt ``if (!resp.ok) throw`` acht
   Zeilen weiter unten.
4. ``.blob()``/``.arrayBuffer()`` sind keine JSON-Faelle - bei einer
   ``data:``-URL gibt es ohnehin keinen sinnvollen Statuscode.
"""
import re

from .frontendquellen import Frontendquellen

from .jsklammern import Klammerzaehler

__all__ = ["REGELN", "Regel", "Fund"]


class Fund:
    """Eine Auffaelligkeit: wo sie steht und warum sie eine ist."""

    __slots__ = ("art", "datei", "zeile", "text", "warum")

    def __init__(self, art, datei, zeile, text, warum):
        self.art = art
        self.datei = datei
        self.zeile = zeile
        self.text = text.strip()[:120]
        self.warum = warum

    def als_zeile(self):
        # Dictionary gewollt: geht unveraendert als JSON an die Seite.
        return {"art": self.art, "ort": "%s:%d" % (self.datei, self.zeile),
                "text": self.text}


#: Wo ein Blockkommentar anfaengt und wo er aufhoert.
#:
#: WARUM (30.08.2026, 3DTools): Zwei Meldungen der Regel `InlineStil` standen
#: in einem CSS-Kommentar, der die alte Lage BESCHREIBT::
#:
#:     /* Aus dem innerHTML des Spurmenues — achtmal `style="width:16px;…"`
#:        und dreimal … */
#:
#: Ein Werkzeug, das seine eigene Aufraeum-Notiz als Befund meldet, ist die
#: unangenehmste Sorte Fehlalarm: Wer ihn beheben will, loescht die
#: Begruendung. Die zeilenweise Ausnahme (`nicht`) trifft das nicht — sie
#: sieht nur den Anfang einer Zeile, und hier steht der Kommentar mittendrin.
BLOCKANFANG = (("/*", "*/"), ("{% comment %}", "{% endcomment %}"),
               ("{#", "#}"), ("<!--", "-->"))


def kommentarzeilen(zeilen):
    """Zeilennummern (1-basiert), die ganz in einem Blockkommentar liegen."""
    drin = set()
    offen = None
    for nummer, zeile in enumerate(zeilen, 1):
        if offen:
            drin.add(nummer)
            if offen in zeile:
                offen = None
            continue
        for anfang, ende in BLOCKANFANG:
            stelle = zeile.find(anfang)
            if stelle >= 0 and ende not in zeile[stelle:]:
                offen = ende
                drin.add(nummer)
                break
    return drin


class Regel:
    """Eine Prüfung über die Zeilen einer Datei."""

    art = ""
    warum = ""
    muster = None
    #: Zeilen, die NICHT passen duerfen (Kommentare, Ausnahmen).
    nicht = None
    #: True = prueft JavaScript. In HTML gilt sie nur in <script>-Bloecken.
    nur_javascript = True
    #: True = Zeilen in Blockkommentaren uebergehen.
    ohne_kommentare = False

    def pruefen(self, datei, zeilen):
        gefunden = []
        kommentar = kommentarzeilen(zeilen) if self.ohne_kommentare else ()
        for nummer, zeile in enumerate(zeilen, 1):
            if nummer in kommentar:
                continue
            if self.nicht and self.nicht.search(zeile):
                continue
            if self.muster.search(zeile):
                gefunden.append(Fund(self.art, datei, nummer, zeile, self.warum))
        return gefunden


#: Zeichen, an denen ein Wert erst zur LAUFZEIT entsteht.
#:
#: WARUM DAS EINE AUSNAHME IST (30.08.2026, 3DTools)
#: =================================================
#: `style="width:${prozent}%"` an einem Fortschrittsbalken ist kein Aussehen,
#: das ins CSS gehoerte — es ist ein ZUSTAND. Eine Klasse kann „47 Prozent"
#: nicht ausdruecken; wer es trotzdem verlangt, verlangt hundert Klassen oder
#: eine CSS-Variable, die genauso im JavaScript gesetzt wird.
#:
#: Das Schwesterwerkzeug `jsstilfassungen` macht die Unterscheidung seit jeher
#: (`DYNAMISCH`) und nennt die Zahl der uebergangenen Faelle. Diese Regel tat
#: es nicht: Von 323 gemeldeten Inline-Stilen in 3DTools waren 289 statisch —
#: die uebrigen liessen sich nicht beheben, ohne den Balken kaputtzumachen,
#: standen aber in derselben Zahl.
#:
#: DIESELBE LISTE WIE DORT, damit die beiden Werkzeuge nicht verschiedene
#: Zahlen fuer dieselbe Frage liefern.
DYNAMISCH = ("{{", "{%", "${", '" +', "' +", '"+', "'+", "` +", "`+")


class Stilregel(Regel):
    """Basis der beiden Stil-Regeln: berechnete Werte zaehlen nicht.

    `ohne_kommentare` ist hier an: Eine Notiz, die den alten Zustand
    beschreibt, ist kein Inline-Stil.

    `dynamisch` zaehlt, wie viele Stellen die Ausnahme geschluckt hat.
    `JsBefunde` setzt den Zaehler vor jedem Lauf zurueck und nennt die Zahl
    in der Zusammenfassung — eine Ausnahme, die schweigt, ist ein blinder
    Fleck (dieselbe Lehre wie bei `uebersprungen`).
    """

    ohne_kommentare = True

    def __init__(self):
        self.dynamisch = 0

    def _berechnet(self, text):
        return any(marke in text for marke in DYNAMISCH)

    def pruefen(self, datei, zeilen):
        gefunden = []
        for fund in super().pruefen(datei, zeilen):
            # ENDET DIE ZEILE MIT `=`, steht der Wert eine Zeile tiefer
            # (30.08.2026). Ohne die naechste Zeile sah jede mehrzeilige
            # Zuweisung wie ein fester Wert aus — `farbfleck.style
            # .backgroundColor =` mit der Farbe aus den Daten darunter.
            text = fund.text
            if text.rstrip().endswith('=') and fund.zeile < len(zeilen):
                text += ' ' + zeilen[fund.zeile].strip()
            if self._berechnet(text):
                self.dynamisch += 1
                continue
            gefunden.append(fund)
        return gefunden


class InlineStil(Stilregel):
    nur_javascript = False   # style="" gilt auch im Markup
    art = "Inline-Stil"
    warum = ("Aussehen gehört ins CSS. Im JavaScript ist es weder über ein "
             "Theme aenderbar noch im Browser auffindbar. Werte, die erst zur "
             "Laufzeit entstehen (`${…}`, `{{ … }}`), sind ausgenommen — die "
             "kann keine Klasse tragen.")
    muster = re.compile(r"""\.style\.cssText\s*=|style\s*=\s*['"][^'"]*:""")
    nicht = re.compile(r"^\s*(//|\*|/\*)")


class StilZuweisung(Stilregel):
    art = "Einzelne Stilzuweisung im JavaScript"
    warum = ("Ein Wert, der das Aussehen bestimmt (Farbe, Größe, Abstand), "
             "gehört in eine CSS-Klasse; display/visibility zum Ein- und "
             "Ausblenden sowie berechnete Werte sind ausgenommen.")
    muster = re.compile(r"\.style\.(color|background\w*|width|height|fontSize"
                        r"|margin\w*|padding\w*|border\w*|opacity)\s*=")
    nicht = re.compile(r"^\s*(//|\*|/\*)")

    #: Groessen, die den ZUSTAND anzeigen statt das Aussehen: die Breite
    #: eines Fortschrittsbalkens, die Hoehe eines aufgezogenen Rahmens.
    #:
    #: WARUM AUSGENOMMEN (30.08.2026): `balken.style.width = '85%'` ist
    #: dieselbe Sache wie `= prozent + '%'` — nur dass der Schritt hier fest
    #: ist. Eine CSS-Klasse kann „85 Prozent" nicht ausdruecken, ohne fuer
    #: jeden Schritt eine eigene zu bekommen. Ebenso `= ''` und `= '0px'`:
    #: Das ist ein Zuruecksetzen, kein Aussehen.
    ZUSTANDSGROESSEN = ("width", "height")

    def _berechnet(self, text):
        """Auch: alles, was rechts vom `=` KEINE feste Zeichenkette ist.

        `b.style.width = prozent + '%'` und `el.style.color = farbe` sind
        Zustand, nicht Aussehen. `el.style.color = '#e94560'` dagegen ist ein
        fester Wert und bleibt ein Befund.
        """
        if super()._berechnet(text):
            return True
        if "=" not in text:
            return False
        links, wert = text.split("=", 1)
        wert = wert.strip().rstrip(";").strip()
        eigenschaft = links.rsplit(".", 1)[-1].strip()
        if eigenschaft in self.ZUSTANDSGROESSEN:
            roh = wert.strip("'\"`")
            if not roh or roh.endswith("%") or roh in ("0", "0px", "auto"):
                return True
        return bool(wert) and wert[:1] not in ("'", '"', "`")


class Dauerlaeufer(Regel):
    art = "setInterval ohne Abbruch in derselben Datei"
    warum = ("Ein Intervall ohne `clearInterval` läuft, solange die Seite "
             "offen ist. Absichtliche Dauerlaeufer (Zwischenspeichern gegen "
             "Absturz) werden mit dem Kommentar \"dauerhaft gewollt\" im "
             "Kommentarblock darueber ausgenommen.")
    muster = re.compile(r"\bsetInterval\s*\(")
    nicht = re.compile(r"^\s*(//|\*|/\*)")

    def pruefen(self, datei, zeilen):
        gefunden = super().pruefen(datei, zeilen)
        if not gefunden or any("clearInterval" in z for z in zeilen):
            return []
        return [f for f in gefunden
                if not Dauerlaeufer._gewollt(zeilen, f.zeile - 1)]

    @staticmethod
    def _gewollt(zeilen, nummer):
        """Steht "dauerhaft gewollt" im Kommentarblock direkt oberhalb?

        Nur die EINE Zeile darueber zu prüfen war zu eng: Die Begründung
        stand als dreizeiliger Block, das Schluesselwort in der ersten Zeile.
        """
        for i in range(nummer - 1, max(-1, nummer - 6), -1):
            if not zeilen[i].lstrip().startswith(("//", "*", "/*")):
                return False
            if "dauerhaft gewollt" in zeilen[i]:
                return True
        return False


class LauteAusgabe(Regel):
    art = "console.log im Betrieb"
    warum = ("Meldungen ohne Not füllen die Konsole und verdecken echte "
             "Fehler. `console.warn`/`console.error` bleiben. Eine Klasse, die "
             "das Protokollieren kapselt, ist ausgenommen.")
    muster = re.compile(r"\bconsole\.log\s*\(")
    nicht = re.compile(r"^\s*(//|\*|/\*)")

    def pruefen(self, datei, zeilen):
        u"""Die Ausnahmen stehen in ``Frontendquellen.ausgabe_gewollt``.

        Dort, weil ``protokoll`` dieselbe Frage stellt und sie ohne diese
        Ausnahmen beantwortete: 189 ``console.*``-Stellen gegen die hier
        gezaehlten, darunter 24 aus einem Playwright-Laeufer, dessen Ausgabe das
        Ergebnis IST. Zwei Werkzeuge, die dasselbe zählen, brauchen EINEN
        Massstab (17.08.2026).
        """
        if Frontendquellen.ausgabe_gewollt(datei, zeilen):
            return []
        return super().pruefen(datei, zeilen)


class AltesVar(Regel):
    art = "var statt let/const"
    warum = ("`var` gilt für die ganze Funktion und lässt sich neu "
             "deklarieren - eine Fehlerquelle, die let/const nicht haben.")
    muster = re.compile(r"^\s*var\s+\w")
    nicht = re.compile(r"^\s*(//|\*|/\*)")


class LoseGleichheit(Regel):
    art = "Vergleich mit == statt ==="
    warum = ("`==` wandelt Typen um: \"\" == 0 und \"0\" == 0 sind wahr. "
             "AUSGENOMMEN `== null`: die uebliche Prüfung auf null ODER "
             "undefined, mit `===` gerade falsch.")
    muster = re.compile(r"[^=!<>]==[^=]")
    nicht = re.compile(r"^\s*(//|\*|/\*)|===|!==|[=!]=\s*null")


class FetchOhneOkPruefung(Regel):
    u"""Antwort wird verwendet, ohne `response.ok` zu prüfen.

    Objektiv prüfbar, anders als „hat einen try-Block": Der Aufrufer kann in
    einer anderen Datei fangen, das sieht diese Datei nicht. Ob aber `.ok`
    geprüft wird, steht hier - und ohne diese Prüfung wird bei einer
    500er-Antwort die Fehlerseite als JSON gelesen und scheitert mit
    "Unexpected token '<'": einer Meldung, die nichts mit der Ursache zu tun hat.
    """

    art = "Antwort ohne .ok-Prüfung verwendet"
    warum = ("Ohne `antwort.ok` wird die Fehlerseite des Servers als JSON "
             "gelesen - die Meldung sagt dann nichts über die Ursache.")
    muster = re.compile(r"\bawait\s+fetch\s*\(")
    nicht = re.compile(r"^\s*(//|\*|/\*)")

    #: So viele Zeilen NACH dem Ende der fetch-Anweisung zaehlen noch.
    FENSTER = 4
    #: Rohdaten-Zugriffe: kein JSON-Fall (siehe Modulkopf, Fehlalarm 4).
    ROHDATEN = (".blob(", ".arrayBuffer(", ".headers", ".formData(")

    def pruefen(self, datei, zeilen):
        gefunden = []
        for nummer, zeile in enumerate(zeilen, 1):
            if self.nicht.search(zeile) or not self.muster.search(zeile):
                continue
            ende = Klammerzaehler.anweisungsende(zeilen, nummer - 1, "fetch(")
            umfeld = "\n".join(zeilen[nummer - 1:self._fensterende(zeilen, ende, nummer)])
            if ".ok" in umfeld or ".status" in umfeld:
                continue
            if any(roh in umfeld for roh in FetchOhneOkPruefung.ROHDATEN):
                continue
            gefunden.append(Fund(self.art, datei, nummer, zeile, self.warum))
        return gefunden

    def _fensterende(self, zeilen, ende, nummer):
        u"""Bis wohin nach dem ``fetch`` noch nach ``.ok`` gesucht wird.

        FENSTER zählt CODE-Zeilen, nicht rohe. Grund (assistant, 22.08.2026):
        Fünf von zwölf Befunden waren Fehlalarme - die Prüfung stand da, nur
        hinter einem Kommentarblock, der begründet, warum der Fehler still
        bleiben darf::

            const r = await fetch('/mail/api/sidebar-counts/', {...});
            // stumm gewollt: Das ist ein Taktgeber, ...   <- fünf Zeilen
            // ... Seitenaufruf auf, weil die dann serverseitig gerendert werden.
            if (!r.ok) return;                             <- außerhalb des Fensters

        Wer seine Entscheidung begründet, wird sonst dafür gemeldet."""
        i = (ende if ende is not None else nummer - 1) + 1
        rest = self.FENSTER
        while i < len(zeilen) and rest > 0:
            if not self.nicht.search(zeilen[i]) and zeilen[i].strip():
                rest -= 1
            i += 1
        return i


class MagischeZahl(Regel):
    art = "Zahl ohne Namen im Code"
    warum = ("Eine Zahl mit Bedeutung (Grenze, Zeit, Faktor) gehört in eine "
             "benannte Konstante - sonst weiß niemand, was sie bedeutet oder "
             "ob sie an zwei Stellen dieselbe ist.")
    muster = re.compile(r"set(?:Timeout|Interval)\s*\([^,]+,\s*\d{2,}\s*\)")
    nicht = re.compile(r"^\s*(//|\*|/\*)")


class LangeZeile(Regel):
    nur_javascript = False   # gilt fuer Markup genauso
    art = "Zeile über 120 Zeichen"
    warum = ("Lange Zeilen verstecken mehrere Anweisungen hintereinander; im "
             "Vergleich zweier Staende ist nicht zu sehen, was sich geändert "
             "hat.")
    muster = re.compile(r"^.{121,}$")
    nicht = re.compile(r"^\s*(//|\*|/\*)|https?://")


class TodoImCode(Regel):
    nur_javascript = False
    art = "TODO/FIXME/HACK"
    warum = "Eine offene Stelle, die der Code selbst als unfertig kennzeichnet."
    muster = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")


#: Reihenfolge = Anzeigereihenfolge. Vorne, was echte Fehler anzeigt.
REGELN = [FetchOhneOkPruefung(), Dauerlaeufer(), LauteAusgabe(), AltesVar(),
          LoseGleichheit(), MagischeZahl(), InlineStil(), StilZuweisung(),
          LangeZeile(), TodoImCode()]
