"""Routen — alle GET-Routen des Projekts auflisten und aufrufbar machen.

Gemeinsame Grundlage der drei Endpunkt-Werkzeuge (Zeiten, Probe, Profil).
Bewusst eine eigene Datei: Ohne sie haetten alle drei denselben Resolver-Code —
genau die Art Duplikat, die dieser Werkzeugkasten aufspueren soll.
"""

import re

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

#: Platzhalter je Django-Konverter. Die Werte sind absichtlich unverfaenglich:
#: Die Probe faehrt echte Endpunkte an, und ein Treffer auf einen existierenden
#: Datensatz waere bei Loesch-Routen fatal. Deshalb Kennungen, die es nicht
#: gibt — die Antwort ist dann 404, und auch das ist ein stabiler Vergleichswert.
PLATZHALTER = {
    'int': '0',
    'str': 'probe',
    'slug': 'probe',
    'uuid': '00000000-0000-0000-0000-000000000001',
    'path': 'probe',
}


class Route:
    """Eine aufrufbare GET-Route mit ihrem Namen."""

    __slots__ = ('weg', 'name', 'ansicht')

    def __init__(self, weg, name, ansicht):
        self.weg = weg
        self.name = name
        self.ansicht = ansicht

    def __str__(self):
        return self.weg


def _fuellen(muster):
    """`<int:pk>` und `(?P<pk>[0-9]+)` durch Platzhalter ersetzen."""
    def ersatz(treffer):
        konverter = treffer.group(1) or 'str'
        return PLATZHALTER.get(konverter, 'probe')

    weg = re.sub(r'<(?:(\w+):)?\w+>', ersatz, muster)
    weg = re.sub(r'\(\?P<\w+>[^)]*\)', 'probe', weg)
    return weg


def _sammeln(resolver, praefix, gefunden, tiefe=0):
    if tiefe > 8:
        return
    for eintrag in resolver.url_patterns:
        teil = str(getattr(eintrag.pattern, '_route', eintrag.pattern))
        if isinstance(eintrag, URLResolver):
            _sammeln(eintrag, praefix + teil, gefunden, tiefe + 1)
        elif isinstance(eintrag, URLPattern):
            weg = '/' + _fuellen(praefix + teil).lstrip('/')
            gefunden.append(Route(weg, eintrag.name or '',
                                  getattr(eintrag.callback, '__name__', '')))


def alle_routen(ausser=('/admin/', '/static/', '/media/', '/__debug__/')):
    """Alle Routen des Projekts, Platzhalter gefuellt, ohne Doppelte.

    Admin und Dateiauslieferung bleiben aussen vor: Die eine ist fremder Code,
    die andere liefert nur Dateien und verfaelscht jede Zeitmessung.
    """
    gefunden = []
    _sammeln(get_resolver(), '', gefunden)
    gesehen, ergebnis = set(), []
    for route in gefunden:
        if any(route.weg.startswith(p) for p in ausser):
            continue
        if route.weg in gesehen or '(' in route.weg or '<' in route.weg:
            continue
        gesehen.add(route.weg)
        ergebnis.append(route)
    ergebnis.sort(key=lambda r: r.weg)
    return ergebnis


def klient():
    """Test-Client, der auch im laufenden Server benutzbar ist.

    ACHTUNG: Er ruft die eigenen Ansichten im selben Prozess und auf der
    ECHTEN Datenbank auf — nicht auf einer Testdatenbank. Deshalb nur GET,
    niemals POST: Ein POST auf eine Loeschroute waere kein Test, sondern ein
    Schaden.
    """
    from django.conf import settings
    from django.test import Client
    if '*' not in settings.ALLOWED_HOSTS and 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']
    return Client()
