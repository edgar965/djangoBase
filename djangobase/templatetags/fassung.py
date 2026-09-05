# -*- coding: utf-8 -*-
u"""``{% fassungspfad %}`` — die Adresse einer statischen Datei MIT Fassung.

Ersetzt in Vorlagen das Muster ``{% static "x/y.js" %}?t={% now "U" %}``.
Der Unterschied ist nicht kosmetisch (siehe `fassungsstatik.py`):

* ``?t={% now "U" %}`` aendert sich bei JEDEM Seitenaufruf — der Browser
  laedt die Datei also immer neu — und die relativen Importe der Datei erben
  die Abfrage NICHT, kommen also weiter aus dem Zwischenspeicher.
* ``{% fassungspfad %}`` legt die Fassung in den PFAD. Relative Importe erben
  sie damit, und die Adresse aendert sich nur, wenn sich wirklich etwas
  geaendert hat.
"""
from django import template

from ..fassungsstatik import Fassungsstatik

register = template.Library()


@register.simple_tag
def fassungspfad(relativ):
    u"""``{% fassungspfad "viewer/viewer/index.js" %}``."""
    return Fassungsstatik.pfad(relativ)
