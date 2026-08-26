# -*- coding: utf-8 -*-
u"""EigenesWerkzeug - Werkzeug mit den Ausschluessen, die jedes Projekt braucht.

WARUM DIESE ERGAENZUNG (belegt beim ersten Lauf, 17.08.2026)
============================================================
``Werkzeug.ausgeschlossen`` kennt venv, Migrationen und Sicherungsordner - nicht
aber die Ablagen, die in gewachsenen Projekten danebenliegen: mitgelieferter
Fremdcode (``vendor``), Modellgewichte (``models``), Arbeitsreste (``tmp``),
uebersetzte Zwischenstaende (``unsloth_compiled_cache``).

Ohne sie meldete das Protokoll-Werkzeug beim ersten Lauf **3.017 Stellen**, die
allermeisten aus Fremdcode. Das ist die teuerste Sorte Fehlalarm: Sie verdeckt
die echten Befunde, statt nur danebenzuliegen.

Ergaenzbar bleibt es je Projekt über ``DJANGOBASE["skills2_ignorieren"]`` - die
Liste hier ist nur die Grundausstattung.
"""
from .werkzeug import Werkzeug

__all__ = ["EigenesWerkzeug", "ZUSATZ_RAUS"]

#: STEHT JETZT IN ``werkzeug.AUSGESCHLOSSEN`` (17.08.2026).
#:
#: Diese Liste galt nur fuer die drei Werkzeuge auf DIESER Basis. Die anderen
#: achtundzwanzig erben direkt von ``Werkzeug`` und durchsuchten weiter
#: ``vendor/``, ``unsloth_compiled_cache/`` und ``diktator/`` mit — 40 % aller
#: Befunde kamen von dort. Der Name bleibt als leere Menge erhalten, weil
#: Projekte ihn importieren koennten; ergaenzen laesst sich weiterhin ueber
#: ``DJANGOBASE["skills2_ignorieren"]``.
ZUSATZ_RAUS = frozenset()


class EigenesWerkzeug(Werkzeug):
    """Basis der Werkzeuge zu den Kriterien 16 und 17.

    Sie unterscheidet sich von ``Werkzeug`` nur noch durch ``hat_code()`` —
    die Ausschluesse sind dort zusammengefasst, wo alle Werkzeuge sie sehen."""

    def hat_code(self):
        """Gibt es im geprueften Baum ueberhaupt Quelltext außer Tests?

        Zwei dieser Werkzeuge beantworten Fragen über das GANZE Projekt
        („keine Tests", „diese Seite hat keinen Test") und holen sich einen Teil
        ihrer Antwort nicht aus den Dateien, sondern aus Django selbst - der
        URL-Tabelle. Auf einem leeren Verzeichnis melden sie dann Befunde über
        ein Projekt, das dort gar nicht liegt. Das ist ein Fehlalarm, und die
        Gegenprobe „läuft auf leerem Projekt ohne Befund" faengt ihn (17.08.2026).
        """
        for d in self.dateien():
            kurz = d.name.rsplit("/", 1)[-1]
            if kurz == "__init__.py" or "/tests" in "/" + d.name:
                continue
            return True
        return False
