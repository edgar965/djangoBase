"""Vorlagenvariablen — wie oft eine Seite Variablen aufloest, und welche."""

import collections

from django.template.base import Variable

from .routen import klient
from .befund import Befund, Befundsatz, BefundWerkzeug


class Vorlagenvariablen(BefundWerkzeug):

    slug = 'vorlagen-variablen'
    titel = 'Vorlagen-Variablen'
    zweck = ('Zaehlt beim Rendern einer Seite jede Variablenaufloesung — '
             'insgesamt und je Name. Zeigt damit, ob eine Seite viele '
             'verschiedene Werte anzeigt oder wenige Werte sehr oft.')
    abhilfe = ('Wenn eine Seite langsam ist und das Profil nur Django-Interna '
            'zeigt. Grosse {% for %}-Schleifen kosten pro Durchlauf eine '
            'Aufloesung je Variable — das summiert sich, ohne dass eine einzelne '
            'Funktion auffaellt.')
    befund = ('Eine Einstellungsseite kam auf 70.772 Aufloesungen bei nur ACHT '
             'verschiedenen Namen: vier Namen mal 7.067 Listeneintraege, und der '
             'Baustein war zweimal eingebunden. Sichtbar war davon nichts — die '
             'Liste startete zugeklappt. Nach dem Umbau: 297 Aufloesungen.')
    dauer = 'Sekunden'
    eingabe = ('weg', 'Welche Route? (z. B. /hilfe/versionen/)', '/')

    def pruefen(self, weg='/', **_argumente):
        ziel = (str(weg).strip() or '/')
        if not ziel.startswith('/'):
            ziel = '/' + ziel

        zaehler = collections.Counter()
        echt = Variable._resolve_lookup

        def gezaehlt(selbst, kontext):
            zaehler[selbst.var if isinstance(selbst.var, str) else repr(selbst.var)] += 1
            return echt(selbst, kontext)

        Variable._resolve_lookup = gezaehlt
        try:
            antwort = klient().get(ziel, follow=True)
        finally:
            # Unbedingt zuruecksetzen: Bleibt der Zaehler haengen, verlangsamt
            # er jede weitere Anfrage des laufenden Servers.
            Variable._resolve_lookup = echt

        gesamt = sum(zaehler.values())
        kopf = [
            '%s -> Status %s, %d Byte' % (ziel, antwort.status_code,
                                          len(antwort.content)),
            '%d Aufloesungen, %d verschiedene Namen' % (gesamt, len(zaehler)),
        ]
        if zaehler:
            haeufigster, anzahl = zaehler.most_common(1)[0]
            if anzahl > 500:
                kopf.append('Auffaellig: "%s" wird %d-mal aufgeloest — das ist '
                            'eine Schleife, keine Seite voller Werte.'
                            % (haeufigster, anzahl))
        befunde = [Befund(name, '%d Aufloesungen' % anzahl,
                          gewicht=(Befund.WARNUNG if anzahl > 500
                                   else Befund.HINWEIS))
                   for name, anzahl in zaehler.most_common(30)]
        return Befundsatz(self.titel, kopf, befunde)
