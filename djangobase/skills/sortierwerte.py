"""Sortierwerte — sind die ``data-sort``-Werte einer Tabelle überhaupt lesbar?"""

import re

from .befund import Befund, Befundsatz, BefundWerkzeug
from .routen import alle_routen, klient


#: WÖRTLICH aus ``tabellen_sortierung.js`` übernommen — dort::
#:
#:     /^[€\$£]?\s*[-+]?\d[\d.,]*\s*(?:%|[°µA-Za-z\/]{1,6}|[€\$£])?$/
#:
#: Ein „ungefährer" Nachbau taugt hier nicht: Der Prüfer soll melden, was der
#: BROWSER falsch liest. Weicht er ab, meldet er entweder Fälle, die im Browser
#: stimmen, oder er übersieht die echten. Beim ersten Anlauf war genau das der
#: Fall - „1.234,5 €" galt als unlesbar, weil das Währungszeichen hinten stand.
ZAHL_MIT_EINHEIT = re.compile(
    r'^[€$£]?\s*[-+]?\d[\d.,]*\s*(?:%|[°µA-Za-z/]{1,6}|[€$£])?$')

#: Datumsangaben sind keine Zahlen - weder „11.08.2026" in der Zelle noch
#: „2026-08-11" im Attribut. ISO sortiert als Text völlig richtig; eine Meldung
#: darüber wäre ein Fehlalarm (und der erste Testlauf hat genau den erzeugt).
DATUM = re.compile(r'^\s*(\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{2,4})')

#: Zellen mit ``data-sort`` — Attribut und Zelleninhalt.
ZELLE = re.compile(r'<t[dh][^>]*?\bdata-sort="([^"]*)"[^>]*>(.*?)</t[dh]>',
                   re.S | re.I)

#: Sichtbarer Text einer Zelle: Markup raus, Leerraum zusammen.
_TAGS = re.compile(r'<[^>]+>')


class Sortierwert:
    """Ein ``data-sort`` mit dem Text, der daneben steht.

    ``roh`` ist der Attributwert, ``text`` der sichtbare Zelleninhalt. Beide
    zusammen ergeben erst den Befund: Ein leeres ``data-sort`` ist völlig in
    Ordnung, solange die Zelle auch nichts anzeigt — und ein Fehler, sobald
    dort eine Zahl steht.
    """

    __slots__ = ('roh', 'text')

    def __init__(self, roh, text):
        self.roh = (roh or '').strip()
        self.text = _TAGS.sub(' ', text or '').replace('&nbsp;', ' ').strip()

    # ----------------------------------------------------------------- lesen

    @staticmethod
    def zahl(text):
        """Was ``tabellen_sortierung._zahl`` aus diesem Text machen würde.

        DEUTSCHE LESART: Komma trennt die Dezimalen, JEDER Punkt gilt als
        Tausenderzeichen und fliegt raus. Genau daran ist ``data-sort="20.9B"``
        gescheitert — daraus wurde 209.
        """
        if text is None:
            return None
        t = str(text).replace('−', '-').replace('–', '-').strip()
        if not t:
            return None
        bruch = re.match(r'^(-?\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)$', t)
        if bruch:
            try:
                nenner = float(bruch.group(2).replace(',', '.'))
                return float(bruch.group(1).replace(',', '.')) / nenner if nenner else None
            except (ValueError, ZeroDivisionError):
                return None
        if not ZAHL_MIT_EINHEIT.match(t):
            return None
        gereinigt = re.sub(r'[^\d,.\-]', '', t)
        if not re.search(r'\d', gereinigt):
            return None
        try:
            return float(gereinigt.replace('.', '').replace(',', '.'))
        except ValueError:
            return None

    @staticmethod
    def _wert_im_text(text):
        """Die Zahl, die in der ZELLE steht — oder None.

        Der Text darf eine Einheit tragen („17,4 GB", „137M"): Was zählt, ist
        die Zahl davor. Sie ist der Massstab, an dem der Sortierschlüssel
        gemessen wird.
        """
        if not text or DATUM.match(text):
            # Ein Datum ist keine sortierbare Zahl. Ohne diese Zeile meldete der
            # Prüfer jede Datumsspalte („2026-08-11" im Attribut, „11.08.2026"
            # in der Zelle) - im ersten Testlauf prompt passiert.
            return None, ''
        treffer = re.match(r'^\s*[€$£]?\s*(-?\d[\d.]*(?:,\d+)?)\s*([%\w]{0,6})', text)
        if not treffer:
            return None, ''
        try:
            return float(treffer.group(1).replace('.', '').replace(',', '.')), treffer.group(2)
        except ValueError:
            return None, ''

    # ---------------------------------------------------------------- prüfen

    def befund(self):
        """Was an dieser Zelle nicht stimmt — oder ``None``.

        DREI FÄLLE, alle am 01.09.2026 real aufgetreten:

        1. **Einheit im Sortierschlüssel.** ``data-sort="137M"`` — das JS liest
           137 und stellt ein 137-Millionen-Modell über eines mit 122 Milliarden.
        2. **Dezimalpunkt im Sortierschlüssel.** ``data-sort="20.9B"`` wird zu
           209. Django rendert lokalisiert mit Komma; ein Punkt im Attribut ist
           deshalb fast immer ein von Hand geschriebener Wert.
        3. **Leerer Schlüssel bei gefüllter Zelle.** ``{{ x|default:'' }}`` mit
           ``x = 0`` — Django hält 0 für falsy und macht einen Leerstring daraus.
           Die Spalte sortiert dann gar nicht (Befund GPU-Bedarf, alle Werte 0).
        """
        zell_zahl, zell_einheit = self._wert_im_text(self.text)
        if not self.roh:
            if zell_zahl is not None:
                return ('leerer Sortierschlüssel, aber die Zelle zeigt „%s" — '
                        'bei Zahlenfeldern ist |default_if_none statt |default '
                        'gemeint (Django hält 0 für leer)' % self.text[:40])
            return None

        sort_zahl = self.zahl(self.roh)
        if sort_zahl is None:
            # Kein Zahlenwert - das ist erlaubt (Datum ISO, Text, Note). Nur
            # wenn die ZELLE eine Zahl zeigt, passen die beiden nicht zusammen.
            if zell_zahl is not None:
                return ('Sortierschlüssel „%s" ist keine Zahl, die Zelle zeigt '
                        'aber „%s"' % (self.roh[:20], self.text[:30]))
            return None

        # Der Schlüssel trägt eine Einheit (137M, 20.9B, 3 GB)?
        einheit = re.sub(r'^[€$]?\s*-?[\d.,]+\s*', '', self.roh).strip()
        if einheit and not einheit.startswith('%'):
            return ('Sortierschlüssel „%s" trägt die Einheit „%s" — die '
                    'Sortierung liest daraus %g und ignoriert sie'
                    % (self.roh[:20], einheit, sort_zahl))

        # Ein Punkt im Attribut, der als Tausenderzeichen weggeworfen wird,
        # obwohl er offensichtlich ein Dezimalpunkt ist.
        if re.match(r'^-?\d+\.\d+$', self.roh):
            return ('Sortierschlüssel „%s" hat einen Dezimalpunkt — die '
                    'Sortierung liest deutsch und macht daraus %g'
                    % (self.roh, sort_zahl))
        return None


class Sortierwerte(BefundWerkzeug):

    slug = 'sortierwerte'
    kriterium = 6
    titel = 'Sortierwerte der Tabellen'
    zweck = ('Ruft jede Seite auf und prüft, ob die ``data-sort``-Werte ihrer '
             'Tabellen für die Sortierung überhaupt lesbar sind — mit '
             'derselben Lesart wie ``tabellen_sortierung.js`` im Browser.')
    abhilfe = ('Nach jeder Änderung an einer Tabellenspalte. Eine falsch '
               'sortierende Spalte sieht aus wie eine sortierte: Die Zeilen '
               'stehen in EINER Reihenfolge, nur nicht in der richtigen.')
    befund = ('Am 01.09.2026 stand auf Hilfe → KI-Modelle ein 137-Millionen-'
              'Modell über einem mit 122 Milliarden Parametern (data-sort='
              '"137M" → 137), und die Spalte GPU-Bedarf sortierte gar nicht '
              '(|default machte aus dem Wert 0 einen Leerstring). Weder die '
              'Tabellen-Konformität noch der Doppelcode-Prüfer schlagen dabei '
              'an: Der eine sieht nur die <table>-Attribute, der andere sucht '
              'Wiederholungen.')
    dauer = ('lang — ein Seitenaufruf je Route. Ein Vollauf über shortlongx war '
             'nach 7 Minuten noch nicht durch (rechenintensive Seiten). Mit '
             '``nur`` gezielt einschränken, dann Sekunden.')
    eingabe = ('nur', 'nur Routen, die so beginnen (z. B. /hilfe/) — leer = alle', '')
    ruft_endpunkte_auf = True

    #: Ein Fall, der gemeldet werden MUSS - die Gegenprobe des Werkzeugs.
    _WIEDERHOLT = '<td data-sort="20.9B">20.9B</td>'

    #: Höchstzahl angezeigter Befunde. Gebündelt wird ohnehin je Seite und Art;
    #: wer hier anschlägt, hat ein durchgängiges Muster und keine Einzelfälle.
    ZEILEN = 60

    def pruefen(self, nur='', **_argumente):
        besucher = klient()
        befunde, seiten, zellen, ohne_tabelle = [], 0, 0, 0
        #: Je Seite und Meldung nur EINMAL: Eine Tabelle mit 300 Zeilen hat den
        #: Fehler 300-mal. Ungebuendelt waere die Liste unlesbar und der zweite
        #: echte Befund nicht mehr zu finden.
        gesehen = set()
        #: Ohne Einschraenkung laeuft das Werkzeug ueber JEDE Route - in einem
        #: Projekt mit rechenintensiven Seiten sind das viele Minuten. Der
        #: Praefix macht es alltagstauglich: „/hilfe/" prueft die Doku-Seiten
        #: in Sekunden, und genau dort stehen die grossen Tabellen.
        praefix = str(nur or '').strip()
        for route in alle_routen():
            if praefix and not route.weg.startswith(praefix):
                continue
            try:
                antwort = besucher.get(route.weg)
            except Exception:                                  # noqa: BLE001
                continue
            if getattr(antwort, 'status_code', 0) != 200:
                continue
            if 'html' not in str(antwort.headers.get('Content-Type') or '').lower():
                continue
            seiten += 1
            inhalt = antwort.content.decode('utf-8', 'replace')
            treffer = ZELLE.findall(inhalt)
            if not treffer:
                ohne_tabelle += 1
                continue
            for attribut, zelltext in treffer:
                zellen += 1
                was = Sortierwert(attribut, zelltext).befund()
                if not was:
                    continue
                # Die Meldung ohne den konkreten Wert ist der Buendelschluessel.
                art = was.split('„')[0]
                if (route.weg, art) in gesehen:
                    continue
                gesehen.add((route.weg, art))
                befunde.append(Befund(route.weg, was, '',
                                      Befund.WARNUNG if 'Einheit' in was
                                      or 'Dezimalpunkt' in was else Befund.HINWEIS))
        kopf = ['%d Seiten aufgerufen, %d davon ohne data-sort-Zelle'
                % (seiten, ohne_tabelle),
                '%d Zellen geprüft, %d Meldungen (je Seite und Art einmal)'
                % (zellen, len(befunde))]
        return Befundsatz(self.titel, kopf, befunde[:self.ZEILEN])
