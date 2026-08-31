# -*- coding: utf-8 -*-
"""Code-Review im Gespraech mit einem zweiten Modell — oder mit einem Werkzeug.

Seite: Hilfe -> Review (djangobase/views/review.py).
Konfiguration: DJANGOBASE["review_partner"], ["review_bereiche"], ...

Zwei Sorten Gegenueber, EINE Schnittstelle:

    ziel "lokal"/"online"   ein Modell im Gespraech (ReviewPartner)
    ziel "werkzeug"         ein lokales Pruefwerkzeug, das den Git-Stand liest
                            und Befunde ausgibt (WerkzeugPartner) — etwa die
                            CodeRabbit-CLI
"""
from .befund import Befund
from .befund_lager import BefundLager
from .faden import ReviewFaden
from .lauf import NACHFASSEN, ROLLE, ReviewLauf
from .partner import ReviewFehler, ReviewPartner
from .register import REGISTER, LaufRegister
from .werkzeug_partner import WerkzeugPartner

__all__ = ["Befund", "BefundLager", "ReviewFaden", "ReviewLauf", "ReviewPartner", "ReviewFehler",
           "WerkzeugPartner", "LaufRegister", "REGISTER", "ROLLE", "NACHFASSEN"]
