# -*- coding: utf-8 -*-
u"""Aufrufkette - faengt wenigstens EIN Glied ueber diesem Aufruf?

Aus ``jsfaenger.py`` herausgeloest (17.08.2026), zusammen mit ``Stelle``.

WARUM ES DIESE KLASSE GIBT
==========================
``jsfaenger`` meldete in 3DTools 20 ungefangene Serverabrufe. **Achtzehn davon
waren keine Fundstelle**: fast alle ein ``return Serverabruf.json(...)`` in
einem Einzeiler-Helfer, um den herum sehr wohl gefangen wird. Eine Liste, in der
neun von zehn Zeilen nichts sind, verdeckt die echten - dieselbe Lehre wie bei
den mechanischen Befunden („Fehlalarme sind teurer als fehlende Befunde").

Gedeckt gilt nur, wer MINDESTENS EINEN Aufrufer hat und bei dem KEIN Aufrufer
offen ist. Die Unsicherheit zeigt damit in die sichere Richtung: Wer nicht
zuzuordnen ist, bleibt ein Befund.

VIER FALLEN, ALLE BELEGT
========================
* **Der Einzeiler.** ``try { await x(); } catch (e) { … }`` in EINER Zeile galt
  nicht als try-Block (siehe ``Stelle._blockende``).
* **Der Name in einer Meldung.** ``throw new Error('loadRetargetConfig() must
  be called …')`` zaehlte als ungefangener Aufruf.
* **Der gleichnamige Fremde.** ``_holen()`` gibt es in zwei Klassen, die nichts
  miteinander zu tun haben; ``load()`` heisst auch die Methode von Three.js'
  ``GLTFLoader``. Gesucht wird deshalb nur, wo der Name sichtbar IST.
* **Die Sammelstelle.** ``save_load.js`` ruft ``fn.CharacterInstance.fromJSON()``
  ohne ``character.js`` zu importieren - der Name wandert ueber ``fn.X = X``.
  Solche Dateien zaehlen mit, aber nur wo ein veroeffentlichter Name in der NAEHE
  des Aufrufs steht (Fenster ``FENSTER``). Ohne diese Einschraenkung war
  ``gltfLoader.load(...)`` der „Aufrufer"; mit der Aufrufzeile allein fiel der
  echte Fall durch (``const f = new fn.Figur();`` steht eine Zeile hoeher).

Von 20 blieben 2. Beide waren echt.
"""
import re

from .jsstelle import Stelle

__all__ = ["Aufrufkette"]


class Aufrufkette:
    """Verfolgt, wer die umgebende Funktion ruft - und ob dort gefangen wird."""

    #: So viele Glieder werden verfolgt. Drei, weil `vorschau.js` in 3DTools
    #: genau drei braucht: `oeffnen()` faengt mit sichtbarer Meldung, `_laden()`
    #: ruft, `_modellBauen()` ruft ab. Mehr bringt nichts - wer vier Ebenen
    #: ueber dem Abruf faengt, zeigt keine passende Meldung mehr.
    TIEFE = 3
    #: Importe stehen am Dateianfang; so viele Zeilen werden dafuer gelesen.
    KOPF = 120
    #: Fenster um einen Aufruf, in dem ein ueber die Sammelstelle gereichter
    #: Name genannt sein muss. Etwa die Groesse einer Funktion.
    FENSTER = 25

    #: Methodennamen, die in jeder zweiten Bibliothek vorkommen. Fuer sie zaehlt
    #: nur der Import-Weg, nicht die Sammelstelle — sonst entscheidet ein
    #: fremdes `load()` ueber den Befund.
    GENERISCH = {"load", "save", "init", "update", "render", "get", "set",
                 "send", "open", "close", "start", "stop", "run", "add",
                 "remove", "reset", "laden", "speichern", "senden"}

    #: `fn.Name = …`, `window.Name = …`, `window.__Name = …` am Zeilenanfang.
    SAMMELSTELLE = re.compile(
        r"^\s*(?:fn|window|globalThis)\.(?:__)?([A-Za-z_$][\w$]*)\s*=")

    def __init__(self, quellen, ausgenommen=()):
        #: [(kurzer Pfad, Zeilenliste)] aller geprueften Dateien.
        self.quellen = list(quellen)
        #: Praefixe, die NICHT als Aufruf zaehlen (die Abrufklasse selbst).
        self.ausgenommen = tuple(ausgenommen)
        self._sicht = {}

    def urteil(self, stelle, tiefe=0, gesehen=None):
        u"""``""`` wenn alle Aufrufstellen fangen, sonst der Grund."""
        name = stelle.umgebende_funktion()
        if not name:
            return "keine umgebende Funktion erkannt"
        gesehen = set(gesehen or ())
        gesehen.add((stelle.datei, name))
        stellen = 0
        for oben in self._aufrufstellen(stelle.datei, name):
            if (oben.datei, oben.umgebende_funktion()) in gesehen:
                continue                      # Ringschluss oder Rekursion
            stellen += 1
            if oben.gefangen():
                continue
            offen = "%s() wird in %s:%d ungefangen gerufen" % (
                name, oben.datei, oben.nummer + 1)
            if tiefe + 1 >= Aufrufkette.TIEFE:
                return offen
            weiter = self.urteil(oben, tiefe + 1, gesehen)
            if weiter:
                # „kein Aufrufer" eine Ebene hoeher sagt nichts ueber DIESE
                # Ebene - dann gilt der Befund hier, mit dieser Fundstelle.
                return offen if "kein Aufrufer" in weiter else weiter
        if not stellen:
            return "%s() — kein Aufrufer gefunden" % name
        return ""

    # ----------------------------------------------------------- Aufrufstellen

    def _aufrufstellen(self, datei, name):
        """Jede Zeile, die ``name`` als Aufruf enthält - dort, wo er sichtbar ist."""
        muster = re.compile(r"(?<![\w$.])(?:\w[\w$]*\.)?" + re.escape(name)
                            + r"\s*\(")
        ueber_import, ueber_sammelstelle, namen = self._sichtbar(datei)
        # Bei einem Allerweltsnamen zaehlt NUR der Import-Weg. `load()` heisst in
        # 3DTools sowohl die Methode von `CharacterInstance` als auch die von
        # Three.js' `GLTFLoader`; ueber die Sammelstelle sichtbar gemacht, wurde
        # `_loadHairForCharacter()` zum „Aufrufer" der Netz-Ladefunktion — eine
        # Kette, die es nicht gibt (17.08.2026). Der eigentliche Weg laeuft
        # ohnehin ueber die eigene Datei und von dort ueber einen eigenen Namen
        # (`fromJSON`) weiter.
        if name in Aufrufkette.GENERISCH:
            ueber_sammelstelle = set()
        for kurz, zeilen in self.quellen:
            if kurz in ueber_import:
                marken = None
            elif kurz in ueber_sammelstelle:
                marken = namen
            else:
                continue
            for nummer, zeile in enumerate(zeilen):
                treffer = muster.search(zeile)
                if not treffer or zeile.lstrip().startswith(("*", "//")):
                    continue
                if Stelle.DEFINITION.match(zeile):
                    continue                      # die Definition selbst
                if any(v in zeile for v in self.ausgenommen):
                    continue                      # der Abruf, um den es geht
                if Stelle.in_zeichenkette(zeile, treffer.start()):
                    continue
                if marken is not None and not self._nahebei(zeilen, nummer,
                                                            marken):
                    continue
                yield Stelle(kurz, zeilen, nummer)

    @staticmethod
    def _nahebei(zeilen, nummer, marken):
        u"""Wird ein veroeffentlichter Name in der Naehe des Aufrufs genannt?

        Bei einer Datei, die den Namen nur ueber die Sammelstelle sieht, ist die
        Frage: Geht es hier ueberhaupt um DIESE Klasse? Zwei Extreme sind beide
        falsch — die ganze Datei zu nehmen liess `gltfLoader.load(...)` als
        Aufrufer von `CharacterInstance.load()` gelten; nur die Aufrufzeile zu
        nehmen verwarf den echten Fall (``const f = new fn.Figur();`` steht eine
        Zeile hoeher). Deshalb ein Fenster um den Aufruf, etwa in der Groesse
        einer Funktion.
        """
        von = max(0, nummer - Aufrufkette.FENSTER)
        bis = min(len(zeilen), nummer + Aufrufkette.FENSTER)
        text = "\n".join(zeilen[von:bis])
        return any(m in text for m in marken)

    def _sichtbar(self, datei):
        """(per Import, per Sammelstelle, veroeffentlichte Namen) — gemerkt."""
        if datei not in self._sicht:
            self._sicht[datei] = self._sichtbar_rechnen(datei)
        return self._sicht[datei]

    def _sichtbar_rechnen(self, datei):
        kurzname = datei.rsplit("/", 1)[-1]
        stamm = kurzname[:-3] if kurzname.endswith(".js") else kurzname
        # `from './bvhtext.js'`, `from '../a/bvhtext'` — und mit
        # Cache-Busting-Anhang: In 3DTools steht
        # `from '../retarget_hybrid.js?v=32'`. Ohne das `?…` im Muster galt die
        # Datei als von niemandem importiert (17.08.2026).
        bezug = re.compile(r"""from\s+['"][^'"]*?/?"""
                           + re.escape(stamm)
                           + r"""(?:\.js)?(?:\?[^'"]*)?['"]""")
        namen = set()
        for kurz, zeilen in self.quellen:
            if kurz == datei:
                namen = self._veroeffentlicht(zeilen)
                break
        per_import, per_sammelstelle = {datei}, set()
        for kurz, zeilen in self.quellen:
            if kurz == datei:
                continue
            if bezug.search("\n".join(zeilen[:Aufrufkette.KOPF])):
                per_import.add(kurz)
            elif namen:
                per_sammelstelle.add(kurz)
        return per_import, per_sammelstelle, namen

    @classmethod
    def _veroeffentlicht(cls, zeilen):
        """Namen, die diese Datei an eine Sammelstelle hängt."""
        aus = set()
        for zeile in zeilen:
            treffer = cls.SAMMELSTELLE.match(zeile)
            if treffer:
                aus.add(treffer.group(1))
        return aus
