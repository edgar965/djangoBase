# -*- coding: utf-8 -*-
u"""Menue-Eintraege, die JEDES djangoBase-Projekt haben soll.

DIE VORGABE (16.08.2026)
========================
    „diese zwei Seiten sollen IMMER sichtbar sein, in jedem Projekt das von
     djangoBase ableitet!"

Gemeint sind die beiden Werkzeugkaesten ``Skills`` und ``Skills2``. Sie standen
bis dahin nur in der Hilfe-Gruppe von ``_nav.html`` - und die schaltet jedes
Projekt ab, das seine eigene Navigation fuehrt (``hilfe_menu: False``). In
shortlongx waren beide Seiten deshalb nur ueber ihre URL erreichbar; gemeldet hat
es der Nutzer, nicht ein Test.

BEIDE SEITEN GEHOEREN UNTER „HILFE" - nirgendwo sonst (Ansage 16.08.2026). Eine
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
PFLICHTSEITEN = (
    PflichtEintrag(
        "Skills", "bi-tools", "skills",
        "Werkzeugkasten: Prüfungen, die Django nach Vorlagen, Routen und "
        "Modulen fragen"),
    PflichtEintrag(
        "Skills2", "bi-clipboard2-check", "skills2",
        "Zweiter Werkzeugkasten: die Prüfwerkzeuge und Lehren aus dem großen "
        "Review"),
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
