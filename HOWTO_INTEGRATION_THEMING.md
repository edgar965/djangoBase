# djangoBase — Integrations- & Theme-HowTo

> Für Projekte, die `djangobase` als shared App einbinden. Ziel: voll
> kompatibel sein UND einen **Theme-Wechsel (dunkel ⇄ hell/CleanOrga)** haben,
> der **alle** Seiten umfärbt — die djangoBase-eigenen Hilfe-/Einstellungs-
> seiten genauso wie die eigenen App-Seiten.
>
> Referenz-Implementierung: das Projekt **PersonalAssistant** (`A:\assistant`).
> Die hier beschriebenen Muster + Stolperfallen stammen aus dessen Umstellung.

---

## 0. TL;DR — was ein Consumer braucht

1. `djangobase` in `INSTALLED_APPS`, Context-Processor `djangobase.context_processors.djangobase`, URLs inkludieren.
2. `DJANGOBASE`-Dict in den Settings (Titel, Logo, Menü, `theme_modes`, `theme_default`, optional `sidebar_template`, `extra_css`).
3. Eigene Seiten erweitern `djangobase/base_app.html` **oder** sind standalone — beide Wege werden unten beschrieben.
4. **Für den app-weiten Theme-Switch:** einen Context-Processor `aktives_theme` bereitstellen + `theme.css` (Variablen-Datei) über `DJANGOBASE["extra_css"]` laden + die eigenen hartkodierten Farben auf CSS-Variablen umstellen.
5. djangoBase setzt `<body data-theme="{{ aktives_theme|default:theme_default }}">` automatisch (siehe `_shell.html`).

---

## 1. Grundintegration (Pflicht)

### 1.1 Settings

```python
INSTALLED_APPS = [
    # ...
    "djangobase",
]

TEMPLATES = [{
    "OPTIONS": {"context_processors": [
        # ... Django-Defaults ...
        "djangobase.context_processors.djangobase",   # PFLICHT
        "myapp.context_processors.active_theme",       # für Theme-Switch (s. §3)
    ]},
}]

DJANGOBASE = {
    "titel": "Meine App",
    "logo_icon": "bi-grid-1x2-fill",
    "version": VERSION,
    # 5-Modi-Palette (Wert = (slug, label, akzentfarbe)):
    "theme_modes": [
        ("dark",   "Dark",   "#4ea8f6"),
        ("light",  "Light",  "#1976d2"),
        ("cyber",  "Cyber",  "#00f0ff"),
        ("forest", "Forest", "#4caf50"),
        ("sunset", "Sunset", "#ff7a45"),
    ],
    "theme_default": "dark",
    # Eigene Live-Sidebar weiterverwenden (statt djangobase/_sidebar.html):
    "sidebar_template": "myapp/_sidebar.html",
    # Zusätzliche CSS auf ALLE djangoBase-Seiten (Hilfe/Einstellungen):
    "extra_css": ["myapp/css/theme.css"],
}
```

### 1.2 URLs

```python
urlpatterns = [
    path("hilfe/", include("djangobase.urls")),   # /hilfe/versionen, /hilfe/einstellungen, ...
    # ...
]
```

### 1.3 Template-Vererbung — zwei Wege

**Weg A — Seite erweitert die djangoBase-Shell** (empfohlen für neue Seiten):

```django
{% extends "djangobase/base_app.html" %}
{% block content %} ... {% endblock %}
```
`base_app.html → _shell.html` liefert Sidebar, Topbar, Theme-Switcher, Toast-Stack.
`_shell.html` setzt `<body data-theme="…">` (s. §2) **automatisch**.

**Weg B — Standalone-Seiten** (eigenes `<html>`, eigene `<head>`, kein `{% extends %}`):
Diese Seiten bekommen NICHTS von djangoBase automatisch. Sie müssen selbst:
- `data-theme` am `<body>` setzen (s. §3.3),
- ihre Theme-CSS laden,
- die gemeinsame Sidebar via `{% include %}` einbinden.

> Der PersonalAssistant hat 16 solcher Standalone-Seiten (Chat, Audio, Suche …).
> Genau die machen den Theme-Switch aufwendig — siehe §3 + §4.

---

## 2. Das Theme-System verstehen

Es gibt in djangoBase **zwei** Theme-Mechanismen — nicht verwechseln:

| Mechanismus | gesteuert über | wirkt auf | Datei |
|---|---|---|---|
| **`data-theme`** (5 Modi) | `<body data-theme="X">` | Variablen `--db-*` flippen | `djangobase/static/djangobase/css/themes.css` |
| **`base_template`** | DJANGOBASE-Profil / Einstellungsseite | welche Layout-Shell die djangoBase-Seiten `{% extends %}` (z. B. `base.html` dunkel vs. `base_cleanorga.html` hell) | Profil-Store `.djangobase.json` |

`themes.css` definiert pro Modus (auch **light**!) die Layout-Variablen:
```css
body[data-theme="light"] { --db-bg:#f5f7fa; --db-fg:#1a2533; --db-accent:#1976d2;
                           --sidebar-bg:#1f3a5f; --sidebar-light:#2e5a8f; ... }
```
**Wichtig:** djangoBase's eigene Seiten sind damit bereits theme-fähig — IHRE Sidebar
wird im Light-Modus z. B. dunkelblau (`#1f3a5f`) mit heller Schrift. Das ist
gewollt und lesbar. **Nicht** versuchen, die djangoBase-Sidebar von außen auf
Weiß zu zwingen (s. Stolperfalle §5.3).

`_shell.html` rendert den Body so (seit dieser Umstellung):
```django
<body{% if aktives_theme or djangobase.theme_default %} data-theme="{{ aktives_theme|default:djangobase.theme_default }}"{% endif %} ...>
```
→ Ein Consumer, der `aktives_theme` per Context-Processor liefert, steuert damit
das Theme **aller** djangoBase-Seiten. Projekte ohne `aktives_theme` fallen
transparent auf `theme_default` zurück (rückwärtskompatibel).

---

## 3. Ein Theme-Switch über ALLE Seiten — Schritt für Schritt

Ziel: **ein** Schalter färbt App-Seiten **und** djangoBase-Seiten um.

### 3.1 Eine zentrale Theme-Variablen-Datei (`theme.css`)

Single Source of Truth für Farben. Pro Modus ein `body[data-theme="X"]`-Block,
der **semantische Variablen** setzt. Kerntrick: **Overlay-Variablen**, die je
Theme kippen (hell-auf-dunkel ⇄ dunkel-auf-hell):

```css
body, body[data-theme="dark"] {
    --bg-primary:#0d2137; --surface:#122a44; --text-primary:#e0e8f0;
    --text-muted:rgba(224,232,240,0.62); --accent:#4ea8f6; --accent-strong:#1976d2;
    /* Overlays: helle Schleier auf dunklem Grund */
    --ov04:rgba(255,255,255,0.04); --ov08:rgba(255,255,255,0.08);
    --ov10:rgba(255,255,255,0.10); --border:rgba(255,255,255,0.10);
}
body[data-theme="light"] {           /* CleanOrga-Light */
    --bg-primary:#f5f5f5; --surface:#ffffff; --text-primary:#2a2f36;
    --text-muted:#5b6675; --accent:#2196F3; --accent-strong:#1976d2;
    /* Overlays GEKIPPT: dunkle Schleier auf hellem Grund */
    --ov04:rgba(0,0,0,0.035); --ov08:rgba(0,0,0,0.08);
    --ov10:rgba(0,0,0,0.10); --border:#e2e6ea;
    background:var(--bg-primary); color:var(--text-primary);
}
/* cyber / forest / sunset analog */
```

Diese Datei wird **überall** geladen:
- App-Seiten: per `<link>` im `<head>` (mit `?v=` Cache-Buster, s. §5.1).
- djangoBase-Seiten: über `DJANGOBASE["extra_css"] = ["myapp/css/theme.css"]`.

### 3.2 Context-Processor `aktives_theme`

Liefert den aktiven Modus für `data-theme`. **Eine** Quelle wählen, sonst
widersprechen sich Schalter (s. Stolperfalle §5.4). Im PersonalAssistant ist die
Quelle das **djangoBase-Profil** (nicht eine per-User-Preference):

```python
def active_theme(request):
    """Profil ist die einzige Quelle. CleanOrga-Layout -> light, sonst theme_default."""
    try:
        from djangobase.conf import conf
        c = conf()
        if (c.get("base_template") or "").endswith("base_cleanorga.html"):
            return {"aktives_theme": "light"}
        return {"aktives_theme": c.get("theme_default") or "dark"}
    except Exception:
        return {"aktives_theme": "dark"}
```
> Alternative Quellen sind möglich (per-User-Cookie etc.) — aber **nur eine**,
> sonst gibt es Konflikte (Profil sagt dunkel, User-Override sagt hell → Chaos).

### 3.3 Standalone-Seiten verkabeln

Jede Standalone-Seite (Weg B) braucht im `<head>`/`<body>`:
```django
<link rel="stylesheet" href="{% static 'myapp/css/theme.css' %}?v={{ JS_VERSION }}">
<link rel="stylesheet" href="{% static 'myapp/css/sidebar.css' %}?v={{ JS_VERSION }}">
...
<body data-theme="{{ aktives_theme|default:'dark' }}">
    {% include 'myapp/_sidebar.html' %}
```

### 3.4 djangoBase-eigene Inhalte hell bekommen

Die djangoBase-Hilfeseiten (z. B. `einstellungen_tabs.html`) bringen eigene
inline-`<style>`-Blöcke mit **hartkodierten** Dunkel-Farben mit, die im `<body>`
NACH `themes.css`/`theme.css` stehen → sie gewinnen per Reihenfolge. Mit
`!important` (in der via `extra_css` geladenen `theme.css`) zurückholen:
```css
body[data-theme="light"] .set-card  { background:#fff !important; border-color:#e0e0e0 !important; }
body[data-theme="light"] .set-hint  { background:#f1f7ff !important; color:#45566a !important; }
body[data-theme="light"] .set-input input,
body[data-theme="light"] .set-input select { background:#fff !important; color:#222 !important; }
/* … alle set-*/prof-*-Klassen … */
```

---

## 4. Farben umstellen: die Technik

Auf den App-Seiten stehen oft **tausende** hartkodierte Farben — in `<style>`-
Blöcken, in `style="…"`-Attributen UND in JS-generiertem HTML. Alle drei Orte
müssen umgestellt werden, sonst flippt der Switch sie nicht.

**Mechanische Ersetzung** (Skript) der wiederkehrenden Tokens auf Variablen.
Schlüssel-Mappings (Schließende `)` IMMER mitnehmen → keine Prefix-Kollisionen,
`0.1)` trifft nicht `0.15)`):

| hartkodiert | Variable |
|---|---|
| `#e0e8f0` (Primärtext) | `var(--text-primary)` |
| `#4ea8f6` (Akzent) | `var(--accent)` |
| `rgba(255,255,255,0.04)` (Fläche/Border) | `var(--ov04)` |
| `rgba(255,255,255,0.5/0.55/0.6)` (Text) | `var(--text-muted)` |
| `rgba(0,0,0,0.25)` (dunkler Inset) | `var(--surface-2)` |
| `linear-gradient(135deg,#0a1628 …)` (Body-BG) | `var(--bg-gradient)` |

Status-Farben (`#ef4444`, `#22c55e`, `#f59e0b`) und `#fff` auf farbigen Buttons
**bleiben** (lesbar auf beiden Themes). Dekorative Akzent-Gradienten (Icon-/
Button-Hintergründe) ebenfalls.

Verifikation: gerenderte Seite auf Resttokens grep'en
(`rgba(255,255,255` / `#e0e8f0` / Body-Gradient) → muss 0 sein.

---

## 5. Stolperfallen (aus der Praxis — bitte lesen)

### 5.1 Cache-Buster bei `extra_css`
`extra_css` wird in `_shell.html` mit `?v={{ JS_VERSION|default:1 }}` geladen.
Ohne `?v` liefert ein **Service-Worker** die alte CSS-Datei (stale) → Änderungen
unsichtbar. App-Seiten-`<link>`s ebenfalls mit `?v={{ JS_VERSION }}` versehen und
`JS_VERSION` bei jedem CSS/JS-Edit hochzählen.

### 5.2 Mehrzeilige Django-Kommentare leaken
`{# … #}` ist **strikt einzeilig**. Ein `\n` zwischen `{#` und `#}` → ab Zeile 2
landet alles als sichtbarer Text in der Sidebar/Seite. Für mehrzeilig **immer**
`{% comment %}…{% endcomment %}`. Nach JEDEM Template-Edit prüfen:
`awk '/{#/ && !/#}/' <file>` muss leer sein.

### 5.3 Die djangoBase-Sidebar NICHT von außen auf Weiß zwingen
djangoBase's eigenes `themes.css` gibt der Sidebar im Light-Modus ein dunkelblaues
`--sidebar-bg` mit heller Schrift (lesbar). Wer von außen nur `--sidebar-bg` auf
Weiß überschreibt, bekommt **helle Schrift auf weiß** = unsichtbar — und kommt
gegen djangoBase's Text-Regeln teils nicht an (selbst Inline-`!important` verlor
in Tests). **Lösung:** die weiße Sidebar gehört in die `sidebar.css`, die NUR auf
den App-Seiten geladen wird; die djangoBase-Seiten behalten djangoBase's eigenes
(lesbares) Light-Theme. Also: `--sidebar-*`-Light-Werte **nicht** in die globale
`theme.css`, sondern in die app-only `sidebar.css`.

### 5.4 Nur EINE Theme-Quelle
Zwei parallele Schalter (Profil + per-User-Punkte) widersprechen sich: setzt der
User-Schalter „light", ist auch das „Standard"-Profil hell. Im PersonalAssistant
ist das Profil die **einzige** Quelle (`aktives_theme` aus `conf()`); ein
zusätzlicher per-User-Switcher wurde wieder entfernt.

### 5.5 `getComputedStyle` im Automations-/Eval-Kontext kann veraltet sein
Beim Debuggen über eine Browser-Automation gab `getComputedStyle(el).color` nach
einem JS-`setAttribute('data-theme', …)` teils **veraltete** Werte zurück (zeigte
weiß, obwohl real dunkel gerendert). Im Zweifel **Screenshot** statt API — der
sichtbare Render ist die Wahrheit.

---

## 6. Checkliste für ein neues Consumer-Projekt

- [ ] `djangobase` in INSTALLED_APPS, URLs inkludiert.
- [ ] `DJANGOBASE`-Dict mit `theme_modes`, `theme_default`, ggf. `sidebar_template`.
- [ ] Context-Processor `djangobase` **und** `active_theme` registriert.
- [ ] `theme.css` mit allen 5 Modi + Overlay-Variablen angelegt.
- [ ] `DJANGOBASE["extra_css"]` lädt `theme.css` (für die djangoBase-Seiten).
- [ ] `!important`-Overrides für djangoBase's `set-*/prof-*`-Inline-Styles.
- [ ] App-Seiten: `theme.css`+`sidebar.css` mit `?v={{ JS_VERSION }}`, `<body data-theme="{{ aktives_theme }}">`.
- [ ] Hartkodierte Farben (Style-Blöcke + `style="…"` + JS-HTML) auf Variablen umgestellt; Rest-Grep = 0.
- [ ] Weiße App-Sidebar-Werte in `sidebar.css` (app-only), nicht in `theme.css`.
- [ ] Kein mehrzeiliges `{# #}`; `JS_VERSION` bei CSS/JS-Edits erhöht.
- [ ] Verifiziert: Dark + Light je auf App-Seite UND djangoBase-Seite (per Screenshot).
