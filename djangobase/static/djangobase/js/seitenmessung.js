/**
 * Seitenmessung — was eine Seite im BROWSER kostet.
 *
 * WOZU (17.08.2026): Ein Werkzeug, das Endpunkte über `urllib` abfragt, misst
 * die Serverzeit — nicht das, was der Benutzer erlebt. Zwischen „der Endpunkt
 * antwortet in 30 ms" und „die Seite ist nach 4 s bedienbar" liegen die
 * eigentlichen Kosten: Zahl und Größe der Dateien, Skripte, die aufeinander
 * warten, und Abrufe, die erst nach dem Laden starten.
 *
 * Gemessen wird alles, was die Navigation-Timing- und Resource-Timing-API
 * hergibt. Keine Schätzung, keine Stoppuhr von Hand.
 *
 * Aufruf in der Konsole (oder über Chrome-MCP):
 *     seitenmessung()
 *
 * ACHTUNG bei der Auswertung: `duration` einer Ressource enthält Wartezeit in
 * der Warteschlange des Browsers (sechs gleichzeitige Verbindungen pro Host).
 * Eine Datei mit 900 ms ist nicht zwingend langsam — sie stand vielleicht 800 ms
 * an. Deshalb steht `transferSize` daneben: Bytes lügen nicht.
 */
function seitenmessung() {
    const nav = performance.getEntriesByType('navigation')[0] || {};
    const mittel = (a, b) => Math.round((a || 0) - (b || 0));

    const dateien = performance.getEntriesByType('resource').map(e => ({
        name: e.name.replace(location.origin, '').split('?')[0],
        art: e.initiatorType,
        ms: Math.round(e.duration),
        bytes: e.transferSize || 0,
    }));
    const summe = (liste, feld) => liste.reduce((s, e) => s + e[feld], 0);
    const nachArt = {};
    for (const datei of dateien) {
        const eintrag = nachArt[datei.art] || { anzahl: 0, bytes: 0, ms: 0 };
        eintrag.anzahl += 1;
        eintrag.bytes += datei.bytes;
        eintrag.ms = Math.max(eintrag.ms, datei.ms);
        nachArt[datei.art] = eintrag;
    }

    return {
        seite: location.pathname,
        // Wann steht das Grundgerüst, wann ist alles geladen?
        html_ms: mittel(nav.responseEnd, nav.requestStart),
        dom_ms: Math.round(nav.domContentLoadedEventEnd || 0),
        geladen_ms: Math.round(nav.loadEventEnd || 0),
        // Was der Benutzer als „es tut sich was" wahrnimmt.
        erste_anzeige_ms: Math.round(
            (performance.getEntriesByName('first-contentful-paint')[0] || {})
                .startTime || 0),
        dateien: dateien.length,
        bytes: summe(dateien, 'bytes'),
        nach_art: nachArt,
        langsamste: [...dateien].sort((a, b) => b.ms - a.ms).slice(0, 8),
        groesste: [...dateien].sort((a, b) => b.bytes - a.bytes).slice(0, 8),
    };
}

/**
 * Dauer einer UI-Aktion messen: vom Klick bis zur letzten Netzantwort und dem
 * Ende der DOM-Änderungen.
 *
 * `aktion` wird ausgeführt, danach wird gewartet, bis `ruhe` Millisekunden
 * lang weder eine Netzanfrage noch eine DOM-Änderung passiert ist.
 *
 *     await aktionsmessung('Pose anwenden', () => knopf.click())
 */
async function aktionsmessung(name, aktion, ruhe = 400, grenze = 20000) {
    // Den Ressourcen-Puffer LEEREN, nicht nur die Länge merken.
    //
    // FALLE, im Browser gemessen (17.08.2026): Der Puffer hält standardmäßig
    // 250 Einträge. Auf der Szenenseite (250 Dateien) war er voll — jede neue
    // Anfrage wurde still verworfen, und die Messung meldete „0 Anfragen, 0
    // Bytes" für eine Aktion, die 2,3 MB geladen hat. Ein Werkzeug, das Null
    // meldet, wo etwas passiert, ist schlimmer als keines.
    performance.clearResourceTimings();
    performance.setResourceTimingBufferSize(1000);
    const start = performance.now();
    const vorher = 0;
    let letzte = performance.now();
    let aenderungen = 0;

    const beobachter = new MutationObserver(liste => {
        aenderungen += liste.length;
        letzte = performance.now();
    });
    beobachter.observe(document.body,
                       { childList: true, subtree: true, attributes: true });
    const netz = new PerformanceObserver(() => { letzte = performance.now(); });
    netz.observe({ entryTypes: ['resource'] });

    await aktion();
    while (performance.now() - letzte < ruhe
           && performance.now() - start < grenze) {
        await new Promise(r => setTimeout(r, 50));
    }
    beobachter.disconnect();
    netz.disconnect();

    const neue = performance.getEntriesByType('resource').slice(vorher);
    return {
        aktion: name,
        ms: Math.round(letzte - start),
        anfragen: neue.length,
        bytes: neue.reduce((s, e) => s + (e.transferSize || 0), 0),
        dom_aenderungen: aenderungen,
        langsamste: neue.map(e => ({
            name: e.name.replace(location.origin, '').split('?')[0],
            ms: Math.round(e.duration),
        })).sort((a, b) => b.ms - a.ms).slice(0, 3),
    };
}

/**
 * Bilder je Sekunde der Renderschleife über `sekunden` messen.
 *
 * WICHTIG: Nur in einem AKTIVEN Tab aussagekräftig — `requestAnimationFrame`
 * ruht im Hintergrund, die Messung liefert dort 0 und sieht nach einem
 * Totalausfall aus.
 */
function bildrate(sekunden = 2) {
    return new Promise(fertig => {
        let bilder = 0;
        const start = performance.now();
        const zaehlen = () => {
            bilder++;
            if (performance.now() - start < sekunden * 1000) {
                requestAnimationFrame(zaehlen);
            } else {
                fertig({ bilder, sekunden,
                         fps: Math.round(bilder / sekunden) });
            }
        };
        requestAnimationFrame(zaehlen);
    });
}

/**
 * Mehrere Seiten nacheinander messen — in EINEM wiederverwendeten Fenster.
 *
 * WARUM KEIN IFRAME (17.08.2026, im Browser gemessen): Django setzt
 * `X-Frame-Options: DENY`. Der Rahmen bleibt dann leer, und der Zugriff auf
 * `contentWindow.performance` scheitert mit „Blocked a frame … from accessing
 * a cross-origin frame" — obwohl es dieselbe Herkunft ist. Die Alternative
 * waere, die Sicherheitseinstellung des Projekts zu lockern; dafuer ist eine
 * Messung kein Grund.
 *
 * Ein Fenster mit festem Namen wird wiederverwendet, also entsteht kein
 * Popup-Regen. Der Aufruf MUSS aus einem Klick heraus geschehen, sonst
 * blockiert der Browser das erste Fenster.
 *
 * @param {string[]} adressen
 * @param {Function} melden  wird nach jeder Seite mit dem Ergebnis gerufen
 */
async function seitenLaufMessen(adressen, melden = null) {
    const ergebnisse = [];
    const fenster = window.open(adressen[0], 'djangobase_messung',
                                'width=1280,height=800');
    if (!fenster) {
        throw new Error('Der Browser hat das Messfenster blockiert — bitte '
                        + 'Popups fuer diese Seite erlauben.');
    }
    try {
        for (const adresse of adressen) {
            const messwert = await _eineSeiteMessen(fenster, adresse);
            ergebnisse.push(messwert);
            if (melden) melden(messwert);
        }
    } finally {
        fenster.close();
    }
    return ergebnisse;
}

/** So lange darf eine Seite hoechstens laden, bevor sie als haengend gilt. */
const SEITE_GRENZE_MS = 30000;
/** So lange wird nach `load` noch auf Nachzuegler gewartet. */
const NACHLAUF_MS = 1500;

async function _eineSeiteMessen(fenster, adresse) {
    const start = performance.now();
    fenster.location.href = adresse;
    // Auf das Ende des Ladens warten — `readyState` statt `onload`, weil das
    // Ereignis bei einer Navigation im fremden Fenster nicht zuverlaessig
    // ankommt.
    while (performance.now() - start < SEITE_GRENZE_MS) {
        await new Promise(r => setTimeout(r, 100));
        try {
            if (fenster.document.readyState === 'complete'
                && fenster.location.pathname === adresse.split('?')[0]) break;
        } catch (fehler) {
            // Waehrend der Navigation ist der Zugriff kurz gesperrt.
        }
    }
    await new Promise(r => setTimeout(r, NACHLAUF_MS));
    try {
        const nav = fenster.performance.getEntriesByType('navigation')[0] || {};
        const dateien = fenster.performance.getEntriesByType('resource');
        const bytes = dateien.reduce((s, e) => s + (e.transferSize || 0), 0);
        const groesste = [...dateien]
            .sort((a, b) => (b.transferSize || 0) - (a.transferSize || 0))
            .slice(0, 3)
            .map(e => e.name.split('/').slice(-2).join('/').split('?')[0]
                      + ' (' + Math.round((e.transferSize || 0) / 1024) + ' KB)');
        return {
            seite: adresse,
            dom_ms: Math.round(nav.domContentLoadedEventEnd || 0),
            geladen_ms: Math.round(nav.loadEventEnd || 0),
            gesamt_ms: Math.round(performance.now() - start - NACHLAUF_MS),
            dateien: dateien.length,
            kb: Math.round(bytes / 1024),
            groesste,
        };
    } catch (fehler) {
        return { seite: adresse, fehler: fehler.message };
    }
}
