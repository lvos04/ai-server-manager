/* Peil-prototypes: alleen gedrag dat de componentspecificatie laat zien (tabs, grafiek, kopiëren, R3-bevestiging).
   In de Hub levert Radix/React dit; hier is het een referentie voor toetsenbord en schermlezer. */
(function () {
  'use strict';
  // Tabs: roving tabindex, pijltjes, Home/End (WAI-ARIA tabs, automatische activatie)
  document.querySelectorAll('[role=tablist]').forEach(function (lijst) {
    var tabs = Array.prototype.slice.call(lijst.querySelectorAll('[role=tab]'));
    function kies(t, focus) {
      tabs.forEach(function (x) {
        var aan = x === t; x.setAttribute('aria-selected', aan); x.tabIndex = aan ? 0 : -1;
        var p = document.getElementById(x.getAttribute('aria-controls')); if (p) p.hidden = !aan;
      });
      if (focus) t.focus();
    }
    tabs.forEach(function (t, k) {
      t.addEventListener('click', function () { kies(t, false); });
      t.addEventListener('keydown', function (e) {
        var n = null;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') n = tabs[(k + 1) % tabs.length];
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') n = tabs[(k - 1 + tabs.length) % tabs.length];
        if (e.key === 'Home') n = tabs[0];
        if (e.key === 'End') n = tabs[tabs.length - 1];
        if (n) { e.preventDefault(); kies(n, true); }
      });
    });
  });

  // Kopiëren: clipboard-API alleen in een secure context; anders tekst selecteren + eerlijke melding (E-34).
  document.querySelectorAll('[data-kopieer]').forEach(function (b) {
    b.addEventListener('click', function () {
      var id = b.getAttribute('data-kopieer'), el = document.getElementById(id);
      var meld = document.querySelector('[data-kopieer-melding="' + id + '"]');
      function selecteer() { var r = document.createRange(); r.selectNodeContents(el); var s = getSelection(); s.removeAllRanges(); s.addRange(r); }
      if (window.isSecureContext && navigator.clipboard) {
        navigator.clipboard.writeText(el.textContent).then(function () { meld.textContent = 'Gekopieerd.'; }, function () { selecteer(); meld.textContent = 'Tekst geselecteerd. Kopieer via het menu van je browser.'; });
      } else { selecteer(); meld.textContent = 'Tekst geselecteerd. Kopieer via het menu van je browser.'; }
    });
  });

  // Grafiek: draadkruis met aanwijzer én pijltjestoetsen; voorlezen via een polite live-regio.
  document.querySelectorAll('[data-grafiek]').forEach(function (g) {
    var d = JSON.parse(g.getAttribute('data-grafiek')), n = d.punten.length, k = n - 1;
    var kruis = g.querySelector('[data-kruis]'), tip = g.querySelector('[data-tip]');
    var voor = document.querySelector('[data-voorlees="' + g.id + '"]');
    function tekst(p) { return p.v == null ? 'Geen meting' : p.v.toLocaleString('nl-NL') + ' ' + d.eenheid; }
    function toon(j, lees) {
      k = Math.max(0, Math.min(n - 1, j)); var p = d.punten[k], x = k / (n - 1) * 100;
      kruis.style.left = x + '%'; kruis.classList.remove('hidden');
      tip.innerHTML = ''; var w = document.createElement('div'); w.className = 'text-base font-bold'; w.textContent = tekst(p);
      var t = document.createElement('div'); t.className = 'text-muted-foreground'; t.textContent = d.reeksnaam + ' · ' + p.t;
      tip.appendChild(w); tip.appendChild(t); tip.style.display = 'block';
      tip.style.left = (x > 60 ? 'auto' : 'calc(' + x + '% + 8px)'); tip.style.right = (x > 60 ? 'calc(' + (100 - x) + '% + 8px)' : 'auto');
      if (lees && voor) voor.textContent = p.t + ': ' + tekst(p);
    }
    function weg() { kruis.classList.add('hidden'); tip.style.display = 'none'; }
    g.addEventListener('pointermove', function (e) { var r = g.getBoundingClientRect(); toon(Math.round((e.clientX - r.left) / r.width * (n - 1)), false); });
    g.addEventListener('pointerleave', weg);
    g.addEventListener('blur', weg);
    g.addEventListener('focus', function () { toon(k, true); });
    g.addEventListener('keydown', function (e) {
      var m = { ArrowRight: 1, ArrowLeft: -1, Home: -n, End: n }[e.key];
      if (m) { e.preventDefault(); toon(k + m, true); }
      if (e.key === 'Escape') weg();
    });
  });

  // R3: bevestigknop pas actief na de getypte controle (C-21).
  document.querySelectorAll('[data-bevestig-tekst]').forEach(function (inp) {
    var knop = document.getElementById(inp.getAttribute('data-bevestig-knop'));
    var reden = document.getElementById(inp.getAttribute('data-bevestig-reden'));
    inp.addEventListener('input', function () {
      var ok = inp.value.trim() === inp.getAttribute('data-bevestig-tekst');
      if (ok) { knop.removeAttribute('aria-disabled'); reden.textContent = 'De naam klopt. Je kunt nu goedkeuren.'; }
      else { knop.setAttribute('aria-disabled', 'true'); reden.textContent = 'Typ eerst de naam van de app om te bevestigen.'; }
    });
    knop.addEventListener('click', function (e) { if (knop.getAttribute('aria-disabled') === 'true') { e.preventDefault(); inp.focus(); } });
  });
})();
