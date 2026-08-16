/**
 * Htmltext — Fremdtext maskieren, bevor er in `innerHTML` landet.
 *
 * KANONISCHE FASSUNG in djangoBase (16.08.2026).
 *
 * DER FALL DAHINTER: Eine Auftragstabelle baute ihre Zeilen mit
 * Zeichenkettenverkettung und schrieb Serverdaten ungefiltert hinein —
 * Dateinamen aus dem Upload und Fehlermeldungen des Servers:
 *
 *     zeile.innerHTML = '<td>' + name + '</td>' + …
 *     fehler.innerHTML = '<strong>Fehler:</strong> ' + daten.error;
 *
 * Ein hochgeladenes Video mit dem Namen `<img src=x onerror=alert(1)>.mp4`
 * führt damit fremdes JavaScript aus. Gefunden im Sparring mit Nemotron am
 * 16.08.2026; die Stelle war vorher genauso offen, also kein neuer Fehler —
 * aber einer, der behoben gehört.
 *
 * REGEL: `textContent` ist immer die erste Wahl. Wo eine Zeile als Ganzes
 * gebaut wird (Tabellenzeilen, Vorlagen), geht jeder Fremdwert durch
 * `Htmltext.maskieren`.
 */
export class Htmltext {

    /** Zeichen, die aus Text in HTML gefährlich werden. */
    static ERSATZ = {
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    };

    /**
     * Text so maskieren, dass er als Inhalt oder in einem
     * doppelt-quotierten Attribut sicher ist.
     * @param {*} wert  beliebiger Wert; null/undefined werden zu ''
     */
    static maskieren(wert) {
        if (wert === null || wert === undefined) return '';
        return String(wert).replace(/[&<>"']/g,
                                    zeichen => Htmltext.ERSATZ[zeichen]);
    }

    /**
     * Kurzform für Vorlagen: `Htmltext.t` liest sich in langen
     * Zeichenketten besser als der volle Name.
     */
    static t(wert) {
        return Htmltext.maskieren(wert);
    }
}
