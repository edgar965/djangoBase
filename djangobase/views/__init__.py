from .logs import LogsView, LogsClearView
from .versions import VersionsView
from .tests import TestsView
from .settings import EinstellungenView
from .traffic import TrafficView, VerbrauchBeaconView
from .uebersetzung import SpracheSetzenView, UebersetzungView
from .benutzer import (BenutzerListeView, BenutzerErstellenView,
                       BenutzerBearbeitenView, BenutzerStatusView,
                       BenutzerInlineView, BenutzerLoeschenView)

__all__ = ["LogsView", "LogsClearView", "VersionsView", "TestsView", "EinstellungenView",
           "TrafficView", "VerbrauchBeaconView",
           "SpracheSetzenView", "UebersetzungView",
           "BenutzerListeView", "BenutzerErstellenView",
           "BenutzerBearbeitenView", "BenutzerStatusView",
           "BenutzerInlineView", "BenutzerLoeschenView"]
