# -*- coding: utf-8 -*-
"""Netzsperre — im Prüflauf ist jeder Zugriff nach draußen ein Fehler, keine Frage der Disziplin.

DER ANLASS (gunSlinger, 18.09.2026)
===================================
Dort hängt in ``tests/conftest.py`` eine autouse-Fixture, die den
HTTP-Transport von ``httpx`` auf ``RuntimeError`` biegt. Folge: Kein Test
kann versehentlich eGun oder eine API anfahren — nicht der neue, nicht der
alte, nicht der, den jemand mit einer anderen Basisklasse schreibt. Wer Netz
braucht, mockt; wer vergisst zu mocken, sieht es sofort und nicht erst, wenn
der Testlauf auf der Bahn ohne WLAN 90 s je Fall hängt.

In den Django-Projekten gab es das nicht. `grundtests` SAGT „braucht kein
Netz" — sagt es aber nur. Der Unterschied zwischen einer Regel im Text und
einer Regel im Lauf ist derselbe wie bei den Strukturregeln
(`strukturtests.py`): Text wird diskutiert, Rot wird behoben.

WARUM AM SOCKET UND NICHT AN EINER BIBLIOTHEK
=============================================
``httpx`` zu sperren hilft nichts gegen ``requests``, ``urllib``, ``smtplib``
oder ``imaplib`` — und genau die stecken in assistant (Mail) und shortlongx
(IB-Gateway). Alle gehen durch ``socket.socket.connect``. Dort sitzt die
Sperre, einmal, für alles.

WAS ERLAUBT BLEIBT
==================
- Loopback (``127.0.0.0/8``, ``::1``, ``localhost``): Die Datenbank (Postgres
  in shortlongx), der ``LiveServerTestCase`` und lokale Dienste laufen darüber.
- Unix-Sockets und alles, was kein INET ist.
- Rechner aus ``DJANGOBASE_NETZ_ERLAUBT`` (Liste von Hostnamen/IPs) — für
  Longrunner, die absichtlich ein LAN-Gerät anfahren. Namen werden beim
  Einrichten aufgelöst, weil ``connect`` nur noch die Adresse sieht.
- Alles innerhalb von ``with Netzsperre.erlaubt():`` — für den EINEN Test, der
  es wirklich braucht, und sichtbar im Code.

BENUTZUNG
=========
Einmal je Prozess, bevor der erste Fall läuft — der Testläufer
(`testlaeufer.Testlaeufer`) tut das; wer einen eigenen Läufer hat, ruft es
in dessen ``setup_test_environment``::

    from djangobase.netzsperre import Netzsperre
    Netzsperre.einrichten()

Ein gesperrter Zugriff wirft ``NetzImTestVerboten`` mit Rechner und Port. Die
Ausnahme erbt bewusst NICHT von ``OSError``: ``httpx``/``requests`` fangen
``OSError`` und machen daraus einen Verbindungsfehler mit Wiederholung — die
eigentliche Meldung ginge im dritten Versuch unter.

AUCH ASYNCIO (die Falle auf Windows)
====================================
Der Proactor-Loop verbindet über ``ConnectEx``, nicht über ``socket.connect``
— ein ``httpx.AsyncClient`` ginge an einer reinen Socket-Sperre vorbei.
Deshalb hängt die Prüfung zusätzlich in ``sock_connect`` beider Loop-Arten;
``create_connection`` führt dort hindurch.
"""

import contextlib
import socket
import threading


class NetzImTestVerboten(RuntimeError):
    """Ein Test wollte nach draußen. Die Meldung nennt Ziel und Ausweg."""

    def __init__(self, ziel):
        self.ziel = ziel
        super().__init__(
            "Netzwerkzugriff im Test verboten: %s. Antwort mocken (respx, "
            "unittest.mock) oder den einen Fall in "
            "`with Netzsperre.erlaubt():` stellen; Rechner dauerhaft freigeben "
            "über DJANGOBASE_NETZ_ERLAUBT." % (ziel,)
        )


class Netzsperre:
    """Klassenweiter Schalter — es gibt je Prozess nur einen Socket-Typ."""

    #: Loopback-Namen; Adressen werden über das Präfix erkannt.
    LOKAL = ("localhost", "127.", "::1", "0.0.0.0", "::")

    _original_connect = None
    _original_connect_ex = None
    _original_sock_connect = {}
    _erlaubte = set()
    _freigaben = threading.local()
    #: Jeder gesperrte Versuch als ``(host, port)`` — für die Auswertung im Test.
    gesperrt = []

    @classmethod
    def einrichten(cls, erlaubt=None):
        """Sperre setzen. Mehrfach aufrufen ist harmlos; ``erlaubt`` ergänzt die Liste."""
        for name in list(erlaubt or ()) + cls._aus_einstellungen():
            cls._erlaubte |= cls._aufloesen(str(name).lower())
        if cls._original_connect is not None:
            return
        cls._original_connect = socket.socket.connect
        cls._original_connect_ex = socket.socket.connect_ex
        # Nackte Funktionen, keine Klassenmethoden: Eine gebundene Methode
        # als Klassenattribut bindet sich NICHT erneut an die Socket-Instanz —
        # ``sock.connect(adresse)`` käme dann ohne Socket an.
        original_connect, original_connect_ex = cls._original_connect, cls._original_connect_ex

        def connect(sock, adresse):
            cls._pruefen(adresse)
            return original_connect(sock, adresse)

        def connect_ex(sock, adresse):
            cls._pruefen(adresse)
            return original_connect_ex(sock, adresse)

        socket.socket.connect = connect
        socket.socket.connect_ex = connect_ex
        for loop_klasse in cls._loop_klassen():
            cls._original_sock_connect[loop_klasse] = loop_klasse.sock_connect
            loop_klasse.sock_connect = cls._sock_connect_fuer(loop_klasse)

    @classmethod
    def aufheben(cls):
        """Zurück zum Original — für Tests der Sperre selbst und Läufer-Abbau."""
        if cls._original_connect is None:
            return
        socket.socket.connect = cls._original_connect
        socket.socket.connect_ex = cls._original_connect_ex
        for loop_klasse, original in cls._original_sock_connect.items():
            loop_klasse.sock_connect = original
        cls._original_sock_connect = {}
        cls._original_connect = None
        cls._original_connect_ex = None

    @classmethod
    def zuruecksetzen(cls):
        """Freigaben und Protokoll leeren — für Tests der Sperre selbst."""
        cls._erlaubte = set()
        cls.gesperrt = []

    @classmethod
    def aktiv(cls):
        return cls._original_connect is not None

    @classmethod
    @contextlib.contextmanager
    def erlaubt(cls):
        """Innerhalb dieses Blocks darf DIESER Thread nach draußen."""
        vorher = getattr(cls._freigaben, "tiefe", 0)
        cls._freigaben.tiefe = vorher + 1
        try:
            yield
        finally:
            cls._freigaben.tiefe = vorher

    @classmethod
    def zulaessig(cls, adresse):
        """Darf dieser Socket dorthin? ``adresse`` wie bei ``connect``."""
        if getattr(cls._freigaben, "tiefe", 0) > 0:
            return True
        if not isinstance(adresse, tuple) or len(adresse) < 2:
            return True  # Unix-Socket, Pfad, Sonderfall
        host = str(adresse[0]).lower()
        if host in cls._erlaubte:
            return True
        return host == "" or any(host == n or host.startswith(n) for n in cls.LOKAL)

    @classmethod
    def _pruefen(cls, adresse):
        if cls.zulaessig(adresse):
            return
        ziel = "%s:%s" % (adresse[0], adresse[1])
        cls.gesperrt.append((str(adresse[0]), adresse[1]))
        raise NetzImTestVerboten(ziel)

    @staticmethod
    def _aufloesen(name):
        """Name plus seine Adressen: ``connect`` sieht nur noch die IP, nie den Namen."""
        adressen = {name}
        try:
            for eintrag in socket.getaddrinfo(name, None):
                adressen.add(str(eintrag[4][0]).lower())
        except (OSError, ValueError):
            pass  # unbekannter Name: bleibt als Text drin
        return adressen

    @staticmethod
    def _loop_klassen():
        klassen = []
        for modul, name in (
            ("asyncio.selector_events", "BaseSelectorEventLoop"),
            ("asyncio.proactor_events", "BaseProactorEventLoop"),
        ):
            try:
                klassen.append(getattr(__import__(modul, fromlist=[name]), name))
            except (ImportError, AttributeError):
                continue
        return klassen

    @classmethod
    def _sock_connect_fuer(cls, loop_klasse):
        original = loop_klasse.sock_connect

        async def sock_connect(loop, sock, adresse):
            cls._pruefen(adresse)
            return await original(loop, sock, adresse)

        return sock_connect

    @staticmethod
    def _aus_einstellungen():
        try:
            from django.conf import settings

            return list(getattr(settings, "DJANGOBASE_NETZ_ERLAUBT", None) or [])
        except Exception:  # ohne Django-Einstellungen: leer
            return []
