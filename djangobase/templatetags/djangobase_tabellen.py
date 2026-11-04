"""``{% djb_tabellen %}`` — dasselbe wie ``{{ djangobase.tabellen_element }}`` (``tabellen_element.py``), für
eigene Vorlagen ohne die djangoBase-Hülle. Die Hülle selbst lädt diese Bibliothek NICHT (Grund dort)."""

from django import template

from ..tabellen_element import TabellenElement

register = template.Library()


@register.simple_tag(takes_context=True)
def djb_tabellen(context):
    return TabellenElement.html(context.get("request"))
