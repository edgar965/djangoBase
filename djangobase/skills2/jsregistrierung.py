# -*- coding: utf-8 -*-
u"""JsRegistrierung - wird jeder gerufene Name eines Funktionsregisters angemeldet?

DER BEFUND (3DTools, 16.08.2026)
================================
Das Projekt sammelt seine seitenweiten Funktionen in einem Objekt ``fn``
(``gemeinsam/registrierung.js``). Jedes Modul meldet dort an, was andere
brauchen - ``fn.applyFacialExpression = applyFacialExpression``. Der Aufruf
steht in einer anderen Datei.

Das ist bequem, hat aber kein Netz: Fehlt die Anmeldung (weil das Modul nie
importiert wird, umbenannt wurde oder wegfiel), merkt es niemand - bis der
Aufruf zur Laufzeit in ein „is not a function" laeuft. Genau das war bei
``applyFacialExpression``, ``startWizard`` und ``renderAlignmentPreview`` der
Fall: drei Zweige einer Seite, still kaputt. Dazu ``fn.syncLightVisibility``,
das mit ``?.()`` gerufen wurde - dort passiert nicht einmal ein Fehler, die
Funktion bleibt einfach aus.

ZWEI ARTEN VON FUND
===================
* **gerufen, nicht angemeldet** - sicherer Laufzeitfehler, sobald der Zweig
  laeuft. Das ist der Befund, der zaehlt.
* **angemeldet, nie gerufen** - nur ein Hinweis auf toten Code. Vorlagen rufen
  Namen ueber ``onclick=""``, und Namenslisten in Zeichenketten
  (``Szenenaufbau.AUFBAUEN``) rufen sie ueber ``fn[name]()``; beides wird
  mitgeprueft, sonst galten 24 lebende Funktionen als tot.

ANPASSEN: Das Register heisst nicht ueberall ``fn``. Ueber
``DJANGOBASE["skills2_register"] = ["fn", "api"]`` kann ein Projekt eigene
Namen nennen.
"""
import re

from django.conf import settings

from .werkzeug import Ergebnis, Werkzeug2

__all__ = ["JsRegistrierung"]

#: Namen in Anfuehrungszeichen - sie koennen ueber `register[name]()` gerufen
#: werden.
ALS_TEXT = re.compile(r"""['"](\w+)['"]""")


class JsRegistrierung(Werkzeug2):
    slug = "jsregistrierung"
    titel = "Funktionsregister: Anmeldung vs. Aufruf"
    zweck = ("Vergleicht `fn.name = …` mit `fn.name(…)` ueber alle .js-Dateien "
             "und Vorlagen: Wird jeder gerufene Name auch angemeldet?")
    befund = ("3DTools: vier Namen wurden gerufen, aber nie angemeldet - drei "
              "Zweige der Foto-Seite und die Lichtsteuerung der Szene waren "
              "still ohne Wirkung.")
    abhilfe = ("Fehlende Anmeldung ergaenzen oder - besser - den Namen direkt "
               "importieren statt ueber das Register zu gehen.")
    dauer = "unter 1 s"
    kriterium = 9

    NICHT_IM_PFAD = ("vendor", "theatre", "theatre-studio", "dist", "bundle",
                     "node_modules")
    #: Vorgabe-Registername, wenn das Projekt keinen nennt.
    VORGABE = ("fn",)

    def register(self):
        eigen = (getattr(settings, "DJANGOBASE", {}) or {}).get("skills2_register")
        return tuple(eigen) if eigen else JsRegistrierung.VORGABE

    def laufen(self):
        namen = "|".join(re.escape(n) for n in self.register())
        anmeldung = re.compile(r"\b(?:%s)\.(\w+)\s*=(?!=)" % namen)
        aufruf = re.compile(r"\b(?:%s)\.(\w+)\s*(?:\?\.)?\(" % namen)
        verweis = re.compile(r"\b(?:%s)\.(\w+)\b" % namen)

        angemeldet, gerufen, verwiesen = {}, {}, set()
        for pfad, text in self._texte():
            ohne = self._ohne_kommentare(text)
            for name in anmeldung.findall(ohne):
                angemeldet.setdefault(name, []).append(pfad)
            for name in aufruf.findall(ohne):
                gerufen.setdefault(name, []).append(pfad)
            # Verweise OHNE die Anmeldezeilen zaehlen - sonst gilt jeder Name
            # als verwendet, weil seine eigene Anmeldung mitzaehlt.
            ohne_anmeldung = anmeldung.sub("", ohne)
            verwiesen.update(verweis.findall(ohne_anmeldung))
            verwiesen.update(ALS_TEXT.findall(ohne_anmeldung))

        fehlend = {n: p for n, p in sorted(gerufen.items())
                   if n not in angemeldet}
        unbenutzt = sorted(n for n in angemeldet
                           if n not in gerufen and n not in verwiesen)

        zeilen = [{"art": "gerufen, NICHT angemeldet", "name": name,
                   "ort": ", ".join(sorted({p for p in pfade})[:3])}
                  for name, pfade in fehlend.items()]
        if unbenutzt:
            zeilen.append({"art": "angemeldet, nie gerufen (Hinweis)",
                           "name": "%d Namen" % len(unbenutzt),
                           "ort": ", ".join(unbenutzt[:25])})
        return Ergebnis(
            ["art", "name", "ort"], zeilen,
            zusammenfassung="%d Namen angemeldet, %d gerufen, %d fehlen"
                            % (len(angemeldet), len(gerufen), len(fehlend)),
            hinweis="Nur die erste Gruppe sind Fehler. „Angemeldet, nie "
                    "gerufen\" ist ein Hinweis: Meist wird die Funktion direkt "
                    "importiert und die Anmeldung ist ueberfluessig.")

    def _texte(self):
        wurzel = self.wurzel()
        raus = self.ausgeschlossen()
        for endung in (".js", ".html"):
            for pfad in sorted(wurzel.rglob("*" + endung)):
                if any(teil in raus for teil in pfad.parts):
                    continue
                if any(teil in JsRegistrierung.NICHT_IM_PFAD
                       for teil in pfad.parts):
                    continue
                if ".min." in pfad.name:
                    continue
                yield (pfad.relative_to(wurzel).as_posix(),
                       pfad.read_text(encoding="utf-8", errors="replace"))

    @staticmethod
    def _ohne_kommentare(text):
        """Reine Kommentarzeilen weglassen - sie erwaehnen Namen oft nur."""
        behalten = []
        for zeile in text.split("\n"):
            if zeile.lstrip().startswith(("//", "*", "/*")):
                continue
            behalten.append(zeile)
        return "\n".join(behalten)
