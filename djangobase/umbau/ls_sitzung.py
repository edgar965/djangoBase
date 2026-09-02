# -*- coding: utf-8 -*-
u"""Eine offene Sitzung mit dem Language Server — JSON-RPC über stdin/stdout.

WOFÜR (Stufe 2 des Plans, Edgar 02.09.2026: „Dateien können umgeschrieben werden")
==================================================================================
Der Stapellauf liefert Befunde. Referenzen („wer benutzt das?"), Definition
und Umbenennen brauchen einen Server, der das Projekt geladen hält — das ist
das Language Server Protocol: Nachrichten mit ``Content-Length``-Kopf, JSON
darin, Anfragen mit ``id``, Antworten mit derselben ``id``.

WAS DER SERVER VOM CLIENT WILL
==============================
pyright fragt nach dem Start ``workspace/configuration`` (seine Einstellungen)
und meldet ``client/registerCapability``. Beides muss beantwortet werden,
sonst wartet er. Die Einstellungen kommen aus ``LsKonfig.als_lsp_einstellungen``
— dieselbe Quelle wie die ``pyrightconfig.json`` des Stapellaufs.

Ein Prozess je (Werkzeug, Wurzel), gehalten in ``SITZUNGEN``; Anfragen laufen
unter einem Schloss nacheinander. Django-frei.
"""
import json
import logging
import subprocess
import threading
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import pathname2url, url2pathname

logger = logging.getLogger("djangobase.languageserver")

__all__ = ["LsSitzung", "holen", "alle_beenden", "uri", "pfad_aus_uri"]


def uri(pfad):
    return "file:" + pathname2url(str(Path(pfad).resolve()))


def pfad_aus_uri(text):
    teile = urlparse(text)
    return Path(url2pathname(unquote(teile.path)))


class LsSitzung:
    u"""Ein laufender ``*-langserver --stdio`` und die Anfragen an ihn."""

    def __init__(self, server, wurzel, einstellungen, zeitlimit=30):
        self.server = server
        self.wurzel = Path(wurzel)
        self.einstellungen = einstellungen
        self.zeitlimit = zeitlimit
        self._prozess = None
        self._id = 0
        self._antworten = {}
        self._wecker = threading.Condition()
        self._schloss = threading.Lock()
        self._offen = set()
        self.diagnosen = 0

    # ── Lebenslauf ───────────────────────────────────────────────────────
    def starten(self):
        self._prozess = subprocess.Popen(
            [self.server, "--stdio"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, cwd=str(self.wurzel))
        threading.Thread(target=self._lesen, name="ls-sitzung", daemon=True).start()
        self.anfragen("initialize", {
            "processId": None, "rootUri": uri(self.wurzel),
            "workspaceFolders": [{"uri": uri(self.wurzel), "name": self.wurzel.name}],
            "capabilities": {"workspace": {"configuration": True,
                                           "workspaceFolders": True},
                             "textDocument": {"rename": {"prepareSupport": False}}},
        })
        self._melden("initialized", {})
        return self

    def lebt(self):
        return self._prozess is not None and self._prozess.poll() is None

    def beenden(self):
        if not self.lebt():
            return
        try:
            self.anfragen("shutdown", None, zeitlimit=5)
            self._melden("exit", None)
            self._prozess.wait(timeout=5)
        except Exception:                                 # noqa: BLE001
            self._prozess.kill()

    # ── Anfragen ─────────────────────────────────────────────────────────
    def oeffnen(self, pfad):
        pfad = Path(pfad)
        if pfad in self._offen:
            return
        self._melden("textDocument/didOpen", {"textDocument": {
            "uri": uri(pfad), "languageId": "python", "version": 1,
            "text": pfad.read_text(encoding="utf-8", errors="replace")}})
        self._offen.add(pfad)

    def referenzen(self, pfad, zeile, spalte):
        u"""Alle Stellen, die das Symbol an (zeile, spalte) benutzen — 1-basiert."""
        self.oeffnen(pfad)
        raus = self.anfragen("textDocument/references", {
            "textDocument": {"uri": uri(pfad)},
            "position": {"line": zeile - 1, "character": spalte - 1},
            "context": {"includeDeclaration": True}})
        return [self._stelle(s) for s in (raus or [])]

    def definition(self, pfad, zeile, spalte):
        self.oeffnen(pfad)
        raus = self.anfragen("textDocument/definition", {
            "textDocument": {"uri": uri(pfad)},
            "position": {"line": zeile - 1, "character": spalte - 1}})
        if isinstance(raus, dict):
            raus = [raus]
        return [self._stelle(s) for s in (raus or [])]

    def umbenennen(self, pfad, zeile, spalte, neuer_name):
        u"""Der ``WorkspaceEdit`` — noch NICHT angewandt (siehe ``ls_umbenennen``)."""
        self.oeffnen(pfad)
        return self.anfragen("textDocument/rename", {
            "textDocument": {"uri": uri(pfad)},
            "position": {"line": zeile - 1, "character": spalte - 1},
            "newName": neuer_name}) or {}

    def _stelle(self, s):
        ziel = s.get("uri") or s.get("targetUri")
        bereich = s.get("range") or s.get("targetSelectionRange") or {}
        start = bereich.get("start") or {}
        pfad = pfad_aus_uri(ziel)
        try:
            rel = str(pfad.relative_to(self.wurzel.resolve()))
        except ValueError:
            rel = str(pfad)
        return {"datei": rel.replace("\\", "/"), "zeile": int(start.get("line", 0)) + 1,
                "spalte": int(start.get("character", 0)) + 1}

    # ── JSON-RPC ─────────────────────────────────────────────────────────
    def anfragen(self, methode, params, zeitlimit=None):
        with self._schloss:
            self._id += 1
            nummer = self._id
            self._senden({"jsonrpc": "2.0", "id": nummer, "method": methode,
                          "params": params})
            with self._wecker:
                if not self._wecker.wait_for(lambda: nummer in self._antworten,
                                             timeout=zeitlimit or self.zeitlimit):
                    raise TimeoutError(u"%s: keine Antwort in %d s"
                                       % (methode, zeitlimit or self.zeitlimit))
                antwort = self._antworten.pop(nummer)
        if "error" in antwort:
            raise RuntimeError(u"%s: %s" % (methode, antwort["error"].get("message")))
        return antwort.get("result")

    def _melden(self, methode, params):
        self._senden({"jsonrpc": "2.0", "method": methode, "params": params})

    def _senden(self, nachricht):
        roh = json.dumps(nachricht).encode("utf-8")
        self._prozess.stdin.write(b"Content-Length: %d\r\n\r\n" % len(roh) + roh)
        self._prozess.stdin.flush()

    def _lesen(self):
        aus = self._prozess.stdout
        try:
            while True:
                laenge = 0
                while True:
                    zeile = aus.readline()
                    if not zeile:
                        return
                    if zeile in (b"\r\n", b"\n"):
                        break
                    if zeile.lower().startswith(b"content-length:"):
                        laenge = int(zeile.split(b":")[1].strip())
                nachricht = json.loads(aus.read(laenge).decode("utf-8"))
                self._eingang(nachricht)
        except Exception:                                 # noqa: BLE001
            logger.debug("LsSitzung: Leser beendet", exc_info=True)

    def _eingang(self, n):
        if "id" in n and "method" in n:                   # Anfrage des Servers
            self._senden({"jsonrpc": "2.0", "id": n["id"],
                          "result": self._antwort_fuer(n["method"], n.get("params"))})
        elif "id" in n:                                   # Antwort auf unsere Anfrage
            with self._wecker:
                self._antworten[n["id"]] = n
                self._wecker.notify_all()
        elif n.get("method") == "textDocument/publishDiagnostics":
            self.diagnosen += len((n.get("params") or {}).get("diagnostics") or [])

    def _antwort_fuer(self, methode, params):
        if methode == "workspace/configuration":
            return [self.einstellungen.get((e or {}).get("section") or "", {})
                    for e in (params or {}).get("items") or []]
        if methode == "workspace/workspaceFolders":
            return [{"uri": uri(self.wurzel), "name": self.wurzel.name}]
        return None


# ── eine Sitzung je (Server, Wurzel) ─────────────────────────────────────
SITZUNGEN = {}
_SCHLOSS = threading.Lock()


def holen(server, wurzel, einstellungen, zeitlimit=30):
    schluessel = (str(server), str(wurzel))
    with _SCHLOSS:
        s = SITZUNGEN.get(schluessel)
        if s is None or not s.lebt():
            s = LsSitzung(server, wurzel, einstellungen, zeitlimit).starten()
            SITZUNGEN[schluessel] = s
        return s


def alle_beenden():
    with _SCHLOSS:
        for s in SITZUNGEN.values():
            s.beenden()
        SITZUNGEN.clear()
