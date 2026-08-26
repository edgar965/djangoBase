# -*- coding: utf-8 -*-
u"""Bereiche - die ZWEITE Einteilung der Tests, quer zur Kategorie.

    „einmal Kategorien (unit, usw.), einmal Bereich (wie Chat usw.) […] Eine
    Tabelle je Kategorie, aber der Bereich ist nochmal extra markiert in der
    Tabelle" · „die bereiche gibt jedes Projekt das von djangoBase ableitet, an"
    (Edgar, 17.08.2026)

ZWEI EINTEILUNGEN
=================
    Kategorie   WIE getestet wird - unit, component, ui, longrunner, …
                Sie steckt im Ordner (``app/tests/<art>/``) und ist deshalb
                verschiebbar (siehe :mod:`.testverschieben`).
    Bereich     WAS getestet wird - Chat, Mail, Musik, Virenscanner, …
                Die Sache, um die es geht. Sie wandert nicht mit einem Klick.

Beide zugleich: EINE Tabelle je Kategorie, darin der Bereich als eigene Spalte
und die Zeilen nach Bereich vorsortiert. Nicht mehrere getrennte Tabellen — die
haetten je eigene Sortierung, eigene Spaltenbreiten und eine eigene Auswahl, und
man koennte nicht mehr „alle Component" in einem Rutsch anhaken.

WOHER DIE BEREICHE KOMMEN
=========================
Vom PROJEKT. djangoBase kennt die Themen eines fremden Projekts nicht — es sieht
nur Modulpfade::

    DJANGOBASE = {"test_bereiche": [
        {"slug": "musik", "name": "Musik",   "praefixe": ["search.tests.musik"]},
        {"slug": "mail",  "name": "Mail",    "praefixe": ["mail.tests"]},
        {"slug": "kalender", "name": "Kalender", "praefixe": ["schedule.tests"]},
    ]}

Kurzform ``{"slug": "Anzeigename"}`` geht auch; dann wird der Slug wie unten
abgeleitet und hier nur umbenannt.

OHNE ANGABE
===========
Faellt es auf den Ordner zurueck: ``app/tests/<bereich>/<art>/`` -> der Ordner,
sonst die App. Damit steht in jedem Konsumenten etwas Brauchbares in der Spalte,
auch bevor jemand die Einstellungen anfasst — nur eben mit Ordnernamen statt mit
den Namen, die das Projekt selbst benutzt.
"""
from .testbefehle import Testbefehle

__all__ = ["Bereiche"]


class Bereiche:
    """Ordnet Test-IDs einem Bereich zu - nach Projekt-Angabe oder Ordner."""

    ARTEN = set(Testbefehle.ARTEN)
    #: Ohne erkennbaren Bereich - eine eigene Gruppe, damit nichts unter den
    #: Tisch faellt.
    REST = ("~rest", "Sonstige")

    def __init__(self, angabe=None):
        #: [(praefix, slug, name)] - laengstes Praefix zuerst (s. `slug_von`).
        self.regeln = []
        #: {"slug": "Anzeigename"} - Umbenennung ohne eigene Zuordnung.
        self.namen = {}
        #: {"slug": Platz} - die REIHENFOLGE der Angabe. „auch die reihenfolge
        #: ist änderbar" (17.08.2026): Wer die Zeilen in den Einstellungen
        #: umsortiert, sortiert damit die Tabelle. Nicht angegebene Bereiche
        #: kommen danach, alphabetisch.
        self.reihung = {}
        #: {"slug": "erstes praefix"} - Ziel beim Bereichswechsel.
        self.praefixe = {}
        #: Die Angabe des Projekts, unveraendert weitergereicht (Slug, Name,
        #: Beschreibung, Praefixe). Projektseiten bauen daraus ihre Navigation,
        #: statt die Liste ein zweites Mal zu fuehren.
        self.angaben = []
        #: Ergebnis von :meth:`ziele` - siehe dort.
        self._ziele = None
        self._lesen(angabe)

    def _lesen(self, angabe):
        if isinstance(angabe, str):
            angabe = angabe.splitlines()
        if isinstance(angabe, dict):
            self.namen = {str(k): str(v) for k, v in angabe.items()}
            self.reihung = {k: i for i, k in enumerate(self.namen)}
            return
        for e in (angabe or []):
            if isinstance(e, str):
                e = self.zeile_lesen(e)
            if not isinstance(e, dict):
                continue
            slug = str(e.get("slug") or "").strip()
            if not slug:
                continue
            name = str(e.get("name") or slug)
            self.namen[slug] = name
            self.reihung.setdefault(slug, len(self.reihung))
            self.angaben.append({"slug": slug, "name": name,
                                 "beschreibung": str(e.get("beschreibung")
                                                     or e.get("description") or ""),
                                 "praefixe": [], "index": self.reihung[slug]})
            praefixe = e.get("praefixe") or e.get("module_prefix") or []
            if isinstance(praefixe, str):
                praefixe = [praefixe]
            for p in praefixe:
                p = str(p).strip(".")
                if not p:
                    continue
                self.regeln.append((p, slug, name))
                self.praefixe.setdefault(slug, p)
                self.angaben[-1]["praefixe"].append(p)
        # Laengstes Praefix gewinnt: „search.tests.musik" schlaegt „search.tests".
        self.regeln.sort(key=lambda r: len(r[0]), reverse=True)

    @staticmethod
    def zeile_lesen(zeile):
        u"""``musik | Musik | search.tests.musik, x.y`` -> Angabe-Dictionary.

        Das ist das Format der Einstellungen-Seite (Feldtyp ``zeilen``): eine
        Zeile je Bereich, Felder mit ``|`` getrennt, Praefixe mit Komma. Kein
        JSON — die Liste soll sich im Betrieb tippen lassen, ohne dass eine
        vergessene Klammer die Seite kostet.

        Fehlt der Anzeigename, wird der Slug genommen; fehlen die Praefixe,
        gilt der Slug als Praefix-Anfang nicht — der Bereich benennt dann nur
        um (dieselbe Wirkung wie die Kurzform als Dictionary).
        """
        teile = [t.strip() for t in str(zeile).split("|")]
        if not teile or not teile[0] or teile[0].startswith("#"):
            return {}
        # Dictionary gewollt: dasselbe Eingabeformat wie in den Settings.
        return {"slug": teile[0],
                "name": teile[1] if len(teile) > 1 and teile[1] else teile[0],
                "praefixe": [p.strip() for p in (teile[2] if len(teile) > 2
                                                 else "").split(",") if p.strip()],
                # Viertes Feld: die Beschreibung, die eine Projektseite ueber
                # ihrer Liste zeigt. djangoBase braucht sie nicht, reicht sie
                # aber durch — sonst muesste das Projekt seine Bereiche ein
                # zweites Mal fuehren, nur wegen eines Satzes Text.
                "beschreibung": teile[3] if len(teile) > 3 else ""}

    @classmethod
    def als_zeilen(cls, angabe):
        u"""Angabe -> Zeilenformat der Oberflaeche (Umkehrung von `zeile_lesen`).

        Ohne sie stuenden im Formular die Python-Dictionaries aus
        ``settings.py`` („{'slug': 'mail', …}") — und wer dort auf Speichern
        drueckt, haette danach einen Bereich namens „{'slug': 'mail'".
        """
        if isinstance(angabe, str):
            return angabe.splitlines()
        aus = []
        for e in cls(angabe).liste():
            aus.append(" | ".join([e["slug"], e["name"],
                                   ", ".join(e["praefixe"]), e["beschreibung"]]
                                  ).rstrip(" |"))
        return aus

    @classmethod
    def aus_einstellungen(cls):
        u"""Angabe aus ``DJANGOBASE["test_bereiche"]`` bzw. den Einstellungen.

        Beide Wege enden hier: ``conf()`` legt die in der Oberflaeche
        gespeicherten Werte ueber die aus ``settings.py``. Ein Projekt kann die
        Bereiche also im Code mitliefern UND sie im Betrieb aendern, ohne dass
        es zwei Quellen gibt.
        """
        from .conf import conf
        return cls(conf().get("test_bereiche"))

    # ----------------------------------------------------------- Ableitung

    def slug_von(self, test_id):
        u"""Bereichs-Slug einer Test-ID - ``""`` wenn keiner ableitbar."""
        kennung = str(test_id or "")
        for praefix, slug, _name in self.regeln:
            if kennung == praefix or kennung.startswith(praefix + "."):
                return slug
        return self._aus_ordner(kennung)

    def _aus_ordner(self, kennung):
        u"""Rueckfall ohne Projekt-Angabe: der Ordner unter ``tests``.

        Gelesen wird der Modulpfad, nicht die Platte: Die Seite baut damit
        hunderte Zeilen, ein Dateisystem-Zugriff je Zeile waere spuerbar.
        """
        teile = [t for t in kennung.split(".") if t]
        if len(teile) < 2 or "tests" not in teile:
            return ""
        i = teile.index("tests")
        if i == 0:                       # „tests.unit.…" - keine App davor
            return ""
        naechstes = teile[i + 1] if len(teile) > i + 1 else ""
        # app/tests/<bereich>/<art>/ -> der Ordner ist der Bereich.
        # app/tests/<art>/          -> die App ist der Bereich.
        if naechstes and naechstes not in self.ARTEN:
            return naechstes
        return teile[i - 1]

    def name_von(self, slug):
        if not slug:
            return self.REST[1]
        if slug in self.namen:
            return self.namen[slug]
        return slug[:1].upper() + slug[1:]

    def zu(self, test_id):
        """``(slug, name)`` eines Falls - für die Spalte „Bereich"."""
        slug = self.slug_von(test_id)
        return (slug or self.REST[0]), self.name_von(slug)

    def liste(self):
        u"""Die Bereiche in der ANGEGEBENEN Reihenfolge - für Navigationen."""
        return list(self.angaben)

    def mit_ordner(self):
        """Gibt es ueberhaupt waehlbare Zielbereiche?"""
        return bool(self.ziele())

    def praefix_von(self, slug):
        """Das Modulpraefix eines Bereichs - Ziel beim Wechseln."""
        return self.praefixe.get(str(slug or ""), "")

    def ziele(self):
        u"""Die Bereiche, in die verschoben werden DARF (gecacht).

        Ausgeschlossen sind Bereiche, deren Praefix ueber anderen liegt:
        ``search.tests`` ist der Elternordner von ``search.tests.chat``,
        ``search.tests.musik`` und allen weiteren. Als Ziel gewaehlt, landet
        die Datei in ``search/tests/<art>/`` — eine Ebene, die es in der
        Hausordnung nicht gibt, und der Fall verschwindet aus seinem Bereich.

        GENAU DAS IST PASSIERT (17.08.2026): Ein Klick auf „Suche (allgemein)"
        hat die Chat-Platzhalterdatei nach ``search/tests/unit/`` gelegt.
        Aufgefallen ist es nur, weil im selben Aufruf ein Fehler folgte —
        sonst waere die Datei still an einem Ort gelandet, an dem sie niemand
        sucht. Solche Bereiche bleiben ANZEIGBAR, sind aber nicht waehlbar.
        """
        # EINMAL rechnen: Die Menge haengt nur an der Angabe, wird aber je
        # Tabellenzeile gebraucht. Gemessen am 18.08.2026: 2.612 Aufrufe und
        # 592.924 Vergleiche je Seitenaufbau — 0,76 s für ein Ergebnis, das
        # sich nie ändert.
        if self._ziele is None:
            aus = {}
            for slug, praefix in self.praefixe.items():
                if any(p != praefix and p.startswith(praefix + ".")
                       for p in self.praefixe.values()):
                    continue
                aus[slug] = praefix
            self._ziele = aus
        return self._ziele

    def auswahl(self, slug, moeglich=True):
        u"""Die Eintraege der Combo-Box „Bereich" - ``[(wert, name, gesetzt)]``.

        Waehlbar sind nur Bereiche MIT Praefix: Ein Bereich, der bloss umbenennt,
        hat keinen Ordner, in den sich etwas verschieben liesse.
        """
        erlaubt = self.ziele()
        if not moeglich or not erlaubt:
            return [(slug, self.name_von(slug), True)]
        ziele = [(s, self.name_von(s)) for s in erlaubt]
        ziele.sort(key=lambda z: (self.reihung.get(z[0], 10 ** 6), z[1].lower()))
        if slug and slug not in erlaubt:
            # Der aktuelle Bereich ist kein erlaubtes Ziel (abgeleitet, oder
            # Elternordner anderer Bereiche). Er steht trotzdem drin - sonst
            # zeigte die Box einen falschen Zustand.
            ziele.insert(0, (slug, self.name_von(slug)))
        return [(s, n, s == slug) for s, n in ziele]

    # --------------------------------------------------------- Sortierung

    def platz(self, slug):
        u"""Sortierplatz eines Bereichs - Angabe-Reihenfolge, dann Name."""
        return (self.reihung.get(slug, 10 ** 6), self.name_von(slug).lower())

    def sortiert(self, tests, schluessel=lambda t: t.get("id", "")):
        u"""Faelle nach Bereich (in der ANGEGEBENEN Reihenfolge), dann nach ID.

        Die Vorsortierung ersetzt getrennte Untertabellen: In EINER Tabelle
        stehen die Faelle eines Bereichs beieinander, und wer anders sortieren
        will, klickt auf eine Spaltenueberschrift.
        """
        return sorted(tests, key=lambda t: (self.platz(self.slug_von(
            schluessel(t))), schluessel(t)))

    def gruppieren(self, tests, schluessel=lambda t: t.get("id", "")):
        u"""[{'slug','name','tests','anzahl'}] - alphabetisch, „Sonstige" zuletzt.

        Fuer Zaehlungen und fuer Seiten, die je Bereich einen Sammellauf
        anbieten (``/tests/<bereich>/<art>/``).
        """
        eimer = {}
        for t in tests:
            slug = self.slug_von(schluessel(t)) or self.REST[0]
            eimer.setdefault(slug, []).append(t)
        aus = [{"slug": s, "name": self.name_von("" if s == self.REST[0] else s),
                "tests": v, "anzahl": len(v)}
               for s, v in eimer.items()]
        aus.sort(key=lambda g: (g["slug"] == self.REST[0], self.platz(g["slug"])))
        return aus
