# -*- coding: utf-8 -*-
u"""Proben - die Gegenproben eines Projekts, an EINER Stelle sichtbar.

WOZU (28.08.2026)
=================
    „kannst du diese Tools gleich speichern auf der Code Review seite für die
     sabotageaktionen, seitenproben usw?"

Waehrend eines Umbaus entstehen Proben: ein Skript, das jede Seite aufruft und
auf Konsolenfehler achtet; eins, das eine geaenderte Datei anfordert und
nachsieht, ob sie wirklich beim Browser ankommt; eins, das die gespeicherten
Szenenwerte im Browser Feld fuer Feld nachrechnet. Sie kosten Stunden im Bau
und beweisen Dinge, die kein Unittest beweisen kann - und dann liegen sie in
einem Ordner und niemand weiss mehr, dass es sie gibt.

Dieses Werkzeug findet sie und stellt sie auf die Werkzeugseite: Name, Art,
Zweck, Aufrufbefehl. Wer sie sucht, findet sie hier - nicht im Verlauf einer
Sitzung von vor drei Wochen.

DIE PRUEFUNG, DIE ES MITBRINGT
==============================
Eine Probe, die NIE rot werden kann, ist schlimmer als keine: Sie laeuft
durch, meldet „alles wie erwartet" und deckt genau dadurch zu. Deshalb liest
dieses Werkzeug jede Probe daraufhin, ob sie ueberhaupt einen Fehlschlag
ausdruecken KANN - ein Rueckgabewert ungleich null, ein ``assert``, ein
``throw``. Fehlt beides, steht das in der Spalte „kann rot werden".

Der Anlass ist belegt: Der erste Anlauf von
``Docu/umbau/szeneneinstellungen_probe.mjs`` (3DTools) meldete fuenfzehn
Abweichungen, die keine waren - die Regler rasten auf ihre Schrittweite. Wer
so eine Probe „beruhigt", indem er den Vergleich weglaesst, hat danach ein
Skript, das immer gruen ist. Die Gegenrichtung ist genauso wichtig und steht
in der Spalte: nach dem Bau EINMAL sabotieren und nachsehen, ob sie rot wird.

WELCHE DATEIEN
==============
Dateien, deren Name auf ``probe`` endet (``seitenprobe.mjs``,
``cache_gegenprobe.py``, ``szeneneinstellungen_probe.mjs``) - Endung ``.py``,
``.js`` oder ``.mjs``. Auf das ENDE zu achten ist nicht Pedanterie: Mit
``*probe*`` fing die Suche in 3DTools ``static/viewer/theatre_studio/
probeszene.js`` mit ein, eine Beispielszene fuer die Buehne, und uebersah dabei
jede echte Probe.

Namen mit fuehrendem Unterstrich gelten als Wegwerfstueck und bleiben draussen.

WO GESUCHT WIRD: im Projekt selbst - und in Verzeichnissen, die das Projekt
nennt:

    DJANGOBASE["proben_ordner"] = ["../Docu/umbau"]   # relativ zur Wurzel
    DJANGOBASE["proben_ausser"] = ["fremd/"]

Der zweite Schluessel ist noetig, wo die Proben NEBEN dem Django-Teil liegen -
in 3DTools etwa unter ``A:/3DTools/Docu/umbau``, eine Ebene ueber dem Repo
``HumanBodyWeb``, weil vier Repos sich diesen Arbeitsplatz teilen.
"""
import re
from pathlib import Path

from django.conf import settings

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["Proben"]


class Proben(Werkzeug):
    slug = "proben"
    titel = "Proben und Gegenproben"
    zweck = (u"Sammelt die Prüfskripte des Projekts (Seitenproben, "
             u"Gegenproben, Sabotagelaeufe) und zeigt Zweck und Aufruf. "
             u"Meldet, welche davon gar nicht rot werden kann.")
    befund = (u"3DTools: Sechs Proben lagen in `Docu/umbau/` — Seitenaufrufe, "
              u"Cache-Header, LOGGING-Gleichheit, Szenenwerte im Browser. Auf "
              u"keiner Seite stand, dass es sie gibt; gefunden wurden sie nur, "
              u"weil dieselbe Sitzung sie geschrieben hatte.")
    abhilfe = (u"Probe mit einem sprechenden Namen (`*_probe.py`, "
               u"`*_gegenprobe.py`, `*_probe.mjs`) ablegen, im Kopf EINE Zeile "
               u"„Start: …\" schreiben und dafür sorgen, dass sie mit einem "
               u"Rückgabewert ungleich null endet, wenn etwas nicht stimmt.")
    dauer = "unter 1 s (liest nur, führt nichts aus)"
    kriterium = 19

    SPALTEN = ["probe", "art", "kann rot werden", "zweck", "aufruf"]

    #: Endungen, unter denen gesucht wird.
    ENDUNGEN = (".py", ".js", ".mjs")
    #: Worauf der Dateiname (ohne Endung) enden muss.
    ENDET_AUF = ("probe", "proben")

    #: Woran man erkennt, dass eine Probe fehlschlagen KANN.
    #:
    #: ``process.exit(0)`` allein zaehlt NICHT - deshalb steht im Muster ein
    #: Ausdruck statt einer festen Null. Ein ``assert`` oder ``throw`` genuegt
    #: ebenfalls: Beides beendet den Lauf mit einem Fehler.
    ROT = (re.compile(r"process\.exit\(\s*(?!0\s*\))"),
           re.compile(r"sys\.exit\(\s*(?!0\s*\))"),
           re.compile(r"^\s*assert\s", re.M),
           re.compile(r"\bthrow\s+new\s"),
           re.compile(r"^\s*raise\s", re.M))

    #: Aus dem Kopf gelesen: „Start: <befehl>" bzw. „Aufruf: <befehl>".
    AUFRUF = re.compile(r"^\s*(?:\*\s*)?(?:Start|Aufruf|Lauf)\s*:\s*(.+)$",
                        re.M | re.I)

    anlassfall = Anlassfall(
        dateien={
            "gute_probe.py": (
                '"""Probe, die rot werden kann.\n\n'
                'Start: python gute_probe.py\n"""\n'
                'import sys\n'
                'sys.exit(1 if kaputt() else 0)\n'),
            "stille_probe.mjs": (
                "// Probe, die IMMER gruen meldet - genau der Fall.\n"
                "console.log(schlecht ? 'FEHL' : 'ok');\n"
                "process.exit(0);\n"),
        },
        mindestens=2, hoechstens=2,
        erwartet_in=u"nein",
        warum=(u"Beide Dateien müssen in der Liste stehen, und die stille muss "
               u"in der Spalte „kann rot werden\" ein Nein bekommen. Faellt die "
               u"Spalte weg, sieht die Liste vollstaendig aus und sagt nichts "
               u"mehr."))

    def _einstellung(self, name):
        return list((getattr(settings, "DJANGOBASE", {}) or {}).get(name) or [])

    #: Ein Kopf, der mit einem dieser Woerter beginnt, macht die Datei zur
    #: Probe - aber NUR in den vom Projekt genannten Ordnern (siehe
    #: ``_zusatzordner``). Im ganzen Projekt danach zu suchen hiesse, jede
    #: Datei zu oeffnen; in einem benannten Ordner sind es ein paar Dutzend.
    KOPFWOERTER = ("gegenprobe", "probe:", "probe ", "sichtprobe")

    def _ist_probe(self, pfad, mit_kopf=False):
        if pfad.suffix not in Proben.ENDUNGEN or pfad.name.startswith("_"):
            return False
        if pfad.stem.lower().endswith(Proben.ENDET_AUF):
            return True
        if not mit_kopf:
            return False
        # Zwei echte Gegenproben in 3DTools heissen `logs_namen_pruefen.py` und
        # `anlass_protokoll.py` - am Namen nicht zu erkennen, am ersten Satz
        # ihres Kopfes sehr wohl.
        try:
            kopf = Proben._kopf(pfad.read_text(encoding="utf-8",
                                               errors="replace"))
        except OSError:
            return False
        return kopf.lower().startswith(Proben.KOPFWOERTER)

    def _zusatzordner(self):
        u"""Die vom Projekt genannten Ordner - auch neben dem Repo.

        Sie gehen NICHT durch ``pfade()``: Der ``.gitignore``-Filter dort haengt
        an der Projektwurzel und kann ueber einen Pfad ausserhalb nichts
        Sinnvolles sagen. Die feste Ausschlussliste gilt trotzdem.
        """
        wurzel = self.wurzel()
        raus = self.ausgeschlossen()
        for eintrag in self._einstellung("proben_ordner"):
            ordner = Path(eintrag)
            if not ordner.is_absolute():
                ordner = (wurzel / ordner).resolve()
            # NEBEN DEM PROJEKT, NICHT IRGENDWO (28.08.2026): Zwei Pruefungen
            # lassen jedes Werkzeug auf einem WEGWERF-Verzeichnis laufen und
            # verlangen, dass es dort nichts findet - der Anlassfall-Check und
            # `test_alle_laufen_auf_leerem_projekt`. Der Eintrag steht aber als
            # absoluter Pfad in den Einstellungen und zeigt weiter auf das echte
            # Projekt; ohne diese Bedingung meldete das Werkzeug dort acht
            # Proben und galt zu Recht als blind.
            #
            # Die Bedingung ist keine Notbremse, sondern die Regel selbst: Ein
            # Probenordner gehoert zum Projekt - er liegt darin oder daneben
            # (vier Repos, ein Arbeitsplatz). Alles andere ist ein fremder
            # Ordner, und den soll dieses Werkzeug nicht auflisten.
            if not self._gehoert_dazu(ordner, wurzel):
                continue
            if not ordner.is_dir():
                continue
            for pfad in sorted(ordner.rglob("*")):
                if pfad.is_file() and not any(t in raus for t in pfad.parts):
                    yield pfad, True

    @staticmethod
    def _gehoert_dazu(ordner, wurzel):
        """Liegt der Ordner im Projekt oder unmittelbar daneben?"""
        return (ordner == wurzel or wurzel in ordner.parents
                or wurzel.parent in ordner.parents)

    def dateien_finden(self):
        u"""Alle Probendateien, ohne Wegwerfstücke und Ausnahmen."""
        raus = tuple(self._einstellung("proben_ausser"))
        wurzel = self.wurzel()
        gefunden = {}
        eigene = [(p, False) for p in self.pfade("*")]
        for pfad, mit_kopf in eigene + list(self._zusatzordner()):
            if not self._ist_probe(pfad, mit_kopf):
                continue
            try:
                rel = pfad.relative_to(wurzel).as_posix()
            except ValueError:
                # Liegt neben der Wurzel (vier Repos, ein Arbeitsplatz).
                rel = pfad.as_posix().replace(
                    wurzel.parent.as_posix() + "/", "../")
            if any(a in rel for a in raus):
                continue
            gefunden[rel] = pfad
        return sorted(gefunden.items())

    @staticmethod
    def _kopf(text):
        u"""Die erste erklärende Zeile — Docstring oder Blockkommentar."""
        for zeile in text.splitlines()[:40]:
            nackt = zeile.strip().lstrip("#/*\" '").strip()
            if len(nackt) > 25 and not nackt.startswith(("import", "from",
                                                         "const", "let")):
                return nackt[:150]
        return ""

    def laufen(self):
        zeilen = []
        stumm = 0
        for rel, pfad in self.dateien_finden():
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError as fehler:
                zeilen.append({"probe": rel, "art": "?",
                               "kann rot werden": "?",
                               "zweck": "nicht lesbar: %s" % fehler,
                               "aufruf": ""})
                continue
            rot = any(m.search(text) for m in Proben.ROT)
            if not rot:
                stumm += 1
            treffer = Proben.AUFRUF.search(text)
            art = "Browser" if pfad.suffix in (".js", ".mjs") else "Server"
            zeilen.append({
                "probe": rel,
                "art": art,
                "kann rot werden": "ja" if rot else "nein",
                "zweck": Proben._kopf(text),
                "aufruf": (treffer.group(1).strip() if treffer
                           else ("node %s" % rel if art == "Browser"
                                 else "python %s" % rel)),
            })
        satz = u"%d Probe(n) gefunden" % len(zeilen)
        if stumm:
            satz += u" — %d davon kann nicht rot werden" % stumm
        return Ergebnis(list(Proben.SPALTEN), zeilen, satz,
                        u"Nach dem Bau einer Probe EINMAL sabotieren und "
                        u"nachsehen, ob sie rot wird — eine Probe, die immer "
                        u"grün meldet, deckt zu statt zu prüfen.")
