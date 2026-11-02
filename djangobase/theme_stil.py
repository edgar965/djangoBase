"""Anpassung der Themes: Farben und Schriftrollen je Theme (Einstellungen → Theme, Edgar 01.11.2026).

Die Seite ordnet alles nach Bereichen des Bildschirms (``BEREICHE``): Grundschrift, Seitenleiste,
Kopfleiste, Inhalt, Tabellen, Formulare, Knöpfe und Reiter — je Bereich seine Farben und Schriftrollen.

* **Farben** setzen die Theme-Variablen selbst (``FARBEN``: eine Farbe → mehrere Variablen, auch die
  RGB-Form für Schleier wie ``--dbt-leiste-rgb``). Ohne Angabe gilt die Palette des Themes.
* **Schriftrollen** (``ROLLEN``) sind wenige, benannte Schriften wie in Textprogrammen: Überschrift I–III,
  Text, Hinweis, Tabellenkopf … Je Rolle Schriftart, Größe, Farbe, fett, kursiv als
  ``--dbt-s-<rolle>-art|groesse|farbe|gewicht|stil``. djangoBase bindet damit seine Shell (Seitenleiste,
  Kopfleiste, ``sidebar.css``); die Seiten eines Projekts binden ihre Klassen selbst, immer mit dem alten
  Wert als Rückfall: ``font-size: var(--dbt-s-h1-groesse, 1.45rem)``. Die Farbe einer Rolle fällt auf die
  Grundschrift zurück: ``color: var(--dbt-s-text-farbe, var(--dbt-s-alle-farbe, <alt>))``.
* **Vorgaben** je Theme bringt das Projekt mit (``DJANGOBASE["theme_vorgaben"]``, gleiche Form wie die
  Ablage); gespeicherte Werte gehen vor.

Gespeichert wird im Store (``theme_anpassung``, keine Datenbank):
``{"weiss": {"farben": {"akzent": "#111827"}, "schriften": {"h1": {"groesse": 24, "gewicht": "fett"}}}}``.
Geprüft wird beim Speichern (``ThemeBereinigung``) — in ``css()`` steht nur, was die Prüfung durchlässt.
"""


class ThemeStil:
    GEWICHTE = {"normal": "400", "fett": "700"}
    # Schriften, die unter Windows ohne Nachladen da sind (wie StayNestors Kalender-Gestaltung); Namen ohne
    # Anführungszeichen, damit der Stilblock kein Escaping braucht.
    SCHRIFTARTEN = [
        ("", "Vorgabe"),
        ("segoe", "Segoe UI"),
        ("arial", "Arial"),
        ("verdana", "Verdana"),
        ("tahoma", "Tahoma"),
        ("trebuchet", "Trebuchet MS"),
        ("calibri", "Calibri"),
        ("georgia", "Georgia"),
        ("times", "Times New Roman"),
        ("consolas", "Consolas"),
        ("courier", "Courier New"),
    ]
    STAPEL = {
        "segoe": "Segoe UI, system-ui, sans-serif",
        "arial": "Arial, Helvetica, sans-serif",
        "verdana": "Verdana, Geneva, sans-serif",
        "tahoma": "Tahoma, Verdana, sans-serif",
        "trebuchet": "Trebuchet MS, sans-serif",
        "calibri": "Calibri, Carlito, sans-serif",
        "georgia": "Georgia, serif",
        "times": "Times New Roman, Times, serif",
        "consolas": "Consolas, monospace",
        "courier": "Courier New, monospace",
    }
    ALLE_ATTRIBUTE = ("art", "groesse", "farbe", "gewicht", "kursiv")

    #: Farbe → (Name, [(CSS-Variable, "hex" | "rgb"), …]). Mehrere Variablen, weil djangoBase (``--dbt-*``,
    #: ``--db-*``) und die Projekte (``--accent``, ``--surface`` …) dieselbe Farbe unter eigenem Namen führen.
    FARBEN = {
        "leiste_flaeche": ("Hintergrund", [("--sidebar-bg", "hex")]),
        "leiste_aktiv": ("Aktiver Eintrag, Maus darüber", [("--sidebar-light", "hex")]),
        "leiste_text": (
            "Schrift (aktiv, Titel)",
            [("--dbt-leiste-text", "hex"), ("--dbt-leiste-rgb", "rgb")],
        ),
        "kopf_flaeche": ("Hintergrund", [("--sidebar-dark", "hex")]),
        "hintergrund": ("Seitenhintergrund", [("--db-bg", "hex"), ("--bg-gradient", "hex")]),
        "flaeche": ("Flächen (Karten, Fenster, Menüs)", [("--dbt-flaeche", "hex"), ("--surface", "hex")]),
        "rand": ("Ränder und Linien", [("--dbt-rand", "hex"), ("--border", "hex")]),
        "eingabe_flaeche": (
            "Eingabefelder",
            [("--dbt-flaeche-tief", "hex"), ("--dbt-s-eingabe-flaeche", "hex")],
        ),
        "akzent": (
            "Akzent (Hauptknöpfe, aktiver Reiter)",
            [
                ("--db-accent", "hex"),
                ("--accent", "hex"),
                ("--accent-rgb", "rgb"),
                ("--dbt-knopf", "hex"),
                ("--dbt-akzent-text", "hex"),
                ("--dbt-akzent-rgb", "rgb"),
            ],
        ),
    }

    #: Rolle → (Name, wo sie steht, einstellbare Attribute). „alle“ ist die Grundschrift: ihre Art gilt über
    #: ``--dbt-schrift`` für die ganze Seite, ihre Farbe für jede Rolle ohne eigene (außer Knopf: dessen Farbe
    #: hängt am Hintergrund des Knopfs).
    ROLLEN = {
        "alle": ("Grundschrift", "Schriftart der Seite, Farbe jeder Rolle ohne eigene", ("art", "farbe")),
        "menue": ("Menüeintrag", "Einträge der Seitenleiste", ALLE_ATTRIBUTE),
        "menue_abschnitt": ("Menüabschnitt", "kleine Überschriften in der Seitenleiste", ALLE_ATTRIBUTE),
        "seitenname": ("Seitenname", "Name der Seite in der Kopfleiste", ALLE_ATTRIBUTE),
        "h1": ("Überschrift I", "Titel der Seite", ALLE_ATTRIBUTE),
        "h2": ("Überschrift II", "Abschnitte einer Seite", ALLE_ATTRIBUTE),
        "h3": ("Überschrift III", "Titel von Karten und Fenstern", ALLE_ATTRIBUTE),
        "abschnitt": ("Abschnittsmarke", "kleine Zeile in Großbuchstaben über einer Gruppe", ALLE_ATTRIBUTE),
        "text": ("Text", "Fließtext", ALLE_ATTRIBUTE),
        "hinweis": ("Hinweis", "Erklärungen, Unterzeilen, Nebenangaben", ALLE_ATTRIBUTE),
        "tabellenkopf": ("Tabellenkopf", "Spaltenüberschriften", ALLE_ATTRIBUTE),
        "tabelle": ("Tabelle", "Zellen", ALLE_ATTRIBUTE),
        "beschriftung": ("Beschriftung", "Namen vor Eingabefeldern", ALLE_ATTRIBUTE),
        "eingabe": ("Eingabe", "Text in Eingabefeldern und Auswahllisten", ALLE_ATTRIBUTE),
        "knopf": ("Knopf", "Schrift auf Knöpfen (Farbe je Art)", ("art", "groesse", "gewicht", "kursiv")),
        "reiter": ("Reiter", "Reiter über einem Inhalt", ALLE_ATTRIBUTE),
    }

    #: (Schlüssel, Titel, Erklärung, Farben, Rollen) — Reihenfolge der Seite; die Nummern der Rollen in der
    #: Vorschau zählen in dieser Reihenfolge.
    BEREICHE = [
        ("grund", "Grundschrift", "Gilt überall, wo eine Rolle nichts Eigenes hat.", [], ["alle"]),
        (
            "leiste",
            "Seitenleiste",
            "Links: Menü mit Gruppen und Abschnitten.",
            ["leiste_flaeche", "leiste_aktiv", "leiste_text"],
            ["menue", "menue_abschnitt"],
        ),
        ("kopf", "Kopfleiste", "Oben: Seitenname und Schnellzugriff.", ["kopf_flaeche"], ["seitenname"]),
        (
            "inhalt",
            "Inhalt",
            "Die Seite selbst: Überschriften, Text, Karten.",
            ["hintergrund", "flaeche", "rand"],
            ["h1", "h2", "h3", "abschnitt", "text", "hinweis"],
        ),
        ("tabellen", "Tabellen", "Listen und Übersichten.", [], ["tabellenkopf", "tabelle"]),
        ("formulare", "Formulare", "Felder zum Ausfüllen.", ["eingabe_flaeche"], ["beschriftung", "eingabe"]),
        ("knoepfe", "Knöpfe und Reiter", "Bedienen und Umschalten.", ["akzent"], ["knopf", "reiter"]),
    ]

    #: Zusätzliche Variablen der Grundschrift — die Grundfarben, die Seiten und djangoBase direkt benutzen.
    ALLE_ART = ("--dbt-schrift",)
    ALLE_FARBE = ("--db-fg", "--dbt-text", "--text-primary")

    @classmethod
    def rgb(cls, hex_farbe):
        h = hex_farbe.lstrip("#")
        return ", ".join(str(int(h[i : i + 2], 16)) for i in (0, 2, 4))

    @classmethod
    def wirksam(cls, gespeichert, vorgaben):
        """Vorgaben des Projekts, darüber die gespeicherten Werte — je Farbe und je Attribut einer Rolle."""
        farben = dict((vorgaben or {}).get("farben") or {})
        farben.update((gespeichert or {}).get("farben") or {})
        schriften = {}
        for quelle in (vorgaben or {}, gespeichert or {}):
            for rolle, werte in (quelle.get("schriften") or {}).items():
                schriften.setdefault(rolle, {}).update(werte or {})
        return {"farben": farben, "schriften": schriften}

    @classmethod
    def deklarationen(cls, werte):
        """``["--name: wert", …]`` für ein Theme; Unbekanntes fällt weg (Werte sind schon geprüft)."""
        teile = []
        for schluessel, farbe in (werte.get("farben") or {}).items():
            for variable, form in cls.FARBEN.get(schluessel, ("", []))[1]:
                teile.append(f"{variable}: {cls.rgb(farbe) if form == 'rgb' else farbe}")
        for rolle, s in (werte.get("schriften") or {}).items():
            if rolle not in cls.ROLLEN:
                continue
            p = f"--dbt-s-{rolle}"
            if s.get("art") in cls.STAPEL:
                stapel = cls.STAPEL[s["art"]]
                teile.append(f"{p}-art: {stapel}")
                if rolle == "alle":
                    teile += [f"{v}: {stapel}" for v in cls.ALLE_ART]
            if isinstance(s.get("groesse"), (int, float)):
                teile.append(f"{p}-groesse: {s['groesse']:g}px")
            if s.get("farbe"):
                teile.append(f"{p}-farbe: {s['farbe']}")
                if rolle == "alle":
                    teile += [f"{v}: {s['farbe']}" for v in cls.ALLE_FARBE]
            if s.get("gewicht") in cls.GEWICHTE:
                teile.append(f"{p}-gewicht: {cls.GEWICHTE[s['gewicht']]}")
            if s.get("kursiv") is True:
                teile.append(f"{p}-stil: italic")
        return teile

    @classmethod
    def css(cls, anpassung, vorgaben, themes):
        """Stilblock für alle Themes des Projekts: ``body[data-theme="x"] { … }`` je Theme mit Angaben."""
        bloecke = []
        for theme in themes:
            werte = cls.wirksam((anpassung or {}).get(theme), (vorgaben or {}).get(theme))
            teile = cls.deklarationen(werte)
            if teile:
                bloecke.append(f'body[data-theme="{theme}"] {{ {"; ".join(teile)}; }}')
        return "\n".join(bloecke)

    @classmethod
    def definition(cls):
        """Alles, was die Seite (``theme_seite.js``) zum Aufbauen und für die Live-Vorschau braucht."""
        nummer, bereiche = 0, []
        for schluessel, titel, erklaerung, farben, rollen in cls.BEREICHE:
            eintraege = []
            for rolle in rollen:
                nummer += 1
                name, wo, attribute = cls.ROLLEN[rolle]
                eintraege.append(
                    {"rolle": rolle, "nr": nummer, "name": name, "wo": wo, "attribute": list(attribute)}
                )
            bereiche.append(
                {
                    "schluessel": schluessel,
                    "titel": titel,
                    "erklaerung": erklaerung,
                    "farben": [{"schluessel": f, "name": cls.FARBEN[f][0]} for f in farben],
                    "rollen": eintraege,
                }
            )
        return {
            "bereiche": bereiche,
            "farben": {k: v[1] for k, v in cls.FARBEN.items()},
            "schriftarten": cls.SCHRIFTARTEN,
            "stapel": cls.STAPEL,
            "gewichte": cls.GEWICHTE,
            "alle_art": cls.ALLE_ART,
            "alle_farbe": cls.ALLE_FARBE,
        }
