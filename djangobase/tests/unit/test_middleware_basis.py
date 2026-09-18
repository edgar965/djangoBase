# -*- coding: utf-8 -*-
"""Eine Middleware muss beide Betriebsarten können — sonst steht der Dienst.

DER VORFALL (CamTrack, 11.09.2026)
==================================
    „server ist tot" / „server immer noch tot"

Der Web-Dienst nahm Verbindungen an und antwortete nicht mehr. Im Stack-Abzug
(``py-spy dump``) wartete die Ereignisschleife beim Aufräumen auf ihren
Faden-Pool, und drei Fäden darin warteten in ``AsyncToSync`` auf die
Ereignisschleife — in ``djangobase/cache_middleware.py``. Ein Ring.

Der Rückruf entsteht nicht im Code dieser Bibliothek, sondern aus einer
Unterlassung: Wer ``async_capable`` nicht setzt, gilt Django als nur synchron,
und Django wickelt dann den ganzen Rest der Kette in ``async_to_sync``.

Die Begründung mit dem vollständigen Abzug steht im Kopf von
``djangobase/middleware_basis.py``.

WAS HIER GEPRÜFT WIRD
=====================
Der Rahmen selbst: dass beide Einstiege da sind, dass die Haken in der
richtigen Reihenfolge laufen, dass ``braucht_faden`` die Arbeit wirklich von
der Ereignisschleife holt und dass ein Fehler im Haken die Antwort nicht
kostet.
"""

import asyncio

from asgiref.sync import iscoroutinefunction
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from djangobase.middleware_basis import ZweiwegMiddleware


def _anfrage(pfad="/irgendwo/"):
    return RequestFactory().get(pfad)


def _synchron(request):
    return HttpResponse(b"ok")


async def _asynchron(request):
    return HttpResponse(b"ok")


class Mitschrift(ZweiwegMiddleware):
    """Schreibt mit, was wann läuft."""

    def __init__(self, get_response):
        super().__init__(get_response)
        self.spur = []

    def vorbereiten(self, request):
        self.spur.append("vor")

    def nachbereiten(self, request, antwort):
        self.spur.append("nach")
        antwort["X-Spur"] = ",".join(self.spur)


class BEIDE_EINSTIEGE(SimpleTestCase):
    """Synchron wie bisher, asynchron ohne Rückruf."""

    databases = []

    def test_synchron_laeuft_alles_der_reihe_nach(self):
        mw = Mitschrift(_synchron)
        antwort = mw(_anfrage())
        self.assertEqual(mw.spur, ["vor", "nach"])
        self.assertEqual(antwort["X-Spur"], "vor,nach")

    def test_asynchron_meldet_sich_als_koroutine(self):
        mw = Mitschrift(_asynchron)
        self.assertTrue(
            iscoroutinefunction(mw),
            "Ohne `markcoroutinefunction` hält Django die Instanz für "
            "synchron und bekommt ein Coroutine-Objekt statt einer Antwort.",
        )

    def test_asynchron_laeuft_alles_der_reihe_nach(self):
        mw = Mitschrift(_asynchron)
        antwort = asyncio.run(mw(_anfrage()))
        self.assertEqual(mw.spur, ["vor", "nach"])
        self.assertEqual(antwort["X-Spur"], "vor,nach")

    def test_die_zwei_zusagen_stehen_da(self):
        self.assertTrue(ZweiwegMiddleware.sync_capable)
        self.assertTrue(
            ZweiwegMiddleware.async_capable,
            "Das ist die Zusage, um die es geht. Ohne sie wickelt Django "
            "den Rest der Kette in `async_to_sync`.",
        )


class DIE_DATENBANK_FALLE(SimpleTestCase):
    """`braucht_faden` holt die Arbeit von der Ereignisschleife herunter."""

    databases = []

    def _laeuft_auf_der_schleife(self, braucht_faden):
        gefunden = {}

        class Prueft(ZweiwegMiddleware):
            def nachbereiten(self, request, antwort):
                try:
                    asyncio.get_running_loop()
                    gefunden["schleife"] = True
                except RuntimeError:
                    gefunden["schleife"] = False

        Prueft.braucht_faden = braucht_faden
        asyncio.run(Prueft(_asynchron)(_anfrage()))
        return gefunden["schleife"]

    def test_ohne_faden_laeuft_es_auf_der_schleife(self):
        self.assertTrue(self._laeuft_auf_der_schleife(False))

    def test_mit_faden_laeuft_es_daneben(self):
        self.assertFalse(
            self._laeuft_auf_der_schleife(True),
            "Mit `braucht_faden` muss der Haken NEBEN der Ereignisschleife "
            "laufen — sonst wirft jeder Datenbank-Zugriff "
            "`SynchronousOnlyOperation`, und der `except`-Block verschluckt "
            "es still.",
        )


class EIN_FEHLER_KOSTET_KEINE_SEITE(SimpleTestCase):
    """Beiwerk darf nie eine Antwort kosten — aber nur, wenn es Beiwerk ist."""

    databases = []

    class Kaputt(ZweiwegMiddleware):
        def nachbereiten(self, request, antwort):
            raise ValueError("kaputt")

    def test_synchron_kommt_die_antwort_trotzdem(self):
        antwort = self.Kaputt(_synchron)(_anfrage())
        self.assertEqual(antwort.status_code, 200)

    def test_asynchron_kommt_die_antwort_trotzdem(self):
        antwort = asyncio.run(self.Kaputt(_asynchron)(_anfrage()))
        self.assertEqual(antwort.status_code, 200)

    def test_wer_nicht_schlucken_will_muss_es_sagen(self):
        class Laut(self.Kaputt):
            fehler_schlucken = False

        with self.assertRaises(ValueError):
            Laut(_synchron)(_anfrage())
        with self.assertRaises(ValueError):
            asyncio.run(Laut(_asynchron)(_anfrage()))


class DIE_VORGABE_IST_NICHTS_TUN(SimpleTestCase):
    """Wer nur einen Haken braucht, soll den anderen nicht schreiben müssen."""

    databases = []

    def test_ohne_haken_geht_die_antwort_unveraendert_durch(self):
        antwort = ZweiwegMiddleware(_synchron)(_anfrage())
        self.assertEqual(antwort.content, b"ok")
        self.assertEqual(asyncio.run(ZweiwegMiddleware(_asynchron)(_anfrage())).content, b"ok")
