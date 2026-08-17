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
   sind die Startknöpfe gesperrt. */

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
    }

    binden() {
        const seite = document.querySelector(".ts-page");
        if (!seite || !this.url) return this;
        // Sagt `tests_auswahl.js`: nicht posten, sondern melden.
        seite.dataset.testsAuswahl = "ereignis";
        this.ausgabe = document.getElementById("ts-strom-ausgabe");
        this.kopf = document.getElementById("ts-strom-kopf");
        this.stop = document.getElementById("ts-strom-stop");
        if (this.stop) this.stop.addEventListener("click", () => this.abbrechen());
        document.addEventListener("click", e => this._klick(e));
        document.addEventListener("tests:auswahl-lauf",
                                  e => this.fahren(e.detail.ids));
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
            this._schreiben("$ " + ev.cmd + "\n");
            return;
        }
        if (ev.type === "progress") {
            const [text, klasse] = STATUS[ev.status] || ["", ""];
            Teststrom.zeilen(ev.id).forEach(tr => statusSetzen(tr, text, klasse));
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
        Object.entries(ev.laeufe || {}).forEach(([id, laeufe]) =>
            Teststrom.zeilen(id).forEach(tr => zeitenSchreiben(tr, laeufe)));
        const teile = [ev.passed + " ok"];
        if (ev.failed) teile.push(ev.failed + " fehlgeschlagen");
        if (ev.errors) teile.push(ev.errors + " Fehler");
        if (ev.skipped) teile.push(ev.skipped + " übersprungen");
        this._melden((ev.ok ? "Bestanden" : "Fehlgeschlagen") + " · "
                     + (ev.name || "") + " · " + teile.join(" · ")
                     + " · " + Teststrom.dauer(ev.dauer),
                     ev.ok ? "gut" : "fehler");
        this._schreiben("\n=== " + teile.join(" · ") + " ===");
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
        // Die angeforderten Zeilen sofort markieren — bei einem Sammellauf
        // sieht man sonst eine Minute lang gar nichts.
        ids.forEach(id => Teststrom.zeilen(id).forEach(
            tr => statusSetzen(tr, ...STATUS.laeuft)));
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
