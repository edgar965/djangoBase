# -*- coding: utf-8 -*-
u"""Hilfe · Werkzeug Klassenmodell — das Objektmodell des Projekts als Bild.

WOZU (Edgar, 24.08.2026)
========================
    „erstelle eine Seite in djangoBase hilfe - werkzeug Klassenmodell, das
     soll einen Button enthalten, der so eine Übersicht des Codes erstellt"

`objektwurzeln` misst dasselbe Verhaeltnis schon — aber als Zahl („74 von
548 Klassen haengen als self.x an einer anderen"). Eine Zahl sagt, wie gut
das Modell ist; sie zeigt nicht, WIE es aussieht.

Das Bild entsteht auf Knopfdruck, nicht beim Seitenaufruf: Der Durchgang
liest jede ``.py`` des Projekts. Bei CamTrack sind das 1004 Klassen — das
gehoert nicht in den Weg von jemandem, der nur die Seite aufschlaegt.
"""
import logging
import time
from pathlib import Path

from django.conf import settings
from django.views import View

from ..mixins import ZugriffMixin
from ..umbau import ablage
from ..umbau.ablage import Speicher
from ..umbau.aufrufnetz import Aufrufnetz
from ..umbau.codequalitaet import Codequalitaet
from ..umbau.codezahlen import Codezahlen
from ..umbau import aufrufnetz as aufrufnetz_modul
from ..umbau import codequalitaet as codequalitaet_modul
from ..umbau import codezahlen as codezahlen_modul
from ..umbau import globalbestand as globalbestand_modul
from ..umbau import klassenmodell as klassenmodell_modul
from ..umbau.gliederung import nach_rolle as gliedern
from ..umbau.globalbestand import Globalbestand, hauptaeste
from ..umbau.klassenbild import Klassenbild
from ..umbau.klassenmodell import Klassenmodell

#: Vorgabe fuer die Nachbarschaft. Zwei Schritte zeigen die Wurzel, was sie
#: haelt, und was DIESE halten — bei drei wird es eine Tapete.
TIEFE_VORGABE = 2

logger = logging.getLogger('djangobase.klassenmodell')


class Letzterlauf:
    u"""Was zuletzt gezeigt wurde — Reiter, Quelle, Startklasse.

    Nicht das ERGEBNIS (das liegt in den Speichern oben), sondern
    die FRAGE. Damit zeigt ein frischer Seitenaufruf denselben
    Stand wie vorhin, statt leer dazustehen — und der Durchgang
    kommt aus dem Speicher.
    """

    BEREICH = 'letzterlauf'
    SCHLUESSEL = 'seite'

    @classmethod
    def holen(cls):
        return ablage.lesen(cls.BEREICH, cls.SCHLUESSEL)

    @classmethod
    def merken(cls, daten):
        ablage.schreiben(cls.BEREICH, cls.SCHLUESSEL,
                         dict((k, daten.get(k, ''))
                              for k in ('reiter', 'bereich',
                                        'start', 'tiefe', 'was')))


class Modellspeicher(Speicher):
    u"""Hält das eingelesene Modell, bis jemand ausdruecklich neu liest.

    DIE ANSAGE (Edgar, 24.08.2026)
    ==============================
        „mach auch einen Refresh button, damit der nicht alles neu
         durchgeht?"

    Berechtigt: Der Durchgang liest jede ``.py`` des Projekts — bei
    CamTrack 1021 Klassen.

    UND EINE ZWEITE (24.08.2026)
    ============================
        „cache die Ergebnisse des letzten Laufs"

    Vorher lag alles nur im Arbeitsspeicher des Web-Dienstes. Der wird
    nach jeder Änderung neu gestartet (Daphne lädt nicht nach), und
    danach stand die Seite wieder leer da. Jetzt liegt das Ergebnis unter
    ``BASE_DIR/.cache/umbau/`` und ueberlebt den Neustart — siehe
    ``djangobase/umbau/ablage.py``.
    """

    bereich = 'klassenmodell'
    #: Aendert sich die Auswertung, gilt das alte Ergebnis nicht mehr.
    #: Am 02.09.2026 hat genau das gefehlt: Der Filter bekam die
    #: virtuellen Umgebungen dazu, und die Seite zeigte trotzdem weiter
    #: die Zahlen mit dem Fremdcode darin.
    quellen = (klassenmodell_modul, )

    @staticmethod
    def bauen(wurzel):
        return Klassenmodell(wurzel).lesen()


class Quellenspeicher(Speicher):
    u"""Die waehlbaren Quellen — einmal gezählt, dann gemerkt.

    AUCH AUF PLATTE (02.09.2026, Edgar: „dauert immer noch sehr lange")
    ===================================================================
    Vorher lag die Liste nur im Arbeitsspeicher. Der Server läuft mit
    ``--noreload`` und wird nach jeder Änderung neu gestartet — und jeder
    Neustart kostete den ERSTEN Seitenaufruf die Zählung aller ``.py`` des
    Projekts: gemessen 1,1–1,3 s auf shortlongx (dazu 0,6 s fürs Übersetzen
    der Vorlage, die niemand wegspeichern kann). Das Ergebnis hatte sich
    dabei nie geändert.

    Es gibt genau EINE Liste (die der Projektwurzel), deshalb ``liste()``
    ohne Wurzel-Argument; abgelegt wird sie trotzdem über ``Speicher``,
    damit sie mit dessen Quellen-Abdruck ungültig wird, sobald sich die
    Zählung selbst ändert.
    """

    bereich = 'hauptaeste'
    quellen = (globalbestand_modul, klassenmodell_modul)

    @staticmethod
    def bauen(wurzel):
        return hauptaeste(wurzel)

    @classmethod
    def liste(cls, neu=False):
        wert, _alter = cls.holen(Path(settings.BASE_DIR), neu=neu)
        return wert


class Netzspeicher(Speicher):
    u"""Das Aufrufnetz — liest jede ``.py`` zweimal (Definitionen, dann
    Aufrufe). Das gehört nicht in jeden Reiterwechsel."""

    bereich = 'aufrufnetz'
    quellen = (aufrufnetz_modul, klassenmodell_modul)

    @staticmethod
    def bauen(wurzel):
        return Aufrufnetz(wurzel).lesen()


class Bestandsspeicher(Speicher):
    u"""Dasselbe für den Modulebenen-Bestand: einmal lesen, oft ansehen."""

    bereich = 'globalbestand'
    quellen = (globalbestand_modul, klassenmodell_modul)

    @staticmethod
    def bauen(wurzel):
        return Globalbestand(wurzel).lesen()


class Zahlenspeicher(Speicher):
    u"""Die Bestandszahlen — der Durchgang geht über JEDE Datei, nicht
    nur über die ``.py``. Bei CamTrack 1119 Quelldateien, knapp zwei
    Sekunden."""

    bereich = 'codezahlen'
    quellen = (codezahlen_modul, klassenmodell_modul)

    @staticmethod
    def bauen(wurzel):
        return Codezahlen(wurzel).lesen()


class Qualitaetsspeicher(Speicher):
    u"""Die Messung — vier Werkzeuge über 711 Dateien: gemessen **19
    Sekunden**. Das gehört nicht in jeden Reiterwechsel und schon gar
    nicht in den Seitenaufruf."""

    bereich = 'codequalitaet'
    quellen = (codequalitaet_modul, codezahlen_modul, klassenmodell_modul)

    @staticmethod
    def bauen(wurzel):
        return Codequalitaet(wurzel).messen()


class KlassenmodellView(ZugriffMixin, View):
    u"""Zeigt die Seite; auf Knopfdruck rechnet sie das Bild."""

    vorlage = 'djangobase/hilfe/klassenmodell.html'

    def get(self, request):
        u"""Zeigt den letzten Lauf, statt leer dazustehen.

        DIE ANSAGE (Edgar, 24.08.2026)
        ==============================
            „cache die Ergebnisse des letzten Laufs"

        Eine Ablage, die den Neustart überlebt, nützt nichts, solange die
        Seite beim Aufschlagen trotzdem leer ist. Gemerkt wird deshalb
        auch, WAS zuletzt gezeigt wurde — Reiter, Quelle, Startklasse.
        Der Durchgang selbst kommt dann aus dem Speicher und kostet
        nichts.

        Fällt das Wiederholen hin (eine Ablage aus einer älteren Fassung,
        eine Quelle, die es nicht mehr gibt), kommt die leere Seite. Das
        ist der alte Zustand, kein Fehler.
        """
        letzter, _alter = Letzterlauf.holen()
        if letzter:
            try:
                return self._zeigen(request, letzter, rechnen=False)
            except Exception:
                logger.warning('letzten Lauf nicht wiederholbar',
                               exc_info=True)
        return self._seite(request)

    #: Die Reiter der Seite. Der Schluessel steht im Formular.
    REITER = (
        ('baum', 'Klassenmodell', 'bi-diagram-3'),
        ('funktionen', 'Globale Funktionen', 'bi-code-slash'),
        ('klassen', 'Globale Klassen', 'bi-boxes'),
        ('variablen', 'Globale Variablen', 'bi-hash'),
        ('seiten', 'HTML-Seiten', 'bi-filetype-html'),
        # Eigener Reiter seit dem 02.09.2026 (Edgar: „Wo ist die
        # Statistik mit der Tabelle der Codezeilen? Mach dafuer einen Tab
        # Statistik"). Sie stand als dritter Knopf im Qualitaets-Reiter
        # und war damit hinter einer 94-Sekunden-Messung versteckt,
        # obwohl sie selbst nur zwei Sekunden kostet.
        ('statistik', 'Statistik', 'bi-bar-chart'),
        ('qualitaet', 'Code Qualität', 'bi-speedometer2'),
    )

    #: Formularfelder, die einen Knopfdruck bedeuten. Nur dann wird
    #: gerechnet — siehe ``_darf_rechnen``.
    RECHENKNOEPFE = ('neu', 'was', 'rechnen')

    def post(self, request):
        Letzterlauf.merken(request.POST)
        return self._zeigen(request, request.POST,
                            rechnen=self._darf_rechnen(request.POST))

    @classmethod
    def _darf_rechnen(cls, daten):
        u"""Hat jemand einen Knopf gedrueckt — oder nur den Reiter gewechselt?

        DER UNTERSCHIED KOSTETE DIE SEITE (Edgar, 02.09.2026)
        =====================================================
            „es soll nicht immer neu eingelesen werden … auch der Wechsel
             auf die Tabs innerhalb der Seite dauert ewig"

        Der Reiterwechsel schickt das Formular per ``form.submit()`` ab —
        ohne den Namen eines Absendeknopfes. Genau daran ist er zu
        erkennen: Kommt keiner der ``RECHENKNOEPFE`` mit, wird nur
        nachgesehen, was schon abgelegt ist.

        Der GET faellt ohnehin nicht hierher: Er uebergibt ``rechnen``
        gar nicht erst.
        """
        return any(k in daten for k in cls.RECHENKNOEPFE)

    @staticmethod
    def _aus_speicher(klasse, wurzel, neu, rechnen):
        u"""``(Wert, Alter)`` — rechnet nur, wenn gerechnet werden darf.

        Ohne Knopfdruck kann der Wert ``None`` sein; die Reiter fangen
        das ab und zeigen die leere Seite mit dem Knopf.
        """
        if rechnen:
            return klasse.holen(wurzel, neu=neu)
        return klasse.nachsehen(wurzel)

    def _zeigen(self, request, daten, rechnen=False):
        u"""Eine Sicht bauen — aus dem Formular ODER aus dem letzten Lauf.

        Beide Wege gehen durch dieselbe Stelle. Zwei Stellen, die
        dieselbe Seite bauen, laufen auseinander; das hat dieses Projekt
        an der Live-Kachel bereits Wochen gekostet.
        """
        wurzel = self._wurzel(daten.get('bereich', ''))
        neu = bool(daten.get('neu'))
        reiter = daten.get('reiter', 'baum')
        if reiter not in dict((k, 1) for k, _l, _i in self.REITER):
            reiter = 'baum'
        if reiter == 'qualitaet':
            return self._qualitaet(request, daten, wurzel, neu, rechnen)
        if reiter == 'statistik':
            return self._statistik(request, daten, wurzel, neu, rechnen)
        if reiter != 'baum':
            bestand, alter = self._aus_speicher(
                Bestandsspeicher, wurzel, neu, rechnen)
            if bestand is None:
                return self._leerer_reiter(request, reiter, daten)
            zusatz = {}
            if reiter in ('klassen', 'funktionen'):
                # DIESELBE GLIEDERUNG UND DIESELBEN STECKBRIEFE WIE IM BILD
                # (24.08.2026, auf Ansage: „mache alle Klassen in allen Tabs
                # und alle Funktionen aus allen Tabs auch als Gliederung mit
                # Knoepfen, so dass man sieht, wer sie nutzt").
                netz, _n = self._aus_speicher(
                    Netzspeicher, wurzel, neu, rechnen)
                if netz is None:
                    return self._leerer_reiter(request, reiter, daten)
                if reiter == 'klassen':
                    # EINE QUELLE JE REITER (24.08.2026, gemeldet:
                    # „struktur noch immer unklar"). Die Karten oben
                    # rechneten mit dem Klassenmodell (1004), die
                    # Gliederung darunter mit dem Modulebenen-Bestand
                    # (584) — zwei Zaehlungen auf EINEM Reiter. Hier zaehlt
                    # nur noch das Klassenmodell, dieselbe Quelle wie das
                    # Auswahlfeld.
                    modell, _a = self._aus_speicher(
                        Modellspeicher, wurzel, neu, rechnen)
                    if modell is None:
                        return self._leerer_reiter(request, reiter, daten)
                    zusatz['kategorien'] = modell.kategorien()
                    zusatz['klassen_gesamt'] = len(modell.klassen)
                    namen = sorted(modell.klassen)
                    zusatz['rollen'] = modell.nach_rolle()
                else:
                    namen = [e.name for e in bestand.funktionen]
                    zusatz['rollen'] = gliedern(
                        (e.name, e.datei) for e in bestand.funktionen)
                zusatz['gesamt'] = len(namen)
                # Nur die gezeigten — alle 1737 waeren ein Megabyte JSON.
                zusatz['steckbriefe_json'] = netz.steckbriefe(namen)
                zusatz['netz_zahlen'] = netz.kennzahlen()
            return self._seite(
                request, reiter=reiter, bestand=bestand,
                kennzahlen=bestand.kennzahlen(),
                bereich=daten.get('bereich', ''),
                alter=int(alter) if alter is not None else None, **zusatz)
        if neu:
            Quellenspeicher.leeren()
            Netzspeicher.leeren()
        modell, alter = self._aus_speicher(
            Modellspeicher, wurzel, neu, rechnen)
        if modell is None:
            return self._leerer_reiter(request, 'baum', daten)
        start = (daten.get('start') or '').strip() or None
        try:
            tiefe = max(1, min(4, int(daten.get('tiefe')
                                      or TIEFE_VORGABE)))
        except (TypeError, ValueError):
            tiefe = TIEFE_VORGABE
        kaesten, linien = modell.nachbarschaft(start, tiefe)
        gewaehlt = start or modell.dickster_ast()
        # STECKBRIEFE FUER ALLES, WAS AUF DER SEITE STEHT (24.08.2026)
        # ============================================================
        # Hier stand `modell.steckbriefe(k.name for k in kaesten)` — also
        # nur fuer die Kaesten IM BILD, mit der Begruendung „alle 1004
        # waeren ein Megabyte JSON". Nachgemessen sind es **430 KB**, und
        # die Gliederung darunter listet alle 1021 Klassen als Knoepfe.
        #
        # Gemeldet: „ich hatte dir aufgegeben, bei jedem Klassen-Eintrag
        # einen Popup zu machen mit den Infos … warum fehlt das???" Genau
        # deshalb: Wer einen Knopf anklickte, bekam nichts, weil zu seinem
        # Namen kein Steckbrief mitgeschickt war.
        #
        # Eine geschaetzte Zahl hat hier eine Funktion verhindert. 430 KB
        # sind fuer eine Entwickler-Seite kein Grund dazu.
        steckbriefe = modell.steckbriefe(sorted(modell.klassen))
        return self._seite(
            request,
            bild=(Klassenbild(kaesten, linien, gewaehlt, steckbriefe).svg()
                  if kaesten else ''),
            # Das Woerterbuch selbst, NICHT als Zeichenkette: `json_script`
            # kodiert noch einmal, und `JSON.parse` liefert dann eine
            # Zeichenkette statt eines Objekts. Das Popup blieb still leer.
            steckbriefe_json=steckbriefe,
            kennzahlen=modell.kennzahlen(),
            gewaehlt=gewaehlt,
            tiefe=tiefe,
            bereich=daten.get('bereich', ''),
            gezeigt=len(kaesten),
            aeste=self._aeste(modell),
            # Alle Klassen, nach Verzeichnis gebuendelt — sonst nennt die
            # Seite eine Zahl, zu der es keinen Weg gibt.
            bereiche_klassen=modell.nach_bereich(),
            # Zwei Ebenen: Rolle im Projekt, darunter das Verzeichnis.
            rollen=modell.nach_rolle(),
            klassen_gesamt=len(modell.klassen),
            alter=int(alter) if alter is not None else None,
            leer=not kaesten and bool(start),
            reiter='baum',
        )

    # ── Code Qualität ───────────────────────────────────────────
    def _leerer_reiter(self, request, reiter, daten):
        u"""Der Reiter ohne Ergebnis — mit dem Knopf, der es holt.

        Kein Fehler und keine leere Seite ins Blaue: Wer den Reiter
        wechselt, bekommt sofort die Seite und entscheidet selbst, ob er
        auf den Durchgang warten will. Vorher rechnete jeder Wechsel und
        jeder Seitenaufruf mit (02.09.2026).
        """
        return self._seite(request, reiter=reiter,
                           bereich=daten.get('bereich', ''),
                           was=daten.get('was_zuletzt', ''),
                           nichts_gerechnet=True)

    # ── Statistik ───────────────────────────────────────────────
    def _statistik(self, request, daten, wurzel, neu, rechnen):
        u"""Die Bestandszahlen — Dateien, Zeilen, Anweisungen je Art.

        EIGENER REITER SEIT DEM 02.09.2026
        ==================================
            „Wo ist die Statistik mit der Tabelle der Codezeilen? Mach
             dafuer einen Tab Statistik auf der Seite und verschiebe sie
             darin" (Edgar)

        Sie stand als dritter Knopf im Qualitaets-Reiter. Wer sie sehen
        wollte, landete zuerst auf der Messung — und die kostet auf
        ``assistant`` 94 Sekunden. Die Zaehlung selbst braucht zwei.
        """
        zahlen, alter = self._aus_speicher(
            Zahlenspeicher, wurzel, neu, rechnen)
        if zahlen is None:
            return self._leerer_reiter(request, 'statistik', daten)
        return self._seite(
            request, reiter='statistik',
            bereich=daten.get('bereich', ''),
            arten=zahlen.liste(),
            arten_gesamt=zahlen.gesamt(),
            zahlen=zahlen.kennzahlen(),
            # Ehrlich sagen, was NICHT mitgezählt wurde. Ohne diese Zeile
            # liest sich „1119 Dateien" wie das ganze Verzeichnis, und im
            # ersten Lauf standen dort 3861 — mit einem 1,7-GB-Video darin.
            ausgelassen=zahlen.ausgelassen,
            ausgelassen_wo=sorted(zahlen.ausgelassen_wo.items(),
                                  key=lambda p: -p[1]),
            # WORAUS „ÜBRIGE" BESTEHT (02.09.2026, Edgar: „bei Statistik
            # habe ich über 3 Millionen leere Zeilen bei Übrige? was ist
            # das, spezifiziere und fixe"). Die Zeile nannte eine Zahl und
            # liess offen, wofür sie steht; die Antwort brauchte ein
            # eigenes Skript. Jetzt steht sie auf der Seite.
            uebrige=zahlen.uebrige_arten(),
            alter=int(alter) if alter is not None else None)

    # ── Code Qualität ───────────────────────────────────────────
    def _qualitaet(self, request, daten, wurzel, neu, rechnen):
        u"""Die Messung mit vier Werkzeugen — und die Befundliste dazu.

        DIE ANSAGE (Edgar, 24.08.2026)
        ==============================
            „Dann brauche ich ein Tool zur Evaluierung der Code-Qualität
             … Mach einen Button dazu der Code-Qualität mit 2-3 Methoden
             überprüft"

        Die Zählung („Statistik") ist seit dem 02.09.2026 ein eigener
        Reiter: Sie kostet zwei Sekunden, diese Messung 94 — das gehört
        nicht hinter denselben Reiter.
        """
        # „Neu einlesen" schickt kein `was` mit — dann gilt, was zuletzt
        # gezeigt wurde. Ein zweites Feld NAMENS `was` ginge nicht: Bei
        # einer QueryDict zaehlt der letzte Wert, und der Knopf verlöre.
        was = (daten.get('was')
               or daten.get('was_zuletzt') or 'qualitaet')
        if was not in ('qualitaet', 'befunde'):
            was = 'qualitaet'
        messung, alter = self._aus_speicher(
            Qualitaetsspeicher, wurzel, neu, rechnen)
        if messung is None:
            return self._leerer_reiter(request, 'qualitaet', daten)
        zusatz = {'was': was, 'bereich': daten.get('bereich', ''),
                  'verfahren': messung.als_liste(),
                  'q_dateien': len(messung.dateien)}
        if was == 'befunde':
            # ALLE Funde in EINER Tabelle (27.08.2026, auf Ansage):
            #     „ich sehe keine Tabelle zu den Findings der 4 Werkzeuge"
            # Die Verfahrensblöcke zeigen je 15 Treffer und sind nach
            # Werkzeug getrennt — man sieht dort nie, was insgesamt das
            # Dringendste ist. Diese Sicht dreht das um: eine Liste,
            # nach Gewicht sortiert, mit dem Werkzeug als Spalte.
            zusatz['befunde'] = self._befundliste(messung)
            zusatz['befund_stufen'] = self._stufenzaehler(zusatz['befunde'])
        # Was beim MESSEN scheiterte, gehört ganz nach oben: Eine
        # Datei, die nicht parst, ist der schwerste Fund — und sie
        # verschwand bis zum 24.08.2026 hinter einem stummen
        # `except: continue`, also aus Statistik UND Bericht.
        zusatz['pannen'] = [{'datei': d, 'verfahren': v, 'grund': g}
                            for d, v, g in messung.pannen]
        return self._seite(request, reiter='qualitaet',
                           alter=int(alter) if alter is not None else None,
                           **zusatz)

    #: Reihenfolge der Dringlichkeit - Fehler zuerst.
    STUFEN = ('fehler', 'warnung', 'hinweis')

    @classmethod
    def _befundliste(cls, messung):
        u"""Alle Treffer aller Verfahren als EINE nach Gewicht sortierte Liste.

        Die Gewichtung kommt aus ``skills.codequalitaet.CodeQualitaet``, wo sie
        ohnehin fuer den Bericht gerechnet wird - ein zweiter Satz Regeln
        daneben liefe irgendwann auseinander, und dann behauptete dieselbe
        Zahl an zwei Stellen zweierlei.

        Hier wird NICHT auf 15 gekuerzt: Der Sinn der Sicht ist gerade, das
        Dringendste ueber alle vier Verfahren hinweg zu sehen. Eine Kuerzung
        je Verfahren wuerde genau das verdecken, was sie zeigen soll.
        """
        from ..skills.codequalitaet import CodeQualitaet
        raus = []
        for v in messung.verfahren:
            if v.fehlt:
                continue
            for t in v.treffer:
                raus.append({
                    'stufe': CodeQualitaet._gewicht(v, t),
                    'verfahren': v.name, 'werkzeug': v.werkzeug,
                    'wert': t.wert, 'nachkomma': v.nachkomma,
                    'name': t.name, 'datei': t.datei, 'zeile': t.zeile,
                    'text': t.text,
                })
        rang = {s: i for i, s in enumerate(cls.STUFEN)}
        raus.sort(key=lambda b: (rang.get(b['stufe'], 9), b['datei'], b['zeile']))
        return raus

    @classmethod
    def _stufenzaehler(cls, befunde):
        u"""``[(stufe, anzahl)]`` fuer den Kopf - auch die leeren Stufen."""
        zahl = {s: 0 for s in cls.STUFEN}
        for b in befunde:
            zahl[b['stufe']] = zahl.get(b['stufe'], 0) + 1
        return [(s, zahl[s]) for s in cls.STUFEN]

    # ── intern ──────────────────────────────────────────────────
    @staticmethod
    def _wurzel(bereich):
        u"""Welcher Teil des Projekts wird gelesen?

        Ohne Angabe der ganze Projektbaum. Ein Unterordner macht das Bild
        kleiner und den Durchgang schneller — bei einem Projekt mit über
        tausend Klassen ist das der Unterschied zwischen Uebersicht und
        Tapete.
        """
        basis = Path(settings.BASE_DIR)
        teil = (bereich or '').strip().strip('/\\')
        if not teil:
            return basis
        ziel = (basis / teil).resolve()
        # Nicht aus dem Projekt heraus: Der Wert kommt aus einem Formular.
        if basis.resolve() not in ziel.parents and ziel != basis.resolve():
            return basis
        return ziel if ziel.is_dir() else basis

    @staticmethod
    def _aeste(modell, wie_viele=12):
        u"""Die dicksten Aeste als Vorschlagsliste — Wer hält wie viele?"""
        gezaehlt = []
        for k in modell.klassen.values():
            # Tests halten oft genau ein Objekt und fuellten die Liste auf
            # zwoelf auf — dabei gibt es nur sechs echte Aeste. Ein Test
            # RUFT das Programm, er ist nicht Teil seines Modells.
            if k.ist_test:
                continue
            eigene = {z for _f, z, _v in k.haelt if z in modell.klassen}
            if len(eigene) > 1:
                gezaehlt.append((len(eigene), k.name))
        gezaehlt.sort(reverse=True)
        return [{'name': n, 'zahl': z} for z, n in gezaehlt[:wie_viele]]

    def _seite(self, request, **zusatz):
        from django.shortcuts import render
        daten = {
            'titel': 'Werkzeug Klassenmodell',
            'tiefe': TIEFE_VORGABE,
            'aktiv': 'klassenmodell',
            'reiter': 'baum',
            'reiter_liste': [{'key': k, 'label': l, 'icon': i}
                             for k, l, i in self.REITER],
            # Je eine Quelle pro Hauptast. GEMERKT, nicht bei jedem
            # Seitenaufruf gerechnet: Die Zaehlung liest jede `.py` des
            # Projekts — das gehoert nicht in den Weg von jemandem, der nur
            # die Seite aufschlaegt.
            'bereiche': Quellenspeicher.liste(),
        }
        daten.update(zusatz)
        return render(request, self.vorlage, daten)


__all__ = ['KlassenmodellView']
