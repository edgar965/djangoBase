from django.urls import path

from .views import api_system_stats
from .views.ki_modelle import KiModelleView
from .views.review_kontext import ReviewKontextView
from .views.languageserver import LanguageServerView
from .views.languageserver_status import LanguageServerStatusView
from .views.languageserver_referenzen import LanguageServerReferenzenView
from .views.uebrige_putz import UebrigePutzView
from .views import (AblaufView, WorkflowsDatenView, WorkflowsView,
                    AufzeichnungView, AktuellDatenView, AktuellLeerenView,
                    AktuellView,
                    BenutzerBearbeitenView, BenutzerErstellenView,
                    BenutzerInlineView, BenutzerListeView, BenutzerLoeschenView,
                    BenutzerStatusView, EinstellungenTabsView, EinstellungenView,
                    JobsView, KlassenmodellView, LogsClearView, LogsView,
                    ReviewBefundeView, ReviewNachfassenView,
                    ReviewStartView, ReviewStatusView, ReviewView,
                    SkillsView, TestDauerView, TestsView,
                    TestNummerView, TestStromView,
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
    # LIVE-Lauf: fährt die angeforderten Ziele und streamt den Fortschritt
    # (Ansage 17.08.2026 „live fortschritt in djangoBase einbauen"). POST,
    # weil bei „Alle auswählen" hunderte Kennungen mitkommen.
    path("tests/strom/", TestStromView.as_view(), name="tests_strom"),
    # Platz eines Falls in der Tabelle („Nr."-Spalte). POST, weil es
    # `logs/testreihenfolge.json` SCHREIBT.
    path("tests/nummer/", TestNummerView.as_view(), name="tests_nummer"),
    # TESTCASE AUFZEICHNEN (Auftrag Edgar, 20.08.2026): Ein Reiter, der die
    # Aktionen im UI mitschreibt, damit daraus echte Tests entstehen koennen.
    # EIN Endpunkt fuer alle sechs Vorgaenge (start/schritte/ende/name/
    # loeschen) - sechs Pfade waeren sechs Gelegenheiten, den Zugriffsschutz
    # zu vergessen. Der haeufigste Aufruf ist „schritte" im Sekundentakt.
    path("tests/aufzeichnung/", AufzeichnungView.as_view(),
         name="tests_aufzeichnung"),
    # DER Werkzeugkasten: alle Werkzeuge, alle Lehren, die Fixer und der
    # server-seitige Stapellauf mit Klartext-Bericht. Die Werkzeuge laufen im
    # Serverprozess und rufen ausschliesslich GET-Routen auf.
    path("skills/", SkillsView.as_view(), name="skills"),
    # Das Objektmodell als Bild: wer haelt wen, wer erbt von wem.
    # Gerechnet wird auf Knopfdruck (POST) — der Durchgang liest
    # jede `.py` des Projekts.
    path("klassenmodell/", KlassenmodellView.as_view(),
         name="klassenmodell"),
    # Die „Uebrigen“ einer Endung loeschen (02.09.2026, auf Ansage).
    # GET = Vorschau, POST = loeschen. Aus dem Browser kommt NIE ein Pfad,
    # nur eine Endung — siehe umbau/uebrigesuche.py.
    path("klassenmodell/uebrige/", UebrigePutzView.as_view(),
         name="klassenmodell_uebrige"),
    # Werkzeug Language Server (02.09.2026): Stapellauf im Hintergrund,
    # Status zum Abfragen, Referenzen/Umbenennen ueber die offene Sitzung.
    path("languageserver/", LanguageServerView.as_view(), name="languageserver"),
    path("languageserver/status/", LanguageServerStatusView.as_view(),
         name="languageserver_status"),
    path("languageserver/referenzen/", LanguageServerReferenzenView.as_view(),
         name="languageserver_referenzen"),
    path("workflows/", WorkflowsView.as_view(), name="workflows"),
    path("ablauf/", AblaufView.as_view(), name="ablauf"),
    path("workflows/daten/", WorkflowsDatenView.as_view(),
         name="workflows_daten"),
    # Skills2 und Skills3 sind UEBERGANGSSEITEN auf dem Weg zur Abschaffung
    # (17.08.2026). Ihre Werkzeuge liegen im Master; sie bleiben nur, damit
    # Lesezeichen und fremde Links nicht ins Leere zeigen.
    # Welches Modell taugt als Sparringspartner? Katalog live von
    # OpenRouter und aus ``ollama list``, Bewertung aus eigener Messung
    # (aus shortlongx hierher, 18.08.2026).
    path("ki-modelle/", KiModelleView.as_view(), name="ki_modelle"),
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
    # DIE GESPEICHERTEN Befunde eines Pruefwerkzeugs - ohne einen Lauf zu
    # starten. ``<slug>`` ist der Partner aus der Konfiguration, NIE ein
    # Pfad: Welches Verzeichnis gelesen wird, entscheidet der Server.
    path("review/werkzeug/<str:slug>/befunde/", ReviewBefundeView.as_view(),
         name="review_befunde"),
    # Kontextverbrauch einer Claude-Code-Sitzung (02.09.2026). Rechnet nur
    # auf Knopfdruck — das Protokoll ist dreistellig MB gross.
    path("review/kontext/", ReviewKontextView.as_view(),
         name="review_kontext"),
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
