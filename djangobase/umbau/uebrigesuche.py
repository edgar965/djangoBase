# -*- coding: utf-8 -*-
u"""Die Dateien EINER Endung aus der Zeile „Übrige" finden — und löschen.

DIE ANSAGE (Edgar, 02.09.2026)
==============================
    „mach mir in der Tabelle bei Statistik, in der Tabelle bei „Übrige"
     einen Button Löschen mit dem ich die die Dinger lösche"

Der Statistik-Reiter schlüsselt „Übrige" seit demselben Tag nach Endung
auf. Was dort steht, ist fast immer Müll, der sich im Projektbaum
angesammelt hat: ein Chrome-Profil unter `var/`, 137 Datenbank-Dumps aus
abgebrochenen Testläufen, eine Virenquarantäne. Von dort aus löschen zu
können, spart den Weg über den Explorer.

WARUM DAS HIER SO VORSICHTIG AUSSIEHT
=====================================
Es löscht echte Dateien, endgültig. Vier Dinge schützen:

1. **Aus dem Browser kommt nie ein Pfad**, nur eine Endung. Ein Pfad im
   Formular wäre ein Weg, jede Datei der Platte zu treffen.
2. **Die Liste wird beim Löschen frisch erhoben**, nicht aus der Ablage
   gelesen. Eine Ablage kann Minuten alt sein; in der Zeit entsteht und
   verschwindet einiges.
3. **Jeder einzelne Pfad wird unmittelbar vor dem Löschen erneut geprüft**
   — innerhalb der Wurzel, eine echte Datei, kein Verweis, die richtige
   Endung, und die Art ist „Übrige". Das ist die Lehre aus
   `rekursiv-loeschen`: Annahmen von vor fünf Minuten gelten nicht mehr.
4. **Dieselben Ausschlüsse wie die Zählung.** Was in `media/`, `logs/`
   oder einer angemeldeten Ablage liegt, taucht gar nicht erst auf — und
   ist damit auch nicht löschbar.

Verzeichnisse fasst diese Klasse nicht an, auch keine leeren.
"""
import logging
import os
from pathlib import Path

# ALS `groesse_text`, NICHT `groesse` (02.09.2026): In `loeschen` heisst
# die Dateigroesse naheliegend `groesse` — und beschattete den Filter, bis
# der erste echte Lauf mit "'int' object is not callable" abbrach. Die
# Dateien waren da schon geloescht; nur die Antwort fehlte.
from ..templatetags.zahlen import groesse as groesse_text
from .codezahlen import (GROESSTE_QUELLDATEI, UEBRIGE, Codezahlen, ablagen)
from .klassenmodell import ausser

logger = logging.getLogger(__name__)

#: Höchstens so viele Pfade zurückgeben. Die Vorschau soll zeigen, worum
#: es geht, nicht 40.000 Zeilen in den Browser schieben.
VORSCHAU = 200

#: WAS NIE ZUM LÖSCHEN ANGEBOTEN WIRD (02.09.2026)
#: ================================================
#: Am Tag des Baus hat dieses Werkzeug echten Schaden angerichtet: 10
#: `.xlsm` (3,74 MB), 6 `.xlsx` (723 kB) und 2 `.otf` sind gelöscht
#: worden — darunter die Collmex-Ausfuhren der Steuer-App. Sie standen in
#: „Übrige", weil die Zählung sie nicht als Quelltext kennt. „Kein
#: Quelltext" heisst aber nicht „Müll": Eine Tabelle, ein Vertrag, eine
#: Schrift sind Arbeit, die niemand wegwirft.
#:
#: Diese Endungen bleiben deshalb sichtbar in der Statistik, bekommen
#: aber keinen Löschen-Knopf — und werden serverseitig abgewiesen, auch
#: wenn jemand sie von Hand schickt.
GESCHUETZT = frozenset((
    # Bürodokumente
    '.xlsx', '.xlsm', '.xls', '.xlsb', '.docx', '.doc', '.docm',
    '.pptx', '.ppt', '.odt', '.ods', '.odp', '.rtf', '.pages',
    '.numbers', '.epub',
    # Daten, die jemand von Hand gepflegt haben kann
    '.csv', '.tsv', '.sqlite', '.sqlite3', '.db', '.mdb', '.accdb',
    '.eml', '.msg', '.pst', '.ost', '.vcf', '.ics',
    # Schriften und Medien, die nicht unter „Bilder & Binäres" fallen
    '.otf', '.fon', '.wav', '.mp3', '.flac', '.aac', '.mov', '.avi',
    '.mkv', '.psd', '.ai', '.indd', '.svgz',
    # Ausführbares und Schlüssel
    '.ps1', '.psm1', '.bat', '.cmd', '.sh', '.bash', '.sql', '.ipynb',
    '.key', '.pem', '.crt', '.cer', '.pfx', '.p12', '.env',
    # Protokolle. In `assistant` liegt darin die Mail-Audit-Spur — jede
    # mutative Aktion, absichtlich getrennt geführt. Am 02.09.2026 sind
    # 43 solche Dateien (3,45 MB) über dieses Werkzeug verschwunden.
    # Protokolle räumt man in der Log-Verwaltung auf, nicht in einer
    # Statistik.
    '.log', '.log1', '.audit', '.jsonl', '.ndjson',
))


def geschuetzt(endung):
    u"""Ist diese Endung vor dem Löschen geschützt?"""
    return (endung or '').lower() in GESCHUETZT


class UebrigeSuche:
    u"""Findet und löscht die „Übrigen" einer Endung unterhalb einer Wurzel."""

    def __init__(self, wurzel):
        self.wurzel = Path(wurzel).resolve()

    # ── finden ──────────────────────────────────────────────────
    def finden(self, endung):
        u"""Alle Dateien dieser Endung, die in „Übrige" fallen.

        ``endung`` ist ``'.log'`` oder ``''`` für die ohne Endung — genau
        die Werte, die ``Codezahlen.uebrige_arten()`` ausweist.
        """
        return self.sammeln([endung]).get((endung or '').lower(), [])

    def sammeln(self, endungen):
        u"""``{endung: [Pfade]}`` für mehrere Endungen in EINEM Durchgang.

        EIN DURCHGANG, NICHT N (02.09.2026, auf Ansage „mach auch Multi
        Auswahl (check boxen) und batch delete"). Wer fünf Endungen
        anklickt, soll nicht fünfmal warten.

        WARUM ``os.walk`` UND NICHT ``rglob`` — GEMESSEN
        ===============================================
        Der erste Entwurf lief mit ``wurzel.rglob('*')`` und brauchte auf
        `assistant` **16,5 Sekunden**; der Knopf schien nichts zu tun
        (genau die Meldung, die dazu führte). Der Grund: ``rglob`` steigt
        in JEDES Verzeichnis hinab und verwirft die Dateien einzeln — auch
        die 72.459 `.eml` im Mail-Archiv, die von vornherein ausgeschlossen
        sind.

        ``os.walk`` erlaubt, die Liste der Unterverzeichnisse an Ort und
        Stelle zu kürzen (``ordner[:] = …``). Ein ausgeschlossener Baum
        wird dann gar nicht erst betreten. Gemessen im selben Lauf:

            rglob, nur durchlaufen                2,6 s   236.627 Einträge
            rglob + is_file() je Eintrag          5,8 s   216.909 Dateien
            os.walk mit Beschneidung              0,1 s     4.416 Dateien
            finden() alte Fassung                16,5 s

        Das ist derselbe Bestand, nur ohne die Bäume, die ohnehin nicht
        zählen — **165× schneller**, nicht durch einen Trick, sondern weil
        die Arbeit gar nicht anfällt.
        """
        # Geschützte Arten kommen gar nicht erst in die Suche — dann kann
        # auch kein Aufrufer sie versehentlich weiterreichen.
        gesucht = set((e or '').lower() for e in endungen
                      if not geschuetzt(e))
        if not gesucht:
            return {}
        raus = ausser()
        anmeldungen = ablagen(self.wurzel)
        daten = Codezahlen.DATEN
        treffer = dict((e, []) for e in gesucht)
        for ordner_pfad, unter, dateien in os.walk(self.wurzel):
            teile = self._teile(ordner_pfad)
            if teile is None:
                unter[:] = []
                continue
            # HIER wird gespart: Was ausgeschlossen ist, wird nicht betreten.
            unter[:] = [o for o in unter
                        if not self._auslassen(teile, o, daten, raus,
                                               anmeldungen)]
            for name in dateien:
                endung = self._endung(name)
                if endung not in gesucht:
                    continue
                if Codezahlen.art(name) != UEBRIGE:
                    continue
                # PUNKTDATEIEN SIND KONFIGURATION, KEIN MÜLL (02.09.2026):
                # `.gitignore` zählt als „ohne Endung" und wurde mit 385
                # Chrome-Cache-Dateien zusammen gelöscht. Ohne sie sah Git
                # plötzlich 528 offene Änderungen statt 57 — der Schaden
                # war stiller als der Verlust selbst. Dasselbe gilt für
                # `.env`, `.dockerignore`, `.editorconfig`.
                if name.startswith('.'):
                    continue
                pfad = Path(ordner_pfad) / name
                try:
                    if pfad.stat().st_size > GROESSTE_QUELLDATEI:
                        continue
                except OSError:
                    continue
                treffer[endung].append(pfad)
        return treffer

    def _teile(self, ordner_pfad):
        u"""Die Pfadteile innerhalb der Wurzel — oder ``None`` bei ausserhalb."""
        try:
            return Path(ordner_pfad).relative_to(self.wurzel).parts
        except ValueError:
            return None

    @staticmethod
    def _auslassen(teile, name, daten, raus, anmeldungen):
        u"""Ist dieses Unterverzeichnis ausgeschlossen?"""
        if name.lower() in daten or name in raus:
            return True
        voll = teile + (name, )
        return any(voll[:len(a)] == a for a in anmeldungen)

    @staticmethod
    def _endung(dateiname):
        u"""``'.log'`` oder ``''`` — dieselbe Regel wie ``Codezahlen.art``."""
        punkt = dateiname.rfind('.')
        return dateiname[punkt:].lower() if punkt > 0 else ''

    def vorschau(self, endung, treffer=None):
        u"""``{anzahl, bytes, groesse, pfade, gekuerzt}`` — was ein Löschen
        träfe.

        ``groesse`` ist der fertige Text mit passender Einheit. Eine
        Rückfrage „5 Dateien (0.0 MB) löschen?" sagt über die Menge
        nichts — dieselbe Beobachtung wie in der Tabelle (Edgar,
        02.09.2026: „anstelle 0,00 MB, dann in kB angeben").
        """
        if treffer is None:
            treffer = self.finden(endung)
        gesamt = 0
        for pfad in treffer:
            try:
                gesamt += pfad.stat().st_size
            except OSError:
                pass
        gezeigt = treffer[:VORSCHAU]
        return {
            'endung': endung or u'(ohne Endung)',
            'anzahl': len(treffer),
            'bytes': gesamt,
            'groesse': groesse_text(gesamt),
            'pfade': [str(p.relative_to(self.wurzel)) for p in gezeigt],
            'gekuerzt': max(0, len(treffer) - len(gezeigt)),
        }

    def vorschau_mehrere(self, endungen):
        u"""Vorschau über mehrere Endungen — ein Durchgang, eine Summe.

        Für die Mehrfachauswahl (Edgar, 02.09.2026). Die Rückfrage nennt
        die Gesamtmenge und je Endung eine Zeile; ohne die Aufteilung
        stünde dort „612 Dateien" und niemand wüsste, welche.
        """
        gefunden = self.sammeln(endungen)
        teile = [self.vorschau(e, treffer=p) for e, p in gefunden.items()]
        teile.sort(key=lambda t: -t['anzahl'])
        bytes_gesamt = sum(t['bytes'] for t in teile)
        return {
            'anzahl': sum(t['anzahl'] for t in teile),
            'bytes': bytes_gesamt,
            'groesse': groesse_text(bytes_gesamt),
            'arten': [{'endung': t['endung'], 'anzahl': t['anzahl'],
                       'groesse': t['groesse']} for t in teile if t['anzahl']],
            'pfade': [p for t in teile for p in t['pfade']][:VORSCHAU],
        }

    # ── löschen ─────────────────────────────────────────────────
    def loeschen_mehrere(self, endungen):
        u"""Mehrere Endungen löschen — ein Durchgang, ein Bericht."""
        gefunden = self.sammeln(endungen)
        gesamt = {'geloescht': 0, 'uebersprungen': 0, 'bytes': 0,
                  'gruende': {}, 'je_endung': []}
        for endung, pfade in sorted(gefunden.items(),
                                    key=lambda p: -len(p[1])):
            if not pfade:
                continue
            b = self.loeschen(endung, treffer=pfade)
            gesamt['geloescht'] += b['geloescht']
            gesamt['uebersprungen'] += b['uebersprungen']
            gesamt['bytes'] += b['bytes']
            for grund, n in b['gruende'].items():
                gesamt['gruende'][grund] = gesamt['gruende'].get(grund, 0) + n
            gesamt['je_endung'].append({'endung': b['endung'],
                                        'geloescht': b['geloescht'],
                                        'groesse': b['groesse']})
        gesamt['groesse'] = groesse_text(gesamt['bytes'])
        return gesamt

    def loeschen(self, endung, treffer=None):
        u"""Löscht sie — jede einzeln, jede nochmals geprüft.

        Zurück kommt ``{geloescht, uebersprungen, bytes, groesse, gruende}``.
        Ein gescheitertes Löschen bricht den Lauf NICHT ab: Eine gesperrte
        Datei ist der Normalfall (ein laufender Prozess hält sie), und der
        Rest soll trotzdem weg. Der Grund steht in der Antwort, nicht nur
        im Log.

        ``treffer`` darf eine bereits erhobene Liste sein — der Aufrufer
        hat sie für die Mengenkontrolle ohnehin gebraucht, und ein zweiter
        Durchgang über den Baum kostet auf `assistant` 20 Sekunden. Das ist
        keine Abkürzung an der Sicherheit vorbei: Der eigentliche Schutz
        ist ``_pruefen`` unmittelbar vor jedem einzelnen ``unlink``.
        """
        bericht = {'endung': endung or u'(ohne Endung)', 'geloescht': 0,
                   'uebersprungen': 0, 'bytes': 0, 'gruende': {}}
        if treffer is None:
            treffer = self.finden(endung)
        for pfad in treffer:
            grund = self._pruefen(pfad, endung)
            if grund:
                bericht['uebersprungen'] += 1
                bericht['gruende'][grund] = bericht['gruende'].get(grund, 0) + 1
                continue
            try:
                groesse = pfad.stat().st_size
                pfad.unlink()
                bericht['geloescht'] += 1
                bericht['bytes'] += groesse
            except OSError as fehler:
                bericht['uebersprungen'] += 1
                grund = type(fehler).__name__
                bericht['gruende'][grund] = bericht['gruende'].get(grund, 0) + 1
        bericht['groesse'] = groesse_text(bericht['bytes'])
        logger.warning(
            u'Statistik → Übrige: %d Dateien „%s" gelöscht (%s), '
            u'%d übersprungen%s', bericht['geloescht'], bericht['endung'],
            bericht['groesse'], bericht['uebersprungen'],
            (u' — ' + u', '.join('%s: %d' % (g, n)
                                 for g, n in bericht['gruende'].items()))
            if bericht['gruende'] else u'')
        return bericht

    def _pruefen(self, pfad, endung):
        u"""Der letzte Blick VOR dem Löschen. Gibt einen Grund oder ``None``.

        ``finden`` hat all das schon geprüft — hier steht es ein zweites
        Mal, weil zwischen Finden und Löschen Zeit vergeht und weil eine
        Löschroutine sich nicht darauf verlassen darf, dass ihr Aufrufer
        sauber gearbeitet hat.
        """
        if geschuetzt(endung):
            return u'geschützte Dateiart'
        if pfad.name.startswith('.'):
            return u'Konfigurationsdatei'
        try:
            echt = pfad.resolve()
        except OSError:
            return u'nicht auflösbar'
        try:
            echt.relative_to(self.wurzel)
        except ValueError:
            return u'ausserhalb des Projekts'
        if pfad.is_symlink():
            return u'Verweis'
        if not pfad.is_file():
            return u'kein einfaches Objekt'
        if self._endung(pfad.name) != (endung or '').lower():
            return u'andere Endung'
        if Codezahlen.art(pfad.name) != UEBRIGE:
            return u'bekannte Dateiart'
        return None


__all__ = ['UebrigeSuche', 'VORSCHAU']
