from .logs import LogsView
from .versions import VersionsView
from .tests import TestsView
from .settings import EinstellungenView
from .benutzer import (BenutzerListeView, BenutzerErstellenView,
                       BenutzerBearbeitenView, BenutzerStatusView)

__all__ = ["LogsView", "VersionsView", "TestsView", "EinstellungenView",
           "BenutzerListeView", "BenutzerErstellenView",
           "BenutzerBearbeitenView", "BenutzerStatusView"]
