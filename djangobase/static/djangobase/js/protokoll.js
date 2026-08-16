/**
 * Protokoll — Meldungen mit Stufen, wie der Python-Teil sie über `logging` hat.
 *
 * KANONISCHE FASSUNG in djangoBase (16.08.2026); die Umsteller unter
 * `djangobase/umbau/` schreiben Importe auf genau diese Klasse.
 *
 * DER FALL DAHINTER (3DTools): 144 `console.log`-Aufrufe im Frontend. Sie sind
 * zweierlei — Vorgangsmeldungen, die man sehen will ("3 Clips gespeichert"),
 * und Debug-Rauschen bei jeder Aktion ("[Undo] SUPPRESSED", 24 Zeilen für EINEN
 * Klick). Das Zweite verdeckt in der Konsole die echten Fehler, und genau dort
 * steckten an diesem Tag drei stille Ausfälle, die niemandem aufgefallen sind.
 *
 * Debug-Meldungen erscheinen nur, wenn sie eingeschaltet sind:
 *   * `?debug=1` an der Adresse, oder
 *   * `localStorage.setItem('app.debug', '1')` in der Konsole.
 */
export class Protokoll {

    /**
     * Schlüssel im localStorage. Projektunabhängig: `app.debug` gilt überall,
     * ein zweiter projekteigener Schlüssel kann daneben gesetzt werden
     * (`Protokoll.SCHLUESSEL = 'humanbody.debug'` beim Start der Seite).
     */
    static SCHLUESSEL = 'app.debug';

    static #an = null;

    /**
     * Debug zur Laufzeit ein- oder ausschalten — ohne Neuladen.
     *
     * Befund von Nemotron UND Gemma im Sparring am 16.08.2026: Der Zustand
     * wurde beim ersten Aufruf festgeschrieben. Wer in der Konsole
     * `localStorage.setItem('app.debug','1')` setzte, sah bis zum Neuladen
     * nichts — beim Debuggen genau der falsche Moment für eine Überraschung.
     *
     * Die Klasse liegt dafür auch auf `window` (siehe Dateiende), damit sie in
     * der Konsole erreichbar ist:  `Protokoll.debugSetzen(true)`
     */
    static debugSetzen(an) {
        Protokoll.#an = !!an;
        try {
            if (an) localStorage.setItem(Protokoll.SCHLUESSEL, '1');
            else localStorage.removeItem(Protokoll.SCHLUESSEL);
        } catch (fehler) {
            // localStorage kann gesperrt sein — der Schalter gilt dann nur
            // für diese Seite, und das ist besser als eine Ausnahme.
        }
        return Protokoll.#an;
    }

    /** true, wenn Debug-Meldungen erscheinen sollen. Wird einmal bestimmt. */
    static debugAn() {
        if (Protokoll.#an === null) {
            let gesetzt = false;
            try {
                gesetzt = new URLSearchParams(location.search).get('debug') === '1'
                          || localStorage.getItem(Protokoll.SCHLUESSEL) === '1';
            } catch (fehler) {
                gesetzt = false;   // localStorage kann gesperrt sein
            }
            Protokoll.#an = gesetzt;
        }
        return Protokoll.#an;
    }

    /** Einzelheiten für die Fehlersuche — still, solange nicht eingeschaltet. */
    static debug(bereich, ...teile) {
        if (Protokoll.debugAn()) console.log(`[${bereich}]`, ...teile);
    }

    /** Was der Benutzer wissen will: abgeschlossene Vorgänge. */
    static info(bereich, ...teile) {
        console.log(`[${bereich}]`, ...teile);
    }

    /** Etwas ist nicht wie erwartet, aber der Ablauf geht weiter. */
    static warnung(bereich, ...teile) {
        console.warn(`[${bereich}]`, ...teile);
    }

    /** Ein Vorgang ist gescheitert. */
    static fehler(bereich, ...teile) {
        console.error(`[${bereich}]`, ...teile);
    }
}

// In der Konsole erreichbar machen — sonst ist `debugSetzen` von aussen nicht
// aufrufbar, und genau dort braucht man ihn.
if (typeof window !== 'undefined') window.Protokoll = Protokoll;
