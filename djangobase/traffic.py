"""Traffic-Erfassung: Middleware + Helfer (Land, Gerät, Bot, Besucher-Hash).

Aktivierung pro Projekt (opt-in, Assistant bleibt unberührt) in settings.py:

    MIDDLEWARE = [
        ...,
        "djangobase.traffic.TrafficMiddleware",   # ganz ans Ende
    ]

Die Middleware ist fail-silent: Ein Fehler bei der Erfassung darf nie eine
Seite crashen. Erfasst werden nur erfolgreiche GET-Antworten (HTML + JSON);
/static/ und /media/ liefert nginx direkt aus und tauchen nicht auf.

Länder-Lookup offline über eine mmdb-Datei (kein externer Aufruf):
DB-IP "IP to Country Lite" (CC BY 4.0, https://db-ip.com) + Paket `maxminddb`.
Pfad über DJANGOBASE["traffic_geo_db"], Default BASE_DIR/daten/
dbip-country-lite.mmdb. Fehlt Datei oder Paket, bleibt das Land einfach leer.
"""
import hashlib
import re
from datetime import date
from urllib.parse import urlparse

from django.conf import settings

from .conf import conf

# Crawler/Monitoring/Tools – werden markiert und in der Statistik ausgeblendet.
BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|scan|preview|monitor|pingdom|uptime|lighthouse|"
    r"headless|curl|wget|python|httpx|libwww|go-http|java/|okhttp|"
    r"facebookexternalhit|whatsapp|telegram|skype|semrush|ahrefs|mj12|"
    r"bytespider|petalbot|yandex|baiduspider|duckduck|gptbot|claudebot",
    re.IGNORECASE)
_TABLET_RE = re.compile(r"ipad|tablet|kindle|silk", re.IGNORECASE)
_MOBIL_RE = re.compile(r"mobi|iphone|ipod|windows phone", re.IGNORECASE)

_geo_reader = None
_geo_versucht = False


def client_ip(request):
    """Echte Client-IP hinter dem nginx-Proxy (X-Real-IP → X-Forwarded-For →
    REMOTE_ADDR). Wird NUR für Land-Lookup und Tages-Hash benutzt, nie
    gespeichert."""
    ip = request.META.get("HTTP_X_REAL_IP", "").strip()
    if not ip:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return ip or request.META.get("REMOTE_ADDR", "")


def land_von_ip(ip):
    """ISO-Ländercode ("DE") aus der offline-Geo-DB – oder "" wenn DB/Paket
    fehlt bzw. die IP privat/unbekannt ist."""
    global _geo_reader, _geo_versucht
    if _geo_reader is None and not _geo_versucht:
        _geo_versucht = True
        try:
            import maxminddb
            pfad = conf().get("traffic_geo_db") or (
                str(settings.BASE_DIR) + "/daten/dbip-country-lite.mmdb")
            _geo_reader = maxminddb.open_database(str(pfad))
        except Exception:  # noqa: BLE001 – ohne Geo-DB läuft alles weiter
            _geo_reader = None
    if _geo_reader is None or not ip:
        return ""
    try:
        treffer = _geo_reader.get(ip) or {}
        return (treffer.get("country") or {}).get("iso_code", "") or ""
    except Exception:  # noqa: BLE001
        return ""


def besucher_hash(ip, user_agent):
    """Täglich rotierender, anonymer Besucher-Hash (16 Hex-Zeichen)."""
    roh = f"{settings.SECRET_KEY}{date.today().isoformat()}{ip}{user_agent}"
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()[:16]


def geraet_von_ua(user_agent):
    if _TABLET_RE.search(user_agent):
        return "tablet"
    # Android-Tablets melden "Android" OHNE "Mobile".
    if "android" in user_agent.lower() and "mobile" not in user_agent.lower():
        return "tablet"
    if _MOBIL_RE.search(user_agent) or "android" in user_agent.lower():
        return "mobile"
    return "desktop"


def referrer_domain(request):
    """Nur die Domain des Referrers (ohne www.) – eigene Hosts werden
    ausgeblendet (interne Navigation ist keine Quelle)."""
    roh = request.META.get("HTTP_REFERER", "")
    if not roh:
        return ""
    try:
        host = (urlparse(roh).netloc or "").lower().split(":")[0]
    except ValueError:
        return ""
    host = host.removeprefix("www.")
    eigene = {request.get_host().split(":")[0].removeprefix("www.")}
    eigene.update(d.removeprefix("www.") for d in conf().get("traffic_eigene_domains", []))
    return "" if host in eigene else host[:120]


class TrafficMiddleware:
    """Erfasst jeden erfolgreichen GET-Seitenaufruf als Seitenaufruf-Zeile.
    Muss NACH der AuthenticationMiddleware stehen (User-Zuordnung)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._erfassen(request, response)
        except Exception:  # noqa: BLE001 – Statistik darf nie Seiten crashen
            pass
        return response

    def _erfassen(self, request, response):
        if request.method != "GET" or response.status_code != 200:
            return
        pfad = request.path
        for prefix in conf().get("traffic_ignorierte_pfade", []):
            if pfad.startswith(prefix):
                return
        ct = (response.get("Content-Type") or "").lower()
        if "text/html" in ct:
            typ = "html"
        elif "json" in ct:
            typ = "json"
        else:
            return  # Bilder/Fonts etc. – liefert in Produktion ohnehin nginx
        ua = request.META.get("HTTP_USER_AGENT", "")
        ip = client_ip(request)
        try:
            groesse = len(response.content)
        except AttributeError:  # StreamingHttpResponse
            groesse = int(response.get("Content-Length") or 0)
        from .models import Seitenaufruf
        Seitenaufruf.objects.create(
            pfad=pfad[:300],
            typ=typ,
            land=land_von_ip(ip),
            besucher=besucher_hash(ip, ua),
            user=request.user if getattr(request, "user", None)
                 and request.user.is_authenticated else None,
            geraet=geraet_von_ua(ua),
            referrer=referrer_domain(request) if typ == "html" else "",
            bot=bool(BOT_RE.search(ua)) or not ua,
            groesse=groesse,
        )
