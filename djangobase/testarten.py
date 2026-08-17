# -*- coding: utf-8 -*-
u"""Arten - Reihenfolge und Anzeigenamen der KATEGORIEN.

    „auch die reihenfolge ist änderbar" (Edgar, 17.08.2026)

Die Kategorien selbst sind Ordnernamen (``app/tests/<art>/``) und stehen als
Menge in :class:`~.testbefehle.Testbefehle`. Aenderbar ist, in WELCHER FOLGE sie
erscheinen und WIE sie heissen — beides ueber eine Zeile je Kategorie::

    DJANGOBASE = {"test_kategorien": ["unit | Unit", "component | Component",
                                      "longrunner | Longrunner (nachts)"]}

oder im Betrieb unter Einstellungen -> djangoBase. Was nicht dasteht, kommt
danach in der eingebauten Reihenfolge; ein unbekannter Slug wird verworfen (er
haette keinen Ordner, in den sich verschieben liesse).

Warum keine freien Kategorien: Ein Name ohne Ordner waere eine Kategorie, in die
man verschieben kann, ohne dass ein Sammellauf sie je faende — genau die stille
Luege, die :mod:`.testverschieben` vermeidet.
"""
from .testbefehle import Testbefehle

__all__ = ["Arten"]


class Arten:
    """Reihenfolge und Namen der Kategorien - aus den Einstellungen."""

    #: Die eingebaute Menge und Reihenfolge (Rueckfall).
    EINGEBAUT = Testbefehle.ARTEN
    NAMEN = Testbefehle.KURZ
    LANG = Testbefehle.ARTNAMEN

    def __init__(self, angabe=None):
        self.namen = {}
        self.folge = []
        self._lesen(angabe)

    def _lesen(self, angabe):
        if isinstance(angabe, str):
            angabe = angabe.splitlines()
        for e in (angabe or []):
            if isinstance(e, dict):
                slug, name = str(e.get("slug") or ""), str(e.get("name") or "")
            else:
                teile = [t.strip() for t in str(e).split("|")]
                slug = teile[0] if teile else ""
                name = teile[1] if len(teile) > 1 else ""
            slug = slug.strip()
            if slug not in self.EINGEBAUT or slug in self.folge:
                continue
            self.folge.append(slug)
            if name:
                self.namen[slug] = name
        # Nicht genannte Kategorien hinten anhaengen - sie verschwinden nicht,
        # nur weil jemand eine Zeile vergessen hat.
        for slug in self.EINGEBAUT:
            if slug not in self.folge:
                self.folge.append(slug)

    @classmethod
    def als_zeilen(cls, angabe):
        u"""Angabe -> Zeilenformat der Oberflaeche („unit | Unit")."""
        if isinstance(angabe, str):
            return angabe.splitlines()
        gelesen = cls(angabe)
        # NUR die ausdruecklich genannten: `liste()` haengt alle uebrigen an,
        # und die haetten im Formular ausgesehen wie eine Vorgabe, die jemand
        # eingetragen hat.
        return ["%s | %s" % (slug, gelesen.name_von(slug))
                for slug in gelesen.folge if slug in gelesen.namen
                or (angabe and slug in [str(x).split("|")[0].strip()
                                        for x in angabe if isinstance(x, str)])]

    @classmethod
    def aus_einstellungen(cls):
        from .conf import conf
        return cls(conf().get("test_kategorien"))

    # ---------------------------------------------------------------- Abfragen

    def liste(self):
        """Die Kategorien-Slugs in der gewuenschten Reihenfolge."""
        return list(self.folge)

    def platz(self, slug):
        return self.folge.index(slug) if slug in self.folge else len(self.folge)

    def name_von(self, slug):
        return self.namen.get(slug) or self.NAMEN.get(slug, slug)

    def lang_von(self, slug):
        u"""Der lange Name („Alle …"-Knoepfe). Eigener Name schlaegt ihn."""
        return self.namen.get(slug) or self.LANG.get(slug, slug)
