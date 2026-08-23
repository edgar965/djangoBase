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


class Regel:
    """Eine Pruefung ueber die Zeilen einer Datei."""

    art = ""
    warum = ""
    muster = None
    #: Zeilen, die NICHT passen duerfen (Kommentare, Ausnahmen).
    nicht = None
    #: True = prueft JavaScript. In HTML gilt sie nur in <script>-Bloecken.
    nur_javascript = True

    def pruefen(self, datei, zeilen):
        gefunden = []
        for nummer, zeile in enumerate(zeilen, 1):
            if self.nicht and self.nicht.search(zeile):
                continue
            if self.muster.search(zeile):
                gefunden.append(Fund(self.art, datei, nummer, zeile, self.warum))
        return gefunden


class InlineStil(Regel):
    nur_javascript = False   # style="" gilt auch im Markup
    art = "Inline-Stil"
    warum = ("Aussehen gehoert ins CSS. Im JavaScript ist es weder ueber ein "
             "Theme aenderbar noch im Browser auffindbar.")
    muster = re.compile(r"""\.style\.cssText\s*=|style\s*=\s*['"][^'"]*:""")
    nicht = re.compile(r"^\s*(//|\*|/\*)")


class StilZuweisung(Regel):
    art = "Einzelne Stilzuweisung im JavaScript"
    warum = ("Ein Wert, der das Aussehen bestimmt (Farbe, Groesse, Abstand), "
             "gehoert in eine CSS-Klasse; display/visibility zum Ein- und "
             "Ausblenden sind ausgenommen.")
    muster = re.compile(r"\.style\.(color|background\w*|width|height|fontSize"
                        r"|margin\w*|padding\w*|border\w*|opacity)\s*=")
    nicht = re.compile(r"^\s*(//|\*|/\*)")


class Dauerlaeufer(Regel):
    art = "setInterval ohne Abbruch in derselben Datei"
    warum = ("Ein Intervall ohne `clearInterval` laeuft, solange die Seite "
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

        Nur die EINE Zeile darueber zu pruefen war zu eng: Die Begruendung
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
    warum = ("Meldungen ohne Not fuellen die Konsole und verdecken echte "
             "Fehler. `console.warn`/`console.error` bleiben. Eine Klasse, die "
             "das Protokollieren kapselt, ist ausgenommen.")
    muster = re.compile(r"\bconsole\.log\s*\(")
    nicht = re.compile(r"^\s*(//|\*|/\*)")

    def pruefen(self, datei, zeilen):
        u"""Die Ausnahmen stehen in ``Frontendquellen.ausgabe_gewollt``.

        Dort, weil ``protokoll`` dieselbe Frage stellt und sie ohne diese
        Ausnahmen beantwortete: 189 ``console.*``-Stellen gegen die hier
        gezaehlten, darunter 24 aus einem Playwright-Laeufer, dessen Ausgabe das
        Ergebnis IST. Zwei Werkzeuge, die dasselbe zaehlen, brauchen EINEN
        Massstab (17.08.2026).
        """
        if Frontendquellen.ausgabe_gewollt(datei, zeilen):
            return []
        return super().pruefen(datei, zeilen)


class AltesVar(Regel):
    art = "var statt let/const"
    warum = ("`var` gilt fuer die ganze Funktion und laesst sich neu "
             "deklarieren - eine Fehlerquelle, die let/const nicht haben.")
    muster = re.compile(r"^\s*var\s+\w")
    nicht = re.compile(r"^\s*(//|\*|/\*)")


class LoseGleichheit(Regel):
    art = "Vergleich mit == statt ==="
    warum = ("`==` wandelt Typen um: \"\" == 0 und \"0\" == 0 sind wahr. "
             "AUSGENOMMEN `== null`: die uebliche Pruefung auf null ODER "
             "undefined, mit `===` gerade falsch.")
    muster = re.compile(r"[^=!<>]==[^=]")
    nicht = re.compile(r"^\s*(//|\*|/\*)|===|!==|[=!]=\s*null")


class FetchOhneOkPruefung(Regel):
    u"""Antwort wird verwendet, ohne `response.ok` zu pruefen.

    Objektiv pruefbar, anders als „hat einen try-Block": Der Aufrufer kann in
    einer anderen Datei fangen, das sieht diese Datei nicht. Ob aber `.ok`
    geprueft wird, steht hier - und ohne diese Pruefung wird bei einer
    500er-Antwort die Fehlerseite als JSON gelesen und scheitert mit
    "Unexpected token '<'": einer Meldung, die nichts mit der Ursache zu tun hat.
    """

    art = "Antwort ohne .ok-Pruefung verwendet"
    warum = ("Ohne `antwort.ok` wird die Fehlerseite des Servers als JSON "
             "gelesen - die Meldung sagt dann nichts ueber die Ursache.")
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

        FENSTER zaehlt CODE-Zeilen, nicht rohe. Grund (assistant, 22.08.2026):
        Fuenf von zwoelf Befunden waren Fehlalarme - die Pruefung stand da, nur
        hinter einem Kommentarblock, der begruendet, warum der Fehler still
        bleiben darf::

            const r = await fetch('/mail/api/sidebar-counts/', {...});
            // stumm gewollt: Das ist ein Taktgeber, ...   <- fuenf Zeilen
            // ... Seitenaufruf auf, weil die dann serverseitig gerendert werden.
            if (!r.ok) return;                             <- ausserhalb des Fensters

        Wer seine Entscheidung begruendet, wird sonst dafuer gemeldet."""
        i = (ende if ende is not None else nummer - 1) + 1
        rest = self.FENSTER
        while i < len(zeilen) and rest > 0:
            if not self.nicht.search(zeilen[i]) and zeilen[i].strip():
                rest -= 1
            i += 1
        return i


class MagischeZahl(Regel):
    art = "Zahl ohne Namen im Code"
    warum = ("Eine Zahl mit Bedeutung (Grenze, Zeit, Faktor) gehoert in eine "
             "benannte Konstante - sonst weiss niemand, was sie bedeutet oder "
             "ob sie an zwei Stellen dieselbe ist.")
    muster = re.compile(r"set(?:Timeout|Interval)\s*\([^,]+,\s*\d{2,}\s*\)")
    nicht = re.compile(r"^\s*(//|\*|/\*)")


class LangeZeile(Regel):
    nur_javascript = False   # gilt fuer Markup genauso
    art = "Zeile ueber 120 Zeichen"
    warum = ("Lange Zeilen verstecken mehrere Anweisungen hintereinander; im "
             "Vergleich zweier Staende ist nicht zu sehen, was sich geaendert "
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
