# -*- coding: utf-8 -*-
u"""Die Cache-Kopfzeile der Statik — auch im Entwicklungsbetrieb.

WARUM DIESE DATEI (05.09.2026)
==============================
`CacheHeaderMiddleware` setzt die richtigen Kopfzeilen und sieht die Statik
trotzdem nie: `runserver` hängt seinen `StaticFilesHandler` VOR die
Middleware-Kette. Gemessen am laufenden Server, vor dem Umbau:

    GET /static/viewer/viewer/skinning.js   ->  nur Last-Modified
    GET /humanbody/scene-model/             ->  Cache-Control: no-store, …

Ohne Angabe zur Frische schätzt der Browser sie selbst — 10 % des
Dateialters. In 3DTools kostete das die halbe Seite: eine frische
Einstiegsdatei neben einem Modul aus dem Zwischenspeicher, und der fehlende
Export riss den ganzen Modulbaum ab. HTTP 200, leere Szene.

DER ERSTE ENTWURF HAT DEN SERVER LAHMGELEGT
===========================================
`__call__(self, scope, empfangen, senden)` — deutsche Parameternamen, wie
sonst überall im Projekt. Daphne ruft die Anwendung aber mit
Schlüsselwörtern auf (`server.py`: `self.application(scope=…, receive=…,
send=…)`), und damit endete JEDE Anfrage in

    TypeError: StatikKopfzeilen.__call__() got an unexpected keyword
    argument 'receive'

Deshalb steht `test_die_huelle_vertraegt_schluesselwoerter` ganz vorn: Es
ist der Fall, der wirklich passiert ist.
"""
import asyncio

from django.test import SimpleTestCase, override_settings

from djangobase.cache_middleware import NACHFRAGEN, STATIK
from djangobase.statik_kopfzeilen import StatikKopfzeilen


class Antwortprobe:
    u"""Eine winzige ASGI-Anwendung, die eine Antwort schickt und mitschreibt,
    welche Kopfzeilen dabei herauskommen."""

    def __init__(self, kopfzeilen=None):
        self.kopfzeilen = kopfzeilen or [(b'content-type', b'text/javascript')]
        self.gesehen = None
        self.aufgerufen = 0

    async def __call__(self, scope, receive, send):
        self.aufgerufen += 1
        await send({'type': 'http.response.start', 'status': 200,
                    'headers': list(self.kopfzeilen)})
        await send({'type': 'http.response.body', 'body': b'x'})

    def lauf(self, pfad, query=b'', typ='http', mit_schluesselwoertern=False):
        u"""Die Hülle einmal fahren; liefert das Kopfzeilen-Wörterbuch."""
        gesammelt = {}

        async def send(nachricht):
            if nachricht['type'] == 'http.response.start':
                gesammelt.update(dict(nachricht['headers']))

        async def leer():
            return {'type': 'http.request'}

        huelle = StatikKopfzeilen(self)
        scope = {'type': typ, 'path': pfad, 'query_string': query}
        if mit_schluesselwoertern:
            asyncio.run(huelle(scope=scope, receive=leer, send=send))
        else:
            asyncio.run(huelle(scope, leer, send))
        return gesammelt


class DieHuelleSitztRichtig(SimpleTestCase):

    def test_die_huelle_vertraegt_schluesselwoerter(self):
        u"""DER FALL, DER PASSIERT IST: Daphne ruft mit `scope=`, `receive=`,
        `send=` auf. Eigene Parameternamen ergeben HTTP 500 auf allem."""
        kopf = Antwortprobe().lauf('/static/a/x.js',
                                   mit_schluesselwoertern=True)
        self.assertEqual(kopf.get(b'cache-control'), NACHFRAGEN.encode())

    def test_und_auch_stellungsweise(self):
        kopf = Antwortprobe().lauf('/static/a/x.js')
        self.assertEqual(kopf.get(b'cache-control'), NACHFRAGEN.encode())

    def test_die_innere_anwendung_wird_immer_gerufen(self):
        u"""Die Hülle setzt Kopfzeilen, sie beantwortet nichts selbst."""
        probe = Antwortprobe()
        probe.lauf('/humanbody/irgendwas/')
        self.assertEqual(probe.aufgerufen, 1)


class WasWelcheKopfzeileBekommt(SimpleTestCase):

    def test_statik_ohne_kennung_wird_nachgefragt(self):
        kopf = Antwortprobe().lauf('/static/viewer/viewer/skinning.js')
        self.assertEqual(kopf.get(b'cache-control'), b'no-cache')

    def test_statik_mit_kennung_bleibt_ein_jahr(self):
        kopf = Antwortprobe().lauf('/static/app/x.css', query=b'v=17')
        self.assertEqual(kopf.get(b'cache-control'), STATIK.encode())

    def test_eine_leere_kennung_zaehlt_nicht(self):
        u"""`?v=` ohne Wert entsteht aus `{{ fassung }}`, wenn die Variable
        fehlt. Ein Jahr Cache wäre dann eine Falle."""
        kopf = Antwortprobe().lauf('/static/app/x.css', query=b'v=')
        self.assertEqual(kopf.get(b'cache-control'), b'no-cache')

    def test_eine_andere_abfrage_zaehlt_auch_nicht(self):
        kopf = Antwortprobe().lauf('/static/app/x.css', query=b't=1788611621')
        self.assertEqual(kopf.get(b'cache-control'), b'no-cache')

    def test_ausserhalb_der_statik_wird_nichts_gesetzt(self):
        u"""Seiten macht die Middleware, APIs entscheidet das Projekt."""
        kopf = Antwortprobe().lauf('/api/status/')
        self.assertIsNone(kopf.get(b'cache-control'))

    def test_eine_vorhandene_kopfzeile_wird_ersetzt(self):
        u"""Nicht angehängt: Zwei `Cache-Control`-Zeilen fasst der Browser
        zusammen, und aus `no-cache` plus `max-age` wird etwas, das niemand
        gemeint hat."""
        probe = Antwortprobe([(b'content-type', b'text/css'),
                              (b'cache-control', b'max-age=999')])
        kopf = probe.lauf('/static/app/x.css')
        self.assertEqual(kopf.get(b'cache-control'), b'no-cache')

    def test_andere_kopfzeilen_bleiben(self):
        probe = Antwortprobe([(b'content-type', b'text/css'),
                              (b'last-modified', b'gestern')])
        kopf = probe.lauf('/static/app/x.css')
        self.assertEqual(kopf.get(b'last-modified'), b'gestern')
        self.assertEqual(kopf.get(b'content-type'), b'text/css')


class WasSieInRuheLaesst(SimpleTestCase):

    def test_websockets_gehen_unveraendert_durch(self):
        u"""Ein `websocket`-Scope kennt gar keine Kopfzeilen — hier etwas zu
        setzen, hiesse den Kanal abzureissen."""
        probe = Antwortprobe()
        probe.lauf('/static/x.js', typ='websocket')
        self.assertEqual(probe.aufgerufen, 1)

    @override_settings(DJANGOBASE_CACHE_HEADER=False)
    def test_abschaltbar_wie_die_middleware(self):
        kopf = Antwortprobe().lauf('/static/app/x.css')
        self.assertIsNone(kopf.get(b'cache-control'))

    @override_settings(STATIC_URL='/dateien/')
    def test_ein_anderes_static_url_wird_geachtet(self):
        self.assertIsNone(
            Antwortprobe().lauf('/static/app/x.css').get(b'cache-control'))
        self.assertEqual(
            Antwortprobe().lauf('/dateien/app/x.css').get(b'cache-control'),
            b'no-cache')
