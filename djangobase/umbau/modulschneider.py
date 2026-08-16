# -*- coding: utf-8 -*-
"""ModulSchneider — Funktionen aus einer grossen Datei in ein neues Modul heben.

Von Hand ist das die fehleranfaelligste Arbeit des ganzen Umbaus: Man vergisst
einen Import, uebersieht eine Modulkonstante, laesst eine Funktion doppelt
stehen. Deshalb macht es ein Werkzeug, und zwar ueber den AST:

    * Die Bloecke werden mit `lineno`/`end_lineno` geschnitten (Dekoratoren
      inbegriffen), nicht mit Textsuche.
    * Die noetigen Importe werden aus den TATSAECHLICH benutzten Namen
      hergeleitet, nicht geraten.
    * Modulweite Konstanten, die der verschobene Code liest, werden gemeldet —
      sie muessen mitgehen oder in ein gemeinsames Modul.
    * Nach dem Schnitt wird beides geparst; nur wenn das gelingt, wird
      geschrieben.
"""
import ast
from pathlib import Path


class ModulSchneider:
    """Schneidet benannte Definitionen aus einer Quelldatei heraus."""

    def __init__(self, quelle):
        self.pfad = Path(quelle)
        self.text = self.pfad.read_text(encoding='utf-8')
        self.zeilen = self.text.split('\n')
        self.baum = ast.parse(self.text)

    # ------------------------------------------------------------------ lesen

    def definitionen(self):
        return {k.name: k for k in self.baum.body
                if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef))}

    def importzeilen(self):
        """{gebundener Name: Quelltextzeile(n) des Imports}"""
        raus = {}
        for k in self.baum.body:
            if not isinstance(k, (ast.Import, ast.ImportFrom)):
                continue
            text = '\n'.join(self.zeilen[k.lineno - 1:k.end_lineno])
            for alias in k.names:
                name = alias.asname or alias.name.split('.')[0]
                raus[name] = text
        return raus

    def konstanten(self):
        """{Name: Quelltext} aller Modulzuweisungen auf oberster Ebene."""
        raus = {}
        for k in self.baum.body:
            if isinstance(k, ast.Assign):
                for ziel in k.targets:
                    if isinstance(ziel, ast.Name):
                        raus[ziel.id] = '\n'.join(
                            self.zeilen[k.lineno - 1:k.end_lineno])
            elif isinstance(k, ast.AnnAssign) and isinstance(k.target, ast.Name):
                raus[k.target.id] = '\n'.join(
                    self.zeilen[k.lineno - 1:k.end_lineno])
        return raus

    @staticmethod
    def benutzte_namen(knoten):
        namen = set()
        for k in ast.walk(knoten):
            if isinstance(k, ast.Name):
                namen.add(k.id)
            elif isinstance(k, ast.Attribute):
                # `settings.MEDIA_ROOT` -> 'settings'
                ziel = k
                while isinstance(ziel, ast.Attribute):
                    ziel = ziel.value
                if isinstance(ziel, ast.Name):
                    namen.add(ziel.id)
        return namen

    @staticmethod
    def gebundene_namen(knoten):
        u"""Namen, die INNERHALB des Blocks entstehen — also nie „offen" sind.

        WARUM (17.08.2026, beim ersten Kommandozeilenlauf gemessen): Der Bericht
        meldete `OFFEN: p, pfad, x` fuer eine Funktion `gross(pfad)` mit der
        lokalen Variablen `p`. Parameter und lokale Namen sind kein offener
        Bedarf — und die OFFEN-Liste ist die wichtigste Ausgabe des Werkzeugs.
        Fehlalarme darin verdecken den echten Fall, siehe
        `~/.claude/rules/analysewerkzeuge.md`.
        """
        namen = set()
        for k in ast.walk(knoten):
            if isinstance(k, ast.arg):
                namen.add(k.arg)
            elif isinstance(k, ast.Name) and isinstance(k.ctx, (ast.Store,
                                                                ast.Del)):
                namen.add(k.id)                 # Zuweisung, for-Ziel, walrus
            elif isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.ClassDef)):
                namen.add(k.name)               # verschachtelte Definition
            elif isinstance(k, ast.ExceptHandler) and k.name:
                namen.add(k.name)               # `except X as fehler`
            elif isinstance(k, (ast.Import, ast.ImportFrom)):
                for teil in k.names:            # Import im Rumpf
                    namen.add((teil.asname or teil.name).split('.')[0])
        return namen

    # --------------------------------------------------------------- schneiden

    def bloecke(self, namen):
        """[(name, quelltext, startzeile, endzeile)] in Dateireihenfolge."""
        defs = self.definitionen()
        fehlend = [n for n in namen if n not in defs]
        if fehlend:
            raise KeyError('nicht in %s: %s' % (self.pfad.name,
                                                ', '.join(fehlend)))
        raus = []
        for name in namen:
            k = defs[name]
            anfang = min([d.lineno for d in k.decorator_list] or [k.lineno]) - 1
            raus.append((name, '\n'.join(self.zeilen[anfang:k.end_lineno]),
                         anfang, k.end_lineno))
        raus.sort(key=lambda e: e[2])
        return raus

    def bedarf(self, namen):
        """(noetige Importe, noetige Konstanten, offene Namen)."""
        defs = self.definitionen()
        benutzt, gebunden = set(), set()
        for name in namen:
            benutzt |= self.benutzte_namen(defs[name])
            gebunden |= self.gebundene_namen(defs[name])
        importe = self.importzeilen()
        konstanten = self.konstanten()
        noetige_importe = {n: importe[n] for n in benutzt if n in importe}
        noetige_konstanten = {n: konstanten[n] for n in benutzt
                              if n in konstanten and n not in importe}
        # `dir(__builtins__)` waere hier falsch: In einem IMPORTIERTEN Modul ist
        # `__builtins__` ein dict, `dir()` liefert also `keys`/`items`/… statt
        # `len`/`print`/`range`. Nur im direkt gestarteten Skript ist es das
        # Modul — der Filter griff also je nach Aufrufart oder gar nicht.
        import builtins
        eingebaut = set(dir(builtins))
        offen = {n for n in benutzt
                 if n not in importe and n not in konstanten and n not in defs
                 and n not in gebunden and n not in eingebaut
                 and not n.startswith('__')}
        return noetige_importe, noetige_konstanten, offen

    @staticmethod
    def _ebene_anheben(zeile, ebenen=1):
        """`from .models import X` -> `from ..models import X`.

        Das Zielmodul liegt eine Paketebene tiefer als die Quelle. pyflakes
        merkt davon nichts (es prueft keine Importpfade), Django dagegen sehr
        wohl — und zwar erst beim ersten Aufruf des Endpunkts."""
        if not zeile.lstrip().startswith('from .'):
            return zeile
        return zeile.replace('from .', 'from .' + '.' * ebenen, 1)

    def schreiben(self, namen, ziel, kopf, zusatz_importe=(), trocken=False,
                  ebenen_tiefer=0):
        """Neues Modul schreiben und die Bloecke aus der Quelle entfernen."""
        bloecke = self.bloecke(namen)
        importe, konstanten, offen = self.bedarf(namen)

        teile = [kopf.rstrip(), '']
        for zeile in sorted(set(importe.values())):
            teile.append(self._ebene_anheben(zeile, ebenen_tiefer)
                         if ebenen_tiefer else zeile)
        for zeile in zusatz_importe:
            teile.append(zeile)
        teile.append('')
        if konstanten:
            teile.append('')
            for name in sorted(konstanten):
                teile.append(konstanten[name])
            teile.append('')
        for _name, text, _a, _e in bloecke:
            teile.append('')
            if ebenen_tiefer:
                # Auch die Importe INNERHALB der Funktionen anheben — in dieser
                # Datei stehen viele `from .models import ...` erst im Rumpf.
                text = '\n'.join(self._ebene_anheben(z, ebenen_tiefer)
                                 for z in text.split('\n'))
            teile.append(text)
            teile.append('')
        neu = '\n'.join(teile).rstrip() + '\n'
        neu = neu.replace('\n\n\n\n', '\n\n\n')
        ast.parse(neu)                       # Gegenprobe

        rest = list(self.zeilen)
        for _name, _text, a, e in sorted(bloecke, key=lambda b: -b[2]):
            del rest[a:e]
        resttext = '\n'.join(rest)
        ast.parse(resttext)                  # Gegenprobe

        if not trocken:
            zielpfad = Path(ziel)
            zielpfad.parent.mkdir(parents=True, exist_ok=True)
            zielpfad.write_text(neu, encoding='utf-8')
            self.pfad.write_text(resttext, encoding='utf-8')
            self.text, self.zeilen = resttext, resttext.split('\n')
            self.baum = ast.parse(resttext)
        return {'ziel': str(ziel), 'funktionen': len(bloecke),
                'zeilen_neu': neu.count('\n') + 1,
                'zeilen_rest': resttext.count('\n') + 1,
                'importe': sorted(importe), 'konstanten': sorted(konstanten),
                'offen': sorted(offen)}


def main():
    u"""Kommandozeile — Probelauf ist die Vorgabe.

        python -m djangobase.umbau.modulschneider gross.py neu.py \\
               --namen a,b [--kopf "..."] [--schreiben]

    Der Probelauf sagt vor allem, was OFFEN bleibt: Namen, die der verschobene
    Code liest, aber weder Import noch Konstante sind. Wer die uebersieht,
    bekommt ein Modul, das sauber parst und beim ersten Aufruf mit `NameError`
    stirbt — siehe `~/.claude/rules/es-module-stumme-fehler.md`, dieselbe
    Fehlerklasse in Python.
    """
    import sys
    argumente = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(argumente) < 2:
        raise SystemExit(main.__doc__)
    namen, kopf = [], '# -*- coding: utf-8 -*-'
    schreiben = '--schreiben' in sys.argv
    for a in sys.argv[1:]:
        if a.startswith('--namen'):
            namen = [n.strip() for n in a.split('=', 1)[-1].split(',') if n.strip()]
        elif a.startswith('--kopf'):
            kopf = a.split('=', 1)[-1]
    if not namen:
        raise SystemExit('--namen fehlt: welche Definitionen sollen umziehen?')
    bericht = ModulSchneider(argumente[0]).schreiben(
        namen, argumente[1], kopf, trocken=not schreiben)
    print('%s  <- %d Definitionen, %d Zeilen (Rest: %d)'
          % (bericht['ziel'], bericht['funktionen'], bericht['zeilen_neu'],
             bericht['zeilen_rest']))
    print('  Importe:    %s' % (', '.join(bericht['importe']) or '—'))
    print('  Konstanten: %s' % (', '.join(bericht['konstanten']) or '—'))
    print('  OFFEN:      %s' % (', '.join(bericht['offen']) or '—'))
    if not schreiben:
        print('  (Probelauf — mit --schreiben wird geschrieben)')


if __name__ == '__main__':
    main()
