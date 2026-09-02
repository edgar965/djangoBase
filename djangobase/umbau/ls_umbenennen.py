# -*- coding: utf-8 -*-
u"""Einen ``WorkspaceEdit`` des Servers ansehen — und mit Netz anwenden.

„Dateien können umgeschrieben werden" (Edgar, 02.09.2026). Also dieselbe
Bauart wie die Fixer des Werkzeugkastens: erst die VORSCHAU (jede Stelle,
alt gegen neu), dann das Schreiben mit SICHERUNG, und danach das NETZ —
jede geänderte ``.py`` muss noch ``compile()`` überstehen, sonst kommt die
Sicherung zurück und der Fehler steht im Bericht. Das Netz ist nicht
verhandelbar (djangoBase-CLAUDE.md, Fixer ``fix-ausnahme``: ein Umbau, der
kompilierte, hat trotzdem einmal den Start verhindert).

Zeilenenden bleiben, wie sie sind: Gelesen und geschrieben wird mit
``newline=""``, sonst würde jede CRLF-Datei beim Umbenennen stillschweigend
zu LF — und ``git`` zeigte 300 geänderte Zeilen für einen Namen.
"""
import shutil
import time
from pathlib import Path

from .ls_sitzung import pfad_aus_uri

__all__ = ["Umbenennung"]


class Umbenennung:
    u"""Vorschau und Anwendung eines ``WorkspaceEdit``."""

    def __init__(self, edit, wurzel, sicherung):
        self.edit = edit or {}
        self.wurzel = Path(wurzel).resolve()
        self.sicherung = Path(sicherung)

    # ── zerlegen ─────────────────────────────────────────────────────────
    def aenderungen(self):
        u"""``{Pfad: [(zeile0, spalte0, endzeile0, endspalte0, neu), …]}``.

        Beide Formen des Protokolls: ``changes`` (uri → edits) und
        ``documentChanges`` (Liste von TextDocumentEdit)."""
        raus = {}
        for u, edits in (self.edit.get("changes") or {}).items():
            raus.setdefault(pfad_aus_uri(u), []).extend(self._edits(edits))
        for d in self.edit.get("documentChanges") or []:
            if "textDocument" in d:
                raus.setdefault(pfad_aus_uri(d["textDocument"]["uri"]), []) \
                    .extend(self._edits(d.get("edits") or []))
        for edits in raus.values():
            edits.sort(key=lambda e: (e[0], e[1]), reverse=True)
        return raus

    @staticmethod
    def _edits(edits):
        raus = []
        for e in edits:
            r = e.get("range") or {}
            s, z = r.get("start") or {}, r.get("end") or {}
            raus.append((int(s.get("line", 0)), int(s.get("character", 0)),
                         int(z.get("line", 0)), int(z.get("character", 0)),
                         e.get("newText") or ""))
        return raus

    def _rel(self, pfad):
        try:
            return str(pfad.relative_to(self.wurzel)).replace("\\", "/")
        except ValueError:
            return str(pfad)

    # ── Vorschau ─────────────────────────────────────────────────────────
    def vorschau(self):
        u"""``[{datei, zeile, alt, neu, zeile_text}]`` — nach Datei und Zeile."""
        raus = []
        for pfad, edits in self.aenderungen().items():
            try:
                zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for z0, s0, z1, s1, neu in sorted(edits):
                text = zeilen[z0] if z0 < len(zeilen) else u""
                alt = text[s0:s1] if z0 == z1 else text[s0:]
                raus.append({"datei": self._rel(pfad), "zeile": z0 + 1,
                             "alt": alt, "neu": neu, "zeile_text": text.strip()})
        raus.sort(key=lambda v: (v["datei"], v["zeile"]))
        return raus

    # ── Anwenden ─────────────────────────────────────────────────────────
    def anwenden(self):
        u"""Schreiben mit Sicherung und Netz. ``{dateien, stellen, sicherung, fehler}``."""
        stempel = time.strftime("%Y%m%d_%H%M%S")
        ablage = self.sicherung / stempel
        dateien, stellen, fehler = 0, 0, []
        for pfad, edits in self.aenderungen().items():
            try:
                with open(pfad, "r", encoding="utf-8", newline="") as f:
                    original = f.read()
            except OSError as e:
                fehler.append(u"%s: nicht lesbar (%s)" % (self._rel(pfad), e))
                continue
            neu = self._anwenden_auf(original, edits)
            if pfad.suffix == ".py":
                try:
                    compile(neu, str(pfad), "exec")
                except SyntaxError as e:
                    fehler.append(u"%s: nach dem Umbau nicht mehr kompilierbar "
                                  u"(Zeile %s) — unverändert gelassen"
                                  % (self._rel(pfad), e.lineno))
                    continue
            ziel = ablage / self._rel(pfad)
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pfad, ziel)
            with open(pfad, "w", encoding="utf-8", newline="") as f:
                f.write(neu)
            dateien += 1
            stellen += len(edits)
        return {"dateien": dateien, "stellen": stellen,
                "sicherung": str(ablage) if dateien else "", "fehler": fehler}

    @staticmethod
    def _anwenden_auf(text, edits):
        u"""Edits von hinten nach vorn auf den Text — Zeilenenden inklusive."""
        zeilen = text.splitlines(keepends=True)
        anfang = [0]
        for z in zeilen:
            anfang.append(anfang[-1] + len(z))
        for z0, s0, z1, s1, neu in edits:            # schon absteigend sortiert
            von = anfang[min(z0, len(zeilen))] + s0
            bis = anfang[min(z1, len(zeilen))] + s1
            text = text[:von] + neu + text[bis:]
        return text
