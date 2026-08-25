# -*- coding: utf-8 -*-
u"""Welches Werkzeug bedient welches Auftrags-Kriterium - und zwar änderbar.

DER AUFTRAG (25.08.2026, Edgar)
===============================
    „http://localhost:5020/hilfe/skills/ die nummern aus spalte 2 sollten
     veränderbar sein"

Spalte 2 der Werkzeug-Tabelle zeigt die Nummer des Kriteriums aus
``kriterien.KRITERIEN`` - die Zuordnung stand bis dahin als Klassenattribut
``kriterium = N`` im Quelltext jedes Werkzeugs. Wer sie ändern wollte, musste
eine Python-Datei bearbeiten und den Server neu starten.

WARUM DAS EINE ABLAGE BRAUCHT UND KEINE EINSTELLUNG
===================================================
Eine Einstellung in ``settings.DJANGOBASE`` wäre wieder Code. Diese Zuordnung
ändert sich beim ARBEITEN: Man sieht beim Durchgehen der Befunde, dass ein
Werkzeug eher Kriterium 9 als 4 bedient, und will das sofort festhalten. Das
gehört in eine Datei, die die Oberfläche schreibt - wie der ``aktuell``-Feed
daneben.

DAS KLASSENATTRIBUT BLEIBT DIE VORGABE
======================================
Die Datei enthält nur die ABWEICHUNGEN. Wo nichts drinsteht, gilt weiterhin
``werkzeug.kriterium``. Zwei Gründe:

  * djangoBase hängt in rund sechs Projekten. Eine Ablage, die alles führt,
    müsste in jedem Projekt erst befüllt werden - bis dahin stünde überall
    „ohne Kriterium".
  * Kommt ein neues Werkzeug dazu, bringt es seine Zuordnung selbst mit. Eine
    vollständige Ablage würde es übergehen, und niemand sähe warum.

Eine Null in der Ablage ist deshalb etwas anderes als ein fehlender Eintrag:
Null heißt ausdrücklich „dieses Werkzeug bedient KEIN Kriterium" und
überschreibt das Klassenattribut. Fehlt der Eintrag, gilt das Attribut.
"""
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["KriterienZuordnung", "zuordnung"]


class KriterienZuordnung:
    u"""Die abweichenden Kriterien-Nummern je Werkzeug - lesen und schreiben."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self._zwischen = None

    # ---------------------------------------------------------------- lesen
    def alle(self):
        u"""``{slug: nummer}`` - im Zwischenspeicher, weil je Seitenaufbau
        einmal je Werkzeug gefragt wird (rund 45 Mal).

        Eine unlesbare oder halb geschriebene Datei darf die Seite nicht
        umbringen: Dann gilt eben überall das Klassenattribut, und die Ursache
        steht im Protokoll.
        """
        if self._zwischen is not None:
            return self._zwischen
        self._zwischen = {}
        if self.pfad.exists():
            try:
                roh = json.loads(self.pfad.read_text(encoding="utf-8") or "{}")
                self._zwischen = {str(k): int(v) for k, v in dict(roh).items()}
            except (ValueError, TypeError, OSError) as e:
                logger.warning("Kriterien-Zuordnung %s nicht lesbar: %s",
                               self.pfad, e)
        return self._zwischen

    def fuer(self, werkzeug):
        u"""Die Nummer dieses Werkzeugs: Ablage schlägt Klassenattribut.

        ``werkzeug`` darf die Klasse oder ihr Slug sein - die Aufrufer in
        ``views/skills.py`` haben mal das eine, mal das andere zur Hand.
        """
        slug = getattr(werkzeug, "slug", werkzeug)
        gespeichert = self.alle().get(str(slug))
        if gespeichert is not None:
            return gespeichert
        return getattr(werkzeug, "kriterium", 0) or 0

    def abweichend(self, werkzeug):
        u"""Weicht dieses Werkzeug von seiner Vorgabe im Code ab?

        Die Oberfläche kennzeichnet solche Zeilen - sonst sieht man einer Zahl
        nicht an, ob sie aus dem Quelltext stammt oder von Hand gesetzt wurde,
        und beim nächsten ``git pull`` wundert sich jemand.
        """
        slug = str(getattr(werkzeug, "slug", werkzeug))
        gespeichert = self.alle().get(slug)
        return (gespeichert is not None
                and gespeichert != (getattr(werkzeug, "kriterium", 0) or 0))

    # -------------------------------------------------------------- ändern
    def setzen(self, slug, nummer, vorgabe=None):
        u"""Eine Nummer festhalten - oder die Abweichung wieder aufheben.

        Entspricht ``nummer`` der ``vorgabe`` aus dem Code, wird der Eintrag
        GELÖSCHT statt gespeichert. Sonst sammelte die Datei Einträge an, die
        nichts bewirken, und ein späterer Wechsel der Vorgabe im Quelltext
        käme nicht mehr durch - stillgelegt von einer Zeile, die dasselbe zu
        sagen schien.
        """
        daten = dict(self.alle())
        slug = str(slug)
        try:
            nummer = int(nummer)
        except (TypeError, ValueError):
            return False
        if vorgabe is not None and nummer == (int(vorgabe) or 0):
            daten.pop(slug, None)
        else:
            daten[slug] = nummer
        return self._schreiben(daten)

    def viele_setzen(self, paare, vorgaben=None):
        u"""Mehrere auf einmal - EIN Schreibvorgang für das ganze Formular.

        Die Tabelle schickt alle Zeilen zugleich ab. Jede einzeln zu schreiben
        hiesse, die Datei 45 Mal zu ersetzen; bricht es in der Mitte ab, steht
        die Hälfte drin.
        """
        daten = dict(self.alle())
        vorgaben = vorgaben or {}
        geaendert = 0
        for slug, nummer in dict(paare).items():
            slug = str(slug)
            try:
                nummer = int(nummer)
            except (TypeError, ValueError):
                continue
            vorher = daten.get(slug)
            if nummer == (int(vorgaben.get(slug, -1)) if slug in vorgaben else -1):
                daten.pop(slug, None)
            else:
                daten[slug] = nummer
            if daten.get(slug) != vorher:
                geaendert += 1
        if geaendert:
            self._schreiben(daten)
        return geaendert

    def _schreiben(self, daten):
        u"""Erst in eine Nebendatei, dann umbenennen.

        Ein abgebrochener Schreibvorgang darf keine halbe JSON-Datei
        hinterlassen - die wäre beim nächsten Lesen unbrauchbar, und die
        Zuordnung aller Werkzeuge wäre weg. ``os.replace`` ist auf einem
        Dateisystem unteilbar.
        """
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.pfad.parent),
                                       prefix="." + self.pfad.name + ".",
                                       suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(daten, f, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(tmp, str(self.pfad))
            self._zwischen = daten
            return True
        except OSError as e:
            logger.warning("Kriterien-Zuordnung %s nicht schreibbar: %s",
                           self.pfad, e)
            return False


def zuordnung():
    u"""Die Zuordnung dieses Projekts (Pfad aus der Konfiguration).

    Liegt neben dem ``aktuell``-Feed im Protokollverzeichnis - dort steht schon
    alles andere, was die Oberfläche schreibt, und es ist in jedem Projekt
    eingerichtet.
    """
    from ..conf import conf
    c = conf()
    return KriterienZuordnung(c.get("skills_kriterien_datei")
                              or (c["log_verzeichnis"] / "skills_kriterien.json"))
