"""Hilfe -> Skills: Werkzeugkasten und Lehren aus Code-Reviews.

Zwei Teile, beide zum Wiederverwenden gedacht:

* **Werkzeuge** — Analysen, die in JEDEM djangoBase-Projekt laufen (Vorlagen,
  Routen, Modulgroessen, Duplikate, Namen, Abhaengigkeiten). Auswahl per
  Ankreuzfeld, Start einzeln oder als Stapel; die Ergebnisse landen als
  Klartext in einer Textbox, damit man sie einer Claude-Sitzung als
  Arbeitsgrundlage geben kann.
* **Lehren** — die Regeln aus einem grossen Durchgang, als Ankreuzliste
  (Vorgabe: an). Aus den angekreuzten baut die Seite einen Auftragstext.

Sicherheit: Gestartet wird nur, was in der Registry steht — die Kennungen aus
der Anfrage werden dagegen geprueft, nicht ausgefuehrt. Die Werkzeuge rufen
ausschliesslich GET-Routen auf.

Der Stapellauf antwortet mit `render`, nicht mit einer Weiterleitung: Die
Textbox schickt ihren bisherigen Inhalt mit und bekommt ihn ergaenzt zurueck.
Damit braucht die Seite keinen Serverzustand — und ein zweiter Lauf haengt an,
statt zu ueberschreiben.
"""

from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.views import View

from ..mixins import ZugriffMixin
from ..skills import werkzeug_finden, werkzeuge
from ..skills.lehren import BEREICHE, LEHREN, Lehrenstand
from ..skills.werkzeug import Ausgabe, Werkzeug


class SkillsView(ZugriffMixin, View):

    def get(self, request):
        # Deep-Link `?run=<slug>` bleibt: ein einzelnes Werkzeug per Adresse.
        ausgabe = Ausgabe()
        gelaufen = []
        slug = request.GET.get('run', '')
        if slug:
            gelaufen = self._laufen([slug], request.GET, ausgabe)

        if request.GET.get('auftrag') == '1':
            # Als Textdatei: Der Auftragstext wird kopiert, nicht gelesen.
            return HttpResponse(Lehrenstand.auftragstext(),
                                content_type='text/plain; charset=utf-8')

        return self._seite(request, ausgabe.text(), gelaufen)

    def post(self, request):
        if request.POST.get('aktion') == 'lehren':
            Lehrenstand.speichern(set(request.POST.getlist('lehre')))
            return redirect(request.path + '#lehren')

        ausgabe = Ausgabe(request.POST.get('ausgabe', ''))
        gelaufen = self._laufen(request.POST.getlist('werkzeug'),
                                request.POST, ausgabe)
        return self._seite(request, ausgabe.text(), gelaufen)

    # ------------------------------------------------------------------ intern

    def _laufen(self, slugs, daten, ausgabe):
        """Die gewaehlten Werkzeuge in Registry-Reihenfolge ausfuehren."""
        gewaehlt = [w for w in werkzeuge() if w.slug in set(slugs)]
        for werkzeug in gewaehlt:
            argumente = {}
            if werkzeug.eingabe:
                feld = werkzeug.eingabe[0]
                argumente[feld] = (daten.get('arg_%s' % werkzeug.slug)
                                   or daten.get(feld) or werkzeug.eingabe[2])
            ergebnis = werkzeug.laufen(**argumente)
            ausgabe.anhaengen(werkzeug, ergebnis,
                              datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
        return [w.slug for w in gewaehlt]

    def _seite(self, request, ausgabetext, gelaufen):
        stand = Lehrenstand.laden()
        return render(request, 'djangobase/hilfe/skills.html', {
            'aktiv': 'skills',
            'tabelle': self._tabelle(gelaufen),
            'ausgabe': ausgabetext,
            'gelaufen': gelaufen,
            'bereiche': self._bereiche(stand),
            'anzahl_aktiv': sum(1 for an in stand.values() if an),
            'anzahl_lehren': len(LEHREN),
            'anzahl_werkzeuge': len(werkzeuge()),
            # Sichtbar machen, was NICHT geprueft wird — eine Liste ohne diese
            # Angabe liest sich wie eine vollstaendige Bestandsaufnahme.
            'ausnahmen': ', '.join(Werkzeug.ausnahmen()),
        })

    def _tabelle(self, gelaufen):
        """Struktur fuer djangobase/_tabelle.html (Sortierung + Spaltenbreiten).

        Die Zellen enthalten Formularfelder. Das ist erlaubt, weil die Tabelle
        innerhalb des Formulars steht — die Sortierung im Browser verschiebt nur
        die Zeilen, die Felder bleiben dieselben.
        """
        zeilen = []
        for werkzeug in werkzeuge():
            zeilen.append({
                'klasse': 'db-hervor' if werkzeug.slug in gelaufen else '',
                'zellen': [
                    {'html': ('<input type="checkbox" name="werkzeug" value="%s"'
                              ' class="sk-wahl"%s>'
                              % (escape(werkzeug.slug),
                                 ' checked' if werkzeug.slug in gelaufen else '')),
                     'sort': 1 if werkzeug.slug in gelaufen else 0,
                     'klasse': 'sk-mitte'},
                    {'html': ('<span class="sk-wname">%s</span>'
                              '<span class="sk-dauer">%s</span>%s'
                              % (escape(werkzeug.name), escape(werkzeug.dauer),
                                 ('<span class="sk-ruft">ruft Endpunkte auf</span>'
                                  if werkzeug.ruft_endpunkte_auf else ''))),
                     'sort': werkzeug.name},
                    {'html': escape(werkzeug.zweck)},
                    {'html': escape(werkzeug.wann), 'klasse': 'sk-leise'},
                    {'html': escape(werkzeug.beleg), 'klasse': 'sk-beleg'},
                    {'html': self._eingabefeld(werkzeug), 'klasse': 'sk-mitte'},
                    {'html': ('<button type="submit" name="werkzeug" value="%s"'
                              ' class="sk-run"><i class="bi bi-play-fill"></i>'
                              ' Start</button>' % escape(werkzeug.slug)),
                     'klasse': 'sk-mitte'},
                ],
            })
        return {
            'key': 'db-skills',
            'spalten': [
                {'label': ('<input type="checkbox" id="sk-alle" '
                           'title="Alle aus- oder abwählen">'),
                 'key': 'wahl', 'sortAus': True},
                {'label': 'Werkzeug', 'key': 'name'},
                {'label': 'Was es tut', 'key': 'zweck'},
                {'label': 'Wann einsetzen', 'key': 'wann'},
                {'label': 'Was es gefunden hat', 'key': 'beleg'},
                {'label': 'Vorgabe', 'key': 'eingabe', 'sortAus': True,
                 'titel': 'Zusatzangabe für dieses Werkzeug'},
                {'label': 'Start', 'key': 'start', 'sortAus': True},
            ],
            'zeilen': zeilen,
            'leer': 'keine Werkzeuge registriert',
        }

    @staticmethod
    def _eingabefeld(werkzeug):
        if not werkzeug.eingabe:
            return '<span class="sk-leise">—</span>'
        feld, beschriftung, vorgabe = werkzeug.eingabe
        return ('<input type="text" name="arg_%s" value="%s" size="8" '
                'title="%s" class="sk-arg">'
                % (escape(werkzeug.slug), escape(vorgabe), escape(beschriftung)))

    @staticmethod
    def _bereiche(stand):
        """Lehren nach Bereich gruppiert, in der Reihenfolge von BEREICHE."""
        gruppen = []
        for bereich in BEREICHE:
            lehren = [{'lehre': lehre, 'an': stand.get(lehre.slug, True)}
                      for lehre in LEHREN if lehre.bereich == bereich]
            if lehren:
                gruppen.append({'name': bereich, 'lehren': lehren,
                                'anzahl': len(lehren)})
        return gruppen
