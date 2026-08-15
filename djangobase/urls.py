from django.urls import path

from .views import api_system_stats
from .views import (BenutzerBearbeitenView, BenutzerErstellenView,
                    BenutzerInlineView, BenutzerListeView, BenutzerLoeschenView,
                    BenutzerStatusView, EinstellungenTabsView, EinstellungenView,
                    JobsView, LogsClearView, LogsView, ReviewNachfassenView,
                    ReviewStartView, ReviewStatusView, ReviewView, TestsView,
                    TrafficView, UebersetzungView, VersionsView)

app_name = "djangobase"

urlpatterns = [
    # Auslastungs-Leiste (GPU/CPU/RAM/Netz) - liefert nur Zahlen, keine Seite.
    # Die zugehoerige Anzeige ist static/djangobase/js/system_stats.js.
    path("api/system-stats/", api_system_stats, name="api_system_stats"),
    path("versionen/", VersionsView.as_view(), name="versionen"),
    path("logs/", LogsView.as_view(), name="logs"),
    path("logs/leeren/", LogsClearView.as_view(), name="logs_leeren"),
    path("tests/", TestsView.as_view(), name="tests"),
    path("jobs/", JobsView.as_view(), name="jobs"),
    # Code-Review im Gespraech mit einem zweiten Modell. Die Runden laufen im
    # Hintergrund (eine bis fuenf Minuten), deshalb Start/Status getrennt.
    path("review/", ReviewView.as_view(), name="review"),
    path("review/start/", ReviewStartView.as_view(), name="review_start"),
    path("review/<str:lauf_id>/nachfassen/", ReviewNachfassenView.as_view(),
         name="review_nachfassen"),
    path("review/<str:lauf_id>/status/", ReviewStatusView.as_view(), name="review_status"),
    # Haupt-Einstellungen: Profil-Combobox + alle Gruppen als Tabs.
    path("einstellungen/", EinstellungenTabsView.as_view(), name="einstellungen"),
    # Einzelseiten je Gruppe (Rueckwaerts-Kompatibilitaet / Deep-Links).
    path("einstellungen/djangobase/", EinstellungenView.as_view(gruppe="djangobase"), name="einstellungen_djangobase"),
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
