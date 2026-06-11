"""Übersetzungsmodul für die öffentliche User-Seite (Basis-Sprache: Deutsch).

Engine: deep_translator.GoogleTranslator – kostenloser Google-Endpoint ohne
API-Key (wie in CleanOrga und auf schwanenburg.de). Die Katalog-Logik mit
Quelltext-Hash zur Änderungserkennung und den Modi fehlend / veraltet / alle
stammt aus dem Schwanenburg-WordPress-Plugin.

Funktionsweise:
- Templates der User-Seite markieren Texte mit {% t "…" %} bzw.
  {% tblock "name" %}…{% endtblock %} (templatetags/uebersetzung.py).
- Beim ersten Rendern registriert sich jeder Text als TextQuelle in der DB.
- Einstellungen → Übersetzung: Sprachen wählen + „Jetzt übersetzen"-Button
  (läuft im Hintergrund-Thread, Fortschritt über den Django-Cache).
- Besucher wählen die Sprache über das Flaggen-Menü ({% sprachen_menue %});
  sie landet als Cookie "sprache", die Tags liefern dann die Übersetzung.
"""
import hashlib
import re
import threading
import time

from django.core.cache import cache
from django.db import connection

from .conf import conf

BASIS = "de"
COOKIE = "sprache"
LAUF_KEY = "djangobase_uebersetzung_lauf"

# Angebotene Zielsprachen: (Code für GoogleTranslator, Eigenname, Flagge)
SPRACHEN = [
    ("en", "English", "🇬🇧"),
    ("fr", "Français", "🇫🇷"),
    ("es", "Español", "🇪🇸"),
    ("it", "Italiano", "🇮🇹"),
    ("nl", "Nederlands", "🇳🇱"),
    ("pl", "Polski", "🇵🇱"),
    ("cs", "Čeština", "🇨🇿"),
    ("da", "Dansk", "🇩🇰"),
    ("sv", "Svenska", "🇸🇪"),
    ("tr", "Türkçe", "🇹🇷"),
    ("ru", "Русский", "🇷🇺"),
    ("uk", "Українська", "🇺🇦"),
    ("ro", "Română", "🇷🇴"),
    ("ar", "العربية", "🇸🇦"),
    ("vi", "Tiếng Việt", "🇻🇳"),
    ("zh-CN", "中文", "🇨🇳"),
    ("ja", "日本語", "🇯🇵"),
]
SPRACH_NAMEN = {code: (name, flagge) for code, name, flagge in SPRACHEN}


def aktive_sprachen():
    """Konfigurierte Zielsprachen (Einstellungen → Übersetzung), ohne Basis."""
    codes = conf().get("uebersetzung_sprachen") or []
    return [c for c, _n, _f in SPRACHEN if c in codes]


def sprache_aus_request(request):
    """Aktive Anzeigesprache des Besuchers (Cookie), Fallback Deutsch."""
    s = getattr(request, "_sprache_aktiv", None)
    if s is None:
        s = request.COOKIES.get(COOKIE, BASIS)
        if s != BASIS and s not in aktive_sprachen():
            s = BASIS
        request._sprache_aktiv = s
    return s


# ------------------------------------------------------------- Google-Engine
_translators = {}


def _translator(ziel):
    """GoogleTranslator pro Sprachpaar cachen (CleanOrga-Muster)."""
    if ziel not in _translators:
        from deep_translator import GoogleTranslator
        _translators[ziel] = GoogleTranslator(source=BASIS, target=ziel)
    return _translators[ziel]


MAX_LAENGE = 4500  # Limit des Google-Endpoints (~5000) mit Puffer
_TAG_RE = re.compile(r"(<[^>]+>)")


def _uebersetze_klartext(text, ziel):
    if not text.strip():
        return text
    if len(text) <= MAX_LAENGE:
        return _translator(ziel).translate(text) or text
    # Lange Texte an Satz-/Absatzgrenzen stückeln
    teile, aktuell = [], ""
    for stueck in re.split(r"(?<=[.!?\n])\s+", text):
        if len(aktuell) + len(stueck) > MAX_LAENGE and aktuell:
            teile.append(aktuell)
            aktuell = stueck
        else:
            aktuell = f"{aktuell} {stueck}".strip()
    if aktuell:
        teile.append(aktuell)
    return " ".join(_translator(ziel).translate(t) or t for t in teile)


def uebersetze(text, ziel):
    """Deutsch → Zielsprache. HTML wird an den Tags zerlegt und nur der
    Text dazwischen übersetzt (Markup bleibt unangetastet) – gleiche Idee
    wie die Shortcode-Zerlegung des Schwanenburg-Plugins."""
    if "<" not in text:
        return _uebersetze_klartext(text, ziel)
    teile = _TAG_RE.split(text)
    out = []
    for teil in teile:
        if teil.startswith("<") or not teil.strip():
            out.append(teil)
        else:
            out.append(_uebersetze_klartext(teil, ziel))
            time.sleep(0.15)  # Endpoint schonen
    return "".join(out)


# ------------------------------------------------------- Katalog (mit Cache)
def _hash(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


_katalog = {"ts": 0.0, "quellen": {}, "spr": {}}
_KATALOG_TTL = 60  # Sekunden; nach einem Übersetzungslauf wird invalidiert
_lock = threading.Lock()


def katalog_leeren():
    with _lock:
        _katalog["ts"] = 0.0


def _katalog_laden():
    """Lädt Quellen-Schlüssel + alle Übersetzungen in den Prozess-Speicher."""
    from .models import TextQuelle, Uebersetzung
    with _lock:
        if time.time() - _katalog["ts"] < _KATALOG_TTL:
            return
        try:
            _katalog["quellen"] = dict(
                TextQuelle.objects.values_list("schluessel", "quelle"))
            spr = {}
            for u in Uebersetzung.objects.select_related("quelle"):
                spr.setdefault(u.sprache, {})[u.quelle.schluessel] = (
                    u.quelle_hash, u.text)
            _katalog["spr"] = spr
            _katalog["ts"] = time.time()
        except Exception:  # noqa: BLE001 – z. B. vor der ersten Migration
            _katalog["ts"] = time.time()


def text_holen(text, sprache, schluessel=None):
    """Übersetzung eines deutschen Texts in der aktiven Sprache – oder der
    deutsche Text selbst (Basis, fehlende oder veraltete Übersetzung).
    Unbekannte Texte werden bei JEDEM Rendern (auch auf Deutsch) als
    TextQuelle registriert (fail-silent)."""
    text = text.strip()
    if not text:
        return text
    _katalog_laden()
    key = schluessel or _hash(text)
    if key not in _katalog["quellen"]:
        _registrieren(key, text)
    elif schluessel and _katalog["quellen"][key] != text:
        _quelle_aktualisieren(key, text)
    if sprache == BASIS:
        return text
    eintrag = _katalog["spr"].get(sprache, {}).get(key)
    if eintrag and eintrag[0] == _hash(text):
        return eintrag[1]
    return text


def _registrieren(key, text):
    from .models import TextQuelle
    try:
        TextQuelle.objects.get_or_create(schluessel=key, defaults={"quelle": text})
        with _lock:
            _katalog["quellen"][key] = text
    except Exception:  # noqa: BLE001 – Registrierung darf nie Seiten crashen
        pass


def _quelle_aktualisieren(key, text):
    """Bei festen Schlüsseln ({% tblock %}) den deutschen Stand mitführen,
    damit der Lauf geänderte Texte als „veraltet" erkennt."""
    from .models import TextQuelle
    try:
        q = TextQuelle.objects.filter(schluessel=key).first()
        if q and q.quelle != text:
            q.quelle = text
            q.save(update_fields=["quelle", "zuletzt_gesehen"])
        with _lock:
            _katalog["quellen"][key] = text
    except Exception:  # noqa: BLE001
        pass


# ----------------------------------------------------- Übersetzungslauf (BG)
def lauf_status():
    return cache.get(LAUF_KEY) or {}


def lauf_starten(modus="veraltet"):
    """Startet den Übersetzungslauf im Hintergrund-Thread. Modi:
    "fehlend"  – nur Texte ohne Übersetzung
    "veraltet" – fehlende + veraltete (Quelltext geändert)  [Standard]
    "alle"     – alles neu übersetzen
    Gibt False zurück, wenn bereits ein Lauf aktiv ist."""
    status = lauf_status()
    if status.get("laeuft"):
        return False
    cache.set(LAUF_KEY, {"laeuft": True, "fertig": 0, "gesamt": 0,
                         "fehler": [], "modus": modus}, 24 * 3600)
    threading.Thread(target=_lauf, args=(modus,), daemon=True).start()
    return True


def _lauf(modus):
    from .models import TextQuelle, Uebersetzung
    status = {"laeuft": True, "fertig": 0, "gesamt": 0, "fehler": [], "modus": modus}
    try:
        sprachen = aktive_sprachen()
        jobs = []
        for q in TextQuelle.objects.prefetch_related("uebersetzungen"):
            h = _hash(q.quelle)
            vorhanden = {u.sprache: u for u in q.uebersetzungen.all()}
            for s in sprachen:
                u = vorhanden.get(s)
                noetig = (modus == "alle" or not u
                          or (modus == "veraltet" and u.quelle_hash != h))
                if noetig:
                    jobs.append((q, s))
        status["gesamt"] = len(jobs)
        cache.set(LAUF_KEY, status, 24 * 3600)

        for q, s in jobs:
            try:
                text = uebersetze(q.quelle, s)
                Uebersetzung.objects.update_or_create(
                    quelle=q, sprache=s,
                    defaults={"text": text, "quelle_hash": _hash(q.quelle)})
            except Exception as e:  # noqa: BLE001 – einzelner Text darf scheitern
                if len(status["fehler"]) < 10:
                    status["fehler"].append(f"{q.quelle[:40]} → {s}: {e}")
            status["fertig"] += 1
            if status["fertig"] % 5 == 0:
                cache.set(LAUF_KEY, status, 24 * 3600)
            time.sleep(0.2)  # Google-Endpoint schonen
    except Exception as e:  # noqa: BLE001
        status["fehler"].append(str(e))
    finally:
        status["laeuft"] = False
        cache.set(LAUF_KEY, status, 24 * 3600)
        katalog_leeren()
        connection.close()


# --------------------------------------------------------------- Status-Info
def sprach_status():
    """Pro aktiver Sprache: wie viele Texte aktuell / veraltet / fehlend sind
    (für die Einstellungen-Seite)."""
    from .models import TextQuelle
    quellen = list(TextQuelle.objects.prefetch_related("uebersetzungen"))
    zeilen = []
    for code in aktive_sprachen():
        name, flagge = SPRACH_NAMEN[code]
        aktuell = veraltet = fehlt = 0
        for q in quellen:
            u = next((u for u in q.uebersetzungen.all() if u.sprache == code), None)
            if not u:
                fehlt += 1
            elif u.quelle_hash != _hash(q.quelle):
                veraltet += 1
            else:
                aktuell += 1
        zeilen.append({"code": code, "name": name, "flagge": flagge,
                       "aktuell": aktuell, "veraltet": veraltet, "fehlt": fehlt})
    return len(quellen), zeilen
