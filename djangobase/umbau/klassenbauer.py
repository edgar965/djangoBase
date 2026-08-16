# -*- coding: utf-8 -*-
"""KlassenBauer — Modulfunktionen zu Methoden einer Klasse machen.

Der zweite Schritt nach dem thematischen Schnitt: Aus `def _generate_rig_hull(...)`
wird `Koerperhuelle.rig(...)`. Von Hand ist das stumpfe Arbeit mit hoher
Fehlerquote (Einrueckung, Selbstaufrufe, Importe); hier macht es der AST.

Was das Werkzeug NICHT entscheidet: welche Funktionen zusammengehoeren und wie
die Methoden heissen. Das steht im Aufrufskript.
"""
import ast
import re
from pathlib import Path


class KlassenBauer:
    """Hebt benannte Funktionen aus einem Modul in eine neue Klassendatei."""

    def __init__(self, quelle):
        self.pfad = Path(quelle)
        self.text = self.pfad.read_text(encoding='utf-8')
        self.zeilen = self.text.split('\n')
        self.baum = ast.parse(self.text)

    # ------------------------------------------------------------------ lesen

    def funktion(self, name):
        for k in self.baum.body:
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)) and k.name == name:
                return k
        raise KeyError('%s nicht in %s' % (name, self.pfad.name))

    def block(self, name):
        k = self.funktion(name)
        anfang = min([d.lineno for d in k.decorator_list] or [k.lineno]) - 1
        return '\n'.join(self.zeilen[anfang:k.end_lineno]), anfang, k.end_lineno

    def importzeilen(self):
        raus = {}
        for k in self.baum.body:
            if isinstance(k, (ast.Import, ast.ImportFrom)):
                text = '\n'.join(self.zeilen[k.lineno - 1:k.end_lineno])
                for alias in k.names:
                    raus[alias.asname or alias.name.split('.')[0]] = text
        return raus

    def benutzte_namen(self, name):
        namen = set()
        for k in ast.walk(self.funktion(name)):
            if isinstance(k, ast.Name):
                namen.add(k.id)
            elif isinstance(k, ast.Attribute):
                ziel = k
                while isinstance(ziel, ast.Attribute):
                    ziel = ziel.value
                if isinstance(ziel, ast.Name):
                    namen.add(ziel.id)
        return namen

    # ------------------------------------------------------------- umschreiben

    @staticmethod
    def _methode(text, alt, neu):
        """Funktionstext -> eingerueckte statische Methode."""
        text = re.sub(r'^def %s\(' % re.escape(alt), 'def %s(' % neu, text, count=1)
        eingerueckt = '\n'.join(('    ' + z) if z.strip() else z
                                for z in text.split('\n'))
        return '    @staticmethod\n' + eingerueckt

    @staticmethod
    def _aufrufe_umbiegen(text, klasse, zuordnung):
        for alt, neu in zuordnung.items():
            text = re.sub(r'(?<![\w.])%s\(' % re.escape(alt),
                          '%s.%s(' % (klasse, neu), text)
        return text

    # ---------------------------------------------------------------- schreiben

    def klasse_bauen(self, klasse, ziel, kopf, zuordnung, ebenen_tiefer=0,
                     zusatz_importe=(), entfernen=True):
        """zuordnung: {alter Funktionsname: neuer Methodenname}"""
        importe = self.importzeilen()
        gebraucht, bloecke = set(), []
        for alt in zuordnung:
            text, a, e = self.block(alt)
            gebraucht |= self.benutzte_namen(alt)
            bloecke.append((alt, text, a, e))

        kopfteile = [kopf.rstrip(), '']
        # Mehrere gebrauchte Namen koennen AUS DERSELBEN Importzeile stammen
        # (`from x import a, b, c`) — sonst steht die Zeile dreimal da.
        gesehen = set()
        for name in sorted(gebraucht):
            if name not in importe:
                continue
            zeile = importe[name]
            if ebenen_tiefer and zeile.lstrip().startswith('from .'):
                zeile = zeile.replace('from .', 'from .' + '.' * ebenen_tiefer, 1)
            if zeile in gesehen:
                continue
            gesehen.add(zeile)
            kopfteile.append(zeile)
        kopfteile += list(zusatz_importe)
        kopfteile.append('')
        kopfteile.append('')
        kopfteile.append('class %s:' % klasse)
        kopfteile.append('    """%s"""' % kopf.strip().split('\n')[1].strip('" '))
        kopfteile.append('')

        for alt, text, _a, _e in sorted(bloecke, key=lambda b: b[2]):
            if ebenen_tiefer:
                text = '\n'.join(
                    z.replace('from .', 'from .' + '.' * ebenen_tiefer, 1)
                    if z.lstrip().startswith('from .') else z
                    for z in text.split('\n'))
            text = self._aufrufe_umbiegen(text, klasse,
                                          {k: v for k, v in zuordnung.items()
                                           if k != alt})
            kopfteile.append(self._methode(text, alt, zuordnung[alt]))
            kopfteile.append('')

        neu = '\n'.join(kopfteile).rstrip() + '\n'
        ast.parse(neu)

        rest = list(self.zeilen)
        if entfernen:
            for _alt, _text, a, e in sorted(bloecke, key=lambda b: -b[2]):
                del rest[a:e]
        resttext = self._aufrufe_umbiegen('\n'.join(rest), klasse, zuordnung)
        ast.parse(resttext)

        Path(ziel).parent.mkdir(parents=True, exist_ok=True)
        Path(ziel).write_text(neu, encoding='utf-8')
        self.pfad.write_text(resttext, encoding='utf-8')
        self.text, self.zeilen = resttext, resttext.split('\n')
        self.baum = ast.parse(resttext)
        return {'klasse': klasse, 'ziel': str(ziel), 'methoden': len(bloecke),
                'zeilen_neu': neu.count('\n') + 1,
                'zeilen_rest': resttext.count('\n') + 1}
