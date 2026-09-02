# -*- coding: utf-8 -*-
u"""LsSitzung: Rahmen, Antworten auf Server-Anfragen, URI-Wandlung — mit einer
Attrappe statt eines echten Servers. Der echte Server ist eine Gegenprobe."""
import io
import json
import threading
import unittest
from pathlib import Path

from djangobase.umbau.ls_sitzung import LsSitzung, pfad_aus_uri, uri


class Rohr:
    u"""stdin-Attrappe: sammelt, was die Sitzung schreibt."""

    def __init__(self):
        self.puffer = io.BytesIO()

    def write(self, b):
        self.puffer.write(b)

    def flush(self):
        pass

    def nachrichten(self):
        roh = self.puffer.getvalue()
        raus = []
        while roh:
            kopf, _, rest = roh.partition(b"\r\n\r\n")
            laenge = int(kopf.split(b":")[1])
            raus.append(json.loads(rest[:laenge]))
            roh = rest[laenge:]
        return raus


class Prozess:
    def __init__(self, antwort_bytes):
        self.stdin = Rohr()
        self.stdout = io.BytesIO(antwort_bytes)

    def poll(self):
        return None


def _rahmen(nachricht):
    roh = json.dumps(nachricht).encode("utf-8")
    return b"Content-Length: %d\r\n\r\n" % len(roh) + roh


class SitzungTest(unittest.TestCase):

    def test_uri_rundreise(self):
        p = Path(r"C:\p\brain\a.py") if Path("C:/").exists() else Path("/p/brain/a.py")
        self.assertEqual(pfad_aus_uri(uri(p)), p.resolve())

    def test_anfrage_wird_gerahmt_und_antwort_zugeordnet(self):
        s = LsSitzung("server", ".", {"python": {"x": 1}})
        s._prozess = Prozess(_rahmen({"jsonrpc": "2.0", "id": 1, "result": [{"uri": uri("a.py"),
                             "range": {"start": {"line": 2, "character": 3}}}]}))
        threading.Thread(target=s._lesen, daemon=True).start()
        raus = s.anfragen("textDocument/references", {"x": 1}, zeitlimit=5)
        self.assertEqual(raus[0]["range"]["start"]["line"], 2)
        gesendet = s._prozess.stdin.nachrichten()
        self.assertEqual(gesendet[0]["method"], "textDocument/references")
        self.assertEqual(gesendet[0]["id"], 1)

    def test_server_anfrage_workspace_configuration_wird_beantwortet(self):
        einstellungen = {"python": {"venv": "v"}, "python.analysis": {"typeCheckingMode": "basic"}}
        s = LsSitzung("server", ".", einstellungen)
        s._prozess = Prozess(b"")
        s._eingang({"jsonrpc": "2.0", "id": 7, "method": "workspace/configuration",
                    "params": {"items": [{"section": "python.analysis"}, {"section": "fremd"}]}})
        antwort = s._prozess.stdin.nachrichten()[0]
        self.assertEqual(antwort["id"], 7)
        self.assertEqual(antwort["result"], [{"typeCheckingMode": "basic"}, {}])

    def test_fehlerantwort_wird_zur_ausnahme(self):
        s = LsSitzung("server", ".", {})
        s._prozess = Prozess(_rahmen({"jsonrpc": "2.0", "id": 1,
                                      "error": {"code": -32601, "message": "unbekannt"}}))
        threading.Thread(target=s._lesen, daemon=True).start()
        with self.assertRaises(RuntimeError):
            s.anfragen("x", None, zeitlimit=5)

    def test_zeitlimit_ohne_antwort(self):
        s = LsSitzung("server", ".", {})
        s._prozess = Prozess(b"")
        with self.assertRaises(TimeoutError):
            s.anfragen("x", None, zeitlimit=0.2)

    def test_diagnosen_werden_gezaehlt(self):
        s = LsSitzung("server", ".", {})
        s._prozess = Prozess(b"")
        s._eingang({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                    "params": {"diagnostics": [{}, {}]}})
        self.assertEqual(s.diagnosen, 2)
