# -*- coding: utf-8 -*-
u"""JsFaenger - werfende Server-Abrufe, die niemand faengt.

DER BEFUND (3DTools, 16.08.2026)
================================
Beim Umstellen von ``fetch`` auf eine Abrufklasse mit Statuspruefung wird die
Fehlerbehandlung schaerfer: Vorher lief eine 400er-Antwort als JSON durch
(``{"ok": false, "error": "..."}``) und der Code zeigte selbst eine Meldung -
danach WIRFT der Abruf bei jedem Status ausser 2xx.

Das ist die bessere Fehlerbehandlung, aber nur dort, wo jemand faengt. Steht der
Aufruf in keinem try-Block, wird aus einer sichtbaren Meldung eine stille
„Unhandled promise rejection" in einer Konsole, die niemand offen hat - genau
die Fehlerklasse, die der Umbau beseitigen sollte.

Im Ursprungsprojekt liefern 200 Stellen im Python-Teil einen echten Fehlerstatus
(``status=400/404/500``) mitsamt JSON-Body. Diese Pruefung listet die
JavaScript-Stellen, an denen so eine Antwort ungefangen bliebe.

WIE GEPRUEFT WIRD
=================
Zwei Schritte, in zwei eigenen Modulen:

* ``Stelle`` (``jsstelle.py``) - deckt ein try-Block mit ``catch``/``finally``
  diese Zeile? Blockende ueber die Klammertiefe, nicht ueber den Abstand.
* ``Aufrufkette`` (``jsaufrufkette.py``) - wenn nicht: Faengt wenigstens ein
  Glied darueber? Bis zu drei Ebenen, und nur dort, wo der Name sichtbar ist.

Ohne den zweiten Schritt standen in 3DTools 20 Zeilen, von denen 18 keine
Fundstelle waren (17.08.2026). Die Zahlen stehen in der Zusammenfassung
getrennt: im try, ueber den Aufrufer gedeckt, offen.

ANPASSEN: ``DJANGOBASE["skills2_abrufklassen"] = ["Serverabruf", "Api"]`` nennt
die Klassen, deren Methoden werfen.
"""
import re

from django.conf import settings

from .anlassfall import Anlassfall
from .jsaufrufkette import Aufrufkette
from .jsstelle import Stelle
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["JsFaenger"]


class JsFaenger(Werkzeug):
    slug = "jsfaenger"
    titel = "Server-Abrufe ohne try-Block"
    zweck = ("Findet Aufrufe einer werfenden Abrufklasse (Vorgabe: "
             "`Serverabruf.json/text/senden`), die weder selbst im try stehen "
             "noch von einem Aufrufer gefangen werden.")
    befund = ("3DTools: 16 von 101 Aufrufen ohne Faenger. Zwei davon hingen "
              "direkt an einer Nutzeraktion (Koerperart wechseln, Pose "
              "anwenden) - ein Serverfehler blieb dort voellig stumm.")
    abhilfe = ("try/catch mit sichtbarer Meldung ergaenzen. Die Spalte "
               "„aufrufer\" nennt die Stelle, an der die Kette abreisst.")
    dauer = "1–5 s"
    kriterium = 13

    VORGABE_KLASSEN = ("Serverabruf",)
    #: Methoden, die werfen. `jsonOderNull` faengt selbst und zaehlt nicht.
    METHODEN = ("json", "text", "senden", "formular")

    def klassen(self):
        eigen = (getattr(settings, "DJANGOBASE", {}) or {}).get(
            "skills2_abrufklassen")
        return tuple(eigen) if eigen else JsFaenger.VORGABE_KLASSEN

    #: Drei Faelle in einer Datei: ungefangen (Befund), im try-Block (darf nicht
    #: zaehlen) und ueber den Aufrufer gedeckt (darf auch nicht zaehlen — das
    #: war der Zustand, in dem 18 von 20 Zeilen Fehlalarm waren).
    anlassfall = Anlassfall(
        {"abruf.js": '''export async function ohneNetz(url) {
  const d = await Serverabruf.json(url);
  return d.wert;
}

export async function mitNetz(url) {
  try {
    const d = await Serverabruf.json(url);
    return d.wert;
  } catch (e) {
    return null;
  }
}

async function _helfer(url) {
  const d = await Serverabruf.json(url);
  return d.wert;
}

export async function ruftDenHelfer(url) {
  try { return await _helfer(url); } catch (e) { return null; }
}
'''},
        mindestens=1, hoechstens=1,
        erwartet_in="ohneNetz",
        warum="Ein werfender Serverabruf ohne try lässt die Seite still "
              "stehenbleiben. Die zwei anderen Fälle sind die Ausnahmen: "
              "eigener try-Block und ein Aufrufer, der fängt.")

    def laufen(self):
        klassen = self.klassen()
        muster = re.compile(r"\b(?:%s)\.(?:%s)\s*\("
                            % ("|".join(re.escape(k) for k in klassen),
                               "|".join(JsFaenger.METHODEN)))
        # Die Abrufklasse selbst SOLL werfen.
        eigene = tuple("%s.js" % k.lower() for k in klassen)
        quellen = [(kurz, pfad.read_text(encoding="utf-8",
                                         errors="replace").split("\n"))
                   for pfad, kurz in self._quellen()
                   if kurz.rsplit("/", 1)[-1] not in eigene]
        kette = Aufrufkette(quellen, tuple("%s." % k for k in klassen))
        offen, gefangen, ueber_aufrufer = [], 0, 0
        for kurz, zeilen in quellen:
            for nummer, zeile in enumerate(zeilen):
                if not muster.search(zeile):
                    continue
                if zeile.lstrip().startswith(("*", "//")):
                    continue
                stelle = Stelle(kurz, zeilen, nummer)
                if stelle.gefangen():
                    gefangen += 1
                    continue
                urteil = kette.urteil(stelle)
                if urteil == "":
                    ueber_aufrufer += 1
                else:
                    offen.append(stelle.als_zeile(urteil))
        return Ergebnis(
            ["ort", "text", "aufrufer"], offen,
            zusammenfassung="%d Aufrufe, %d in einem try-Block, %d über den "
                            "Aufrufer gedeckt, %d offen"
                            % (gefangen + ueber_aufrufer + len(offen), gefangen,
                               ueber_aufrufer, len(offen)),
            hinweis="Die Aufrufkette wird bis zu %d Ebenen verfolgt und nur "
                    "dort, wo der Name sichtbar ist (Import oder Sammelstelle). "
                    "Was übrig bleibt, nennt die Stelle, an der sie abreißt."
                    % Aufrufkette.TIEFE)

    #: Ausschlussliste und Suche stehen seit dem 17.08.2026 in
    #: ``Frontendquellen`` — vorher hatte sie jedes JS-Werkzeug einzeln,
    #: in vier verschiedenen Fassungen.
    def _quellen(self):
        return self.frontendquellen().paare(".js")
