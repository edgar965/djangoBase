from .logs import LogsView
from .versions import VersionsView
from .tests import TestsView
from .settings import EinstellungenView
from .traffic import TrafficView, VerbrauchBeaconView
from .uebersetzung import SpracheSetzenView, UebersetzungView
from .benutzer import (BenutzerListeView, BenutzerErstellenView,
                       BenutzerBearbeitenView, BenutzerStatusView,
                       BenutzerInlineView, BenutzerLoeschenView)

__all__ = ["LogsView", "VersionsView", "TestsView", "EinstellungenView",
           "TrafficView", "VerbrauchBeaconView",
           "SpracheSetzenView", "UebersetzungView",
           "BenutzerListeView", "BenutzerErstellenView",
           "BenutzerBearbeitenView", "BenutzerStatusView",
           "BenutzerInlineView", "BenutzerLoeschenView"]
