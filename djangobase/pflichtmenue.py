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
Zusammenfuehrung beider Kaesten - war gebaut, lieferte HTTP 200 und stand in
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
