# -*- coding: utf-8 -*-
u"""Aus einer Test-Kennung einen deutschen Satz machen.

DIE ANSAGE (Edgar, 26.08.2026)
==============================
    „verbessere meine testcases, so dass es die Gherkin BDD Anforderungen
     erfüllt, z. B. Wer kann es lesen: auch Nicht-Programmierer"

Das ist die eine Eigenschaft, die Gherkin wirklich voraus hatte. Eine
``.feature``-Datei liest jeder:

    Szenario: Eine ausgeblendete Person bleibt ausgeblendet

Auf ``/hilfe/tests/`` stand dagegen dies:

    AliasVerbundTest.test_falte_behaelt_reihenfolge_und_einzelne

Derselbe Satz — nur in Maschinenschrift. Unterstriche statt Leerzeichen,
``test_`` davor, ``ae`` statt ``ä``, und der Gegenstand steckt im
Klassennamen ohne Trennung.

WARUM DAS REICHT, UND KEINE ZWEITE DATEI NÖTIG IST
===================================================
Der Satz ist bereits da. Er steht nur in der Schreibweise, die Python für
Bezeichner verlangt. Eine ``.feature``-Datei daneben wäre eine ZWEITE
Fassung desselben Satzes — und zwei Fassungen laufen auseinander, sobald
jemand die eine ändert und die andere vergisst.

Hier wird stattdessen gelesen, was ohnehin dasteht:

    AliasVerbundTest.test_falte_behaelt_reihenfolge_und_einzelne
    -> „Alias-Verbund: Falte behält Reihenfolge und einzelne"

Damit gilt dieselbe Zusage wie bei Gherkin — lesbar ohne Code — ohne ein
zweites Rahmenwerk, einen zweiten Testläufer und eine zweite Liste.

WAS DER LESER NICHT SIEHT — UND WARUM DAS IN ORDNUNG IST
=========================================================
Gherkin trennt „Gegeben / Wenn / Dann". Diese drei Teile stehen hier im
Docstring der Prüfung, nicht im Namen. Der Name trägt das ERGEBNIS, und
das ist der Teil, den man beim roten Balken braucht: Was sollte stimmen
und stimmt jetzt nicht?
"""
from __future__ import annotations

import re

#: Wörter, die in Bezeichnern ohne Umlaut geschrieben werden müssen — beim
#: Anzeigen bekommen sie ihn zurück. Keine Regel „ae -> ä": die machte aus
#: ``Maerz`` ein ``März``, aber auch aus ``Aeon`` ein ``Äon``.
UMLAUTE = {
    'behaelt': 'behält', 'faellt': 'fällt', 'haelt': 'hält',
    'laeuft': 'läuft', 'laesst': 'lässt', 'traegt': 'trägt',
    'zaehlt': 'zählt', 'waechst': 'wächst', 'haengt': 'hängt',
    'faehrt': 'fährt', 'schlaegt': 'schlägt', 'traegen': 'trägen',
    'gezaehlt': 'gezählt', 'gefaehrlich': 'gefährlich',
    'aendert': 'ändert', 'geaendert': 'geändert', 'aendern': 'ändern',
    'erklaert': 'erklärt', 'waehrend': 'während', 'waehlt': 'wählt',
    'ausgewaehlt': 'ausgewählt', 'erhaelt': 'erhält', 'enthaelt': 'enthält',
    'naechste': 'nächste', 'naechsten': 'nächsten', 'spaeter': 'später',
    'haeufig': 'häufig', 'taeglich': 'täglich', 'saemtliche': 'sämtliche',
    'staendig': 'ständig', 'vollstaendig': 'vollständig',
    'unvollstaendig': 'unvollständig', 'zustaendig': 'zuständig',
    'verstaendlich': 'verständlich', 'auffaellt': 'auffällt',
    'auffaellig': 'auffällig', 'anhaengen': 'anhängen',
    'abhaengig': 'abhängig', 'unabhaengig': 'unabhängig',
    'ueber': 'über', 'ueberall': 'überall', 'uebernimmt': 'übernimmt',
    'uebernommen': 'übernommen', 'ueberholt': 'überholt',
    'ueberschreibt': 'überschreibt', 'uebersprungen': 'übersprungen',
    'ueberlebt': 'überlebt', 'uebergeben': 'übergeben',
    'uebrig': 'übrig', 'ueberlappend': 'überlappend',
    'fuer': 'für', 'fuehrt': 'führt', 'gefuehrt': 'geführt',
    'zusammenfuehren': 'zusammenführen', 'zusammengefuehrt': 'zusammengeführt',
    'auffuellt': 'auffüllt', 'erfuellt': 'erfüllt', 'fuellt': 'füllt',
    'zurueck': 'zurück', 'zurueckgibt': 'zurückgibt',
    'zurueckgesetzt': 'zurückgesetzt', 'zurueckbleibt': 'zurückbleibt',
    'grueн': 'grün', 'gruen': 'grün', 'gruene': 'grüne',
    'prueft': 'prüft', 'pruefung': 'Prüfung', 'geprueft': 'geprüft',
    'ungeprueft': 'ungeprüft', 'pruefen': 'prüfen',
    'stueck': 'Stück', 'stuecke': 'Stücke', 'stueckeln': 'stückeln',
    'muessen': 'müssen', 'muss': 'muss', 'duerfen': 'dürfen',
    'darf': 'darf', 'wuenscht': 'wünscht', 'genuegt': 'genügt',
    'unguenstig': 'ungünstig', 'guenstig': 'günstig', 'gueltig': 'gültig',
    'ungueltig': 'ungültig', 'buendel': 'Bündel', 'schluessel': 'Schlüssel',
    'luecke': 'Lücke', 'luecken': 'Lücken', 'lueckenlos': 'lückenlos',
    'stuende': 'stünde', 'koennen': 'können', 'koennte': 'könnte',
    'moeglich': 'möglich', 'unmoeglich': 'unmöglich',
    'geloescht': 'gelöscht', 'loescht': 'löscht', 'loeschen': 'löschen',
    'aufgeloest': 'aufgelöst', 'aufloesung': 'Auflösung',
    'oeffnet': 'öffnet', 'geoeffnet': 'geöffnet', 'gehoert': 'gehört',
    'groesse': 'Größe', 'groesser': 'größer', 'groesste': 'größte',
    'gross': 'groß', 'grosse': 'große', 'grossen': 'großen',
    'heisst': 'heißt', 'weiss': 'weiß', 'schliesst': 'schließt',
    'ausser': 'außer', 'ausserhalb': 'außerhalb', 'draussen': 'draußen',
    'noetig': 'nötig', 'roentgen': 'Röntgen',
    'entitaet': 'Entität', 'qualitaet': 'Qualität',
    'komplexitaet': 'Komplexität', 'aktivitaet': 'Aktivität',
    'faelle': 'Fälle', 'aehnlich': 'ähnlich', 'naehe': 'Nähe',
    'waere': 'wäre', 'haette': 'hätte', 'gaebe': 'gäbe',
    'zaehler': 'Zähler', 'raenge': 'Ränge', 'saetze': 'Sätze',
    'eintraege': 'Einträge', 'auftraege': 'Aufträge',
    'vorschlaege': 'Vorschläge', 'anlaesse': 'Anlässe',
    'blaetter': 'Blätter', 'laender': 'Länder', 'raeume': 'Räume',
    'kaesten': 'Kästen', 'flaechen': 'Flächen', 'schluesseln': 'Schlüsseln',
    'zaehlbar': 'zählbar', 'erzaehlt': 'erzählt',
    'aufraeumen': 'aufräumen', 'aufgeraeumt': 'aufgeräumt',
    'ergaenzt': 'ergänzt', 'verlaesst': 'verlässt',
    'gefaedelt': 'gefädelt', 'gefaedelte': 'gefädelte',
    'zurueckgesetzt': 'zurückgesetzt', 'nachtraeglich': 'nachträglich',
    # Aus der echten Tests-Seite nachgetragen (26.08.2026). Bewusst NICHT
    # dabei: `quelle`, `dauer`, `neue`, `neuer`, `aktuell`, `zuerst`,
    # `sequenzen`, `values`, `query`, `true`, `does`, `enqueue` — die
    # tragen ihr ue/ae zu Recht.
    'rueckfall': 'Rückfall', 'rueckweg': 'Rückweg', 'menue': 'Menü',
    'bruecke': 'Brücke', 'bloecke': 'Blöcke', 'unberuehrt': 'unberührt',
    'kuerzel': 'Kürzel', 'zurueckspulen': 'zurückspulen',
    'fuellbilder': 'Füllbilder', 'rueckblick': 'Rückblick',
    'ueberhaupt': 'überhaupt', 'aufloesen': 'auflösen',
    'schluesselwort': 'Schlüsselwort', 'zurueckblicken': 'zurückblicken',
    'rueckstand': 'Rückstand', 'waechter': 'Wächter', 'fuenf': 'fünf',
    'empfaenger': 'Empfänger', 'bestaetigen': 'bestätigen',
    'uebergaenge': 'Übergänge', 'erklaeren': 'erklären',
    'erklaertes': 'erklärtes', 'verstaerkt': 'verstärkt',
    'fuehrende': 'führende', 'fuehrend': 'führend', 'fuehren': 'führen',
    'raeumt': 'räumt', 'ausdruecklich': 'ausdrücklich',
    'faengt': 'fängt', 'geraeteliste': 'Geräteliste',
    'laeufer': 'Läufer', 'hauptaufloesung': 'Hauptauflösung',
    'verfuegbarkeit': 'Verfügbarkeit', 'uebergangen': 'übergangen',
    'loesen': 'lösen', 'juengsten': 'jüngsten', 'guete': 'Güte',
    'stoeren': 'stören', 'verknuepft': 'verknüpft',
    'vertraegt': 'verträgt', 'uistoerung': 'UI-Störung',
    'uebrigen': 'übrigen', 'zurueckholen': 'zurückholen',
    'zusammenfuehrung': 'Zusammenführung', 'noetigen': 'nötigen',
    'aelter': 'älter', 'hoehe': 'Höhe', 'ende': 'Ende',
    'uebergebene': 'übergebene', 'uebergebenen': 'übergebenen',
    'zuordnung': 'Zuordnung',
}

#: Wortanfaenge, die im Klassennamen keine eigene Trennung verdienen —
#: sonst wird aus ``JsBefunde`` ein „Js Befunde".
ZUSAMMEN = ('Js', 'Ui', 'Roi', 'Api', 'Db', 'Ki')

#: KLEIN GESCHRIEBEN, auch wenn sie im Bezeichner groß stehen.
#:
#: Nur die geschlossene Klasse der Füllwörter — Hauptwörter und Verben
#: bleiben, wie sie dastehen. Bei einem unbekannten Wort lieber groß
#: lassen: Ein falsch großes Hauptwort stört weniger als ein falsch
#: kleines.
KLEIN = {
    'und', 'oder', 'aber', 'sondern', 'denn',
    'der', 'die', 'das', 'den', 'dem', 'des',
    'ein', 'eine', 'einer', 'einen', 'einem', 'eines',
    'kein', 'keine', 'keinen', 'keiner',
    'in', 'im', 'an', 'am', 'auf', 'aus', 'bei', 'beim', 'mit', 'nach',
    'seit', 'von', 'vom', 'zu', 'zum', 'zur', 'ueber', 'über', 'unter',
    'vor', 'hinter', 'neben', 'zwischen', 'ohne', 'gegen', 'fuer', 'für',
    'durch', 'um', 'als', 'wie', 'wenn', 'dann', 'weil', 'dass', 'ob',
    'nicht', 'nur', 'auch', 'noch', 'schon', 'sehr', 'mehr', 'immer',
    'ist', 'sind', 'war', 'waren', 'wird', 'werden', 'wurde', 'hat',
    'haben', 'kann', 'koennen', 'können', 'muss', 'muessen', 'müssen',
    'darf', 'duerfen', 'dürfen', 'soll', 'sollen', 'bleibt', 'bleiben',
    'steht', 'stehen', 'laeuft', 'läuft', 'laufen', 'geht', 'gehen',
    'kommt', 'kommen', 'macht', 'machen', 'gibt', 'geben',
    'meldet', 'melden', 'traegt', 'trägt', 'zaehlt', 'zählt',
    'sie', 'er', 'es', 'ihn', 'ihm', 'ihr', 'sich', 'selbst',
    'voll', 'leer', 'ganz', 'halb', 'gleich', 'anders',
}

_LEERE = re.compile(r'\s+')


class Testsatz:
    u"""EINE Test-Kennung, gelesen als Satz.

        >>> Testsatz('app.tests.unit.test_a.AliasVerbundTest'
        ...          '.test_falte_behaelt_reihenfolge').satz()
        'Alias-Verbund: Falte behält Reihenfolge'
    """

    #: Was am Anfang einer Prüfmethode wegfällt.
    VORSATZ = 'test_'

    #: Was am Ende eines Klassennamens wegfällt — es sagt nichts über den
    #: Gegenstand, nur dass es eine Prüfung ist.
    NACHSATZ = ('Tests', 'Test', 'TestCase', 'Case')

    def __init__(self, kennung):
        self.kennung = str(kennung or '')
        teile = self.kennung.split('.')
        self.methode = teile[-1] if teile else ''
        self.klasse = teile[-2] if len(teile) >= 2 else ''

    # ── Der Satz ────────────────────────────────────────────────

    def satz(self):
        u"""``'Gegenstand: das erwartete Ergebnis'`` — oder nur eines davon."""
        links = self.gegenstand()
        rechts = self.ergebnis()
        if links and rechts:
            return '%s: %s' % (links, rechts)
        return rechts or links or self.kennung

    def gegenstand(self):
        u"""Der Klassenname als Wortfolge: ``AliasVerbundTest`` -> ``Alias-Verbund``."""
        name = self.klasse
        for nach in self.NACHSATZ:
            if name.endswith(nach) and len(name) > len(nach):
                name = name[:-len(nach)]
                break
        if not name:
            return ''
        woerter = [self._umlaut(w) for w in self._trennen(name)]
        return ' '.join(self._klein(w, i) for i, w in enumerate(woerter))

    def ergebnis(self):
        u"""Der Methodenname als Satz: ``test_falte_behaelt_x`` -> ``Falte behält x``."""
        name = self.methode
        if name.startswith(self.VORSATZ):
            name = name[len(self.VORSATZ):]
        if not name:
            return ''
        woerter = [self._umlaut(w) for w in name.split('_') if w]
        if not woerter:
            return ''
        satz = ' '.join(woerter)
        return _LEERE.sub(' ', satz[:1].upper() + satz[1:]).strip()

    # ── Kleinteile ──────────────────────────────────────────────

    @classmethod
    def _trennen(cls, name):
        u"""``AliasVerbund`` -> ``['Alias', 'Verbund']``, ``JsBefunde`` -> eines."""
        roh = re.findall(r'[A-Z][a-z0-9]*|[a-z0-9]+', name)
        aus = []
        for wort in roh:
            if aus and aus[-1] in ZUSAMMEN:
                aus[-1] = aus[-1] + wort
            else:
                aus.append(wort)
        return aus

    @staticmethod
    def _klein(wort, stelle):
        u"""Füllwörter klein — aber nie das erste Wort eines Satzes.

        In ``KameraUndPerson`` steht jedes Wort groß, weil CamelCase es
        verlangt, nicht weil es ein Hauptwort wäre. Ohne diesen Schritt
        liest sich der Satz wie ein englischer Titel: „Kamera Und Person".
        """
        if stelle and wort.lower() in KLEIN:
            return wort.lower()
        return wort

    @staticmethod
    def _umlaut(wort):
        u"""``behaelt`` -> ``behält``. Nur bekannte Wörter, nie eine Regel."""
        klein = wort.lower()
        if klein not in UMLAUTE:
            return wort
        richtig = UMLAUTE[klein]
        # Grossschreibung des Ausgangsworts beibehalten.
        if wort[:1].isupper():
            return richtig[:1].upper() + richtig[1:]
        return richtig
