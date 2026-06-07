from django.urls import path

from .views import EinstellungenView, LogsView, TestsView, VersionsView

app_name = "djangobase"

urlpatterns = [
    path("versionen/", VersionsView.as_view(), name="versionen"),
    path("logs/", LogsView.as_view(), name="logs"),
    path("tests/", TestsView.as_view(), name="tests"),
    path("einstellungen/", EinstellungenView.as_view(gruppe="djangobase"), name="einstellungen"),
    path("einstellungen/website/", EinstellungenView.as_view(gruppe="website"), name="einstellungen_website"),
]
