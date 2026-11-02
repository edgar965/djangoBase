"""Azure Translator als umschaltbarer Anbieter für ``djangobase.uebersetzung``.

Eingeschaltet mit ``DJANGOBASE["uebersetzung_anbieter"] = "azure"``; Schlüssel und Region aus den
Django-Settings ``AZURE_TRANSLATOR_KEY`` / ``AZURE_TRANSLATOR_REGION`` (dieselben Namen wie in CleanOrga).
Ohne Einstellung bleibt alles beim kostenlosen Google-Endpunkt — die Projekte ändern sich nicht (Edgar,
31.10.2026, für StayNestor).

Nach CleanOrga ``webinterface/services/azure_translator_dienst.py`` und ``uebersetzer_kette.py`` (dort
gelesen 31.10.2026): REST-Aufruf mit echtem Zeitlimit, ``textType=html`` lässt Tags und
``class="notranslate"`` stehen, HTTP 429 = Kontingent erreicht. Anders als dort über ``urllib`` statt
``requests`` — djangoBase hat ``requests`` nicht als Abhängigkeit. Kontingent laut CleanOrgas Notiz (nach
Microsoft-Doku, 11.08.2026): Stufe F0 2 Mio. Zeichen pro Stunde.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class AzureUebersetzer:
    """Ein Text Deutsch → Zielsprache über die Azure-Translator-API.

    ``uebersetze`` liefert den übersetzten Text oder ``None`` — nie den Originaltext, damit der Aufrufer
    auf den nächsten Anbieter ausweichen kann, statt Deutsch als „Übersetzung“ zu speichern.
    """

    URL = "https://api.cognitive.microsofttranslator.com/translate"
    API_VERSION = "3.0"
    ZEITLIMIT_SEKUNDEN = 6
    #: Codes aus ``uebersetzung.SPRACHEN``, die Azure anders schreibt.
    CODES = {"zh-CN": "zh-Hans"}

    @classmethod
    def aktiv(cls):
        return bool(getattr(settings, "AZURE_TRANSLATOR_KEY", ""))

    @classmethod
    def _anfrage(cls, text, quelle, ziel):
        params = {"api-version": cls.API_VERSION, "from": quelle, "to": cls.CODES.get(ziel, ziel)}
        if "<" in text:
            params["textType"] = "html"
        kopf = {
            "Ocp-Apim-Subscription-Key": getattr(settings, "AZURE_TRANSLATOR_KEY", ""),
            "Content-Type": "application/json",
        }
        region = getattr(settings, "AZURE_TRANSLATOR_REGION", "")
        if region:
            kopf["Ocp-Apim-Subscription-Region"] = region
        return urllib.request.Request(
            f"{cls.URL}?{urllib.parse.urlencode(params)}",
            data=json.dumps([{"Text": text}]).encode("utf-8"),
            headers=kopf,
            method="POST",
        )

    @classmethod
    def uebersetze(cls, text, quelle, ziel):
        if not cls.aktiv() or not text.strip():
            return None
        anfrage = cls._anfrage(text, quelle, ziel)
        try:
            with urllib.request.urlopen(anfrage, timeout=cls.ZEITLIMIT_SEKUNDEN) as antwort:
                daten = json.loads(antwort.read().decode("utf-8"))
        except urllib.error.HTTPError as fehler:
            if fehler.code == 429:
                logger.warning("Azure-Kontingent erreicht (HTTP 429) [%s->%s]", quelle, ziel)
            else:
                logger.warning("Azure-Übersetzung [%s->%s]: HTTP %s", quelle, ziel, fehler.code)
            return None
        except (OSError, ValueError) as fehler:  # Zeitlimit, Netz, kaputtes JSON
            logger.warning("Azure-Übersetzung [%s->%s] fehlgeschlagen: %s", quelle, ziel, fehler)
            return None
        try:
            ergebnis = daten[0]["translations"][0]["text"]
        except (LookupError, TypeError):
            logger.warning("Azure-Übersetzung [%s->%s]: unerwartete Antwort", quelle, ziel)
            return None
        return ergebnis if ergebnis and ergebnis.strip() else None
