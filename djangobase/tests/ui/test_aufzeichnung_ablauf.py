# -*- coding: utf-8 -*-
u"""Der komplette Aufzeichnungs-Weg: starten, Seite wechseln, beenden.

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „teste in chrome, ob eine aufzeichnung funktioniert. Mach dir auch dafür
     einen Testcase bei „UI Tests" in djangoBase"

Der Ablauf wurde in Chrome durchgespielt — und hat dabei **drei** Fehler
offengelegt, die alle erst über einen Seitenwechsel sichtbar werden. Genau
gegen diese drei prüft diese Datei; sie sind der Grund, warum es sie gibt.

1. EIN MODUL, ZWEI URLs
   ``_shell.html`` lädt ``aufzeichner.js?v=1787…``, während
   ``aufzeichner_leiste.js`` dieselbe Datei ohne Query importierte. Für den
   Browser sind das zwei Module: ``aufzeichnerStarten()`` lief zweimal, es gab
   ZWEI Aufzeichner mit eigenen Puffern, und jeder Klick stand doppelt in der
   Aufnahme — neun Schritte mit identischen Zeitstempeln. Im erzeugten Testfall
   wäre jede Aktion zweimal nachgefahren worden.

2. sendBeacon KANN KEINEN CSRF-HEADER
   Der Puffer ging beim Verlassen der Seite per ``navigator.sendBeacon`` raus.
   Der Endpunkt ist bewusst nicht ``csrf_exempt`` (er schreibt eine Datei ins
   Projekt) und hat jeden Beacon mit **403** abgewiesen. Folge: Bei jedem
   Seitenwechsel gingen bis zu drei Sekunden verloren — genau die um den Klick
   herum, der die Navigation ausgelöst hat. In der Gegenprobe fehlte die
   Startseite komplett. Jetzt: ``fetch(..., {keepalive: true})``.

3. DER PUFFER WURDE NICHT GELEERT
   Der Beacon schickte ``this.puffer``, ohne ihn zu entnehmen. Kam danach noch
   ein Timer-Tick, ging derselbe Inhalt ein zweites Mal raus.

WAS HIER GEPRÜFT WIRD - UND WAS NICHT
=====================================
Kein echter Browser: Es gibt in djangoBase keine Selenium-Schicht, und eine
dafür einzuführen wäre mehr Wartung als Nutzen. Nachgestellt wird stattdessen
**genau das, was der Browser tut** — dieselben Ereignisfolgen über denselben
Endpunkt, inklusive Seitenwechsel. Dazu kommen drei Quelltext-Prüfungen für die
Fallen oben: Sie sind statisch erkennbar, und sie kommen sonst beim nächsten
Umbau still zurück.
"""
import ast
import re
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.aufzeichnung import Aufzeichnungen
from djangobase.aufzeichnung_steuerung import Steuerung
from djangobase.aufzeichnung_testfall import Testfall

#: Wurzel des djangoBase-Pakets (…/djangobase/), von tests/ui/ aus zwei hoch.
PAKET = Path(__file__).resolve().parents[2]
JS = PAKET / "static" / "djangobase" / "js"
SHELL = PAKET / "templates" / "djangobase" / "_shell.html"


class AufzeichnungsWegTest(SimpleTestCase):
    u"""Der Weg über zwei Seiten - so, wie der Browser ihn schickt."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bestand = Aufzeichnungen(Path(self._tmp.name) / "auf.json")
        self.s = Steuerung(self.bestand)

    def tearDown(self):
        self._tmp.cleanup()

    def _puffer_seite_eins(self):
        u"""Was der Browser auf der ersten Seite sammelt."""
        return [
            {"art": "seite", "seite": "/dax-handel/", "t": 0.7},
            {"art": "abruf", "methode": "GET", "pfad": "/hilfe/api/system-stats/",
             "status": 200, "t": 1.6},
            {"art": "klick", "ziel": "button.dax-tab", "text": "Alle Signale", "t": 3.1},
            {"art": "abruf", "methode": "GET", "pfad": "/hilfe/api/system-stats/",
             "status": 200, "t": 3.4},
        ]

    def _puffer_seite_zwei(self):
        u"""Was nach dem Wechsel auf der zweiten Seite dazukommt."""
        return [
            {"art": "seite", "seite": "/depot/ib-paper/", "t": 4.7},
            {"art": "abruf", "methode": "GET", "pfad": "/api/ib/auto/",
             "status": 200, "t": 5.2},
            {"art": "abruf", "methode": "GET", "pfad": "/api/ib/auto/",
             "status": 200, "t": 6.2},
            {"art": "klick", "ziel": "#itc-zurueck", "text": "Vortag", "t": 17.6},
            {"art": "abruf", "methode": "GET", "pfad": "/api/ib/auto/",
             "status": 200, "t": 17.9},
        ]

    def test_weg_ueber_zwei_seiten(self):
        u"""Start, Seitenwechsel, Ende - beide Seiten und beide Klicks stehen drin."""
        a, _ = self.s.starten(seite="/dax-handel/")
        self.s.anhaengen(a.id, self._puffer_seite_eins())
        self.s.anhaengen(a.id, self._puffer_seite_zwei())
        fertig = self.s.beenden(a.id, ["irgendeine Logzeile"])

        self.assertIsNotNone(fertig)
        self.assertFalse(fertig.laeuft)
        seiten = [s["seite"] for s in fertig.schritte if s["art"] == "seite"]
        self.assertEqual(seiten, ["/dax-handel/", "/depot/ib-paper/"],
                         u"Die Aufnahme muss über den Seitenwechsel hinweg laufen")
        klicks = [s["ziel"] for s in fertig.schritte if s["art"] == "klick"]
        self.assertEqual(klicks, ["button.dax-tab", "#itc-zurueck"])

    def test_keine_doppelten_schritte(self):
        u"""Derselbe Puffer zweimal (Timer UND Seitenwechsel) darf nichts verdoppeln.

        Genau das ist passiert: In einer Aufnahme über zwei Seiten standen neun
        Schritte doppelt, mit identischen Zeitstempeln."""
        a, _ = self.s.starten(seite="/dax-handel/")
        puffer = self._puffer_seite_zwei()
        self.s.anhaengen(a.id, puffer)
        self.s.anhaengen(a.id, [dict(s) for s in puffer])       # der Doppelversand
        fertig = self.s.beenden(a.id)

        # Klicks und Seitenwechsel sind Marken - sie dürfen NIE verschmelzen,
        # und deshalb sind sie der ehrliche Nachweis für einen Doppelversand.
        marken = [(s["art"], s.get("ziel") or s.get("seite"), s["t"])
                  for s in fertig.schritte if s["art"] in ("klick", "seite")]
        self.assertEqual(len(marken), len(set(marken)),
                         u"Ein doppelt gesendeter Puffer darf keine doppelten "
                         u"Marken erzeugen: %r" % (marken,))

    def test_erzeugter_testfall_ist_gueltiges_python(self):
        a, _ = self.s.starten(seite="/dax-handel/")
        self.s.anhaengen(a.id, self._puffer_seite_eins())
        self.s.anhaengen(a.id, self._puffer_seite_zwei())
        fertig = self.s.beenden(a.id)
        ast.parse(Testfall(fertig).quelltext())


class QuelltextFallenTest(SimpleTestCase):
    u"""Die drei Fallen, die den Chrome-Durchlauf gekostet haben - statisch.

    Sie sind alle am Quelltext erkennbar und kommen sonst beim nächsten Umbau
    lautlos zurück."""

    def test_aufzeichner_wird_nur_unter_einer_url_geladen(self):
        u"""Falle 1: zwei URLs für dasselbe Modul = zwei Aufzeichner.

        ``_shell.html`` lädt ``aufzeichner.js`` mit ``?v=``. Wer dieselbe Datei
        daneben OHNE Query importiert, bekommt eine zweite Modulinstanz - und
        jedes Ereignis steht doppelt in der Aufnahme."""
        leiste = (JS / "aufzeichner_leiste.js").read_text(encoding="utf-8")
        # Beide Formen: statischer Import und dynamisches import(...).
        blank = re.findall(
            r"""import\s*\{[^}]*\}\s*from\s*['"]([^'"]*aufzeichner\.js)['"]"""
            r"""|import\s*\(\s*['"]([^'"]*aufzeichner\.js)['"]\s*\)""",
            leiste)
        blank = [t for paar in blank for t in paar if t]
        self.assertEqual(blank, [],
                         u"aufzeichner.js darf nicht ohne ?v= importiert werden "
                         u"(gefunden: %r) - das Script-Tag der Shell lädt es MIT "
                         u"Query, und zwei URLs sind zwei Module" % (blank,))
        self.assertIn("import.meta.url", leiste,
                      u"Der Import muss die Query dieses Moduls übernehmen "
                      u"(new URL(import.meta.url).search)")

    def test_kein_sendbeacon(self):
        u"""Falle 2: sendBeacon kann keinen CSRF-Header setzen -> 403.

        Der Endpunkt ist bewusst nicht csrf_exempt. Jeder Beacon wurde
        abgewiesen, und mit ihm die letzten Sekunden vor dem Seitenwechsel."""
        quelle = (JS / "aufzeichner.js").read_text(encoding="utf-8")
        code = "\n".join(z for z in quelle.splitlines()
                         if not z.strip().startswith("//"))
        self.assertNotIn("sendBeacon", code,
                         u"sendBeacon trägt keinen CSRF-Header - der Endpunkt "
                         u"antwortet mit 403. Stattdessen fetch(..., keepalive)")
        self.assertIn("keepalive", code)

    def test_puffer_wird_beim_verlassen_entnommen(self):
        u"""Falle 3: gesendet, aber nicht geleert -> der nächste Tick schickt nochmal."""
        quelle = (JS / "aufzeichner.js").read_text(encoding="utf-8")
        pagehide = quelle.split("pagehide", 1)[1]
        self.assertIn("splice", pagehide.split("});", 1)[0],
                      u"Der pagehide-Handler muss den Puffer ENTNEHMEN, nicht nur "
                      u"lesen - sonst geht derselbe Inhalt zweimal raus")

    def test_bedienung_liegt_auf_jeder_seite(self):
        u"""Der Bereich steht in der Sidebar, das Modul in der Shell.

        Aufgezeichnet werden Wege, und ein Weg führt über Seiten. Läge die
        Bedienung nur im Reiter unter Hilfe → Tests, wäre die Aufnahme beim
        ersten Menüklick vorbei - also genau dann, wenn es interessant wird."""
        shell = SHELL.read_text(encoding="utf-8")
        self.assertIn("aufzeichner_leiste.js", shell)
        self.assertIn("css/aufzeichner.css", shell)
        sidebar = (PAKET / "templates" / "djangobase" / "_sidebar.html")             .read_text(encoding="utf-8")
        for stueck in ('id="djb-aufz"', "djb-aufz-knopf", "djb-aufz-zuknopf",
                       "djb-aufz-zaehler"):
            self.assertIn(stueck, sidebar,
                          u"Dem Sidebar-Bereich fehlt %r - Knopf, X und "
                          u"Sekundenanzeige gehören dorthin" % stueck)

    def test_x_ist_waehrend_der_aufnahme_gesperrt(self):
        u"""„X nur aktivierbar wenn die Aufzeichnung beendet ist" (Ansage).

        Geprüft an beiden Stellen: Der Knopf wird gesperrt UND der Handler
        steigt aus. Nur das Attribut zu setzen genügt nicht - ein Klick per
        Tastatur oder Skript käme durch und machte eine laufende Aufnahme
        unsichtbar."""
        leiste = (JS / "aufzeichner_leiste.js").read_text(encoding="utf-8")
        self.assertIn("this.zuknopf.disabled = !!this.laeuft", leiste)
        # Die METHODE, nicht ihr Aufruf im Konstruktor - deshalb mit Klammer
        # und Rumpfbeginn geschnitten.
        ausblenden = leiste.split("ausblenden() {", 1)[1].split(chr(10) + "  }", 1)[0]
        self.assertIn("if (this.laeuft) return", ausblenden,
                      u"Der Handler muss bei laufender Aufnahme aussteigen")

    def test_reiterknopf_startet_keine_aufnahme(self):
        u"""„der Button ‚Aufzeichnen' im Tab soll nur den Bereich im Menü oben
        links einblenden, die Aufnahme aber NICHT starten" (Ansage 21.08.2026).

        Vorher gab es zwei Schalter für dieselbe Sache. Wer im Reiter startete,
        sah die Aufnahme danach nur dort mitlaufen."""
        reiter = (JS / "aufzeichnung.js").read_text(encoding="utf-8")
        klick = reiter.split("schalter.addEventListener('click'", 1)[1]
        klick = klick.split("});", 1)[0]
        for verboten in ("aktion: 'start'", "aktion: 'ende'"):
            self.assertNotIn(verboten, klick,
                             u"Der Reiter-Knopf darf die Aufnahme weder starten "
                             u"noch beenden (%r gefunden)" % verboten)
        self.assertIn("djb-aufz-weg", klick,
                      u"Er soll den Bereich einblenden")

    def test_ausgeblendet_bleibt_nicht_bei_laufender_aufnahme(self):
        u"""Eine Aufnahme, die niemand sieht, schreibt sonst stundenlang mit."""
        leiste = (JS / "aufzeichner_leiste.js").read_text(encoding="utf-8")
        self.assertIn("weg === '1' && !this.laeuft", leiste)

    def test_liste_wird_nur_einmal_gebaut(self):
        u"""Popup und Reiter benutzen DIESELBE Listen-Klasse.

        Vorher baute jeder sein eigenes Tabellen-Markup. Zwei Kopien derselben
        Tabelle laufen auseinander - die eine bekommt einen neuen Knopf, die
        andere nicht."""
        quelle = (JS / "aufzeichnung.js").read_text(encoding="utf-8")
        self.assertIn("AufzeichnungsListe", quelle,
                      u"Der Reiter baut seine Tabelle selbst statt die "
                      u"gemeinsame Klasse zu nutzen")
        liste = (JS / "aufzeichner_liste.js").read_text(encoding="utf-8")
        for stueck in ("db-tabelle sortable", "TabellenSortierung.binden",
                       "new TabellenBreiten", "au-name", "au-weg"):
            self.assertIn(stueck, liste)

    def test_eigene_bedienung_wird_nicht_aufgezeichnet(self):
        u"""Sonst stünde in jeder Aufnahme der Klick auf „Aufzeichnen" selbst."""
        quelle = (JS / "aufzeichner.js").read_text(encoding="utf-8")
        self.assertIn("data-djb-aufzeichner-ui", quelle,
                      u"Der Aufzeichner muss die eigene Bedienung ausnehmen")
        # Die Marke sitzt am Sidebar-Markup, seit die Bedienung dort steht.
        sidebar = (PAKET / "templates" / "djangobase" / "_sidebar.html")             .read_text(encoding="utf-8")
        self.assertIn("data-djb-aufzeichner-ui", sidebar,
                      u"Ohne die Marke stünde in jeder Aufnahme als erster "
                      u"Schritt der Klick auf „Aufnahme“ selbst")

    def test_zustandsfarben_stehen_im_javascript(self):
        u"""Chrome berechnete den Stil nach dem Klassenwechsel nicht neu.

        Auf /dax-handel/ blieb der Knopf grau bzw. weiß, obwohl Klasse und
        Beschriftung stimmten; ein Klon desselben Elements bekam die richtige
        Farbe. Deshalb setzt das Modul die drei Zustandsfarben inline."""
        leiste = (JS / "aufzeichner_leiste.js").read_text(encoding="utf-8")
        ohne_leer = "".join(leiste.split())
        self.assertIn("constBILD", ohne_leer,
                      u"Die Zustandsbilder müssen als Tabelle im Modul stehen")
        for zustand in ("bereit:", "laeuft:", "wartet:"):
            self.assertIn(zustand, ohne_leer,
                          u"Zustand %r fehlt in der Farbtabelle" % zustand)
        self.assertIn("Object.assign(k.style", leiste,
                      u"Die Farben müssen INLINE gesetzt werden - ein Klassen"
                      u"wechsel allein hat Chrome hier nicht zum Neuberechnen "
                      u"gebracht")
