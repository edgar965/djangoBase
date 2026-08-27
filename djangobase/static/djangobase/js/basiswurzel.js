/**
 * Unter welchem Praefix `djangobase.urls` eingebunden ist.
 *
 * WARUM (Befund 27.08.2026, 3DTools)
 * ==================================
 * Jedes Projekt haengt djangoBase woanders ein:
 *
 *     shortlongx   /hilfe/...
 *     assistant    /...
 *     3DTools      /help/...
 *
 * `aufzeichner.js`, `aufzeichner_abspieler.js`, `aufzeichner_leiste.js` und
 * `aufzeichnung.js` hatten `/hilfe/tests/aufzeichnung/` fest im Text. In
 * 3DTools liefen sie damit bei JEDEM Seitenaufruf dreimal in eine 404 — keine
 * Fehlerseite, kein Eintrag im Fehlerlog, die Aufnahme war einfach still tot.
 *
 * Die Wurzel steht seither einmal im Grundgeruest (`_shell.html`,
 * `<meta name="djangobase-wurzel">`) und wird hier gelesen.
 */
export class Basiswurzel {
    /** Name des Kennzeichens im Kopf der Seite. */
    static KENNZEICHEN = 'djangobase-wurzel';

    /** Was gilt, wenn das Kennzeichen fehlt — die haeufigste Einbindung. */
    static ERSATZ = '/hilfe/';

    /** @returns {string} z. B. `'/help/'`, `'/hilfe/'` oder `'/'` */
    static wurzel() {
        const kopf = document.querySelector(
            `meta[name="${Basiswurzel.KENNZEICHEN}"]`);
        const wert = kopf?.getAttribute('content') || '';
        // Ein leeres `content` ist kein gueltiger Praefix: Es entstuende
        // `tests/aufzeichnung/` — relativ zur aktuellen Seite, also woanders
        // je nachdem, wo man gerade steht.
        if (!wert.startsWith('/')) return Basiswurzel.ERSATZ;
        return wert.endsWith('/') ? wert : wert + '/';
    }

    /**
     * Vollstaendige Adresse einer djangoBase-Route.
     * @param {string} rest Weg hinter der Wurzel, z. B. `'tests/aufzeichnung/'`
     * @returns {string}
     */
    static weg(rest) {
        return Basiswurzel.wurzel() + String(rest).replace(/^\/+/, '');
    }
}
