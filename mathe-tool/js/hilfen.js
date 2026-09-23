/* Allgemeine Hilfsfunktionen: Zufallszahlen, Zahlformat, Zahlengerade als SVG. */
window.MT = window.MT || {};
MT.themen = [];

(function (MT) {
  'use strict';

  /** Ganze Zufallszahl zwischen a und b (beide inklusive). */
  MT.rnd = function (a, b) {
    return a + Math.floor(Math.random() * (b - a + 1));
  };

  /** Wie rnd, aber nie 0. */
  MT.rndNZ = function (a, b) {
    let x;
    do { x = MT.rnd(a, b); } while (x === 0);
    return x;
  };

  MT.pick = function (arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  };

  MT.shuffle = function (arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };

  /** Zahl mit typografischem Minuszeichen: −7 */
  MT.z = function (n) {
    return n < 0 ? '−' + Math.abs(n) : String(n);
  };

  /** Negative Zahl in Klammern: (−7); positive Zahl ohne Klammern. */
  MT.k = function (n) {
    return n < 0 ? '(−' + Math.abs(n) + ')' : String(n);
  };

  MT.esc = function (s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  MT.term = function (s) {
    return '<div class="term">' + s + '</div>';
  };

  MT.schritte = function (arr) {
    return '<ol class="schritte">' + arr.map(function (s) { return '<li>' + s + '</li>'; }).join('') + '</ol>';
  };

  /**
   * Zahlengerade als SVG.
   * o.min, o.max        Bereich (ganze Zahlen)
   * o.beschriftung      jede wievielte Zahl beschriftet wird (Standard 5)
   * o.punkte            [{x, text, art:'b'}]  markierte Punkte (art 'b' = zweite Farbe)
   * o.pfeile            [{von, bis}]           Bewegung als Bogenpfeil
   */
  let zaehler = 0;
  MT.zahlengerade = function (o) {
    const min = o.min, max = o.max, beschr = o.beschriftung || 5;
    const punkte = o.punkte || [], pfeile = o.pfeile || [];
    const W = 640, P = 24;
    const y = pfeile.length ? 70 : 24;
    const H = y + (punkte.some(function (p) { return p.text; }) ? 56 : 36);
    const sx = function (x) { return P + (x - min) * (W - 2 * P) / (max - min); };
    const id = 'zg' + (++zaehler);
    const aria = o.aria || ('Zahlengerade von ' + MT.z(min) + ' bis ' + MT.z(max));

    let s = '<svg class="zg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + MT.esc(aria) + '">' +
      '<defs>' +
      '<marker id="' + id + 'a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,1 L9,5 L0,9 z" class="zg-spitze-achse"/></marker>' +
      '<marker id="' + id + 'p" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="zg-spitze"/></marker>' +
      '</defs>';

    s += '<line x1="' + (P - 16) + '" y1="' + y + '" x2="' + (W - 4) + '" y2="' + y + '" class="zg-achse" marker-end="url(#' + id + 'a)"/>';

    for (let x = min; x <= max; x++) {
      const gross = x % beschr === 0;
      const X = sx(x).toFixed(1);
      const l = gross ? 8 : 5;
      s += '<line x1="' + X + '" y1="' + (y - l) + '" x2="' + X + '" y2="' + (y + l) + '" class="zg-strich' + (gross ? ' gross' : '') + '"/>';
      if (gross) s += '<text x="' + X + '" y="' + (y + 26) + '" class="zg-zahl">' + MT.z(x) + '</text>';
    }

    pfeile.forEach(function (p) {
      const x1 = sx(p.von), x2 = sx(p.bis), yy = y - 9;
      const h = Math.min(48, 16 + Math.abs(x2 - x1) * 0.2);
      s += '<path d="M' + x1.toFixed(1) + ',' + yy + ' Q' + ((x1 + x2) / 2).toFixed(1) + ',' + (yy - 2 * h).toFixed(1) + ' ' + x2.toFixed(1) + ',' + yy + '" class="zg-pfeil" marker-end="url(#' + id + 'p)"/>';
    });

    punkte.forEach(function (p) {
      const X = sx(p.x).toFixed(1);
      const kl = p.art === 'b' ? ' b' : '';
      s += '<circle cx="' + X + '" cy="' + y + '" r="6.5" class="zg-punkt' + kl + '"/>';
      if (p.text) s += '<text x="' + X + '" y="' + (y + 48) + '" class="zg-marke' + kl + '">' + MT.esc(p.text) + '</text>';
    });

    return s + '</svg>';
  };
})(window.MT);
