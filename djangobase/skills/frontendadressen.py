# -*- coding: utf-8 -*-
u"""Frontendadressen - ruft das Frontend eine Adresse, die es nicht gibt?

DER BEFUND (3DTools, 17.08.2026)
================================
Die Kontextmenues der Kleider- und der MakeHuman-Liste bieten Umbenennen,
Verschieben, Kopieren und Loeschen an und riefen dafuer
``/api/character/garment/manage/``. **Diesen Endpunkt gab es nicht.** Acht
Aufrufstellen in zwei Modulen liefen in eine 404; der umgebende ``catch``
schrieb die Meldung in die Konsole, und fuer den Benutzer passierte beim Klick
gar nichts.

Kein Test sieht das: Die Seite laedt mit 200, das Modul ist syntaktisch heil,
der Import stimmt. Erst der Abgleich der Adressen gegen Djangos
URL-Konfiguration bringt es heraus — von 94 Adress-Literalen war genau eines
unbekannt.

WARUM NUR LITERALE DIREKT IM AUFRUF
===================================
Die erste Fassung nahm jedes ``'/api/...'`` im Quelltext. Ergebnis: 13
Meldungen, davon 12 falsch. Denn

* ``static ENDPUNKT = '/api/animationen/'`` ist ein ANFANG — die Kategorie
  kommt an der Verwendungsstelle dazu.
* ``export const API = '/api/character'`` genauso.
* ``* @param {string} config.apiPrefix  z.B. '/api/character-test'`` steht in
  einem Kommentar.

Zwoelf Fehlalarme verdecken den einen echten Fall — genau die Falle aus
``~/.claude/rules/analysewerkzeuge.md``. Deshalb zaehlt hier nur, was
DIREKT ALS ERSTES ARGUMENT eines Abrufs steht: dort ist das Literal die ganze
Adresse, und wenn sie nicht aufloest, ist der Aufruf tot.

PLATZHALTER: ``${id}`` und ``{{ x }}`` werden mit mehreren Kandidaten probiert
(Zahl, UUID, Wort) — passt einer, gilt die Adresse als bekannt. Ohne das
meldete jede Route mit ``<uuid:...>`` einen Fehlalarm.
"""
import re

from django.urls import Resolver404, resolve

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug2

__all__ = ["Frontendadressen"]

#: Aufrufe, deren erstes Argument eine Adresse ist.
ABRUF = re.compile(
    r"""(?:fetch|\.json|\.senden|\.holen|\.text|axios\.\w+|\$\.\w+)"""
    r"""\s*\(\s*['"`](/[^'"`\s]*)['"`]""")
#: Platzhalter, die zur Laufzeit gefuellt werden.
PLATZ = re.compile(r"\$\{[^}]*\}|\{\{[^}]*\}\}|\{%[^%]*%\}")
#: Werte, mit denen ein Platzhalter probiert wird - einer muss passen.
KANDIDATEN = ("1", "b7eca979-03e3-4461-bbcc-51bb854faa83", "name", "1.5")
#: Zeilen, die so beginnen, sind Kommentar.
KOMMENTAR = re.compile(r"^\s*(//|\*|/\*|#)")
#: Geht es nach dem Literal mit `+` weiter, war es nur ein Anfang.
#:
#: GEMESSEN (17.08.2026): Der Zusatz kann in der NAECHSTEN Zeile stehen —
#:     return Serverabruf.json('/api/character/model/'
#:                             + encodeURIComponent(name) + '/');
#: Ohne den Blick ueber das Zeilenende meldete der Pruefer genau diese zwei
#: Stellen als tote Adresse. Deshalb `\s*` inklusive Zeilenumbruch.
WEITER = re.compile(r"\s*\+")
#: So weit wird hinter dem Literal nach dem Pluszeichen gesucht.
#:
#: 40 Zeichen waren zu wenig: In `kleiderhuelle.js` steht der Zusatz nach einem
#: Zeilenumbruch und 42 Leerzeichen Einrueckung (der Aufruf steckt in einem
#: try-Block). Genau diese eine Stelle blieb als Fehlalarm stehen — und ein
#: Fehlalarm in einer Liste mit einem echten Fall macht die Liste wertlos.
FENSTER = 200


class Frontendadressen(Werkzeug2):
    slug = "frontendadressen"
    titel = "Frontend: Adresse ohne Route"
    zweck = ("Vergleicht jede Adresse, die direkt in einem `fetch`/`Serverabruf` "
             "steht, mit Djangos URL-Konfiguration.")
    befund = ("3DTools: `/api/character/garment/manage/` gab es nicht — acht "
              "Aufrufstellen, vier tote Menuepunkte in zwei Listen, ohne "
              "Hinweis fuer den Benutzer. Die Seite lud mit 200.")
    abhilfe = ("Route ergaenzen oder die Adresse im Frontend berichtigen. Die "
               "Spalte „Stellen\" zeigt, wie viele Aufrufe daran haengen.")
    dauer = "1-3 s"
    kriterium = 5

    NICHT_IM_PFAD = ("vendor", "theatre", "theatre-studio", "dist", "bundle",
                     "node_modules", "staticfiles")

    #: Eine Adresse, die keine URLconf kennt - und daneben die drei Formen, die
    #: NICHT zaehlen duerfen: ein Praefix in einer Konstanten, eine Adresse, die
    #: hinter dem Literal weitergebaut wird, und eine im Kommentar. Genau diese
    #: drei erzeugten in der ersten Fassung 12 von 13 Meldungen.
    #:
    #: Bewusst KEIN gueltiger Endpunkt im Fall: Welche Routen es gibt, weiss nur
    #: das jeweilige Projekt - ein ``/api/status/`` waere hier richtig und in der
    #: naechsten App ein Fehlalarm.
    anlassfall = Anlassfall(
        {"menue.js": '''const API = '/api/character';

/** Ruft z.B. '/api/character-test/' auf. */
export async function umbenennen(name) {
  await fetch('/api/gibt-es-nicht-xyz/');
  await fetch(API + '/' + encodeURIComponent(name) + '/');
}
'''},
        mindestens=1, hoechstens=1,
        erwartet_in="gibt-es-nicht-xyz",
        warum="3DTools: ``/api/character/garment/manage/`` gab es nicht — acht "
              "Aufrufstellen, vier tote Menüpunkte, Seite lud mit 200")

    def laufen(self):
        gefunden = {}
        for pfad, kurz in self._quellen():
            text = pfad.read_text(encoding="utf-8", errors="replace")
            zeilen = text.split("\n")
            for treffer in ABRUF.finditer(text):
                nummer = text.count("\n", 0, treffer.start())
                if KOMMENTAR.match(zeilen[nummer]):
                    continue
                if WEITER.match(text[treffer.end():treffer.end() + FENSTER]):
                    continue        # nur der Anfang, der Rest wird angehaengt
                adresse = treffer.group(1).split("?")[0].split("#")[0]
                gefunden.setdefault(adresse, []).append(
                    "%s:%d" % (kurz, nummer + 1))

        zeilen_aus = []
        for adresse, stellen in sorted(gefunden.items()):
            if self._bekannt(adresse):
                continue
            zeilen_aus.append({"adresse": adresse, "stellen": len(stellen),
                               "wo": ", ".join(stellen[:3])})
        zeilen_aus.sort(key=lambda z: -z["stellen"])
        return Ergebnis(
            ["adresse", "stellen", "wo"], zeilen_aus,
            zusammenfassung="%d Adressen im Frontend, %d kennt die "
                            "URL-Konfiguration nicht"
                            % (len(gefunden), len(zeilen_aus)),
            hinweis="Gezaehlt wird nur, was DIREKT als erstes Argument eines "
                    "Abrufs steht. Eine Adresse, die als Konstante liegt und "
                    "spaeter zusammengesetzt wird, ist kein vollstaendiger Weg "
                    "— sie zu melden waere ein Fehlalarm.")

    @staticmethod
    def _bekannt(adresse):
        u"""Loest die Adresse auf - mit mehreren Platzhalter-Werten probiert."""
        rohformen = ([PLATZ.sub(k, adresse) for k in KANDIDATEN]
                     if PLATZ.search(adresse) else [adresse])
        for weg in rohformen:
            for kandidat in {weg, weg if weg.endswith("/") else weg + "/"}:
                try:
                    resolve(kandidat)
                    return True
                except (Resolver404, Exception):     # noqa: BLE001
                    continue
        return False

    def _quellen(self):
        wurzel = self.wurzel()
        raus = self.ausgeschlossen()
        for endung in ("*.js", "*.html"):
            for pfad in sorted(wurzel.rglob(endung)):
                if any(teil in raus for teil in pfad.parts):
                    continue
                if any(teil in Frontendadressen.NICHT_IM_PFAD
                       for teil in pfad.parts):
                    continue
                if ".min." in pfad.name:
                    continue
                yield pfad, pfad.relative_to(wurzel).as_posix()
