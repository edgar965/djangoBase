"""Hilfe -> Einstellungen.

Zwei Wege auf dieselben Store-Werte:
  * EinstellungenTabsView  -> kombinierte Seite mit Profil-Auswahl (Combobox)
    oben und allen generischen Gruppen als Tabs. Haupt-Einstiegspunkt
    ("djangobase:einstellungen").
  * EinstellungenView      -> Einzelseite je Gruppe (Rueckwaerts-Kompatibilitaet,
    z. B. /hilfe/einstellungen/website/). Nutzt dieselben Helfer.

Profile: mehrere benannte Einstellungs-Saetze (z. B. "djangoBase Standard" und
"CleanOrga"); genau eines ist aktiv und wird von conf() angewendet. Persistiert
als JSON via store.py — keine DB/Migration.
"""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views import View

from .. import store
from ..conf import conf
from ..mixins import ZugriffMixin
from ..store import FARB_KEYS, GRUPPEN

# Generische, rein feldbasierte Gruppen — erscheinen als Tabs (Reihenfolge zaehlt).
# uebersetzung/benutzer haben eigene Views und bleiben separate Seiten.
TAB_GRUPPEN = ["website", "djangobase", "freigabe", "email"]


def _felder_werte(c, gruppe):
    """Aktuelle (effektive) Werte je Feld der Gruppe fuers Formular.
    CSV-Typ: Liste wird fuer die Anzeige zu 'a, b, c'."""
    felder = []
    for key, typ, label in GRUPPEN[gruppe]["felder"]:
        wert = c["farben"].get(key, "") if key in FARB_KEYS else c.get(key, "")
        if typ == "csv" and isinstance(wert, (list, tuple)):
            wert = ", ".join(str(x) for x in wert)
        felder.append({"key": key, "typ": typ, "label": label, "wert": wert})
    return felder


def _werte_aus_post(request, gruppe):
    """POST-Daten der Gruppe in getypte Werte konvertieren."""
    werte = {}
    for key, typ, _label in GRUPPEN[gruppe]["felder"]:
        if typ == "bool":
            werte[key] = request.POST.get(key) == "on"
            continue
        roh = (request.POST.get(key) or "").strip()
        if typ == "int":
            try:
                werte[key] = int(roh)
            except ValueError:
                continue  # leer/ungueltig -> Settings-Default behalten
        elif typ == "csv":
            werte[key] = [s.strip() for s in roh.split(",") if s.strip()]
        else:
            werte[key] = roh
    return werte


def _template_existiert(name):
    try:
        get_template(name)
        return True
    except TemplateDoesNotExist:
        return False


def _base_template_pruefen(request, werte):
    """Validiert ein evtl. gesetztes base_template. True = darf gespeichert
    werden; sonst False (+ Fehlermeldung). Verhindert Aussperren durch ein
    nicht existierendes Layout-Template."""
    if "base_template" not in werte:
        return True
    bt = (werte.get("base_template") or "").strip()
    if bt and not _template_existiert(bt):
        messages.error(
            request,
            f"Basis-Template „{bt}“ nicht gefunden — nicht gespeichert. "
            "(Leer lassen = djangoBase-Standard.)")
        return False
    return True


class EinstellungenTabsView(ZugriffMixin, View):
    """Kombinierte Einstellungen: Profil-Combobox + alle Gruppen als Tabs."""

    def get(self, request):
        c = conf()
        tabs = [{
            "slug": slug,
            "label": GRUPPEN[slug]["label"],
            "icon": GRUPPEN[slug]["icon"],
            "beschreibung": GRUPPEN[slug]["beschreibung"],
            "felder": _felder_werte(c, slug),
        } for slug in TAB_GRUPPEN]
        return render(request, "djangobase/hilfe/einstellungen_tabs.html", {
            "aktiv": "einstellungen",
            "tabs": tabs,
            "theme_modes": c["theme_modes"],
            "profile": store.profile_liste(),
            "base_template_aktiv": c["base_template"],
        })

    def post(self, request):
        aktion = request.POST.get("aktion")

        if aktion == "profil_aktiv":
            if store.aktiv_setzen((request.POST.get("profil") or "").strip()):
                c = conf()
                if c["base_template"] and not _template_existiert(c["base_template"]):
                    messages.warning(
                        request,
                        f"Profil aktiviert, aber dessen Basis-Template "
                        f"„{c['base_template']}“ existiert hier nicht — es greift der "
                        "djangoBase-Standard, bis du es korrigierst.")
                else:
                    messages.success(request, "Profil gewechselt.")
            else:
                messages.error(request, "Profil nicht gefunden.")
            return redirect(request.path)

        if aktion == "profil_neu":
            label = (request.POST.get("profil_label") or "").strip()
            if label:
                slug = store.profil_anlegen(label, kopie_von=store.aktiv_slug())
                store.aktiv_setzen(slug)
                messages.success(request, f"Profil „{label}“ angelegt und aktiviert.")
            else:
                messages.error(request, "Bitte einen Profilnamen angeben.")
            return redirect(request.path)

        if aktion == "profil_loeschen":
            if store.profil_loeschen((request.POST.get("profil") or "").strip()):
                messages.success(request, "Profil gelöscht.")
            else:
                messages.error(request, "Profil kann nicht gelöscht werden (letztes Profil).")
            return redirect(request.path)

        # Standard: eine Gruppe speichern / zuruecksetzen.
        gruppe = request.POST.get("gruppe")
        if gruppe in GRUPPEN:
            ziel = f"{request.path}#tab-{gruppe}"
            if request.POST.get("zuruecksetzen"):
                store.leeren_gruppe(gruppe)
                messages.success(request, "Gruppe auf Settings-Werte zurückgesetzt.")
                return redirect(ziel)
            werte = _werte_aus_post(request, gruppe)
            if not _base_template_pruefen(request, werte):
                return redirect(ziel)
            store.speichern_gruppe(gruppe, werte)
            messages.success(request, "Einstellungen gespeichert.")
            return redirect(ziel)
        return redirect(request.path)


class EinstellungenView(ZugriffMixin, View):
    """Einzelseite je Gruppe (Rueckwaerts-Kompatibilitaet)."""
    gruppe = "djangobase"  # via .as_view(gruppe="website") ueberschrieben

    def _aktiv(self):
        return "einstellungen" if self.gruppe == "djangobase" else f"einstellungen_{self.gruppe}"

    def get(self, request):
        c = conf()
        g = GRUPPEN[self.gruppe]
        keys = {k for k, _t, _l in g["felder"]}
        return render(request, "djangobase/hilfe/einstellungen.html", {
            "aktiv": self._aktiv(),
            "gruppe": self.gruppe,
            "gruppe_label": g["label"],
            "gruppe_titel": g["titel"],
            "gruppe_icon": g["icon"],
            "gruppe_beschreibung": g["beschreibung"],
            "felder": _felder_werte(c, self.gruppe),
            "theme_modes": c["theme_modes"],
            "hat_overrides": any(k in store.laden() for k in keys),
        })

    def post(self, request):
        if request.POST.get("zuruecksetzen"):
            store.leeren_gruppe(self.gruppe)
            messages.success(request, "Einstellungen auf Settings-Werte zurückgesetzt.")
            return redirect(request.path)
        werte = _werte_aus_post(request, self.gruppe)
        if not _base_template_pruefen(request, werte):
            return redirect(request.path)
        store.speichern_gruppe(self.gruppe, werte)
        messages.success(request, "Einstellungen gespeichert.")
        return redirect(request.path)
