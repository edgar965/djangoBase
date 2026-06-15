/**
 * djangoBase Sidebar-Toggle — Collapse (Desktop) + Drawer (Mobile).
 * Portiert aus dem Assistant (mail/js/base/SidebarToggle.js), ohne
 * ES-Modul-Abhaengigkeit.
 *
 * - Desktop (>768px): Toggle klappt die Sidebar ein/aus; Zustand wird in
 *   localStorage['djangobase.sidebarCollapsed'] gemerkt.
 * - Mobile (<=768px): Toggle oeffnet die Sidebar als Drawer; Klick auf den
 *   Hintergrund schliesst sie wieder.
 *
 * Der Topbar-Button in _shell.html ruft window.toggleSidebar() auf.
 * Der eingeklappte Zustand wird zusaetzlich schon im <head> (Pre-Paint)
 * wiederhergestellt, um Flackern zu vermeiden.
 */
(function () {
    var MOBILE = 768;
    var KEY = 'djangobase.sidebarCollapsed';

    function istMobil() {
        return window.matchMedia('(max-width: ' + MOBILE + 'px)').matches;
    }

    function toggle() {
        if (istMobil()) {
            document.body.classList.toggle('sidebar-mobile-open');
            return;
        }
        var collapsed = document.body.classList.toggle('sidebar-collapsed');
        try { localStorage.setItem(KEY, collapsed ? '1' : '0'); } catch (e) {}
    }

    // Gespeicherten eingeklappten Zustand wiederherstellen.
    try {
        if (localStorage.getItem(KEY) === '1') {
            document.body.classList.add('sidebar-collapsed');
        }
    } catch (e) {}

    // Klick auf den abgedunkelten Hintergrund (Mobile) schliesst den Drawer.
    document.addEventListener('click', function (e) {
        if (!document.body.classList.contains('sidebar-mobile-open')) return;
        if (e.target.closest('.sidebar')) return;
        if (e.target.closest('#sidebar-toggle')) return;
        document.body.classList.remove('sidebar-mobile-open');
    });

    // Global fuer den inline-onclick im Topbar.
    window.toggleSidebar = toggle;

    // Aktuellen Pfad in der Sidebar markieren + die zugehoerige Menue-Gruppe
    // (Bootstrap-Collapse) aufklappen. So zeigt die per DJANGOBASE["menu"]
    // gerenderte Sidebar denselben Active-State wie eine handgebaute — ohne
    // dass jedes Projekt das serverseitig pro Link loesen muss.
    (function markActive() {
        function norm(p) { return (p || '/').replace(/\/+$/, '') || '/'; }
        var here;
        try { here = new URL(location.href); } catch (e) { return; }
        var path = norm(here.pathname);

        // Alle Links einsammeln, deren PFAD zur aktuellen Seite passt.
        var cands = [];
        document.querySelectorAll('.sidebar .nav-link[href]').forEach(function (a) {
            var href = a.getAttribute('href');
            if (!href || href.charAt(0) === '#') return;
            var u;
            try { u = new URL(href, location.origin); } catch (e) { return; }
            if (norm(u.pathname) !== path) return;
            cands.push({ el: a, search: u.search, hash: u.hash });
        });
        if (!cands.length) return;

        // Teilen sich mehrere Links denselben Pfad (Listen-/Tab-Eintraege, die
        // sich nur in ?query oder #fragment unterscheiden — z.B. `?q=tag:a` vs
        // `?q=tag:b`, oder `/config/` vs `/config/#tab`), waehlen wir den zur
        // aktuellen URL SPEZIFISCHSTEN Treffer — statt alle zu markieren (alter
        // Bug: alles leuchtet) oder keinen (zu grob: Active-State geht verloren).
        // Links mit nicht-passender Query/Fragment fallen raus.
        var filtered = cands.filter(function (c) {
            if (c.search && c.search !== here.search) return false;
            if (c.hash && c.hash !== here.hash) return false;
            return true;
        });
        if (!filtered.length) return;

        function score(c) {
            return (c.search && c.search === here.search ? 2 : 0)
                 + (c.hash && c.hash === here.hash ? 1 : 0);
        }
        filtered.sort(function (a, b) { return score(b) - score(a); });
        // Top-Score genau einmal -> eindeutiger Gewinner. Mehrfach (echt
        // identische Hrefs) -> lieber keinen markieren als willkuerlich einen.
        var top = score(filtered[0]);
        var winners = filtered.filter(function (c) { return score(c) === top; });
        if (winners.length !== 1) return;

        var a = winners[0].el;
        a.classList.add('active');
        // ALLE Collapse-Vorfahren aufklappen (nicht nur den innersten), damit
        // bei 3-stufigen Menues die komplette Kette zum aktiven Link offen ist.
        // Bei 2-stufigen Menues gibt es genau einen Vorfahren -> Verhalten
        // identisch zu vorher.
        var node = a, coll;
        while (node && (coll = node.closest('.collapse'))) {
            coll.classList.add('show');
            var tgl = document.querySelector('.menu-toggle[href="#' + coll.id + '"]');
            if (tgl) tgl.setAttribute('aria-expanded', 'true');
            node = coll.parentElement;
        }
    })();
})();
