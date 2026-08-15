# -*- coding: utf-8 -*-
"""LaufRegister — die laufenden Sitzungen im Arbeitsspeicher.

Bewusst KEINE Datenbanktabelle: Ein Lauf ist ein Gespraech, das man gerade
fuehrt; nach einem Server-Neustart faengt man ohnehin neu an. Was bleiben soll,
steht in den Mitschriften auf der Platte (siehe ReviewFaden).

Die Zahl der gehaltenen Laeufe ist begrenzt — ein Lauf ueber vier Bereiche haelt
den kompletten Quelltext im Verlauf, das sind schnell einige Megabyte je Lauf.
Die aeltesten fallen heraus, sobald neue kommen.
"""
import threading
from collections import OrderedDict


class LaufRegister:
    """Wenige, kurzlebige Laeufe — aelteste fallen heraus."""

    MAX_LAEUFE = 12

    def __init__(self):
        self._laeufe = OrderedDict()
        self._lock = threading.Lock()

    def hinzu(self, lauf):
        with self._lock:
            self._laeufe[lauf.id] = lauf
            while len(self._laeufe) > self.MAX_LAEUFE:
                # `laeuft` wird nicht geprueft: Ein herausgefallener Lauf
                # rechnet zwar im Hintergrund zu Ende und schreibt seine
                # Mitschrift, ist aber ueber die Oberflaeche nicht mehr
                # erreichbar. Bei zwoelf Laeufen ist das kein realer Fall.
                self._laeufe.popitem(last=False)
        return lauf

    def holen(self, lauf_id):
        with self._lock:
            return self._laeufe.get(lauf_id)

    def liste(self):
        with self._lock:
            return list(reversed(self._laeufe.values()))


#: Ein Register je Serverprozess.
REGISTER = LaufRegister()
