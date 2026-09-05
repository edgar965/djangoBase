# -*- coding: utf-8 -*-
u"""TotesModul - Dateien, die niemand importiert und niemand erwaehnt.

DIE GEFAEHRLICHSTE PRUEFUNG IM KASTEN
=====================================
Ihre Befunde sind Loeschvorschlaege. Eine frueherer Fassung in shortlongx hat
damit dreimal danebengelegen, und jedes Mal waere lebender Code verschwunden:

* ``technik_archiv_verwaltung`` liefert drei URL-Ziele, ``menue_archiv`` das
  Archiv-Untermenue, ``storno_lage`` eine Klasse mit dreizehn Verwendungen -
  alle drei galten als tot, weil ihr Modulname bei ``from .x import *`` genau
  einmal vorkommt: in der Datei selbst.
* ``hilfe_netzsysteme_teil2..5`` galten als tot, obwohl Zeile 15-18 der
  Sammeldatei sie importiert. ``teil1`` entkam nur, weil der Docstring
  „teil1..5" schreibt.
* 122 lebende Namen auf einmal, weil „wird auswaerts benutzt?" jede Klasse traf,
  die nur ihr eigenes Modul benutzt. Kapselung ist kein toter Code.

Deshalb fragt diese Fassung in DREI Stufen und meldet nur, was alle drei
ueberlebt - und nimmt vorher aus, was per Konvention nirgends stehen DARF.

DIE RUECKKOPPLUNG (03.09.2026)
==============================
Die shortlongx-Fassung zaehlte auch ``*.md`` mit - einschliesslich des
Berichts, den sie selbst schrieb. Dort steht jeder gemeldete Name. Beim
naechsten Lauf galt das Modul als erwaehnt, die Pruefung schwieg; schwieg sie,
verschwand der Name aus dem Bericht, und beim uebernaechsten Lauf meldete sie
wieder. Vier Laeufe ergaben 62, 1, 60, 1 - jede Zahl sah nach einem Ergebnis
aus. Hier ist das Ergebnisverzeichnis deshalb ausdruecklich ausgenommen.

Reine stdlib.
"""
import ast
from pathlib import Path

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug
from .modulindex import ModulIndex


class TotesModul(BefundWerkzeug):

    slug = 'totes-modul'
    kriterium = 5
    titel = 'Module, die niemand erwähnt'
    zweck = ('Findet Python-Dateien, die nirgends importiert werden, deren Name '
             'nirgends vorkommt und von denen kein öffentlicher Name benutzt '
             'wird — in drei Stufen, damit kein lebendes Modul zum '
             'Löschvorschlag wird.')
    abhilfe = ('Nach einem Umbau, der Module zusammenlegt. Jeden Treffer '
               'EINZELN nachsehen: Die Prüfung kann dynamische Aufrufe nicht '
               'sehen, und ein falscher Löschvorschlag ist die teuerste Sorte '
               'Fehlalarm.')
    befund = ('In shortlongx meldete eine frühere Fassung 62 Module, davon 59 '
              'Testmodule und per Dekorator angemeldete Funktionen. Übrig '
              'blieben zwei echte — darunter eine tote Funktion ausgerechnet in '
              'dem Werkzeug, das tote Importe entfernt.')
    dauer = 'Sekunden'

    #: Dateinamen, die ein Framework selbst findet.
    RAHMEN = frozenset(("__init__", "settings", "urls", "wsgi", "asgi", "manage",
                        "apps", "admin", "models", "conftest", "middleware",
                        "signals", "forms", "serializers", "tasks"))
    #: Verzeichnisse, in denen Dateien per Konvention gefunden werden.
    GEFUNDEN_IN = ("/management/commands/", "/migrations/", "/templatetags/")
    #: Wo Namen ausserhalb des Python-Codes stehen koennen.
    TEXTMUSTER = ("*.html", "*.md", "*.js", "*.mjs", "*.txt", "*.json", "*.cfg")
    #: Der eigene Bericht zaehlt nicht mit - siehe Modulkopf.
    EIGENE_ABLAGE = ("/ergebnis/", "/.cache/", "/pruefwerk/")
    #: Einzeldateien darueber sind Daten, kein Code.
    MAX_BYTES = 2_000_000

    #: Eine KETTE, damit alle drei Stufen geprueft sind: Das Skript ruft den
    #: Nutzer, der Nutzer importiert die Bibliothek, und ``tot.py`` haengt an
    #: nichts. Danebengestellt die zwei Faelle, die per Konvention nirgends
    #: stehen duerfen - ``hoechstens=1`` faengt ab, wenn eine Ausnahme
    #: verlorengeht.
    anlassfall = Anlassfall(
        {"lebt.py": "WERT = 1\n",
         "nutzer.py": "from lebt import WERT\n\n\ndef zeigen():\n    return WERT\n",
         "start.py": 'from nutzer import zeigen\n\n'
                     'if __name__ == "__main__":\n    print(zeigen())\n',
         "tot.py": "def niemand_ruft_das():\n    return 2\n",
         "test_etwas.py": "def test_lauf():\n    assert True\n"},
        mindestens=1, hoechstens=1, erwartet_in="tot.py",
        warum="Ein Loeschvorschlag fuer lebenden Code ist die teuerste Sorte "
              "Fehlalarm - drei davon standen in einer frueheren Fassung")

    def pruefen(self, **_argumente):
        dateien = self.dateien(".py")
        index = ModulIndex(dateien)
        importiert = self._importierte_module(dateien, index)
        text = self._gesamttext(dateien)
        befunde, ausgenommen = [], 0
        for d in dateien:
            grund = self._ausgenommen(d)
            if grund:
                ausgenommen += 1
                continue
            if self._lebt(d, index, importiert, text):
                continue
            befunde.append(self._befund(d))
        kopf = ["%d Dateien" % len(dateien),
                "%d per Konvention gefunden (nicht gelistet)" % ausgenommen]
        return Befundsatz(self.titel, kopf, befunde)

    # ------------------------------------------------------------- Ausnahmen
    def _ausgenommen(self, datei):
        u"""Warum diese Datei nirgends stehen MUSS - oder ``''``."""
        name = Path(datei.name).name
        if Path(datei.name).stem in self.RAHMEN:
            return "Rahmenname"
        if any(m in "/" + datei.name for m in self.GEFUNDEN_IN):
            return "per Verzeichnis gefunden"
        if name.startswith("test_") or name.endswith("_test.py"):
            # Der Runner SUCHT nach diesem Muster - ein Testmodul darf nirgends
            # erwaehnt sein, das ist sein Normalfall.
            return "Testmodul"
        if self._ist_skript(datei):
            return "Skript"
        return ""

    #: Aufrufe, die auf Modulebene nur in einem Einstiegspunkt stehen.
    STARTRUF = frozenset(("print", "setup", "main", "haupt", "exit", "_exit",
                          "run", "flush", "basicConfig"))

    @classmethod
    def _ist_skript(cls, datei):
        u"""Wird die Datei ausgefuehrt statt importiert?

        Am Code erkannt, nicht am Ordner: Eine Ordnerliste raet, was der Autor
        gemeint hat, und liegt beim naechsten neuen Verzeichnis daneben.

        DREI MERKMALE (03.09.2026, aus shortlongx uebernommen und erweitert):

        * ``__main__`` steht im Text,
        * auf Modulebene wird ``print``/``setup``/``main``/``exit`` gerufen,
        * auf Modulebene laeuft eine Schleife.

        Die ersten beiden stammen aus der shortlongx-Fassung; ihr Anlass waren
        ``depot/stock3_vs_yf.py`` und ``depot/ohlcv_check.py`` - Diagnose-Skripte,
        die ``sys.path`` setzen, Django einrichten und eine Tabelle drucken. Als
        Loeschvorschlaege waeren sie richtig gezaehlt und trotzdem falsch.

        Das dritte kam dazu, weil ``depot/vol_futures_probe.py`` beides nicht
        hat: Es arbeitet in einer ``for``-Schleife auf Modulebene und endet mit
        ``sys.stdout.flush()``. Auch das ist kein Bibliotheksmodul.

        Die Abwaegung ist bewusst schief: Ein uebersehener Befund kostet nichts,
        ein falscher Loeschvorschlag kostet lebenden Code."""
        if datei.baum is None:
            return True                       # nicht lesbar: nichts behaupten
        if "__main__" in datei.text:
            return True
        for k in datei.baum.body:
            if isinstance(k, (ast.For, ast.While)):
                return True
            if not isinstance(k, ast.Expr) or not isinstance(k.value, ast.Call):
                continue
            f = k.value.func
            if (getattr(f, "id", None) or getattr(f, "attr", None) or "") \
                    in cls.STARTRUF:
                return True
        return False

    # ----------------------------------------------------------- drei Stufen
    def _lebt(self, datei, index, importiert, text):
        u"""Drei Fragen. EINE reicht, damit das Modul lebt."""
        punktnamen = {p for p, d in index.je_name.items() if d is datei}
        if punktnamen & importiert:
            return True                       # 1. jemand importiert es
        stamm = Path(datei.name).stem
        if text.count(stamm) > datei.text.count(stamm):
            return True                       # 2. der Name steht anderswo
        return self._name_benutzt(datei, text)  # 3. ein Inhalt wird benutzt

    @staticmethod
    def _importierte_module(dateien, index):
        u"""Alle Punktnamen, die irgendwo importiert werden - inklusive Paket.

        ``from a.b.c import x`` haelt auch ``a.b`` am Leben: Ein Paket, dessen
        Inhalt gebraucht wird, ist nicht tot."""
        aus = set()
        for d in dateien:
            if d.baum is None:
                continue
            for k in ast.walk(d.baum):
                if isinstance(k, ast.Import):
                    for a in k.names:
                        aus.add(a.name)
                elif isinstance(k, ast.ImportFrom):
                    ziel = index.ziel(d, k)
                    if not ziel:
                        continue
                    aus.add(ziel)
                    for a in k.names:
                        aus.add("%s.%s" % (ziel, a.name))
        # Jedes Elternpaket eines benutzten Moduls lebt mit.
        for name in list(aus):
            teile = name.split(".")
            for i in range(1, len(teile)):
                aus.add(".".join(teile[:i]))
        return aus

    def _name_benutzt(self, datei, text):
        u"""Wird ein oeffentlicher Name des Moduls anderswo benutzt?

        Die dritte Stufe, und die wichtigste: Bei ``from .x import *`` steht der
        MODULNAME nur in der Datei selbst - der Inhalt aber ueberall."""
        if datei.baum is None:
            return True                       # nicht lesbar: nichts behaupten
        namen = [k.name for k in datei.baum.body
                 if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef)) and not k.name.startswith("_")]
        namen += [z.id for k in datei.baum.body if isinstance(k, ast.Assign)
                  for z in k.targets
                  if isinstance(z, ast.Name) and not z.id.startswith("_")]
        for name in namen:
            if len(name) > 2 and text.count(name) > datei.text.count(name):
                return True
        # Ein Modul, das NUR Konstanten fuehrt, hat keine oeffentlichen Namen im
        # Sinne von Funktionen und Klassen - und waere ohne diese Zeile tot.
        return not namen and not datei.text.strip()

    # --------------------------------------------------------------- Textbasis
    def _gesamttext(self, dateien):
        u"""Aller Projekttext in EINER Zeichenkette - Python plus Vorlagen.

        Das eigene Ergebnisverzeichnis bleibt draussen: Ein Bericht, der jeden
        gemeldeten Namen nennt, macht beim naechsten Lauf jedes Modul lebendig
        (siehe Modulkopf)."""
        teile = [d.text for d in dateien
                 if not self._ist_eigene_ablage(d.name)]
        for muster in self.TEXTMUSTER:
            for p in self.pfade(muster):
                if self._ist_eigene_ablage(Path(p).as_posix()):
                    continue
                try:
                    if p.stat().st_size > self.MAX_BYTES:
                        continue
                    teile.append(p.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError):
                    pass
        return "\n".join(teile)

    def _ist_eigene_ablage(self, pfad):
        return any(t in "/" + pfad.replace("\\", "/") for t in self.EIGENE_ABLAGE)

    def _befund(self, datei):
        return Befund(
            datei.name,
            "wird nirgends importiert und nirgends erwähnt",
            "Weder der Modulname noch einer seiner öffentlichen Namen kommt "
            "außerhalb dieser Datei vor. EINZELN nachsehen: ein dynamischer "
            "Aufruf ist von außen nicht zu sehen.",
            Befund.WARNUNG)
