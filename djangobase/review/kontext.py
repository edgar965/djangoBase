# -*- coding: utf-8 -*-
u"""Wohin der Kontext einer Claude-Code-Sitzung geht — gemessen.

DIE ANSAGE (Edgar, 02.09.2026)
==============================
    „in dieser session wird sehr oft compact aufgefordert, warum? kannst
     du analysieren und ggf. aufräumen?" — und danach: „baue die
     Kontextanalyse auch als werkzeug ein"

WAS DIE MESSUNG AM ERSTEN TAG ZEIGTE
====================================
Sitzung ``14d72ea8`` im Projekt ``assistant``, 280 MB Protokoll:

    Bash (Ergebnis)     22,0 MB   18.863 Aufrufe
    Write (Aufruf)      12,7 MB    2.736 ×
    Read (Ergebnis)     11,6 MB      634 ×   ->  18 KB je Aufruf
    Browser-Ergebnisse   9,2 MB      198 ×   ->  46 KB je Aufruf
    Bilder               4,0 MB        9 ×   -> 444 KB je Bildschirmfoto

Das groesste EINZELNE Ergebnis: 676.644 Zeichen — rund 178.000 Token fuer
einen einzigen ``Read``. Ein Bildschirmfoto kostet etwa 117.000 Token.
Wer das weiss, liest Dateien in Abschnitten und macht Bilder sparsam.

WARUM AUF KNOPFDRUCK
====================
Das Protokoll ist dreistellig MB gross. Gelesen wird zeilenweise (kein
``json.load`` ueber alles), aber ein Durchgang dauert trotzdem Sekunden —
das gehoert nicht in den Weg von jemandem, der nur die Seite aufschlaegt.
Dieselbe Lehre wie beim Werkzeug Klassenmodell am selben Tag.
"""
import json
from collections import Counter
from pathlib import Path

#: Grobe Umrechnung Zeichen -> Token. Fuer deutschen Text und Quelltext
#: liegt der Faktor bei etwa 3,5 bis 4 Zeichen je Token. Die Zahl ist
#: eine Groessenordnung, keine Abrechnung — sie steht deshalb neben den
#: Zeichen, nicht an ihrer Stelle.
ZEICHEN_JE_TOKEN = 3.8

#: Ab dieser Groesse gilt ein einzelnes Ergebnis als Brocken und wird
#: mit Namen und Aufruf gezeigt.
BROCKEN_AB = 20000


class Kontextanalyse:
    u"""Zaehlt, welche Art von Eintrag wie viele Zeichen belegt."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.nach_art = Counter()
        self.anzahl_art = Counter()
        self.nach_werkzeug = Counter()
        self.anzahl_werkzeug = Counter()
        self.brocken = []
        #: ``{tool_use_id: Werkzeugname}`` und ``{id: Aufruf}`` — das
        #: Ergebnis nennt nur die Kennung, nicht den Namen.
        self._namen = {}
        self._befehle = {}

    # ── Lesen ───────────────────────────────────────────────────
    def lesen(self):
        u"""Das Protokoll einmal durchgehen. Liest nur, schreibt nichts."""
        with self.pfad.open('r', encoding='utf-8', errors='replace') as f:
            for zeile in f:
                try:
                    satz = json.loads(zeile)
                except ValueError:
                    continue
                self._satz(satz, len(zeile))
        self.brocken.sort(reverse=True)
        del self.brocken[40:]
        return self

    def _satz(self, satz, laenge):
        art = satz.get('type', '?')
        self.nach_art[art] += laenge
        self.anzahl_art[art] += 1
        inhalt = (satz.get('message') or {}).get('content')
        if not isinstance(inhalt, list):
            return
        for teil in inhalt:
            if isinstance(teil, dict) and teil.get('type') == 'tool_use':
                self._namen[teil.get('id')] = teil.get('name', '?')
                self._befehle[teil.get('id')] = self._aufruf(teil)
        for teil in inhalt:
            if isinstance(teil, dict):
                self._teil(teil)

    def _teil(self, teil):
        sorte = teil.get('type')
        if sorte == 'tool_use':
            self._zaehlen('%s (Aufruf)' % teil.get('name', '?'),
                          len(json.dumps(teil.get('input', {}),
                                         ensure_ascii=False)))
        elif sorte == 'tool_result':
            gross = len(json.dumps(teil.get('content', ''),
                                   ensure_ascii=False))
            kennung = teil.get('tool_use_id')
            name = self._namen.get(kennung, 'Werkzeug')
            self._zaehlen('%s (Ergebnis)' % name, gross)
            if gross > BROCKEN_AB:
                self.brocken.append(
                    (gross, name, self._befehle.get(kennung, '')))
        elif sorte == 'image':
            self._zaehlen('Bildschirmfoto',
                          len(json.dumps(teil.get('source', {}),
                                         ensure_ascii=False)))

    def _zaehlen(self, name, gross):
        self.nach_werkzeug[name] += gross
        self.anzahl_werkzeug[name] += 1

    @staticmethod
    def _aufruf(teil):
        u"""Woran man den Aufruf wiedererkennt — Befehl, Pfad, Muster."""
        eingabe = teil.get('input') or {}
        for feld in ('command', 'file_path', 'pattern', 'url', 'text'):
            wert = eingabe.get(feld)
            if wert:
                return ' '.join(str(wert).split())[:120]
        return ''

    # ── Auskunft ────────────────────────────────────────────────
    def kennzahlen(self):
        gesamt = sum(self.nach_art.values())
        return {
            'datei': self.pfad.name,
            'mb': round(gesamt / 1e6, 1),
            'token': int(gesamt / ZEICHEN_JE_TOKEN),
            'eintraege': sum(self.anzahl_art.values()),
            'werkzeugaufrufe': sum(
                n for k, n in self.anzahl_werkzeug.items()
                if k.endswith('(Aufruf)')),
        }

    def arten(self):
        u"""``[{name, mb, token, anzahl}]`` — nach Groesse."""
        return [self._zeile(k, v, self.anzahl_art[k])
                for k, v in self.nach_art.most_common()]

    def werkzeuge(self, wie_viele=15):
        return [self._zeile(k, v, self.anzahl_werkzeug[k])
                for k, v in self.nach_werkzeug.most_common(wie_viele)]

    def groesste(self, wie_viele=15):
        u"""Die dicksten Einzelergebnisse — dort liegt der Hebel."""
        return [{'zeichen': g, 'token': int(g / ZEICHEN_JE_TOKEN),
                 'werkzeug': n, 'aufruf': b}
                for g, n, b in self.brocken[:wie_viele]]

    @staticmethod
    def _zeile(name, zeichen, anzahl):
        return {
            'name': name,
            'mb': round(zeichen / 1e6, 2),
            'token': int(zeichen / ZEICHEN_JE_TOKEN),
            'anzahl': anzahl,
            # Der Schnitt je Aufruf ist die eigentliche Aussage: 634 Reads
            # mit 18 KB im Schnitt sind teurer als 18.863 kurze Befehle.
            'je_aufruf': int(zeichen / anzahl) if anzahl else 0,
        }


__all__ = ['Kontextanalyse', 'ZEICHEN_JE_TOKEN']
