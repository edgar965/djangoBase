# -*- coding: utf-8 -*-
"""Unter welchem Praefix `djangobase.urls` eingebunden ist.

WARUM ES DIESE KLASSE GIBT (Befund 27.08.2026, 3DTools)
=======================================================
Jedes Projekt bindet `djangobase.urls` unter einem eigenen Praefix ein::

    shortlongx   path("hilfe/", include("djangobase.urls"))   -> /hilfe/...
    assistant    path("",       include("djangobase.urls"))   -> /...
    3DTools      path("help/",  include("djangobase.urls"))   -> /help/...

Vier mitgelieferte JS-Module hatten `/hilfe/tests/aufzeichnung/` fest im Text.
In 3DTools liefen sie damit auf **404 bei jedem Seitenaufruf** — dreimal je
Seite, ohne Fehlerseite, ohne Eintrag im Fehlerlog. Gefunden wurde es erst
durch eine Browserprobe, die auf Antwortcodes >= 400 achtet.

`SystemStatsLeiste.URL` loeste dasselbe Problem, indem es die Adresse
UEBERSCHREIBBAR machte — die Last liegt damit beim Projekt, und wer den Schritt
vergisst, hat wieder eine stille 404. Hier steht die Wurzel stattdessen EINMAL
im Grundgeruest, und die Module lesen sie von dort.
"""

from django.urls import NoReverseMatch, reverse


class Basiswurzel:
    """Der Praefix, unter dem `djangobase.urls` haengt — mit Schrägstrich."""

    #: Route, ueber die rueckwaerts gerechnet wird. Sie ist seit der ersten
    #: Fassung dabei; faellt sie je weg, meldet der Test `basiswurzel` das.
    ANKER = "djangobase:versionen"

    #: Was `ANKER` hinter der Wurzel anhaengt.
    ANKERWEG = "versionen/"

    #: Was gilt, wenn `djangobase.urls` gar nicht eingebunden ist. Historischer
    #: Wert — die Mehrzahl der Projekte haengt dort.
    ERSATZ = "/hilfe/"

    @staticmethod
    def weg():
        """@returns z. B. ``'/help/'``, ``'/hilfe/'`` oder ``'/'``."""
        try:
            adresse = reverse(Basiswurzel.ANKER)
        except NoReverseMatch:
            return Basiswurzel.ERSATZ
        if not adresse.endswith(Basiswurzel.ANKERWEG):
            # Ein Projekt hat die Route umgehaengt. Dann ist der Rueckschluss
            # auf die Wurzel nicht mehr gueltig — lieber der alte Wert als ein
            # falsch abgeschnittener Pfad.
            return Basiswurzel.ERSATZ
        return adresse[:-len(Basiswurzel.ANKERWEG)]
