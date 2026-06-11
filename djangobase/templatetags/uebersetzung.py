"""Template-Tags für das Übersetzungsmodul (djangobase.uebersetzung).

In Templates der öffentlichen User-Seite:

    {% load uebersetzung %}
    {% t "Ausflüge" %}                       – kurzer Text (auch Variablen:
    {% t ort.kategorie.name %})                wird automatisch registriert)
    {% tblock "impressum" %}…{% endtblock %} – ganzer HTML-Block unter festem
                                               Schlüssel (Änderung ⇒ veraltet)
    {% sprachen_menue %}                     – Flaggen-Menü zum Umschalten
                                               (braucht URL-Name "sprache_setzen")

Basis-Sprache ist Deutsch; ohne Cookie / für unbekannte Sprachen liefern die
Tags einfach den deutschen Text – die Seite kann also nie kaputtgehen.
"""
from django import template
from django.utils.safestring import mark_safe

from .. import uebersetzung

register = template.Library()


def _sprache(context):
    request = context.get("request")
    if request is None:
        return uebersetzung.BASIS
    return uebersetzung.sprache_aus_request(request)


@register.simple_tag(takes_context=True)
def t(context, text):
    """Kurztext übersetzen: {% t "Orte" %} oder {% t variable %}."""
    return uebersetzung.text_holen(str(text), _sprache(context))


@register.tag(name="tblock")
def tblock(parser, token):
    """{% tblock "schluessel" %}…HTML…{% endtblock %} – übersetzt den ganzen
    Block; das Markup bleibt erhalten (nur Text zwischen Tags wird ersetzt)."""
    try:
        _name, schluessel = token.split_contents()
    except ValueError as e:
        raise template.TemplateSyntaxError(
            "tblock erwartet genau ein Argument: den Schlüssel") from e
    nodelist = parser.parse(("endtblock",))
    parser.delete_first_token()
    return TBlockNode(nodelist, schluessel.strip("\"'"))


class TBlockNode(template.Node):
    def __init__(self, nodelist, schluessel):
        self.nodelist = nodelist
        self.schluessel = schluessel

    def render(self, context):
        inhalt = self.nodelist.render(context)
        ergebnis = uebersetzung.text_holen(
            inhalt, _sprache(context), schluessel=self.schluessel)
        return mark_safe(ergebnis)


@register.inclusion_tag("djangobase/_sprachen.html", takes_context=True)
def sprachen_menue(context):
    """Flaggen-Dropdown für den Header der User-Seite."""
    aktiv = _sprache(context)
    request = context.get("request")
    eintraege = [{"code": uebersetzung.BASIS, "name": "Deutsch", "flagge": "🇩🇪"}]
    for code in uebersetzung.aktive_sprachen():
        name, flagge = uebersetzung.SPRACH_NAMEN[code]
        eintraege.append({"code": code, "name": name, "flagge": flagge})
    aktuelle = next((e for e in eintraege if e["code"] == aktiv), eintraege[0])
    return {
        "sprachen": eintraege,
        "aktiv": aktiv,
        "aktuelle": aktuelle,
        "next": request.get_full_path() if request else "/",
        # Menü nur zeigen, wenn mindestens eine Zielsprache konfiguriert ist
        "anzeigen": len(eintraege) > 1,
    }
