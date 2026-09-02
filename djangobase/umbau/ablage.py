# -*- coding: utf-8 -*-
u"""Ergebnisse eines Durchgangs behalten — im Arbeitsspeicher UND auf Platte.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „cache die Ergebnisse des letzten Laufs auf
     http://localhost:8000/hilfe/klassenmodell/"

WAS VORHER FEHLTE
=================
Es gab fünf fast gleiche Klassen im Ansichts-Modul, jede mit einem
``dict`` im Arbeitsspeicher. Zwei Dinge liefen damit schief:

1. **Ein Neustart des Web-Dienstes leerte alles.** Und der kommt oft —
   Daphne lädt nicht neu, also wird nach jeder Änderung neu gestartet.
   Danach stand die Seite wieder leer da, und der nächste Durchgang
   kostete erneut 19 Sekunden (Qualität) bzw. 3 (Klassenmodell).
2. **Ein frischer Seitenaufruf zeigte nichts.** Wer die Seite aufschlug,
   sah ein leeres Feld und einen Knopf — obwohl das Ergebnis von vorhin
   noch galt.

WARUM PICKLE UND NICHT JSON
===========================
Gespeichert werden fertige Objektmodelle mit Verweisen untereinander
(``Klasse`` hält ``Beziehung`` hält ``Klasse``). Als JSON müsste jedes
davon einen Auf- und Abbau bekommen — fünf Modelle, zehn Umwandlungen,
die beim nächsten Feld auseinanderlaufen.

Der Preis: Eine Ablage aus einer älteren Fassung des Codes lässt sich
womöglich nicht mehr laden. Deshalb steht die **Fassung im Dateinamen**,
und ein Fehlschlag beim Lesen ist kein Fehler, sondern ein leerer
Speicher — dann rechnet der nächste Durchgang eben neu.

NICHT für Daten, die stimmen müssen. Das hier ist eine Bequemlichkeit:
Was drinsteht, ist der Stand von vorhin, und die Seite sagt dazu, wie alt
er ist.
"""
import hashlib
import logging
import pickle
import time
from pathlib import Path

from django.conf import settings

logger = logging.getLogger('djangobase.ablage')

#: Steht im Dateinamen. Hochzählen, sobald sich die gespeicherten Klassen
#: so ändern, dass eine alte Ablage falsch gelesen würde.
FASSUNG = 1

#: Älter als das, und der Inhalt wird verworfen. Nicht weil er dann falsch
#: wäre — sondern weil „Stand von vorletzter Woche" niemandem hilft und
#: die Platte sonst voll läuft.
HALTBAR_SEK = 14 * 24 * 3600


def ordner():
    u"""Wohin die Ablage schreibt.

    Unter ``BASE_DIR``, nicht ins Temp-Verzeichnis: Das ist eine harte
    Regel des Wirtsprojekts (100-GB-Vorfall), und eine Ablage, die beim
    nächsten Aufräumen des Systems verschwindet, ist keine.
    """
    ziel = Path(getattr(settings, 'BASE_DIR', '.')) / '.cache' / 'umbau'
    ziel.mkdir(parents=True, exist_ok=True)
    return ziel


def _pfad(bereich, schluessel):
    kurz = hashlib.md5(str(schluessel).encode('utf-8')).hexdigest()[:16]
    return ordner() / ('%s-v%d-%s.pickle' % (bereich, FASSUNG, kurz))


def lesen(bereich, schluessel):
    u"""``(wert, alter_in_sekunden)`` — oder ``(None, None)``."""
    pfad = _pfad(bereich, schluessel)
    try:
        roh = pfad.read_bytes()
    except OSError:
        return None, None
    try:
        wann, wert = pickle.loads(roh)
    except Exception:
        # Eine Ablage aus einer aelteren Fassung. Kein Fehler — nur nichts
        # zu holen. Weg damit, sonst scheitert jeder weitere Versuch.
        logger.info('Ablage %s/%s nicht lesbar — verworfen', bereich,
                    schluessel)
        try:
            pfad.unlink()
        except OSError:
            pass
        return None, None
    alter = time.time() - wann
    if alter > HALTBAR_SEK:
        return None, None
    return wert, alter


def schreiben(bereich, schluessel, wert):
    u"""Legt ab. Ein Fehlschlag kostet nur die Bequemlichkeit.

    Geschrieben wird über eine Zwischendatei und ``replace``: Wer beim
    Schreiben unterbrochen wird, hinterlässt sonst eine halbe Datei, und
    die liest sich beim nächsten Mal als „kaputte Fassung".
    """
    pfad = _pfad(bereich, schluessel)
    tmp = pfad.with_suffix('.tmp')
    try:
        tmp.write_bytes(pickle.dumps((time.time(), wert),
                                     pickle.HIGHEST_PROTOCOL))
        tmp.replace(pfad)
    except Exception:
        logger.warning('Ablage %s/%s nicht schreibbar', bereich, schluessel,
                       exc_info=True)
        try:
            tmp.unlink()
        except OSError:
            pass


def leeren(bereich):
    u"""Alles dieses Bereichs von der Platte nehmen."""
    for pfad in ordner().glob('%s-v%d-*.pickle' % (bereich, FASSUNG)):
        try:
            pfad.unlink()
        except OSError:
            pass


class Speicher:
    u"""Ein Ergebnis je Quelle — gemerkt und abgelegt.

    Fünf fast gleiche Klassen standen dafür im Ansichts-Modul. Eine
    Grundform mit ``bereich`` und ``bauen`` tut dasselbe, und ein Zusatz
    (die Ablage auf Platte) musste nun nicht fünfmal geschrieben werden.

    Unterklassen setzen::

        bereich = 'klassenmodell'
        @staticmethod
        def bauen(wurzel): return Klassenmodell(wurzel).lesen()
    """

    #: Name im Dateinamen der Ablage. MUSS je Unterklasse verschieden sein.
    bereich = ''

    @staticmethod
    def bauen(wurzel):                              # pragma: no cover
        raise NotImplementedError

    @classmethod
    def _gemerkt(cls):
        u"""Das dict DIESER Unterklasse.

        Ohne ``cls.__dict__`` teilten sich alle Unterklassen eines der
        Grundklasse — und das Klassenmodell läge unter demselben
        Schlüssel wie die Qualitätsmessung.
        """
        if '_werte' not in cls.__dict__:
            cls._werte = {}
        return cls._werte

    #: Module, deren INHALT das Ergebnis bestimmt.
    #:
    #: DER SPEICHER MUSS MERKEN, WENN SEIN ERZEUGER SICH AENDERT
    #: ========================================================
    #:     „ich brauche einen Button zum neu Berechnen, sehe noch den
    #:      alten Stand" (Edgar, 27.08.2026)
    #:
    #: Der Schlüssel war nur der Projektpfad. Wurde die AUSWERTUNG
    #: geändert — am selben Tag zweimal: der Klassenkasten zeigte die
    #: ganze Klasse statt den Konstruktor —, blieb das alte Ergebnis
    #: gültig. Die Seite zeigte weiter die 26 erfundenen Kanten, und nur
    #: wer den Knopf fand, sah die richtigen neun.
    #:
    #: Ein Knopf ist die falsche Antwort auf diese Frage: Er verlangt,
    #: dass der Leser weiß, dass sich etwas geändert hat. Genau das kann
    #: er nicht wissen — und genau darum geht es auf dieser Seite.
    #:
    #: Wer hier seine Quellmodule einträgt, bekommt bei jeder Änderung an
    #: ihnen automatisch einen neuen Schlüssel und damit eine neue
    #: Rechnung. Ohne Eintrag bleibt alles wie bisher.
    quellen = ()

    @classmethod
    def abdruck(cls):
        u"""Ein kurzes Kennzeichen der Quellmodule — leer, wenn keine.

        Gemessen wird Groesse und Aenderungszeit, nicht der Inhalt: Beides
        aendert sich bei jeder Bearbeitung, und eine Datei zu lesen kostet
        mehr als sie zu befragen.
        """
        if not cls.quellen:
            return ''
        teile = []
        for quelle in cls.quellen:
            pfad = Path(getattr(quelle, '__file__', quelle))
            try:
                stand = pfad.stat()
                teile.append('%s:%d:%d' % (pfad.name, stand.st_size,
                                           int(stand.st_mtime)))
            except OSError:
                teile.append('%s:fehlt' % pfad.name)
        return hashlib.md5('|'.join(teile).encode('utf-8')).hexdigest()[:8]

    @classmethod
    def holen(cls, wurzel, neu=False):
        u"""``(Wert, Alter in Sekunden oder None)``.

        ``None`` als Alter heißt: gerade eben gerechnet.
        """
        abdruck = cls.abdruck()
        schluessel = '%s#%s' % (wurzel, abdruck) if abdruck else str(wurzel)
        gemerkt = cls._gemerkt()
        if not neu:
            if schluessel in gemerkt:
                wert, wann = gemerkt[schluessel]
                return wert, time.time() - wann
            wert, alter = lesen(cls.bereich, schluessel)
            if wert is not None:
                gemerkt[schluessel] = (wert, time.time() - alter)
                return wert, alter
        wert = cls.bauen(wurzel)
        gemerkt[schluessel] = (wert, time.time())
        schreiben(cls.bereich, schluessel, wert)
        return wert, None

    @classmethod
    def nachsehen(cls, wurzel):
        u"""``(Wert, Alter)`` NUR aus Speicher und Ablage — rechnet nie.

        WARUM DAS NOETIG WURDE (Edgar, 02.09.2026)
        ==========================================
            „es soll nicht immer neu eingelesen werden, die ergebnisse
             sind gecacht … auch der Wechsel auf die Tabs innerhalb der
             Seite dauert ewig"

        ``holen`` rechnet, wenn nichts abgelegt ist — auch beim blossen
        Seitenaufruf und beim Reiterwechsel. Auf ``assistant`` kostet die
        Qualitaetsmessung **94 Sekunden** (gemessen 02.09.2026: quellen
        6,8 · Komplexitaet 5,5 · Wartbarkeit 32,8 · Fehler 21,9 · Stil
        27,1). Wer so lange wartet, bricht ab — und weil ``schreiben``
        erst NACH ``bauen`` laeuft, wird nie etwas abgelegt. Der naechste
        Aufruf faengt von vorn an: Die Seite kann sich nie erholen.

        Deshalb rechnet ab jetzt nur noch, wer einen Knopf drueckt.
        Alles andere sieht nach — und zeigt notfalls die leere Seite.
        """
        gemerkt = cls._gemerkt()
        abdruck = cls.abdruck()
        schluessel = '%s#%s' % (wurzel, abdruck) if abdruck else str(wurzel)
        if schluessel in gemerkt:
            wert, wann = gemerkt[schluessel]
            return wert, time.time() - wann
        wert, alter = lesen(cls.bereich, schluessel)
        if wert is not None:
            gemerkt[schluessel] = (wert, time.time() - alter)
        return wert, alter

    @classmethod
    def leeren(cls):
        cls._gemerkt().clear()
        leeren(cls.bereich)


__all__ = ['Speicher', 'lesen', 'schreiben', 'leeren', 'ordner', 'FASSUNG']
