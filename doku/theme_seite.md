# Einstellungen → Theme (01.11.2026, aus StayNestor)

Aus `CLAUDE.md` ausgelagert am 02.11.2026 (wörtlich). Bei Arbeit an diesem Thema lesen.

**Einstellungen → Theme** (01.11.2026, aus StayNestor; `/hilfe/einstellungen/theme/`, `views/theme_seite.py`):
Theme umschalten (Knöpfe mit `.theme-pick`) und je Theme Farben und Schriftrollen einstellen, nach Bereichen des
Bildschirms geordnet (Grundschrift, Seitenleiste, Kopfleiste, Inhalt, Tabellen, Formulare, Knöpfe und Reiter),
rechts eine Vorschau, jede Änderung wirkt sofort auf die ganze Seite. Definition `theme_stil.py` (9 Farben → je
mehrere Variablen samt RGB-Form, 16 Schriftrollen wie Überschrift I–III, Text, Hinweis, Tabellenkopf …), Prüfung
`theme_bereinigung.py` (nur `#rrggbb`, bekannte Rollen/Attribute, 7–40 px — auch beim Ausgeben, denn die Werte
stehen roh im `<style>`). Ablage im Store, Gruppe `theme`, Schlüssel `theme_anpassung` (keine Migration).
Ausgabe: `djangobase.theme_css` (Kontextprozessor) als `<style id="dbt-theme-anpassung">` in `_shell.html` NACH
`extra_css`; ohne Anpassung und Vorgaben kein Block. Schriftrollen heißen `--dbt-s-<rolle>-art|groesse|farbe|
gewicht|stil` und sind in KEINEM Theme gesetzt (`test_theme_variablen` nimmt das Präfix `--dbt-s-` aus).
djangoBase bindet Seitenleiste und Seitenname (`sidebar.css`, alter Wert als Rückfall); die Seiten eines Projekts
binden ihre Klassen selbst (StayNestor: `staynestor/css/schriften.css`). Neue Schlüssel: `theme_vorgaben` (gleiche
Form wie die Ablage, z. B. StayNestor „weiss“: Schrift schwarz) und `theme_vorschau` (Vorlage mit den echten
Klassen des Projekts und `data-rolle="<rolle>"` je Beispiel; leer = `hilfe/_theme_vorschau.html`). Nav-Eintrag
„Theme“ unter Einstellungen nur bei `theme_modes`. Tests `tests/unit/test_theme_stil.py` (nicht gelaufen).
Die Rollentabellen sind EINE `TabellenBreiten`-Gruppe mit Vorgaben (`theme_seite.js`, `SPALTEN`; „Schrift“ füllt den
Rest): gleiche Spalten und Breite in allen Bereichen; `data-djb-gebunden` im Markup hält `tabellen_auto.js` ab.
Die Seite lädt `tabellen.css` selbst: die Middleware bringt nur `tabellen_auto.js`, ohne das CSS sind die Griffe
0 px breit (01.11.2026 gemessen, auch auf allen StayNestor-Seiten — StayNestor lädt `tabellen.css` nirgends).
Knopf „Alle Schriftfarben“ setzt jede Rolle mit Farbe und `leiste_text` auf einmal (Knopf-Rolle hat keine Farbe).
