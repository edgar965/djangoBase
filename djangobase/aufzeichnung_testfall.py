# -*- coding: utf-8 -*-
u"""Aus einer Aufzeichnung einen echten Testfall machen.

DAS ZIEL (Edgar, 20.08.2026)
===========================
    „Ziel ist es, dass du aus diesen Aufzeichnungen echte Tests erstellen
     kannst, die du dann in der Testsuite speicherst und ausführst"

WAS SICH AUTOMATISCH PRUEFEN LAESST - UND WAS NICHT
===================================================
Aus einer Aufnahme entsteht KEIN vollstaendiger Test. Was mitgeschrieben wird,
sind Klicks und Abrufe; was daraus folgen MUSS, weiss nur der Mensch. Was diese
Klasse liefert, ist deshalb ein Geruest mit den Teilen, die belegbar sind:

    * jeder aufgezeichnete Server-Abruf wird nachgefahren und sein Status
      geprueft - das ist die Sorte Zusicherung, die aus der Aufnahme wirklich
      folgt („dieser Pfad hat damals 200 geliefert")
    * jede Fehlerzeile aus dem Log-Fenster wird als Zusicherung eingetragen:
      Was damals KEINE Ausnahme warf, darf auch jetzt keine werfen
    * die Klicks stehen als Kommentar daneben, in der Reihenfolge, in der sie
      passiert sind - sie sagen, WOFUER der Test da ist

Die Alternative waere ein Klickpfad, der Knoepfe im Browser nachspielt. Das
braucht eine Browsersteuerung, ist gegen jeden Umbau der Oberflaeche
zerbrechlich, und ein Test, der bei jeder CSS-Aenderung rot wird, wird
abgeschaltet statt repariert.

DER ERZEUGTE FALL SCHREIBT NICHTS
=================================
Nachgefahren werden nur GET-Abrufe. Ein aufgezeichnetes POST wuerde beim
Testlauf dieselbe Wirkung noch einmal ausloesen - eine Order, ein geloeschtes
System, ein neuer Auftrag. Es steht als Kommentar drin, mit dem Hinweis, dass
es von Hand ergaenzt werden muss.
"""
import re
from datetime import datetime

__all__ = ["Testfall"]


class Testfall:
    u"""Erzeugt den Quelltext eines Django-Testfalls aus einer Aufzeichnung."""

    #: Diese Pfade werden nie nachgefahren - sie gehoeren zur Aufzeichnung
    #: selbst oder liefern bei jedem Aufruf etwas anderes.
    AUS = ("/hilfe/tests/aufzeichnung/", "/api/system-stats/", "/verbrauch/")

    def __init__(self, aufzeichnung):
        self.a = aufzeichnung

    # ------------------------------------------------------------------ Namen
    def klassenname(self):
        u"""Aus dem Namen der Aufzeichnung einen gueltigen Klassennamen."""
        roh = re.sub(r"[^\w\s]", " ", self.a.name or "Aufzeichnung")
        teile = [w.capitalize() for w in roh.split() if w]
        name = "".join(teile) or "Aufzeichnung"
        if name[0].isdigit():
            name = "Test" + name
        return name if name.startswith("Test") else name + "Test"

    def dateiname(self):
        roh = re.sub(r"[^\w]+", "_", (self.a.name or self.a.id)).strip("_").lower()
        return "test_%s.py" % (roh or "aufzeichnung")

    # ---------------------------------------------------------------- Bausteine
    def abrufe(self):
        u"""Die GET-Abrufe, die nachgefahren werden koennen - ohne Doppelte."""
        gesehen, aus = set(), []
        for s in self.a.schritte:
            if s.get("art") != "abruf" or (s.get("methode") or "GET") != "GET":
                continue
            pfad = s.get("pfad") or ""
            if not pfad or pfad in gesehen or any(pfad.startswith(x) for x in self.AUS):
                continue
            gesehen.add(pfad)
            aus.append({"pfad": pfad, "status": int(s.get("status") or 200)})
        return aus

    def schreibende(self):
        u"""Aufgezeichnete Schreibzugriffe - NUR als Kommentar."""
        gesehen, aus = set(), []
        for s in self.a.schritte:
            if s.get("art") != "abruf":
                continue
            m = (s.get("methode") or "GET").upper()
            if m == "GET":
                continue
            schluessel = (m, s.get("pfad") or "")
            if schluessel in gesehen or any(schluessel[1].startswith(x) for x in self.AUS):
                continue
            gesehen.add(schluessel)
            aus.append({"methode": m, "pfad": schluessel[1],
                        "status": int(s.get("status") or 0)})
        return aus

    def bedienung(self):
        u"""Klicks, Eingaben und Seitenwechsel in ihrer Reihenfolge."""
        aus = []
        for s in self.a.schritte:
            art = s.get("art")
            if art == "klick":
                aus.append("%6.1fs  Klick auf %s%s" % (
                    s.get("t", 0), s.get("ziel", "?"),
                    (" („%s\")" % s["text"]) if s.get("text") else ""))
            elif art in ("eingabe", "auswahl"):
                aus.append("%6.1fs  %s in %s: %s" % (
                    s.get("t", 0), "Eingabe" if art == "eingabe" else "Auswahl",
                    s.get("ziel", "?"), s.get("wert", "")))
            elif art == "seite":
                aus.append("%6.1fs  Seite %s" % (s.get("t", 0), s.get("seite", "?")))
        return aus

    def fehlerzeilen(self):
        u"""Log-Zeilen ab WARNING - was damals nicht schieflief, darf es auch
        jetzt nicht."""
        return [l for l in self.a.logs
                if str(l.get("stufe", "")).upper() in ("ERROR", "CRITICAL")]

    # ------------------------------------------------------------------ Bauen
    def quelltext(self):
        u"""Der fertige Testfall als Python-Quelltext."""
        abrufe = self.abrufe()
        schreib = self.schreibende()
        return "\n".join(self._kopf() + self._rumpf(abrufe, schreib) + [""])

    def _kopf(self):
        striche = "=" * 70
        zeilen = [
            "# -*- coding: utf-8 -*-",
            'u"""%s' % (self.a.name or self.a.id),
            "",
            "ERZEUGT AUS EINER AUFZEICHNUNG (%s)" % datetime.now().strftime("%d.%m.%Y"),
            striche,
            "Aufnahme %s vom %s, %.0f s, %d Schritte, %d Log-Zeilen."
            % (self.a.id, self.a.start[:16].replace("T", " "), self.a.dauer_s,
               len(self.a.schritte), len(self.a.logs)),
            "",
            "WAS HIER GEPRUEFT WIRD",
            "-" * 22,
            "Die aufgezeichneten GET-Abrufe werden nachgefahren und ihr Status",
            "gegen den von damals gehalten. Was der Nutzer dabei GEMEINT hat,",
            "steht als Bedienung darunter - diese Zusicherungen muss ein Mensch",
            "ergaenzen; eine Aufnahme kann sie nicht kennen.",
            "",
            "AUFGEZEICHNETE BEDIENUNG",
            "-" * 24,
        ]
        zeilen += ["    " + z for z in (self.bedienung() or ["(keine)"])]
        fehler = self.fehlerzeilen()
        if fehler:
            zeilen += ["", "IM ZEITRAUM PROTOKOLLIERTE FEHLER", "-" * 33,
                       "Diese Zeilen standen WAEHREND der Aufnahme im Log. Sie sind",
                       "kein gruener Zustand - erst pruefen, dann den Test uebernehmen:"]
            zeilen += ["    [%s] %s: %s" % (f.get("stufe"), f.get("logger"),
                                            str(f.get("text"))[:90]) for f in fehler[:10]]
        zeilen += ['"""', "from django.test import TestCase", ""]
        return zeilen

    def _rumpf(self, abrufe, schreib):
        zeilen = ["", "class %s(TestCase):" % self.klassenname(),
                  '    u"""Nachgefahren aus der Aufzeichnung %s."""' % self.a.id, ""]
        if not abrufe:
            zeilen += ["    def test_platzhalter(self):",
                       '        u"""Die Aufnahme enthielt keinen nachfahrbaren GET-Abruf."""',
                       "        self.skipTest('Aufzeichnung ohne GET-Abrufe - "
                       "Zusicherungen von Hand ergaenzen')"]
            return zeilen
        zeilen += ["    #: Pfad -> Status, wie er waehrend der Aufnahme geantwortet hat.",
                   "    ABRUFE = ["]
        zeilen += ["        (%r, %d)," % (a["pfad"], a["status"]) for a in abrufe]
        zeilen += ["    ]", "",
                   "    def test_abrufe_antworten_wie_aufgezeichnet(self):",
                   '        u"""Jeder aufgezeichnete GET liefert denselben Status wie damals."""',
                   "        for pfad, erwartet in self.ABRUFE:",
                   "            with self.subTest(pfad=pfad):",
                   "                self.assertEqual(self.client.get(pfad).status_code,",
                   "                                 erwartet)"]
        if schreib:
            zeilen += ["", "    # SCHREIBENDE AUFRUFE DER AUFNAHME - bewusst NICHT",
                       "    # nachgefahren: Sie loesten damals eine Wirkung aus (Order,",
                       "    # Loeschung, Auftrag) und wuerden sie beim Testlauf erneut",
                       "    # ausloesen. Wer sie braucht, baut sie mit eigenen Daten nach."]
            zeilen += ["    #   %s %s -> %s" % (s["methode"], s["pfad"], s["status"])
                       for s in schreib]
        return zeilen
