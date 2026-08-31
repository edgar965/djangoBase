# -*- coding: utf-8 -*-
u"""Die Ablage der CodeRabbit-CLI lesen — welcher Lauf gehörte zu welchem Repo?

DAS PROBLEM MIT DEM ORDNERNAMEN
-------------------------------
Die CLI legt ihre Läufe unter einem Namen ab, der wie ein Hash aussieht::

    reviews/2f9756ea/2d6ad78f/reviews/1788168853877/<uuid>.json

Nachgerechnet am 31.08.2026 sind die ersten acht Zeichen der **MD5 des
Repository-Pfades** — ``md5(r"A:\\shortlongx")`` ergibt ``2f9756ea``, und
``md5(r"A:\\shared\\djangoBase")`` ergibt ``a4e10a93``. Beide stimmen.

**Darauf allein wird trotzdem nicht gebaut.** Es ist das Innenleben eines
fremden Werkzeugs, nachgerechnet an zwei Fällen; die Schreibweise des Pfades
geht schon mit einem Schrägstrich statt Backslash daneben (``A:/shortlongx``
ergibt einen völlig anderen Hash). Der Beweis steht stattdessen IM Lauf: Jeder
Ordner enthält eine ``git.json`` mit ``workingDirectory``, ``head`` und
``baseBranch``. Danach wird zugeordnet.

Die MD5 bleibt als **Abkürzung**: Trifft sie, ist nur ein Ordner zu lesen.
Trifft sie nicht, werden alle durchgesehen — dann kostet es ein paar
Dateizugriffe statt einer falschen Antwort.

WAS HIER NICHT PASSIERT
-----------------------
Es wird **kein Lauf gestartet**. Diese Klasse liest, was da ist, und sagt
ausdrücklich „nichts da", wenn nichts da ist. Das Starten bleibt beim
Knopf — im kostenlosen Plan sind es drei Läufe je Stunde, und eine Seite, die
beim Öffnen eines davon verbraucht, wäre nach dem dritten Blick wertlos.
"""
import hashlib
import json
import logging
import os
from pathlib import Path

from .befund import Befund

logger = logging.getLogger(__name__)

__all__ = ["BefundLager"]


class BefundLager:
    u"""Die Läufe eines Repositorys aus der CLI-Ablage."""

    #: Name der Datei, die einen Lauf ausweist. Sie ist der Beleg für die
    #: Zuordnung — ohne sie gilt ein Ordner nicht als Lauf.
    GIT = "git.json"

    #: Beidateien im selben Ordner, die keine Befunde sind. Sie werden nicht
    #: über den Namen ausgeschlossen (der kann sich ändern), sondern über den
    #: Inhalt — ``Befund.gueltig()`` entscheidet. Diese Liste spart nur das
    #: Einlesen der größten davon: der Diff des ganzen Laufs.
    UEBERSPRINGEN = ("git.json", "internalState.json")

    #: So viele Läufe werden höchstens gelesen. Die Seite zeigt den letzten;
    #: die älteren stehen für den Verlauf zur Verfügung.
    MAX_LAEUFE = 20

    def __init__(self, wurzel, ablage=None):
        #: Das Repository, um das es geht.
        self.wurzel = Path(wurzel)
        #: ``…/coderabbit/reviews``. Ohne Angabe wird gesucht.
        self.ablage = Path(ablage) if ablage else self._ablage_finden()

    # ------------------------------------------------------------- Ablage

    @staticmethod
    def _ablage_finden():
        u"""Wo die CLI ihre Läufe hinlegt.

        Unter Windows ist es ``%LOCALAPPDATA%\\coderabbit`` — belegt durch den
        eigenen ``doctor``-Bericht („Storage C:\\Users\\e\\AppData\\Local\\
        coderabbit is writable"). Die anderen beiden Pfade sind die üblichen
        Orte auf macOS und Linux; sie sind hier NICHT nachgemessen und stehen
        nur, damit die Seite dort nicht ins Leere greift.

        WICHTIG FÜR DEN SERVERPROZESS: ``LOCALAPPDATA`` ist das Profil DESSEN,
        der den Prozess fährt. Läuft er als Dienstkonto, zeigt die Variable ins
        Dienstprofil, wo keine Läufe liegen — dieselbe Falle, die bei der
        Anmeldung schon zugeschnappt hat (siehe ``werkzeug_partner.py``). Die
        Projekt-Konfiguration setzt sie deshalb ausdrücklich; hier wird sie nur
        gelesen."""
        kandidaten = []
        lokal = os.environ.get("LOCALAPPDATA")
        if lokal:
            kandidaten.append(Path(lokal) / "coderabbit")
        heim = Path.home()
        kandidaten += [heim / ".local" / "share" / "coderabbit",
                       heim / "Library" / "Application Support" / "coderabbit",
                       heim / ".coderabbit"]
        for k in kandidaten:
            if (k / "reviews").is_dir():
                return k / "reviews"
        return kandidaten[0] / "reviews" if kandidaten else Path("reviews")

    def vorhanden(self):
        return self.ablage.is_dir()

    # ------------------------------------------------------------- Zuordnung

    def _md5_ordner(self):
        u"""Der Ordner, den die MD5-Abkürzung nennt — falls es ihn gibt."""
        try:
            name = hashlib.md5(str(self.wurzel).encode("utf-8")).hexdigest()[:8]
        except (TypeError, ValueError):
            return None
        pfad = self.ablage / name
        return pfad if pfad.is_dir() else None

    def repo_ordner(self):
        u"""Der Oberordner dieses Repositorys — und ob er BELEGT ist.

        GEMESSEN AM 31.08.2026, und es ändert den Bau: Von sechs Lauf-Ordnern
        trugen nur die beiden JÜNGSTEN eine ``git.json``. Die CLI räumt sie in
        älteren Läufen offenbar weg — übrig bleiben die Befunde und eine
        Marke ``.session-complete-v2``.

        Ein Leser, der jeden Lauf einzeln beglaubigen will, sieht deshalb genau
        einen: Die Historie wäre still verschwunden, und die Seite hätte
        „1 Lauf" angezeigt, wo fünf liegen.

        Beglaubigt wird darum der ORDNER, nicht der einzelne Lauf: Zeigt
        IRGENDEIN Lauf darin per ``git.json`` auf unser Verzeichnis, gehört
        der Ordner diesem Repository — das ist die Struktur der Ablage (ein
        Oberordner je Repo), keine Vermutung über einen Hash.

        Zweiter Rückgabewert ``belegt``: Findet sich keine einzige
        ``git.json``, bleibt nur die MD5-Abkürzung. Sie wird benutzt, aber als
        unbelegt gekennzeichnet — die Seite sagt das dann auch."""
        for oben in sorted(self._oberordner()):
            if any(self._passt(o) for o in self._laeufe_unter(oben)):
                return oben, True
        abkuerzung = self._md5_ordner()
        return (abkuerzung, False) if abkuerzung else (None, False)

    def _oberordner(self):
        try:
            return [p for p in self.ablage.iterdir() if p.is_dir()]
        except OSError as e:
            logger.warning(u"CodeRabbit-Ablage '%s' nicht lesbar: %s", self.ablage, e)
            return []

    @staticmethod
    def _laeufe_unter(oben):
        u"""Die Lauf-Ordner unterhalb eines Repo-Ordners.

        Die Ebene dazwischen ist der Zweig; ihr Name ist ebenfalls ein Hash und
        wird deshalb nicht gedeutet, sondern durchlaufen."""
        try:
            return [d for d in oben.glob("*/reviews/*") if d.is_dir()]
        except OSError:
            return []

    def _passt(self, ordner):
        u"""Gehört dieser Lauf zu unserem Repository?

        Verglichen werden aufgelöste Pfade: ``A:\\shortlongx`` und
        ``A:/shortlongx/`` sind dasselbe Verzeichnis und dürfen nicht an einer
        Schreibweise auseinanderfallen."""
        kopf = self._git(ordner)
        verzeichnis = (kopf or {}).get("workingDirectory")
        if not verzeichnis:
            return False
        try:
            return Path(verzeichnis).resolve() == self.wurzel.resolve()
        except (OSError, ValueError):
            return str(verzeichnis).rstrip("\\/") == str(self.wurzel).rstrip("\\/")

    def _git(self, ordner):
        u"""``git.json`` — aber nur, wenn es ein Objekt ist.

        BEFUND CODERABBIT (31.08.2026): ``_json()`` gibt zurück, was in der
        Datei steht, und das kann eine Liste oder eine Zahl sein — im selben
        Ordner liegt schließlich eine Datei, die genau das ist (der Diff).
        Ein ``(kopf or {}).get(...)`` darauf wirft einen AttributeError, und
        die Befundseite antwortet mit HTTP 500 statt „Zuordnung nicht belegt".

        Die Normalisierung steht HIER und nicht bei jedem Aufrufer: Sonst
        hängt sie daran, dass niemand eine vierte Verwendung vergisst."""
        kopf = self._json(ordner / self.GIT)
        return kopf if isinstance(kopf, dict) else None

    @staticmethod
    def _json(pfad):
        u"""Eine JSON-Datei — oder ``None``.

        Eine halb geschriebene Datei (der Lauf schreibt gerade) ist kein
        Grund für einen Serverfehler; sie ist beim nächsten Blick vollständig."""
        try:
            with open(pfad, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError, UnicodeDecodeError):
            return None

    # --------------------------------------------------------------- Läufe

    def laeufe(self):
        u"""Alle Läufe, neuester zuerst — mit ihren Befunden.

        Sortiert wird nach dem Ordnernamen (Millisekunden seit 1970), nicht
        nach der Änderungszeit der Dateien: Die ändert sich, wenn jemand den
        Ordner kopiert, der Name nicht.

        Läufe OHNE Befunddateien fallen heraus. Sie sind kein „sauberer Lauf",
        sondern ein abgebrochener: Ein Lauf, der wirklich nichts fand, legt
        seine ``git.json`` trotzdem ab. Einer, der beim Start scheiterte,
        hinterlässt einen leeren Ordner — den als „0 Befunde" zu zeigen wäre
        eine Entwarnung, die niemand gegeben hat."""
        ordner, belegt = self.repo_ordner()
        if ordner is None:
            return []
        raus = [self._lauf_lesen(o, belegt) for o in self._laeufe_unter(ordner)]
        raus = [l for l in raus if l["anzahl"] or l["uebersprungen"] or l["commit"]]
        raus.sort(key=lambda l: l["ms"], reverse=True)
        return raus[:self.MAX_LAEUFE]

    def letzter(self):
        u"""Der jüngste Lauf — oder ``None``."""
        alle = self.laeufe()
        return alle[0] if alle else None

    def _lauf_lesen(self, ordner, belegt=True):
        kopf = self._git(ordner) or {}
        befunde, verworfen = self._befunde_lesen(ordner)
        return {
            "id": ordner.name,
            "ms": self._ms(ordner.name),
            "zeitpunkt": self._zeitpunkt(kopf, ordner.name),
            "zweig": kopf.get("baseBranch") or kopf.get("currentBranch") or "",
            "commit": (kopf.get("head") or "")[:8],
            "verzeichnis": kopf.get("workingDirectory") or "",
            # Ohne ``git.json`` steht hier nur, was der Ordner hergibt — der
            # Zeitpunkt aus dem Namen. Die Seite unterscheidet das, statt
            # einen leeren Commit wie einen unbekannten aussehen zu lassen.
            "belegt": bool(belegt and kopf),
            "befunde": [b.als_dict() for b in befunde],
            "anzahl": len(befunde),
            # NICHT VERSCHWEIGEN, WAS NICHT GELESEN WERDEN KONNTE: Eine Datei,
            # die keinen Befund ergab, ist entweder eine Beidatei (normal) oder
            # ein Formatwechsel (wichtig). Die Zahl steht auf der Seite; ohne
            # sie sähe ein kaputter Leser aus wie ein sauberer Lauf.
            "uebersprungen": verworfen,
        }

    def _befunde_lesen(self, ordner):
        befunde, verworfen = [], 0
        try:
            dateien = sorted(ordner.glob("*.json"))
        except OSError:
            return [], 0
        for datei in dateien:
            if datei.name in self.UEBERSPRINGEN:
                continue
            roh = self._json(datei)
            if isinstance(roh, list):
                continue                      # der Diff des Laufs, kein Befund
            befund = Befund(roh, quelle=datei.name)
            if befund.gueltig():
                befunde.append(befund)
            else:
                verworfen += 1
        befunde.sort(key=lambda b: (b.rang, b.datei, b.zeile_von))
        return befunde, verworfen

    @staticmethod
    def _ms(name):
        try:
            return int(name)
        except (TypeError, ValueError):
            return 0

    def _zeitpunkt(self, kopf, name):
        u"""Wann der Lauf war — aus ``git.json`` (Sekunden) oder dem Ordner (ms)."""
        import datetime
        sekunden = kopf.get("timestamp")
        try:
            if sekunden:
                return datetime.datetime.fromtimestamp(int(sekunden)).isoformat(" ", "seconds")
            ms = self._ms(name)
            if ms:
                return datetime.datetime.fromtimestamp(ms / 1000).isoformat(" ", "seconds")
        except (OverflowError, OSError, TypeError, ValueError):
            pass
        return ""
