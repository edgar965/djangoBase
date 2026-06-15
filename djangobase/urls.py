from django.urls import path

from .views import (BenutzerBearbeitenView, BenutzerErstellenView,
                    BenutzerInlineView, BenutzerListeView, BenutzerLoeschenView,
                    BenutzerStatusView, EinstellungenView, LogsClearView, LogsView,
                    TestsView, TrafficView, UebersetzungView, VersionsView)

app_name = "djangobase"

urlpatterns = [
    path("versionen/", VersionsView.as_view(), name="versionen"),
    path("logs/", LogsView.as_view(), name="logs"),
    path("logs/leeren/", LogsClearView.as_view(), name="logs_leeren"),
    path("tests/", TestsView.as_view(), name="tests"),
    path("einstellungen/", EinstellungenView.as_view(gruppe="djangobase"), name="einstellungen"),
    path("einstellungen/website/", EinstellungenView.as_view(gruppe="website"), name="einstellungen_website"),
    path("einstellungen/email/", EinstellungenView.as_view(gruppe="email"), name="einstellungen_email"),
    path("traffic/", TrafficView.as_view(), name="traffic"),
    path("einstellungen/uebersetzung/", UebersetzungView.as_view(), name="uebersetzung"),
    path("einstellungen/benutzer/", BenutzerListeView.as_view(), name="benutzer"),
    path("einstellungen/benutzer/neu/", BenutzerErstellenView.as_view(), name="benutzer_neu"),
    path("einstellungen/benutzer/<int:pk>/bearbeiten/", BenutzerBearbeitenView.as_view(), name="benutzer_bearbeiten"),
    path("einstellungen/benutzer/<int:pk>/status/", BenutzerStatusView.as_view(), name="benutzer_status"),
    path("einstellungen/benutzer/<int:pk>/inline/", BenutzerInlineView.as_view(), name="benutzer_inline"),
    path("einstellungen/benutzer/<int:pk>/loeschen/", BenutzerLoeschenView.as_view(), name="benutzer_loeschen"),
]
