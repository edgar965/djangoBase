# -*- coding: utf-8 -*-
u"""Deutsche Zahlenformatierung als Template-Filter.

Unabhaengig von Django-Locale-Settings, damit die Darstellung reproduzierbar ist:
Tausender-Punkt, Dezimal-Komma. Der numerische Rohwert bleibt in der Vorlage fuer
``{% if %}``-Vergleiche erhalten - nur die Ausgabe wird formatiert.

AUS shortlongx HIERHER (18.08.2026): Die Seite Hilfe → KI-Modelle ist nach
djangoBase gezogen und benutzt ``|de``. Den Filter dort nachzubauen waere die
Doppelung, gegen die dieses Paket antritt - shortlongx' ``fmt.py`` reicht
seither auf diese Fassung durch.

    {% load zahlen %}
    {{ wert|de:2 }}        1.234.567,89
    {{ wert|de_signed }}   +1.234   (Vorzeichen nur bei echt positivem Wert)
"""
from django import template

register = template.Library()


#: Anzeige fuer fehlende/nicht-numerische Werte (wie das alte floatformat: leer statt "None").
DASH = "—"


@register.filter
def de(value, decimals=0):
    """Formatiert eine Zahl deutsch: 1.234.567,89.  Aufruf: {{ v|de:2 }}.
    None/nicht-numerisch -> Gedankenstrich (nie der Literaltext "None")."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return DASH
    try:
        dec = int(decimals)
    except (TypeError, ValueError):
        dec = 0
    if round(n, dec) == 0:                   # "-0" vermeiden (z.B. -0,3 gerundet auf 0)
        n = 0.0
    s = f"{n:,.{dec}f}"                      # US-Format: 1,234,567.89
    # US -> DE: Trennzeichen tauschen ueber Platzhalter
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


@register.filter
def de_signed(value, decimals=0):
    """Wie de, aber mit Vorzeichen bei positiven Zahlen (+1.234). Verhindert
    Krueppel-Vorzeichen wie "+-4" und "-0"/"+0", wenn der Wert (gerundet) 0 oder None ist."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return DASH
    try:
        dec = int(decimals)
    except (TypeError, ValueError):
        dec = 0
    s = de(value, decimals)
    return f"+{s}" if round(n, dec) > 0 else s   # + nur bei echt positivem (gerundetem) Wert
