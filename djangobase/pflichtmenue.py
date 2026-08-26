# -*- coding: utf-8 -*-
u"""Menue-Eintraege, die JEDES djangoBase-Projekt haben soll.

DIE VORGABE (16.08.2026)
========================
    „diese zwei Seiten sollen IMMER sichtbar sein, in jedem Projekt das von
     djangoBase ableitet!"

Gemeint sind die Werkzeugkaesten ``Skills``, ``Skills1`` und ``Skills2``. Sie
standen bis dahin nur in der Hilfe-Gruppe von ``_nav.html`` - und die schaltet
jedes Projekt ab, das seine eigene Navigation fuehrt (``hilfe_menu: False``). In
shortlongx waren sie deshalb nur ueber ihre URL erreichbar; gemeldet hat es der
Nutzer, nicht ein Test.

DERSELBE FEHLER NOCHMAL, mit einer Seite mehr (17.08.2026): ``Skills1`` - die
Zusammenfuehrung beider Kästen - war gebaut, lieferte HTTP 200 und stand in
KEINER der beiden Menue-Quellen. Sie war damit nur zu finden, wer die URL kannte.
Eine Seite ohne Menueeintrag ist keine Seite. Wer hier eine Route ergaenzt,
traegt sie in DIESE Liste ein - ``_nav_skills.html`` liest dieselbe Quelle.

ALLE SEITEN GEHOEREN UNTER „HILFE" - nirgendwo sonst (Ansage 16.08.2026). Eine
eigene Menue-Gruppe dafuer war ein Fehlgriff und ist wieder entfernt: Es sind
Hilfe-Seiten, und dort sucht sie auch jemand.

ZWEI WEGE, EINE QUELLE
======================
Projekte binden ihre Navigation unterschiedlich ein:

    1. ``_nav.html`` mit der Hilfe-Gruppe   -> ``djangobase/_nav_skills.html``
    2. KOMPLETT eigene Sidebar (``menue.py``) -> dieses Modul hier

Fall 2 - shortlongx baut seine Sidebar selbst und bindet ``_nav.html`` gar nicht
ein - loest diese Funktion: Das Projekt haengt ``pflicht_eintraege()`` in seine
EIGENE Hilfe-Gruppe. Kommt eines Tages eine dritte Pflichtseite dazu, erscheint
sie ueberall, ohne dass ein Projekt etwas aendern muss.

Reine Daten, kein Django-Import ausser ``reverse_lazy`` - die Eintraege werden
beim Aufbau des Menues ausgewertet, nicht beim Import.
"""
from django.urls import reverse_lazy

__all__ = ["PflichtEintrag", "pflicht_eintraege", "PFLICHTSEITEN"]


class PflichtEintrag:
    """Ein Menuepunkt, den jedes Projekt bekommt."""

    def __init__(self, label, icon, route, zweck=""):
        self.label = label
        self.icon = icon
        #: Routenname innerhalb des ``djangobase``-Namensraums.
        self.route = route
        #: Wofuer die Seite da ist - fuer Doku und Tooltips.
        self.zweck = zweck

    @property
    def url(self):
        return reverse_lazy("djangobase:%s" % self.route)

    def als_dict(self):
        """Die Form, die die Menue-Bauer der Projekte erwarten."""
        aus = {"label": self.label, "icon": self.icon, "url": self.url}
        if self.zweck:
            aus["title"] = self.zweck
        return aus

    def __repr__(self):
        return "<PflichtEintrag %s -> djangobase:%s>" % (self.label, self.route)


#: Die Seiten selbst. Neue Pflichtseite? HIER eintragen - dann erscheint sie in
#: allen drei Einbau-Wegen zugleich.
#: „Werkzeug Code Review" (bis 24.08.2026 „Skills") ist der EINE
#: Werkzeugkasten. Der Routenname bleibt `skills` — Lesezeichen und die
#: `aktiv|slice`-Abfrage in `_nav.html` haengen daran. Die Übergangsseiten „Skills2" und
#: „Skills3" sind am 18.08.2026 ENTFALLEN: Skills2 zeigte dieselben 44
#: Werkzeuge und dieselben 18 Lehren (gemessen, kein einziger Unterschied),
#: Skills3 hatte zusätzlich die 20 Review-Lehren — die stehen jetzt hier.
#: „grossdateien" war der einzige Werkzeug-Unterschied und steht bewusst auf
#: der Überspringen-Liste (von „dateigroesse" abgedeckt).
#:
#: VIER SEITEN DAZU (25.08.2026) — derselbe Fehler wie bei „Skills1"
#: ==================================================================
#: Gemessen im Projekt assistant mit ``werkzeug/hilfe_menue_probe.py``:
#: jede Route unter ``/hilfe/`` abgerufen und gegen die GERENDERTE
#: Seitenleiste gehalten. Ergebnis: „Review", „Aktuell", „KI-Modelle",
#: „Traffic" und „Übersetzung" lieferten alle HTTP 200 und standen in
#: KEINEM Menü.
#:
#: Der Grund ist derselbe wie damals: „Review" und „Aktuell" standen
#: EINZELN in ``_nav.html`` statt in dieser Liste. Projekte mit eigener
#: Navigation (assistant, NoiseSpy, CamTrack — die Hälfte aller
#: Konsumenten) binden ``_nav.html`` gar nicht ein und sahen sie
#: deshalb nie. „KI-Modelle", „Traffic" und „Übersetzung" standen
#: nirgends, auch nicht in ``_nav.html``.
#:
#: Sie stehen jetzt alle hier, und ``_nav.html`` führt sie nicht mehr
#: einzeln — sonst stünden sie in den Standard-Shell-Projekten doppelt.
#:
#: KEINE BEDINGUNGEN, auch nicht bei Traffic und Übersetzung, die ein
#: Projekt abschalten kann. Das ist die Vorgabe vom 13.08.2026: Fehlt
#: die Konfiguration, erklärt die Seite selbst, was einzutragen ist —
#: das ist hilfreicher als ein fehlender Menüpunkt, den niemand sucht.
PFLICHTSEITEN = (
    PflichtEintrag(
        "Werkzeug Code Review", "bi-tools", "skills",
        "Der Werkzeugkasten: alle Prüfungen und Fixer, Stapellauf mit Bericht "
        "zum Mitnehmen, Sicherung und Netz, dazu die Lehren aus den "
        "Code-Reviews als Ankreuzliste"),
    PflichtEintrag(
        "Werkzeug Klassenmodell", "bi-diagram-3", "klassenmodell",
        "Das Objektmodell als Bild: wer hält wen, wer erbt von wem — auf "
        "Knopfdruck aus dem Quelltext gezeichnet"),
    PflichtEintrag(
        "Review", "bi-chat-left-text", "review",
        "Code-Review im Gespräch mit einem zweiten Modell — die Runden "
        "laufen im Hintergrund, eine bis fünf Minuten"),
    PflichtEintrag(
        "Aktuell", "bi-broadcast", "aktuell",
        "Rollierendes Fenster mit den Ergebnissen der Claude-CLI; "
        "geschrieben wird ausschließlich über `manage.py aktuell`"),
    PflichtEintrag(
        "KI-Modelle", "bi-cpu", "ki_modelle",
        "Welches Modell taugt als Sparringspartner? Katalog live von "
        "OpenRouter und aus `ollama list`, Bewertung aus eigener Messung"),
    PflichtEintrag(
        "Traffic", "bi-graph-up", "traffic",
        "Zugriffsstatistik: welche Seiten wie oft aufgerufen wurden"),
    PflichtEintrag(
        "Übersetzung", "bi-translate", "uebersetzung",
        "Oberflächentexte in andere Sprachen übersetzen (deep_translator)"),
)


def pflicht_eintraege():
    """Die Pflicht-Menuepunkte als Dictionaries fuer eigene ``menue.py``.

    Beispiel (shortlongx)::

        from djangobase.pflichtmenue import pflicht_eintraege

        def bereich_hilfe():
            return {"gruppen": [{"eintraege": [
                …eigene Punkte…,
                *pflicht_eintraege(),
            ]}]}

    Woerterbuch gewollt: Das ist das Uebergabeformat der Menue-Bauer, kein
    Datensatz, der durch Funktionen wandert."""
    return [e.als_dict() for e in PFLICHTSEITEN]
