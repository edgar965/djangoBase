from django.urls import path

from .views import api_system_stats
from .views import (AktuellDatenView, AktuellLeerenView, AktuellView,
                    BenutzerBearbeitenView, BenutzerErstellenView,
                    BenutzerInlineView, BenutzerListeView, BenutzerLoeschenView,
                    BenutzerStatusView, EinstellungenTabsView, EinstellungenView,
                    JobsView, LogsClearView, LogsView, ReviewNachfassenView,
                    ReviewStartView, ReviewStatusView, ReviewView, Skills3View,
                    Skills2View, SkillsView, TestDauerView, TestsView,
                    TestVerschiebenView, TrafficView,
                    UebersetzungView, VersionsView)

app_name = "djangobase"

urlpatterns = [
    # Auslastungs-Leiste (GPU/CPU/RAM/Netz) - liefert nur Zahlen, keine Seite.
    # Die zugehoerige Anzeige ist static/djangobase/js/system_stats.js.
    path("api/system-stats/", api_system_stats, name="api_system_stats"),
    path("versionen/", VersionsView.as_view(), name="versionen"),
    path("logs/", LogsView.as_view(), name="logs"),
    path("logs/leeren/", LogsClearView.as_view(), name="logs_leeren"),
    path("tests/", TestsView.as_view(), name="tests"),
    # Laufzeit eines im Browser gefahrenen UI-Tests. Der EINZIGE
    # Schreib-Endpunkt der Tests-Seite; Grenzen siehe testdauer.py.
    path("tests/dauer/", TestDauerView.as_view(), name="tests_dauer"),
    # Testfall in eine andere Kategorie umhaengen (Combo-Box
    # „Verschieben" in jeder Testcase-Tabelle). POST, weil es eine
    # DATEI verschiebt — siehe testverschieben.py.
    path("tests/verschieben/", TestVerschiebenView.as_view(),
         name="tests_verschieben"),
    # DER Werkzeugkasten: alle Werkzeuge, alle Lehren, die Fixer und der
    # server-seitige Stapellauf mit Klartext-Bericht. Die Werkzeuge laufen im
    # Serverprozess und rufen ausschliesslich GET-Routen auf.
    path("skills/", SkillsView.as_view(), name="skills"),
    # Skills2 und Skills3 sind UEBERGANGSSEITEN auf dem Weg zur Abschaffung
    # (17.08.2026). Ihre Werkzeuge liegen im Master; sie bleiben nur, damit
    # Lesezeichen und fremde Links nicht ins Leere zeigen.
    path("skills2/", Skills2View.as_view(), name="skills2"),
    path("skills3/", Skills3View.as_view(), name="skills3"),
    path("jobs/", JobsView.as_view(), name="jobs"),
    # Rollierendes Fenster mit den Ergebnissen der Claude-CLI. Geschrieben wird
    # NUR ueber `manage.py aktuell` — es gibt bewusst keinen Schreib-Endpunkt.
    path("aktuell/", AktuellView.as_view(), name="aktuell"),
    path("aktuell/daten/", AktuellDatenView.as_view(), name="aktuell_daten"),
    path("aktuell/leeren/", AktuellLeerenView.as_view(), name="aktuell_leeren"),
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
