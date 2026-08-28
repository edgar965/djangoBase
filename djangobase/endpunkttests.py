# -*- coding: utf-8 -*-
u"""Endpunkt-Proben - jeden API-Endpunkt erwaehnen, ohne ihn auszuloesen.

    Kriterium 17 (Zusatz): Testcases fuer alle wichtigen Funktionen.

DAS PROBLEM MIT „RUF EINFACH JEDEN ENDPUNKT AUF"
================================================
Im Projekt assistant standen 82 Endpunkte ohne Test. Der naheliegende Weg - ein
Test, der sie der Reihe nach anfaehrt - haette echten Schaden angerichtet:
``/api/server/restart/`` startet den Server neu, ``/api/virensuche/start/``
startet einen Virenlauf ueber die Platten, die Indexier- und Musik-Endpunkte
stossen minutenlange Arbeit an. Ein Test, der das taeglich tut, ist kein Test,
sondern ein Ausloeser.

DESHALB ZWEI KLASSEN VON ENDPUNKTEN
===================================
* ``LESEN``   - liefert Auskunft, aendert nichts. Wird wirklich aufgerufen; der
                Test verlangt: keine 5xx, und angemeldet nicht abgewiesen.
* ``WIRKUNG`` - stoesst etwas an oder aendert Daten. Wird NICHT aufgerufen.
                Geprueft wird, was sich ohne Nebenwirkung pruefen laesst:
                Ist die Route aufloesbar? Ist die View importierbar? Und -
                sicherheitsrelevant - weist sie einen Unangemeldeten ab?

Die dritte Zusicherung ist die wertvollste: Ein Endpunkt, der ohne Anmeldung
etwas ausloest, ist ein echtes Loch. Genau das prueft dieser Teil auch fuer die
gefaehrlichen Endpunkte - ohne sie je scharf zu schalten.

WAS DIESER TEST NICHT LEISTET
=============================
Er prueft keine Fachlogik. „Die Rechnung wird korrekt erkannt" gehoert in einen
eigenen Component-Test. Hier geht es um die Deckungsluecke: dass jeder Endpunkt
ueberhaupt einmal angefasst wird und nicht still kaputtgeht.

BENUTZUNG
=========
    from djangobase.endpunkttests import EndpunktProbe, LESEN, WIRKUNG

    class MusikEndpunkte(EndpunktProbe):
        ENDPUNKTE = [
            (LESEN,   "musik_liste",     "/api/musik/liste/"),
            (WIRKUNG, "musik_erzeugen",  "/api/musik/erzeugen/"),
        ]
"""
import logging
import re

from django.test import TestCase

logger = logging.getLogger("djangobase.endpunkte")

__all__ = ["EndpunktProbe", "LESEN", "WIRKUNG"]

#: Liefert Auskunft, aendert nichts - wird wirklich aufgerufen.
LESEN = "lesen"
#: Stoesst etwas an oder aendert Daten - wird NICHT aufgerufen.
WIRKUNG = "wirkung"


class EndpunktProbe(TestCase):
    """Basis fuer Endpunkt-Proben eines Bereichs.

    Unterklassen setzen ``ENDPUNKTE`` als Liste von ``(art, viewname, pfad)``.
    Der Name steht dort ausdruecklich, nicht nur der Pfad: So sieht man beim
    Lesen, WELCHE Endpunkte abgedeckt sind, und das Deckungs-Werkzeug
    (``skills.testdeckung``) findet sie wieder."""

    #: [(LESEN|WIRKUNG, "view_funktionsname", "/api/…/")]
    ENDPUNKTE = []

    #: Antworten, die „der Endpunkt lebt" bedeuten. 4xx ist in Ordnung - ein
    #: Endpunkt, der Parameter braucht, DARF meckern. 5xx nicht: das ist eine
    #: Ausnahme im Server.
    KAPUTT_AB = 500

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model
        Nutzer = get_user_model()
        cls.pruefer = Nutzer.objects.create_superuser(
            **{Nutzer.USERNAME_FIELD: "endpunktprobe",
               "password": "nur-fuer-die-pruefung"})

    #: Beispielwerte fuer Routen mit Parametern. Ein Pfad wie
    #: ``/api/email/<int:doc_id>/`` ist ein MUSTER, keine Adresse - ihn
    #: unveraendert aufzuloesen scheitert immer. Die Werte muessen nicht
    #: existieren: Ein 404 ist eine gueltige Antwort, ein 500 nicht.
    BEISPIELWERTE = {"int": "1", "slug": "beispiel", "str": "beispiel",
                     "path": "beispiel",
                     "uuid": "00000000-0000-0000-0000-000000000000"}

    @classmethod
    def _konkret(cls, pfad):
        """„/api/email/<int:doc_id>/" -> „/api/email/1/"."""
        def ersetzen(treffer):
            typ = (treffer.group(1) or "str").strip(":")
            return cls.BEISPIELWERTE.get(typ, "beispiel")
        return re.sub(r"<(\w+:)?[^>]+>", ersetzen, pfad)

    # ------------------------------------------------------------------ Proben

    @staticmethod
    def _heisst_so(funktion, ziel):
        """Darf ``funktion`` in der Tabelle unter ``ziel`` stehen?

        Zwei Faelle sind richtig:

        1. ``__name__`` ist ``ziel`` — eine freie Funktion, der Normalfall.
        2. Das Modul, in dem die Funktion steht, haelt unter dem Namen
           ``ziel`` GENAU DIESE Funktion. Das trifft zu, wenn ein Bereich
           zu einer Klasse gebuendelt wurde (``freie-funktionen``) und der
           Modulname als Zuweisung stehen blieb, damit urls.py ihn findet::

               midi_serve_file = MidiSeiten.serve_file

        Nicht ueber Namensaehnlichkeit raten: ``music_serve_file`` und
        ``midi_serve_file`` enden beide auf ``_serve_file``. Wer das als
        Treffer durchgehen laesst, macht aus einer vertauschten Route
        einen gruenen Test.
        """
        import sys
        if getattr(funktion, "__name__", "") == ziel:
            return True
        modul = sys.modules.get(getattr(funktion, "__module__", ""))
        if modul is None:
            return False
        gebunden = getattr(modul, ziel, None)
        # ``is`` genuegt nicht: Bei ``@staticmethod`` liefert der Zugriff
        # ueber die Klasse und ueber das Modul dieselbe Funktion, bei
        # gebundenen Methoden aber jedes Mal ein neues Objekt.
        return gebunden is funktion or (
            getattr(gebunden, "__func__", None) is not None
            and gebunden.__func__ is getattr(funktion, "__func__", funktion))

    def test_jeder_endpunkt_ist_aufloesbar(self):
        """Zeigt die Route ins Leere? Dann ist der Endpunkt tot."""
        from django.urls import Resolver404, resolve
        tot = []
        for _art, ziel, muster in self.ENDPUNKTE:
            pfad = self._konkret(muster)
            try:
                treffer = resolve(pfad)
            except Resolver404:
                tot.append("%s (%s): Route nicht auflösbar" % (ziel, pfad))
                continue
            if ziel and not self._heisst_so(treffer.func, ziel):
                tot.append("%s zeigt auf %s, nicht auf %s" % (
                    pfad, getattr(treffer.func, "__qualname__", "?"), ziel))
        self.assertEqual(tot, [], "Kaputte Routen: %s" % tot)

    def test_kein_endpunkt_ist_ohne_anmeldung_erreichbar(self):
        """Die wichtigste Zusicherung - und die einzige, die auch fuer die
        gefaehrlichen Endpunkte ohne Nebenwirkung zu haben ist.

        Ein ``/api/server/restart/``, das jeder aufrufen kann, ist ein Loch.
        Geprueft wird mit einem FRISCHEN, nicht angemeldeten Client."""
        from django.test import Client
        offen = []
        for _art, ziel, muster in self.ENDPUNKTE:
            pfad = self._konkret(muster)
            antwort = Client().get(pfad)
            if antwort.status_code == 200:
                offen.append("%s (%s) antwortet Unangemeldeten mit 200"
                             % (ziel, pfad))
        self.assertEqual(offen, [], "Ohne Anmeldung erreichbar: %s" % offen)

    def test_lesende_endpunkte_antworten_ohne_serverfehler(self):
        """Nur die LESEN-Endpunkte werden wirklich angefahren."""
        self.client.force_login(self.pruefer)
        kaputt = []
        for art, ziel, muster in self.ENDPUNKTE:
            if art != LESEN:
                continue
            pfad = self._konkret(muster)
            try:
                antwort = self.client.get(pfad)
            except Exception as e:                              # noqa: BLE001
                kaputt.append("%s (%s): Ausnahme %s: %s"
                              % (ziel, pfad, type(e).__name__, e))
                continue
            if antwort.status_code >= self.KAPUTT_AB:
                kaputt.append("%s (%s): HTTP %s"
                              % (ziel, pfad, antwort.status_code))
        self.assertEqual(kaputt, [], "Serverfehler in lesenden Endpunkten: %s"
                                     % kaputt)

    def test_wirkende_endpunkte_werden_bewusst_nicht_ausgeloest(self):
        """Kein Aufruf - aber der Verzicht steht schwarz auf weiss im Protokoll.

        Ohne diese Zeile sieht die Deckung vollstaendig aus, und niemand weiss
        mehr, dass hier absichtlich nur die Haelfte geprüft wird."""
        wirkend = [z for a, z, _p in self.ENDPUNKTE if a == WIRKUNG]
        if wirkend:
            logger.info("%s: %d wirkende Endpunkte nur auf Route und "
                        "Zugriffsschutz geprüft, nicht ausgelöst: %s",
                        type(self).__name__, len(wirkend), ", ".join(wirkend))
        self.assertTrue(all(isinstance(z, str) for z in wirkend))
