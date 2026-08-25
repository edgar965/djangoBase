# -*- coding: utf-8 -*-
u"""Die Stellschrauben einer KI-Anfrage - je Modell einstellbar.

DER AUFTRAG (25.08.2026, Edgar)
===============================
    „mach die ollama änderungen mit den Einstellungen pro KI. das müsste man
     für jede KI machen, oder? Sind die Parameter gleich bei jeder KI?"
    „es gibt auch einstellungen für max tokens usw."

Anlass war der Eindruck, Ollama biete diese Regler nicht - SGLang und vLLM
zeigen sie im Playground (System-Prompt, Temperature, Top P, Top K, Max
Tokens). Ollama kann sie alle. Sie wurden hier nur nie gesetzt: Im ganzen
Bestand stand genau EIN ``options``-Wörterbuch, in ``review/partner.py``, mit
``num_ctx`` und ``temperature``. Sparring, Messungen und GPU-Test liefen auf
der Voreinstellung.

DIE ANTWORT AUF „SIND DIE PARAMETER GLEICH?" - NEIN
===================================================
Die NAMEN sind gleich (es ist dieselbe Ollama-Schnittstelle), die sinnvollen
WERTE nicht. Ausgelesen am 25.08.2026 über ``/api/show``, also das, was die
Modelle selbst mitbringen:

    Modell                          temp  top_k  top_p  min_p  rep_pen  pres_pen
    gemma4:26b-a4b-it-qat              1     64   0.95      -        -         -
    gpt-oss:20b                        1      -      -      -        -         -
    nemotron-3.5-lightning:30b-a3b     1      -   0.95      -        -         -
    nemotron:70b-instruct-q2_K         -      -      -      -        -         -
    qwen3.6:35b-a3b-q4_K_M             1     20   0.95      0        1       1.5
    qwen3.8:27b                        1     20   0.95      0        1         0
    qwen3.8:27b-q8_0                   1     20   0.95      0        1         0

Drei Dinge stehen da drin, die man nicht raten kann:

  * ``gpt-oss`` bringt NUR eine Temperatur mit, ``nemotron:70b-q2`` gar nichts
    (nur Stop-Marken). Wer dort top_k setzt, erfindet eine Vorgabe.
  * ``qwen3.6`` will ``presence_penalty 1.5``, ``qwen3.8`` will ``0`` - dieselbe
    Familie, gegenteilige Empfehlung.
  * ``gemma4`` will ``top_k 64``, qwen ``top_k 20``. Ein globaler Wert wäre für
    eines der beiden immer falsch.

DESHALB IST ``None`` DER WICHTIGSTE WERT HIER
=============================================
Ein Feld auf ``None`` wird NICHT gesendet - dann greift, was das Modell selbst
mitbringt. Das ist etwas anderes als „auf Standard setzen": Ein mitgeschickter
Wert überschreibt die Herstellervorgabe auch dann, wenn er zufällig gleich
aussieht. Genau diesen Unterschied zeigt der Playground mit dem Platzhalter
„default" in leeren Feldern.

Wer also nichts einstellt, bekommt das Verhalten von vorher - wichtig, weil
djangoBase in rund sechs Projekten hängt.
"""

__all__ = ["KiParameter"]


class KiParameter:
    u"""Was eine Anfrage steuert - und was davon überhaupt mitgeschickt wird."""

    #: Die Felder, die als Ollama-``options`` durchgereicht werden, mit dem
    #: Namen, den die Schnittstelle dafür erwartet. Reihenfolge = Anzeige.
    FELDER = (
        ("temperature", "temperature", u"Zufälligkeit: 0 = immer dasselbe"),
        ("top_p", "top_p", u"Kernauswahl nach Wahrscheinlichkeitsmasse"),
        ("top_k", "top_k", u"nur die k wahrscheinlichsten Wörter"),
        ("min_p", "min_p", u"Untergrenze relativ zum besten Wort"),
        # VORSICHT BEI DENKENDEN MODELLEN. ``num_predict`` deckelt ALLE Token,
        # auch die des internen Denkens - und die kommen ZUERST. Gemessen am
        # 25.08.2026 an ``gpt-oss:20b`` (``think: False`` war gesetzt):
        #
        #     max_tokens=30  ->  30 Token verbraucht, Antworttext LEER
        #     max_tokens=60  ->  60 Token verbraucht, Antworttext LEER
        #     max_tokens=120 -> 120 Token verbraucht, Text ab hier
        #
        # Kein Fehler, keine Warnung - eine leere Zeichenkette. Wer einen
        # knappen Deckel setzt, bekommt bei solchen Modellen also nichts
        # zurueck und sieht nicht warum. Unter 150 nicht gehen, oder vorher
        # gegen das konkrete Modell pruefen.
        ("max_tokens", "num_predict", u"Länge der Antwort (Playground: Max tokens)"),
        ("kontext", "num_ctx", u"Fenster für Frage + Antwort"),
        ("seed", "seed", u"fester Startwert - macht Läufe wiederholbar"),
        ("wiederholstrafe", "repeat_penalty", u"dämpft Wortwiederholungen"),
    )

    def __init__(self, system=None, temperature=None, top_p=None, top_k=None,
                 min_p=None, max_tokens=None, kontext=None, seed=None,
                 wiederholstrafe=None):
        #: Systemanweisung. Gehört NICHT in ``options`` - sie ist eine Nachricht
        #: mit ``role: system`` und wird von :meth:`vor_verlauf` geliefert.
        self.system = system
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.min_p = min_p
        self.max_tokens = max_tokens
        self.kontext = kontext
        self.seed = seed
        self.wiederholstrafe = wiederholstrafe

    # ------------------------------------------------------------- Vorlagen
    @classmethod
    def modellstandard(cls, kontext=None):
        u"""Nichts überschreiben - das Modell entscheidet.

        Der richtige Ausgangspunkt für Gespräche und Review: Die Werte in der
        Modelldatei stammen vom Hersteller und sind auf dieses eine Modell
        abgestimmt. ``kontext`` bleibt erlaubt, weil er keine Qualitätsfrage
        ist, sondern eine Speicherfrage.
        """
        return cls(kontext=kontext)

    @classmethod
    def wiederholbar(cls, seed=42, kontext=None, max_tokens=None):
        u"""Zweimal dieselbe Frage, zweimal dieselbe Antwort.

        Gemessen am 25.08.2026 gegen ``gpt-oss:20b``: ``seed=42``,
        ``temperature=0``, ``top_k=1`` liefern über zwei Läufe zeichengleiche
        Antworten (211/211 Zeichen). Ohne ``seed`` weichen sie ab.

        FÜR MESSUNGEN, NICHT FÜR QUALITÄTSURTEILE: ``temperature=0`` überschreibt
        die Herstellervorgabe (bei allen Modellen oben ist sie 1). Ein Modell
        greedy zu fahren macht es reproduzierbar, nicht besser - wer damit
        Antwortqualität bewertet, misst ein anderes Verhalten als im Betrieb.
        """
        return cls(seed=seed, temperature=0, top_k=1, kontext=kontext,
                   max_tokens=max_tokens)

    # -------------------------------------------------------------- Ausgabe
    def als_optionen(self):
        u"""Das ``options``-Wörterbuch für ``/api/chat`` - ohne die leeren Felder.

        Wörterbuch gewollt: Das ist das Übergabeformat der Ollama-Schnittstelle.
        """
        aus = {}
        for eigen, fremd, _zweck in self.FELDER:
            wert = getattr(self, eigen)
            if wert is not None:
                aus[fremd] = wert
        return aus

    def als_openai(self):
        u"""Dieselben Werte für OpenAI-kompatible Dienste (OpenRouter, vLLM).

        Nicht jeder Name wandert mit: ``top_k``, ``min_p`` und
        ``repeat_penalty`` gehören nicht zum OpenAI-Schema und werden von
        vielen Diensten kommentarlos verworfen - hier bleiben sie deshalb
        draußen, statt Wirkung vorzutäuschen. ``num_ctx`` hat dort gar kein
        Gegenstück: Das Fenster gibt der Server beim Start vor.

        ONLINE IST ES UNGLEICHMÄSSIGER ALS LOKAL (gemessen 25.08.2026 über
        ``supported_parameters`` der OpenRouter-Modellliste, 418 Modelle):

            Modell                      temp  top_p  top_k  seed  max_tokens
            nvidia/nemotron-3-ultra       ja     ja     ja    ja      ja
            moonshotai/kimi-k3            ja     ja     ja    ja      ja
            google/gemma-4-26b-a4b-it     ja     ja     ja    ja      ja
            stealth/ox-alpha              ja     ja     ja    --      ja
            x-ai/grok-4.6                 ja     ja     --    ja      ja
            anthropic/claude-opus-4.8     ja     --     --    --      ja
            openai/gpt-5.2                --     --     --    ja      ja

        Zwei Dinge, die man wissen muss, bevor man sich auf die Werte verlässt:

          * ``openai/gpt-5.2`` nimmt **keine Temperatur** mehr - bei den
            Reasoning-Modellen von OpenAI ist sie entfallen. Was diese Methode
            liefert, ist also nicht überall anwendbar.
          * ``stealth/ox-alpha`` und ``anthropic/claude-opus-4.8`` kennen
            **kein seed**. Eine wiederholbare Messung ist dort nicht möglich -
            wer sie trotzdem ansetzt, misst Streuung und nennt sie Unterschied.

        DIESE METHODE FILTERT NICHT DANACH. OpenRouter verwirft nicht
        unterstützte Felder still; ein Wert kann also mitgehen und wirkungslos
        bleiben. Wer sicher gehen will, holt ``supported_parameters`` des
        Modells und schneidet danach - siehe den Vorschlag im Protokoll vom
        25.08.2026.
        """
        aus = {}
        if self.temperature is not None:
            aus["temperature"] = self.temperature
        if self.top_p is not None:
            aus["top_p"] = self.top_p
        if self.max_tokens is not None:
            aus["max_tokens"] = self.max_tokens
        if self.seed is not None:
            aus["seed"] = self.seed
        return aus

    def vor_verlauf(self, verlauf):
        u"""Den Verlauf mit der Systemanweisung davor - falls eine gesetzt ist.

        Ohne ``system`` kommt der Verlauf UNVERÄNDERT zurück, damit Aufrufer
        ohne Systemanweisung nichts anders machen als bisher. Führt der Verlauf
        bereits eine ``system``-Nachricht, wird sie NICHT verdoppelt - die
        vorhandene gewinnt, weil sie näher am Aufruf steht.
        """
        if not self.system:
            return verlauf
        if verlauf and (verlauf[0] or {}).get("role") == "system":
            return verlauf
        return [{"role": "system", "content": self.system}] + list(verlauf)

    # --------------------------------------------------------- Zusammenbau
    def mit(self, **werte):
        u"""Eine Kopie mit geänderten Feldern - das Original bleibt unberührt.

        Nötig, weil ein Parametersatz aus der Konfiguration mehrfach benutzt
        wird: Wer ihn an einer Stelle verändert, änderte ihn sonst überall mit.
        Dieselbe Falle wie bei flachen Store-Kopien.
        """
        eigen = {name: getattr(self, name) for name, _f, _z in self.FELDER}
        eigen["system"] = self.system
        eigen.update(werte)
        return KiParameter(**eigen)

    @classmethod
    def _bekannt(cls):
        return {name for name, _f, _z in cls.FELDER} | {"system"}

    @classmethod
    def aus_dict(cls, quelle):
        u"""Aus gespeicherter Konfiguration - unbekannte Schlüssel fliegen raus.

        Ein Tippfehler im Namen darf nicht als stiller Wunsch durchgehen: Was
        hier nicht bekannt ist, wird verworfen, statt an Ollama zu gehen, wo es
        ebenfalls kommentarlos verschwände.
        """
        if not quelle:
            return cls()
        bekannt = cls._bekannt()
        return cls(**{k: v for k, v in dict(quelle).items() if k in bekannt})

    @classmethod
    def fuer_modell(cls, modell, tabelle=None, grund=None):
        u"""Der Satz für EIN Modell: Grundeinstellung, überschrieben je Modell.

        ``tabelle`` ist ``{modellname: {feld: wert}}`` aus der Konfiguration.
        Gesucht wird erst der volle Name (``qwen3.8:27b-q8_0``), dann der Name
        ohne Kennzeichnung (``qwen3.8:27b``), dann die Familie (``qwen3.8``) -
        so gilt eine Einstellung für alle Quantisierungen eines Modells, ohne
        dass man sie dreimal hinschreibt.
        """
        satz = grund or cls()
        bekannt = cls._bekannt()
        voll = modell or ""
        for name in (voll, voll.rsplit("-", 1)[0], voll.split(":")[0]):
            eintrag = (tabelle or {}).get(name)
            if eintrag:
                return satz.mit(**{k: v for k, v in dict(eintrag).items()
                                   if k in bekannt})
        return satz

    def __repr__(self):
        gesetzt = ", ".join("%s=%r" % (n, getattr(self, n))
                            for n, _f, _z in self.FELDER
                            if getattr(self, n) is not None) or "Modellstandard"
        return "<KiParameter %s>" % gesetzt
