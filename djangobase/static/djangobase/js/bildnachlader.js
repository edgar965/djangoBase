/**
 * Bildnachlader — Bilder erst laden, wenn ihr Behälter sichtbar wird.
 *
 * WOZU (3DTools, 17.08.2026, im Browser gemessen): Die Szenenseite lud beim
 * Start **125 Vorschaubilder mit 4,77 MB** — die Hälfte aller Dateien der Seite.
 * Alle steckten in zugeklappten Listen (`display:none`), kein einziges war zu
 * sehen. Das langsamste meldete 1.361 ms; davon war fast alles Wartezeit in der
 * Warteschlange, denn der Browser hält je Host nur sechs Verbindungen offen —
 * und die brauchte die Seite für Netz und Gewichte (5,1 MB + 2,4 MB).
 *
 * WARUM NICHT `loading="lazy"` (gemessen, nicht vermutet): Zuerst stand an allen
 * 543 Bildern `loading="lazy"`. Danach lud die Seite **125 statt 127** Bilder —
 * also nichts gewonnen. Chrome verschiebt nur Bilder, die es UNTERHALB des
 * Fensters verortet; ein Bild in einem `display:none`-Behälter hat gar keine
 * Box, und Chrome lädt es sofort. Nachgeprüft am Bild selbst: `loading` war
 * `'lazy'`, `complete` trotzdem `true`, Höhe 0, Elternkette mit
 * `[display:none]`.
 *
 * WIE ES HIER GEHT: Der `src` wird gar nicht gesetzt, sondern in
 * `data-nachladen` geparkt. Ein `IntersectionObserver` schlägt zu, sobald das
 * Bild wirklich sichtbar wird — beim Aufklappen, beim Panelwechsel, beim
 * Scrollen. Das braucht KEINE Änderung an den Aufklapp-Handlern; wer eine Liste
 * baut, tauscht nur eine Zeile.
 *
 *     import { Bildnachlader } from '/static/djangobase/js/bildnachlader.js';
 *     Bildnachlader.vormerken(img, `/api/…/thumb/${id}/`);
 *
 * WICHTIG: Das `<img>` braucht eine feste Größe aus CSS (Breite UND Höhe).
 * Sonst ist es ohne `src` 0 Pixel hoch, liegt nie im Fenster — und wird nie
 * geladen. Genau diese Falle hat `loading="lazy"` oben zunichte gemacht.
 */

/** So weit vor dem Fenster wird schon geladen (flüssiges Scrollen). */
const VORLAUF = '200px';

export class Bildnachlader {
    /** @type {IntersectionObserver|null} */
    static _beobachter = null;

    /**
     * Bild vormerken, statt `src` zu setzen.
     *
     * @param {HTMLImageElement} bild
     * @param {string} quelle  die URL, die später eingesetzt wird
     */
    static vormerken(bild, quelle) {
        if (!quelle) return;
        // Ohne IntersectionObserver (sehr alte Browser) sofort laden — ein
        // fehlendes Bild wäre schlimmer als ein früh geladenes.
        if (typeof IntersectionObserver === 'undefined') {
            bild.src = quelle;
            return;
        }
        bild.dataset.nachladen = quelle;
        Bildnachlader._sicherstellen().observe(bild);
    }

    /**
     * Alle vorgemerkten Bilder unterhalb von `wurzel` sofort laden.
     *
     * Für die Fälle, in denen kein Sichtbarwerden eintritt: Druckansicht,
     * Bildexport, Tests.
     *
     * @param {ParentNode} [wurzel]
     */
    static sofort(wurzel = document) {
        for (const bild of wurzel.querySelectorAll('img[data-nachladen]')) {
            Bildnachlader._einsetzen(bild);
        }
    }

    /** Wie viele Bilder warten noch? Für Messung und Tests. */
    static offen(wurzel = document) {
        return wurzel.querySelectorAll('img[data-nachladen]').length;
    }

    static _sicherstellen() {
        if (!Bildnachlader._beobachter) {
            Bildnachlader._beobachter = new IntersectionObserver(
                eintraege => {
                    for (const eintrag of eintraege) {
                        if (!eintrag.isIntersecting) continue;
                        Bildnachlader._einsetzen(eintrag.target);
                    }
                },
                { rootMargin: VORLAUF });
        }
        return Bildnachlader._beobachter;
    }

    static _einsetzen(bild) {
        const quelle = bild.dataset.nachladen;
        if (!quelle) return;
        delete bild.dataset.nachladen;
        bild.src = quelle;
        if (Bildnachlader._beobachter) Bildnachlader._beobachter.unobserve(bild);
    }
}
