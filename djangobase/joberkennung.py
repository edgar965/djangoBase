# -*- coding: utf-8 -*-
u"""Die Jobs eines Projekts selbst finden - ohne dass jemand sie eintraegt.

Angelegt am 26.08.2026 (Ansage Edgar): "das soll für alle Projekte per
Knopfdruck die Jobs ermitteln und die Übersicht erzeugen".

WARUM NICHT EINTRAGEN LASSEN
============================
``djangobase.jobs`` verlangt, dass jedes Projekt seine Jobs in
``AppConfig.ready()`` anmeldet. Fuer Daemon-Threads ist das richtig - sie
haben einen Zustand, den nur das Projekt kennt. Fuer die WIEDERKEHRENDEN
Ablaeufe ist es untauglich: assistant hat 93 Management-Commands, und
kein Mensch traegt die von Hand ein. Was nicht eingetragen ist, faellt aus
der Uebersicht - und zwar unbemerkt.

Django fuehrt bereits ein Verzeichnis aller Commands
(``get_commands()``). Diese Klasse liest es, wirft heraus, was kein Job
ist, und ergaenzt die angemeldeten Daemons aus der Registry.

WAS KEIN JOB IST
================
- Django-eigene Befehle (migrate, runserver, shell, collectstatic …):
  Werkzeuge des Entwicklers, keine Ablaeufe des Projekts.
- Namen mit fuehrendem Unterstrich: In assistant sind das Basisklassen
  (``_base_indexer``, ``_musicgen_basis``) - importierbar, aber nicht
  aufrufbar.
- Was das Projekt selbst ausschliesst (``DJANGOBASE['jobs_ausschluss']``).
"""
import logging

logger = logging.getLogger(__name__)

__all__ = ['Joberkennung']


class Joberkennung(object):
    u"""Findet die Jobs des laufenden Projekts.

        gefunden = Joberkennung().ermitteln()
        # [{'kennung': 'mail_sync', 'name': 'mail_sync', 'app': 'mail',
        #   'art': 'befehl', 'hilfe': 'Synchronisiert …'}, …]
    """

    #: Apps, deren Commands nie ein Job des Projekts sind.
    FREMDE_APPS = (
        'django.core', 'django.contrib', 'djangobase',
        'allauth', 'rest_framework', 'debug_toolbar',
    )

    #: Namen, die auch aus einer Projekt-App kein Job sind.
    NIE = ('test', 'testserver', 'runserver', 'shell', 'dbshell', 'migrate',
           'makemigrations', 'collectstatic', 'createsuperuser',
           'changepassword', 'squashmigrations', 'flush', 'loaddata',
           'dumpdata', 'sqlmigrate', 'showmigrations', 'check', 'diffsettings')

    def __init__(self, ausschluss=None):
        self.ausschluss = set(ausschluss or self._ausschluss_aus_einstellungen())

    @staticmethod
    def _ausschluss_aus_einstellungen():
        from django.conf import settings

        angabe = (getattr(settings, 'DJANGOBASE', {}) or {}).get('jobs_ausschluss')
        if not angabe:
            return []
        if isinstance(angabe, str):
            return [t.strip() for t in angabe.replace(',', '\n').split('\n')
                    if t.strip()]
        return list(angabe)

    # ----------------------------------------------------------- ermitteln
    def ermitteln(self):
        u"""Alle Jobs: erst die Befehle, dann die angemeldeten Daemons."""
        gefunden = self.befehle()
        vorhanden = {j['kennung'] for j in gefunden}
        for daemon in self.daemons():
            if daemon['kennung'] not in vorhanden:
                gefunden.append(daemon)
        gefunden.sort(key=lambda j: (j['art'], j['app'], j['kennung']))
        return gefunden

    def befehle(self):
        u"""Die Management-Commands der Projekt-Apps."""
        from django.core.management import get_commands

        raus = []
        try:
            alle = get_commands()
        except Exception:
            logger.exception('Joberkennung.befehle: get_commands scheiterte')
            return raus

        for name, app in sorted(alle.items()):
            if not self.ist_job(name, app):
                continue
            raus.append({
                'kennung': name,
                'name': name,
                'app': app.split('.')[-1] if isinstance(app, str) else str(app),
                'art': 'befehl',
                'hilfe': self._hilfe(name),
            })
        return raus

    def ist_job(self, name, app):
        if name in self.NIE or name in self.ausschluss:
            return False
        if name.startswith('_'):
            return False
        if not isinstance(app, str):
            # Bei Commands aus einem geladenen Modul steht hier keine
            # App - dann gilt sie als Projekt-App.
            return True
        return not any(app.startswith(f) for f in self.FREMDE_APPS)

    @staticmethod
    def _hilfe(name):
        u"""Die erste Zeile der Command-Hilfe.

        Der Import kann alles Moegliche tun (Modelle laden, Bibliotheken
        ziehen). Ein Fehler dabei darf die Uebersicht nicht kosten - dann
        bleibt die Beschreibung eben leer.
        """
        try:
            from django.core.management import load_command_class, get_commands

            app = get_commands().get(name)
            if not isinstance(app, str):
                return ''
            befehl = load_command_class(app, name)
            text = (getattr(befehl, 'help', '') or '').strip()
            return text.split('\n')[0][:200]
        except Exception:
            logger.debug('Joberkennung._hilfe: %r nicht ladbar', name,
                         exc_info=True)
            return ''

    @staticmethod
    def daemons():
        u"""Die in ``djangobase.jobs`` angemeldeten Hintergrund-Jobs.

        Sie kommen aus der bestehenden Registry - shortlongx meldet dort
        seine Runner an (``dashboard/jobs_anmeldung.py``). Diese Seite
        erfindet dafuer nichts Neues, sie liest mit.
        """
        try:
            from . import jobs as registry

            return [{
                'kennung': j['slug'],
                'name': j['name'],
                'app': '',
                'art': 'daemon',
                'hilfe': j.get('beschreibung') or '',
                'zustand': j.get('state'),
            } for j in registry.snapshot()]
        except Exception:
            logger.exception('Joberkennung.daemons: Registry nicht lesbar')
            return []
