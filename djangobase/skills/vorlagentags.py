# -*- coding: utf-8 -*-
u"""Vorlagentags - ein ``{% … %}`` ueber zwei Zeilen ist KEIN Tag.

DER FALL, GEMESSEN (28.08.2026, 3DTools)
========================================
Fuenf Einstellungsseiten bekamen einen gemeinsamen Baustein fuer die Zeile
„Standard-Animation". Der Aufruf war der Lesbarkeit halber umbrochen:

    {% include "_einstellungen_animation.html" with feld="default_anim_config"
       wert=settings.default_anim_config kennung="anim-sel-config" %}

Danach war das Auswahlfeld auf ALLEN fuenf Seiten weg. Status 200, keine
Ausnahme, kein Logeintrag, die Seite sonst vollstaendig. Djangos Lexer
(``django.template.base.tag_re``) kennt kein ``DOTALL``: Was ueber eine
Zeilengrenze geht, ist fuer ihn kein Tag, sondern Text - und Text mit
``{%``-Klammern faellt im HTML niemandem auf.

Gefunden hat es eine Browser-Probe, nicht der Testlauf: Der Baustein rendert
einzeln aufgerufen tadellos, denn dort steht der Aufruf in einer Zeile.

WAS NICHT GEMELDET WIRD
=======================
* ``{% comment %} … {% endcomment %}`` und ``{% verbatim %} … {% endverbatim %}``:
  Genau dort steht die Verwendungsanleitung eines Bausteins, und die zeigt den
  Aufruf oft umbrochen. Das ist Absicht und wirkt nie.
* ``{{ … }}``: Variablen haben denselben Lexer, aber niemand schreibt sie
  mehrzeilig - und ein Fehlalarm ist teurer als der seltene Fund.

WIE MAN ES RICHTIG MACHT: Das Tag in EINE Zeile. Wird sie zu lang, gehoert der
Inhalt in den Baustein statt in den Aufruf.
"""
import re

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["Vorlagentags"]


class Vorlagentags(BefundWerkzeug):
    slug = "vorlagen-tags"
    titel = u"Vorlagen: Tags über zwei Zeilen"
    zweck = (u"Sucht ``{% … %}``, die über eine Zeilengrenze gehen. Django "
             u"liest sie als Text, nicht als Tag — die Vorlage rendert dann "
             u"still das Falsche.")
    befund = (u"3DTools: Ein umbrochenes ``{% include %}`` liess das Auswahlfeld "
              u"für die Standard-Animation auf FÜNF Einstellungsseiten "
              u"verschwinden. Status 200, keine Ausnahme, kein Logeintrag.")
    abhilfe = (u"Das Tag in eine Zeile schreiben. Wird sie zu lang, gehört der "
               u"Inhalt in den Baustein statt in den Aufruf.")
    dauer = "unter 1 s"
    kriterium = 12

    #: Ein ``{%`` und das naechste ``%}`` mit mindestens einem Zeilenumbruch
    #: dazwischen. ``[^%]`` im Rumpf haelt die Suche kurz und verhindert, dass
    #: zwei benachbarte Tags zu einem Treffer verschmelzen.
    MEHRZEILIG = re.compile(r"\{%[^%\n]*\n[^%]*?%\}")

    #: Bereiche, in denen ein umbrochenes Tag folgenlos ist - dort steht die
    #: Anleitung, wie man den Baustein aufruft.
    GESCHUETZT = re.compile(
        r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}"
        r"|\{%\s*verbatim\s*%\}.*?\{%\s*endverbatim\s*%\}", re.S)

    anlassfall = Anlassfall(
        dateien={
            "seite.html": (
                '{% include "teil.html" with feld="a"\n'
                '   wert=b %}\n'
                '{% include "teil.html" with feld="c" wert=d %}\n'),
            "anleitung.html": (
                "{% comment %}\nSo wird es aufgerufen:\n\n"
                '  {% include "teil.html" with feld="a"\n'
                "     wert=b %}\n{% endcomment %}\n"),
        },
        mindestens=1, hoechstens=1,
        erwartet_in="seite.html",
        warum=(u"Der echte Fall und die Anleitung sehen gleich aus. Wer den "
               u"Kommentarblock nicht ausnimmt, meldet jede gut dokumentierte "
               u"Vorlage — und wird nach dem dritten Fehlalarm ignoriert."))

    def pruefen(self, **argumente):
        befunde = []
        dateien = self.pfade("*.html")
        for pfad in dateien:
            text = pfad.read_text(encoding="utf-8", errors="replace")
            frei = Vorlagentags.GESCHUETZT.sub(
                lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
            for treffer in Vorlagentags.MEHRZEILIG.finditer(frei):
                zeile = frei.count("\n", 0, treffer.start()) + 1
                anfang = " ".join(text[treffer.start():
                                       treffer.end()].split())[:70]
                befunde.append(Befund(
                    "%s:%d" % (self.kurz(pfad), zeile),
                    u"Tag über zwei Zeilen: %s" % anfang,
                    u"Django liest das als Text — die Vorlage rendert es "
                    u"woertlich statt es auszufuehren",
                    Befund.FEHLER))
        return Befundsatz(self.titel,
                          kopf=["%d Vorlagen geprüft" % len(dateien)],
                          befunde=befunde)
