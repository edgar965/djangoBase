/* tests_strom.js — Testläufe LIVE, ohne die Seite neu zu laden.
   ==========================================================================
   Ansage 17.08.2026: „live fortschritt in djangoBase einbauen".

   Vorher lud jeder Lauf die Seite mit `?run=…` neu: Man klickte, sah zehn
   Minuten nichts und bekam am Ende alles auf einmal — inklusive der Frage, ob
   es überhaupt noch läuft. Jetzt geht der Lauf an `/hilfe/tests/strom/`, und
   die Antwort kommt zeilenweise: ✓/✗ erscheint in der Zeile, während der Test
   läuft, die Ausgabe wächst mit, und am Ende stehen die Laufzeiten in den
   Spalten „letzte", „Ø" und „letzte 4 Läufe".

   WAS ABGEFANGEN WIRD
   -------------------
     * `a.ts-run`     Run je Zeile und die Sammelknöpfe („Alles ausführen",
                      „Kategorie ausführen") — der `?run=`-Link bleibt im HTML
                      und funktioniert weiter, wenn dieses Modul nicht lädt.
     * `.ts-wahl-lauf`  „Alle ausführen" im Kartenkopf
     * `.ts-ber-run`    „Bereich ausführen" in der Abschnittszeile
     * `tests:auswahl-lauf`  die Checkbox-Auswahl (aus `tests_auswahl.js`)

   Deshalb setzt dieses Modul `data-tests-auswahl="ereignis"` auf die Seite:
   `tests_auswahl.js` postet dann kein Formular mehr, sondern meldet die
   Kennungen — dieselbe Bedienung, anderes Ziel.

   EIN LAUF ZUR ZEIT: Zwei Testprozesse gleichzeitig bauen dieselbe
   Testdatenbank zweimal auf und scheitern aneinander. Solange einer läuft,
   sind die Startknöpfe gesperrt (der Server sperrt zusätzlich, siehe
   `testsperre.Laufsperre` — ein zweiter Tab weiß von dieser Sperre nichts).

   FORTSCHRITTSBALKEN (Ansage 18.08.2026 „ich sehe noch nicht die progress bar")
   Die Gesamtzahl sagt der Lauf selbst („Found 173 test(s)."), der Server schickt
   sie als `plan`. Bis sie da ist, läuft der Balken unbestimmt — das ist die
   Phase, in der die Testdatenbank aufgebaut wird, und die dauert am längsten.
   Ohne diese Unterscheidung stünde der Balken eine halbe Minute auf 0 % und
   sähe aus wie „hängt".

   ANGEHAKT WIRD, WAS LÄUFT (Ansage 18.08.2026: „bei alle test laufen sollen auch
   die checkboxen ausgewählt werden die gerade laufen") Bei einem Sammellauf
   („Alle ausführen", „Bereich ausführen") kennt die Seite die einzelnen Fälle
   nicht — sie schickt ein Label. Angehakt wird deshalb zweifach: beim Start
   alles, was unter dem Label liegt, und danach jeder Fall, den der Server
   MELDET. Am Ende steht in den Kästchen genau, was gefahren wurde. */

import { zeitenSchreiben, statusSetzen } from "./testzeiten.js";

const STATUS = {
    pass: ["✓", "ok"],
    fail: ["✗", "fail"],
    error: ["!", "fail"],
    skip: ["–", ""],
    laeuft: ["läuft …", "laeuft"],
};

class Teststrom {
    constructor(url) {
        this.url = url;
        this.laeuft = false;
        this.ausgabe = null;
        this.kopf = null;
        this.zeilen = 0;
        this.plan = 0;        // erwartete Testzahl (0 = noch unbekannt)
        this.fertig = 0;      // gemeldete Fälle
    }

    binden() {
        const seite = document.querySelector(".ts-page");
        if (!seite || !this.url) return this;
        // Sagt `tests_auswahl.js`: nicht posten, sondern melden.
        seite.dataset.testsAuswahl = "ereignis";
        this.ausgabe = document.getElementById("ts-strom-ausgabe");
        this.kopf = document.getElementById("ts-strom-kopf");
        this.stop = document.getElementById("ts-strom-stop");
        this.balken = document.getElementById("ts-strom-balken");
        this.fuellung = document.getElementById("ts-strom-fuellung");
        this.zahl = document.getElementById("ts-strom-zahl");
        if (this.stop) this.stop.addEventListener("click", () => this.abbrechen());
        document.addEventListener("click", e => this._klick(e));
        document.addEventListener("tests:auswahl-lauf",
                                  e => this.fahren(e.detail.ids));
        // Ein nachgeladener Reiter bringt neue Kästchen mit; der gemerkte
        // Satz zeigte sonst auf Elemente, die nicht mehr im DOM hängen.
        document.addEventListener("tests:panel-geladen",
                                  () => { this._kaesten = null; });
        return this;
    }

    _klick(e) {
        if (!e.target.closest) return;
        const run = e.target.closest("a.ts-run, .ts-wahl-lauf, .ts-ber-run");
        if (!run) return;
        const ids = this._ziele(run);
        if (!ids.length) return;
        e.preventDefault();
        this.fahren(ids);
    }

    /** Welche Kennungen ein Knopf meint. */
    _ziele(el) {
        if (el.dataset && el.dataset.run) return [el.dataset.run];
        // Abschnittszeile: alle Zeilen dieses Bereichs (bis zur nächsten Gruppe).
        if (el.classList.contains("ts-ber-run")) {
            const aus = [];
            for (let tr = el.closest("tr").nextElementSibling; tr;
                 tr = tr.nextElementSibling) {
                if (tr.dataset.gruppe !== undefined) break;
                const k = tr.querySelector("input.ts-wahl");
                if (k) aus.push(k.value);
            }
            return aus;
        }
        // Link mit `?run=…` — die Kennung steht in der Query.
        const href = el.getAttribute("href") || "";
        const wert = new URLSearchParams(href.split("?")[1] || "").get("run");
        return wert ? [wert] : [];
    }

    async fahren(ids) {
        if (this.laeuft) {
            this._melden("Es läuft schon ein Testlauf — bitte abwarten.", "fehler");
            return;
        }
        this.laeuft = true;
        this._sperren(true);
        if (this.stop) this.stop.hidden = false;
        this._zuruecksetzen(ids);
        try {
            const antwort = await fetch(this.url, {
                method: "POST",
                headers: {"Content-Type": "application/json",
                          "X-CSRFToken": this._csrf()},
                credentials: "same-origin",
                body: JSON.stringify({ids}),
            });
            if (!antwort.ok && antwort.headers.get("content-type")
                    ?.includes("json")) {
                const d = await antwort.json();
                this._melden(d.error || ("HTTP " + antwort.status), "fehler");
                return;
            }
            await this._lesen(antwort);
        } catch (fehler) {
            this._melden("Abgebrochen: " + fehler.message, "fehler");
        } finally {
            this.laeuft = false;
            this._sperren(false);
            if (this.stop) this.stop.hidden = true;
        }
    }

    /** Abbrechen — der Server beendet den Prozessbaum und löst die Sperre.
     *
     *  Nicht nur `fetch` abbrechen: Das schließt die Verbindung, aber der
     *  Testprozess läuft weiter, bis der Server das merkt (bei blockierender
     *  Ausgabe gar nicht). Deshalb wird der Abbruch AUSGESPROCHEN. */
    async abbrechen() {
        this._melden("bricht ab …", "laeuft");
        try {
            const r = await fetch(this.url, {
                method: "POST",
                headers: {"Content-Type": "application/json",
                          "X-CSRFToken": this._csrf()},
                credentials: "same-origin",
                body: JSON.stringify({abbrechen: true}),
            });
            const d = await r.json();
            this._melden(d.meldung || d.error || "abgebrochen",
                         d.ok ? "gut" : "fehler");
        } catch (fehler) {
            this._melden("Abbruch fehlgeschlagen: " + fehler.message, "fehler");
        }
    }

    async _lesen(antwort) {
        const leser = antwort.body.getReader();
        const dekoder = new TextDecoder();
        let puffer = "";
        for (;;) {
            const {done, value} = await leser.read();
            if (done) break;
            puffer += dekoder.decode(value, {stream: true});
            const zeilen = puffer.split("\n");
            puffer = zeilen.pop();
            for (const zeile of zeilen) {
                if (!zeile.trim()) continue;
                try { this._ereignis(JSON.parse(zeile)); }
                catch (e) { this._schreiben(zeile); }
            }
        }
    }

    _ereignis(ev) {
        if (ev.type === "log") { this._schreiben(ev.line); return; }
        if (ev.type === "start") {
            this._melden("läuft: " + (ev.name || ""), "laeuft");
            // Die AUFGELÖSTEN Labels: „Alles ausführen" und „Kategorie
            // ausführen" schicken den Slug eines Sammelbefehls, und was dahinter
            // steckt, weiß nur der Server. Damit sind auch bei diesen Knöpfen
            // die richtigen Kästchen angehakt (Ansage 18.08.2026).
            // `alles` = Lauf ohne Label (ganzes Projekt): Dann ist jeder Fall
            // dabei, also wird jedes Kästchen angehakt.
            if (ev.alles) this._alleAnhaken();
            else this._anhaken(ev.ziele || []);
            this._schreiben("$ " + ev.cmd + "\n");
            return;
        }
        if (ev.type === "plan") { this._plan(ev.tests); return; }
        if (ev.type === "progress") {
            const [text, klasse] = STATUS[ev.status] || ["", ""];
            Teststrom.zeilen(ev.id).forEach(tr => statusSetzen(tr, text, klasse));
            // Was der Server meldet, ist gelaufen — also anhaken.
            this._anhaken([ev.id]);
            this.fertig++;
            this._balken();
            this._schreiben("[" + ev.status.toUpperCase() + "] " + ev.test);
            return;
        }
        if (ev.type === "error") {
            // `belegt` heisst: Es laeuft schon einer (serverseitige Sperre).
            this._melden(ev.detail || "Fehler", "fehler");
            return;
        }
        if (ev.type === "summary") this._abschluss(ev);
    }

    _abschluss(ev) {
        // Der Lauf ist durch: Balken voll, auch wenn „Found N" gefehlt hat
        // (dann steht dort jetzt die tatsächlich gefahrene Zahl).
        if (!this.plan) this.plan = ev.total || this.fertig;
        this.fertig = ev.total || this.fertig;
        if (this.balken) this.balken.classList.remove("unbestimmt");
        this._balken();
        Object.entries(ev.laeufe || {}).forEach(([id, laeufe]) =>
            Teststrom.zeilen(id).forEach(tr => zeitenSchreiben(tr, laeufe)));
        const teile = [ev.passed + " ok"];
        if (ev.failed) teile.push(ev.failed + " fehlgeschlagen");
        if (ev.errors) teile.push(ev.errors + " Fehler");
        if (ev.skipped) teile.push(ev.skipped + " übersprungen");
        // Gelb ist ein eigener Zustand: „Bestanden" waere die Unwahrheit,
        // wenn ein Teil des Laufs gar nicht stattgefunden hat.
        const zustand = ev.zustand
            || (ev.ok ? (ev.skipped ? "gelb" : "gruen") : "rot");
        const wort = { gruen: "Bestanden", gelb: "Unvollständig",
                       rot: "Fehlgeschlagen" }[zustand];
        const art = { gruen: "gut", gelb: "teilweise", rot: "fehler" }[zustand];
        this._melden(wort + " · " + (ev.name || "") + " · " + teile.join(" · ")
                     + " · " + Teststrom.dauer(ev.dauer), art);
        this._schreiben("\n=== " + teile.join(" · ") + " ===");
    }

    /** Jedes Kästchen anhaken (Lauf über das ganze Projekt). */
    _alleAnhaken() {
        const karten = new Set();
        document.querySelectorAll("input.ts-wahl").forEach(kasten => {
            if (!kasten.checked) {
                kasten.checked = true;
                const karte = kasten.closest(".ts-wahlkarte");
                if (karte) karten.add(karte);
            }
        });
        karten.forEach(karte => {
            const kasten = karte.querySelector("input.ts-wahl");
            if (kasten) kasten.dispatchEvent(new Event("change", {bubbles: true}));
        });
    }

    /** Gesamtzahl bekannt: Balken von „unbestimmt" auf Prozent umschalten. */
    _plan(anzahl) {
        this.plan = parseInt(anzahl, 10) || 0;
        if (this.balken) this.balken.classList.remove("unbestimmt");
        this._balken();
    }

    _balken() {
        if (!this.fuellung) return;
        const anteil = this.plan ? Math.min(100, this.fertig / this.plan * 100) : 0;
        this.fuellung.style.width = anteil + "%";
        if (this.zahl) {
            this.zahl.textContent = this.plan
                ? this.fertig + " / " + this.plan
                : (this.fertig ? String(this.fertig) : "");
        }
    }

    /** Kästchen anhaken — je betroffener Karte EIN `change`, damit
     *  `tests_auswahl.js` seine Zähler nachzieht (und nicht 173-mal). */
    _anhaken(ids) {
        if (!ids || !ids.length) return;
        const karten = new Set();
        // Kästchen EINMAL einsammeln: `_anhaken` läuft auch je gemeldetem Test,
        // und ein `querySelectorAll` über 1.300 Zeilen je Aufruf wäre spürbar.
        if (!this._kaesten) {
            this._kaesten = [...document.querySelectorAll("input.ts-wahl")];
        }
        ids.forEach(id => {
            this._kaesten.forEach(kasten => {
                // Genau dieser Fall — oder alles unter einem Label
                // („mail.tests.unit" hakt „mail.tests.unit.test_x.K.test_y" an).
                if (kasten.value === id || kasten.value.startsWith(id + ".")) {
                    if (!kasten.checked) {
                        kasten.checked = true;
                        const karte = kasten.closest(".ts-wahlkarte");
                        if (karte) karten.add(karte);
                    }
                }
            });
        });
        karten.forEach(karte => {
            const kasten = karte.querySelector("input.ts-wahl");
            if (kasten) kasten.dispatchEvent(new Event("change", {bubbles: true}));
        });
    }

    /** ALLE Zeilen zu einer Test-ID — über den Run-Knopf/Link, den sie tragen.
     *
     *  Mehrzahl, und das ist der Punkt: Derselbe Fall steht in ZWEI Tabellen —
     *  im Reiter seiner Kategorie und im Reiter „Alle". Die erste Fassung nahm
     *  den ersten Treffer, und der lag im gerade unsichtbaren Panel: Der Lauf
     *  war grün, in der Tabelle stand weiter „läuft …" (gemessen 17.08.2026). */
    static zeilen(id) {
        if (!id) return [];
        return [...document.querySelectorAll(".ts-run")]
            .filter(el => el.dataset.run === id
                || (el.getAttribute("href") || "").includes(
                    "run=" + encodeURIComponent(id)))
            .map(el => el.closest("tr"))
            .filter(Boolean);
    }

    static dauer(s) {
        if (s === null || s === undefined) return "";
        return s < 1 ? Math.round(s * 1000) + " ms"
                     : s.toFixed(2).replace(".", ",") + " s";
    }

    // ------------------------------------------------------------ Anzeige

    _zuruecksetzen(ids) {
        if (this.ausgabe) { this.ausgabe.textContent = ""; this.zeilen = 0; }
        const kasten = document.querySelector(".ts-strom");
        if (kasten) kasten.hidden = false;
        document.querySelectorAll("tr [data-status]").forEach(s => {
            s.textContent = ""; s.className = "ts-status";
        });
        this.plan = 0;
        this.fertig = 0;
        this._kaesten = null;          // Zeilen können sich geändert haben
        if (this.balken) this.balken.classList.add("unbestimmt");
        if (this.fuellung) this.fuellung.style.width = "0%";
        if (this.zahl) this.zahl.textContent = "";
        // Die angeforderten Zeilen sofort markieren — bei einem Sammellauf
        // sieht man sonst eine Minute lang gar nichts.
        ids.forEach(id => Teststrom.zeilen(id).forEach(
            tr => statusSetzen(tr, ...STATUS.laeuft)));
        this._anhaken(ids);
    }

    _sperren(an) {
        document.querySelectorAll(".ts-run, .ts-wahl-lauf, .ts-ber-run, "
                                 + ".ts-wahl-run").forEach(el => {
            el.classList.toggle("gesperrt", an);
            if (el.tagName === "BUTTON" && !el.classList.contains("ts-wahl-run"))
                el.disabled = an;
        });
    }

    _melden(text, art) {
        if (!this.kopf) return;
        this.kopf.className = "ts-strom-kopf " + (art || "");
        this.kopf.textContent = text;
    }

    /** Ausgabe anhängen — mit Deckel, sonst frisst ein langer Lauf den Speicher. */
    _schreiben(text) {
        if (!this.ausgabe) return;
        this.ausgabe.textContent += text + "\n";
        this.zeilen++;
        if (this.zeilen > 4000) {
            const zeilen = this.ausgabe.textContent.split("\n");
            this.ausgabe.textContent = zeilen.slice(-2000).join("\n");
            this.zeilen = 2000;
        }
        this.ausgabe.scrollTop = this.ausgabe.scrollHeight;
    }

    _csrf() {
        return (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
    }
}

const feld = document.getElementById("ts-strom-url");
if (feld) new Teststrom(JSON.parse(feld.textContent)).binden();
