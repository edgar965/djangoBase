"""Einstellungen → Übersetzung: Sprachen wählen, Status sehen, Lauf starten.
Dazu die öffentliche SpracheSetzenView (Cookie) für das Flaggen-Menü."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from .. import store, uebersetzung
from ..mixins import ZugriffMixin


class SpracheSetzenView(View):
    """Öffentlich: ?s=en&next=/ setzt das Sprach-Cookie und leitet zurück.
    Vom Projekt unter dem URL-Namen "sprache_setzen" zu mounten."""

    def get(self, request):
        s = (request.GET.get("s") or uebersetzung.BASIS).strip()
        if s != uebersetzung.BASIS and s not in uebersetzung.aktive_sprachen():
            s = uebersetzung.BASIS
        ziel = request.GET.get("next") or "/"
        if not ziel.startswith("/") or ziel.startswith("//"):
            ziel = "/"
        antwort = redirect(ziel)
        antwort.set_cookie(uebersetzung.COOKIE, s,
                           max_age=365 * 24 * 3600, samesite="Lax")
        return antwort


class UebersetzungView(ZugriffMixin, View):
    """Einstellungen → Übersetzung (Staff)."""

    def get(self, request):
        anzahl_quellen, zeilen = uebersetzung.sprach_status()
        aktive = uebersetzung.aktive_sprachen()
        status = uebersetzung.lauf_status()
        return render(request, "djangobase/hilfe/uebersetzung.html", {
            "aktiv": "einstellungen_uebersetzung",
            "sprachen": [{"code": c, "name": n, "flagge": f, "an": c in aktive}
                         for c, n, f in uebersetzung.SPRACHEN],
            "anzahl_quellen": anzahl_quellen,
            "zeilen": zeilen,
            "lauf": status,
            "lauf_laeuft": bool(status.get("laeuft")),
        })

    def post(self, request):
        aktion = request.POST.get("aktion")

        if aktion == "sprachen":
            gewaehlt = request.POST.getlist("sprachen")
            codes = [c for c, _n, _f in uebersetzung.SPRACHEN if c in gewaehlt]
            store.speichern_gruppe("uebersetzung", {"uebersetzung_sprachen": codes})
            uebersetzung.katalog_leeren()
            messages.success(request, f"{len(codes)} Zielsprache(n) gespeichert.")

        elif aktion == "uebersetzen":
            modus = request.POST.get("modus") or "veraltet"
            if modus not in ("fehlend", "veraltet", "alle"):
                modus = "veraltet"
            if not uebersetzung.aktive_sprachen():
                messages.error(request, "Bitte zuerst mindestens eine Zielsprache wählen.")
            elif uebersetzung.lauf_starten(modus):
                messages.success(request, "Übersetzungslauf gestartet – die Seite "
                                          "aktualisiert sich automatisch.")
            else:
                messages.info(request, "Es läuft bereits ein Übersetzungslauf.")

        return redirect(request.path)
