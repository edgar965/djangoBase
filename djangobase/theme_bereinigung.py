import re

from .theme_stil import ThemeStil


class ThemeBereinigung:
    """Prüft die Anpassung der Themes, bevor sie in den Store geht (``ThemeStil``).

    Durch kommt nur, was ``css()`` gefahrlos in einen Stilblock schreiben kann: Themes des Projekts, bekannte
    Farben als ``#rrggbb``, bekannte Rollen mit ihren Attributen (Art aus der Liste, Größe 7–40 px, Gewicht
    ``normal``/``fett``, kursiv nur ``true``). Alles andere fällt still weg — die Seite schickt nur Felder,
    die sie selbst gebaut hat; was dort nicht passt, war kein Bedienfehler. Leere Themes und Rollen fallen
    weg.
    """

    HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
    GROESSE_MIN = 7
    GROESSE_MAX = 40

    def __init__(self, themes):
        self.themes = set(themes)

    def bereinigen(self, daten):
        raus = {}
        for theme, werte in (daten or {}).items() if isinstance(daten, dict) else ():
            if theme not in self.themes or not isinstance(werte, dict):
                continue
            eins = {
                "farben": self._farben(werte.get("farben")),
                "schriften": self._schriften(werte.get("schriften")),
            }
            eins = {k: v for k, v in eins.items() if v}
            if eins:
                raus[theme] = eins
        return raus

    def _farben(self, farben):
        if not isinstance(farben, dict):
            return {}
        return {
            k: v.lower()
            for k, v in farben.items()
            if k in ThemeStil.FARBEN and isinstance(v, str) and self.HEX.match(v)
        }

    def _schriften(self, schriften):
        if not isinstance(schriften, dict):
            return {}
        raus = {}
        for rolle, s in schriften.items():
            if rolle not in ThemeStil.ROLLEN or not isinstance(s, dict):
                continue
            erlaubt = ThemeStil.ROLLEN[rolle][2]
            eins = {}
            if "art" in erlaubt and s.get("art") in ThemeStil.STAPEL:
                eins["art"] = s["art"]
            groesse = self._zahl(s.get("groesse"))
            if "groesse" in erlaubt and groesse is not None:
                eins["groesse"] = groesse
            farbe = s.get("farbe")
            if "farbe" in erlaubt and isinstance(farbe, str) and self.HEX.match(farbe):
                eins["farbe"] = farbe.lower()
            if "gewicht" in erlaubt and s.get("gewicht") in ThemeStil.GEWICHTE:
                eins["gewicht"] = s["gewicht"]
            if "kursiv" in erlaubt and s.get("kursiv") is True:
                eins["kursiv"] = True
            if eins:
                raus[rolle] = eins
        return raus

    def _zahl(self, wert):
        if isinstance(wert, bool) or not isinstance(wert, (int, float, str)):
            return None
        try:
            zahl = round(float(wert), 2)
        except ValueError:
            return None
        if not self.GROESSE_MIN <= zahl <= self.GROESSE_MAX:
            return None
        return int(zahl) if zahl == int(zahl) else zahl
