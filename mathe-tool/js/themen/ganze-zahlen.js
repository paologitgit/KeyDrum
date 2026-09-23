/* Thema: Ganze Zahlen (Lehrplan 21, MA.1 Zahl und Variable) */
(function (MT) {
  'use strict';

  const rnd = MT.rnd, rndNZ = MT.rndNZ, pick = MT.pick, shuffle = MT.shuffle;
  const z = MT.z, k = MT.k, term = MT.term, schritte = MT.schritte, zg = MT.zahlengerade;

  const vorzeichenText = function (a, b) {
    return (a < 0) === (b < 0)
      ? 'gleiche Vorzeichen → Ergebnis positiv'
      : 'verschiedene Vorzeichen → Ergebnis negativ';
  };

  /* ------------------------------------------------------------------ */
  /* Einführung                                                          */
  /* ------------------------------------------------------------------ */

  function widgetGerade(el) {
    el.innerHTML =
      '<label class="regler">Zahl wählen <input type="range" min="-10" max="10" value="-4" step="1"><output></output></label>' +
      '<div class="bild"></div><p class="widget-text"></p>';
    const r = el.querySelector('input'), o = el.querySelector('output');
    const bild = el.querySelector('.bild'), text = el.querySelector('.widget-text');
    function zeichnen() {
      const x = Number(r.value);
      o.textContent = z(x);
      const punkte = [{ x: x, text: z(x) }];
      if (x !== 0) punkte.push({ x: -x, text: z(-x), art: 'b' });
      bild.innerHTML = zg({ min: -10, max: 10, beschriftung: 5, punkte: punkte });
      text.innerHTML = x === 0
        ? 'Die Zahl 0 ist weder positiv noch negativ. Ihr Betrag ist 0, ihre Gegenzahl ebenfalls 0.'
        : 'Die Zahl <strong>' + z(x) + '</strong> ist ' + (x < 0 ? 'negativ' : 'positiv') + '. ' +
          'Ihr Abstand zur 0 beträgt ' + Math.abs(x) + '. Das ist der <strong>Betrag</strong>: |' + z(x) + '| = ' + Math.abs(x) + '. ' +
          'Die <strong>Gegenzahl</strong> ist <span class="farbe-b">' + z(-x) + '</span>. Sie ist gleich weit von 0 entfernt, liegt aber auf der anderen Seite.';
    }
    r.addEventListener('input', zeichnen);
    zeichnen();
  }

  function widgetRechnen(el) {
    el.innerHTML =
      '<div class="regler-gruppe">' +
      '<label class="regler">Startzahl <input type="range" min="-10" max="10" value="3" data-k="a"><output></output></label>' +
      '<label class="regler">Rechenart <select data-k="op"><option value="+">+ addieren</option><option value="-">− subtrahieren</option></select></label>' +
      '<label class="regler">Zweite Zahl <input type="range" min="-10" max="10" value="-5" data-k="b"><output></output></label>' +
      '</div><div class="term gross"></div><div class="bild"></div><p class="widget-text"></p>';
    const ea = el.querySelector('[data-k=a]'), eb = el.querySelector('[data-k=b]'), eop = el.querySelector('[data-k=op]');
    const outs = el.querySelectorAll('output');
    function zeichnen() {
      const a = Number(ea.value), b = Number(eb.value), op = eop.value;
      outs[0].textContent = z(a);
      outs[1].textContent = z(b);
      const d = op === '+' ? b : -b, erg = a + d;
      el.querySelector('.term').innerHTML = op === '+'
        ? z(a) + ' + ' + k(b) + ' = ' + z(erg)
        : z(a) + ' − ' + k(b) + ' = ' + z(a) + ' + ' + k(-b) + ' = ' + z(erg);
      el.querySelector('.bild').innerHTML = zg({
        min: -20, max: 20, beschriftung: 5,
        punkte: [{ x: a, text: z(a) }].concat(d !== 0 ? [{ x: erg, text: z(erg), art: 'b' }] : []),
        pfeile: d !== 0 ? [{ von: a, bis: erg }] : []
      });
      let t = d === 0
        ? 'Mit 0 verändert sich nichts.'
        : 'Sie starten bei ' + z(a) + ' und gehen ' + Math.abs(d) + (Math.abs(d) === 1 ? ' Schritt' : ' Schritte') + ' nach ' + (d < 0 ? 'links' : 'rechts') + '.';
      if (op === '-' && b !== 0) t += ' Das Subtrahieren von ' + k(b) + ' entspricht dem Addieren der Gegenzahl ' + k(-b) + '.';
      el.querySelector('.widget-text').innerHTML = t;
    }
    [ea, eb, eop].forEach(function (e) { e.addEventListener('input', zeichnen); });
    zeichnen();
  }

  const einfuehrung = [
    {
      titel: 'Wozu negative Zahlen?',
      html:
        '<p>Mit den natürlichen Zahlen 0, 1, 2, 3, … lassen sich viele Situationen nicht beschreiben. Dafür braucht es Zahlen unter null:</p>' +
        '<ul class="beispiele">' +
        '<li><strong>Temperatur:</strong> In einer Winternacht misst man −12 °C.</li>' +
        '<li><strong>Kontostand:</strong> Ein Konto mit Fr. −250 ist um 250 Franken überzogen.</li>' +
        '<li><strong>Höhe:</strong> Das Ufer des Toten Meeres liegt rund 430 m unter dem Meeresspiegel, also auf −430 m.</li>' +
        '<li><strong>Stockwerk:</strong> Im Lift steht −2 für das zweite Untergeschoss.</li>' +
        '</ul>' +
        '<p>Die Zahlen …, −3, −2, −1, 0, 1, 2, 3, … heissen <strong>ganze Zahlen</strong>. Man bezeichnet sie mit dem Zeichen ℤ. ' +
        'Positive Zahlen schreibt man meist ohne Vorzeichen: 5 bedeutet +5.</p>'
    },
    {
      titel: 'Die Zahlengerade',
      html:
        '<p>Auf der Zahlengerade liegen die negativen Zahlen links von 0 und die positiven rechts davon. Es gilt: <strong>Je weiter rechts eine Zahl liegt, desto grösser ist sie.</strong></p>' +
        '<p>Deshalb ist −8 kleiner als −3, obwohl 8 grösser ist als 3: −8 &lt; −3.</p>' +
        '<dl class="begriffe">' +
        '<dt>Betrag</dt><dd>Der Abstand einer Zahl zur 0. Er ist nie negativ: |−6| = 6 und |6| = 6.</dd>' +
        '<dt>Gegenzahl</dt><dd>Die Zahl mit dem gleichen Betrag auf der anderen Seite der 0: Die Gegenzahl von −6 ist 6.</dd>' +
        '</dl>' +
        '<p class="klein">Verschieben Sie den Regler und beobachten Sie Betrag und Gegenzahl.</p>',
      widget: widgetGerade
    },
    {
      titel: 'Addieren und subtrahieren',
      html:
        '<p>Addieren und Subtrahieren lassen sich als Bewegung auf der Zahlengerade verstehen:</p>' +
        '<ul>' +
        '<li>Eine <strong>positive</strong> Zahl addieren: nach <strong>rechts</strong> gehen. &nbsp; −2 + 5 = 3</li>' +
        '<li>Eine <strong>negative</strong> Zahl addieren: nach <strong>links</strong> gehen. &nbsp; 4 + (−6) = −2</li>' +
        '<li>Eine Zahl <strong>subtrahieren</strong> heisst: ihre <strong>Gegenzahl addieren</strong>. &nbsp; 5 − (−3) = 5 + 3 = 8</li>' +
        '</ul>' +
        '<p>Daraus ergibt sich eine Kurzregel für zwei Zeichen nebeneinander:</p>' +
        '<table class="tabelle"><thead><tr><th>Zeichen</th><th>wird zu</th><th>Beispiel</th></tr></thead><tbody>' +
        '<tr><td>+ (+ …)</td><td>+</td><td>7 + (+2) = 7 + 2 = 9</td></tr>' +
        '<tr><td>− (− …)</td><td>+</td><td>7 − (−2) = 7 + 2 = 9</td></tr>' +
        '<tr><td>+ (− …)</td><td>−</td><td>7 + (−2) = 7 − 2 = 5</td></tr>' +
        '<tr><td>− (+ …)</td><td>−</td><td>7 − (+2) = 7 − 2 = 5</td></tr>' +
        '</tbody></table>' +
        '<p class="klein">Probieren Sie verschiedene Rechnungen aus.</p>',
      widget: widgetRechnen
    },
    {
      titel: 'Multiplizieren und dividieren',
      html:
        '<p>Beim Multiplizieren und Dividieren rechnet man zuerst mit den Beträgen. Das Vorzeichen bestimmt man separat:</p>' +
        '<table class="tabelle"><thead><tr><th>Vorzeichen</th><th>Ergebnis</th><th>Beispiel</th></tr></thead><tbody>' +
        '<tr><td>gleich: (+)·(+) oder (−)·(−)</td><td>positiv</td><td>(−3) · (−4) = 12</td></tr>' +
        '<tr><td>verschieden: (+)·(−) oder (−)·(+)</td><td>negativ</td><td>3 · (−4) = −12</td></tr>' +
        '</tbody></table>' +
        '<p>Für die Division gelten dieselben Regeln: (−12) : (−4) = 3 und (−12) : 4 = −3.</p>' +
        '<p><strong>Warum ist „minus mal minus“ plus?</strong> Betrachten Sie die folgende Reihe:</p>' +
        '<div class="muster">' +
        '<span>3 · (−2) = −6</span><span>2 · (−2) = −4</span><span>1 · (−2) = −2</span><span>0 · (−2) = 0</span>' +
        '<span class="hervor">(−1) · (−2) = 2</span><span class="hervor">(−2) · (−2) = 4</span>' +
        '</div>' +
        '<p>Mit jedem Schritt wird der erste Faktor um 1 kleiner und das Ergebnis um 2 grösser. Wenn man dieses Muster fortsetzt, ergibt sich ein positives Ergebnis.</p>' +
        '<p>Auch bei ganzen Zahlen gilt: <strong>Punkt- vor Strichrechnung</strong>, und Klammern werden zuerst berechnet.</p>'
    },
    {
      titel: 'Durchgerechnete Beispiele',
      html:
        '<details class="beispiel"><summary><span class="term inline">−7 + 12 − (−4)</span></summary>' +
        schritte([
          'Subtraktion als Addition der Gegenzahl schreiben: −7 + 12 + 4',
          'Von links nach rechts: −7 + 12 = 5',
          '5 + 4 = <strong>9</strong>'
        ]) + '</details>' +
        '<details class="beispiel"><summary><span class="term inline">(−3) · (−5) + (−20) : 4</span></summary>' +
        schritte([
          'Punkt vor Strich: (−3) · (−5) = 15 &nbsp;(gleiche Vorzeichen)',
          '(−20) : 4 = −5 &nbsp;(verschiedene Vorzeichen)',
          '15 + (−5) = 15 − 5 = <strong>10</strong>'
        ]) + '</details>' +
        '<details class="beispiel"><summary>Ein Kühlraum hat eine Temperatur von −18 °C. Nach einem Stromausfall steigt die Temperatur um 3 °C pro Stunde. Wie warm ist es nach 4 Stunden?</summary>' +
        schritte([
          'Änderung in 4 Stunden: 4 · 3 °C = 12 °C',
          'Neue Temperatur: −18 + 12 = <strong>−6 °C</strong>'
        ]) + '</details>'
    },
    {
      titel: 'Das Wichtigste in Kürze',
      html:
        '<ul class="kurz">' +
        '<li>Auf der Zahlengerade ist die Zahl weiter rechts die grössere.</li>' +
        '<li>Der Betrag ist der Abstand zur 0. Die Gegenzahl hat denselben Betrag und das andere Vorzeichen.</li>' +
        '<li>Positive Zahl addieren: nach rechts. Negative Zahl addieren: nach links.</li>' +
        '<li>Subtrahieren heisst: die Gegenzahl addieren.</li>' +
        '<li>Multiplizieren und Dividieren: Gleiche Vorzeichen ergeben ein positives Ergebnis, verschiedene Vorzeichen ein negatives.</li>' +
        '<li>Punkt- vor Strichrechnung gilt weiterhin.</li>' +
        '</ul>'
    }
  ];

  /* ------------------------------------------------------------------ */
  /* Stufe 1 – Grundlagen                                                */
  /* ------------------------------------------------------------------ */

  function vergleichen() {
    const a = rnd(-15, 15);
    let b;
    do { b = rnd(-15, 15); } while (b === a || (a >= 0 && b >= 0));
    const rel = a < b ? '<' : '>';
    return {
      typ: 'auswahl',
      frage: 'Welches Zeichen gehört in die Lücke?' + term(z(a) + ' <span class="luecke">☐</span> ' + z(b)),
      optionen: [{ wert: '<', text: '<  (kleiner als)' }, { wert: '>', text: '>  (grösser als)' }],
      antwort: rel,
      hinweis: 'Auf der Zahlengerade liegt die grössere Zahl weiter rechts.',
      loesung:
        '<p>' + z(a) + ' liegt auf der Zahlengerade ' + (a < b ? 'links' : 'rechts') + ' von ' + z(b) + '. Also gilt: <strong>' + z(a) + ' ' + MT.esc(rel) + ' ' + z(b) + '</strong></p>' +
        zg({ min: -15, max: 15, beschriftung: 5, punkte: [{ x: a, text: z(a) }, { x: b, text: z(b), art: 'b' }] })
    };
  }

  function ablesen() {
    let x;
    do { x = rndNZ(-10, 10); } while (x % 5 === 0);
    return {
      typ: 'zahl',
      frage: 'Welche Zahl ist auf der Zahlengerade markiert?',
      bild: zg({ min: -10, max: 10, beschriftung: 5, punkte: [{ x: x }] }),
      antwort: x,
      hinweis: 'Zählen Sie die Striche von der nächsten beschrifteten Zahl aus. Links von 0 liegen die negativen Zahlen.',
      loesung: '<p>Der Punkt liegt ' + Math.abs(x) + ' Striche ' + (x < 0 ? 'links' : 'rechts') + ' von 0. Die markierte Zahl ist <strong>' + z(x) + '</strong>.</p>' +
        zg({ min: -10, max: 10, beschriftung: 5, punkte: [{ x: x, text: z(x) }] })
    };
  }

  function addSub() {
    const op = pick(['+', '−']);
    let a, b;
    do { a = rndNZ(-15, 15); b = rndNZ(-15, 15); } while (a > 0 && b > 0);
    const d = op === '+' ? b : -b, erg = a + d;
    let hinweis;
    if (op === '+') hinweis = b < 0 ? 'Eine negative Zahl addieren heisst: auf der Zahlengerade nach links gehen.' : 'Eine positive Zahl addieren heisst: auf der Zahlengerade nach rechts gehen.';
    else hinweis = b < 0 ? 'Eine negative Zahl subtrahieren heisst: ihre Gegenzahl addieren. Aus − (−' + Math.abs(b) + ') wird + ' + Math.abs(b) + '.' : 'Eine positive Zahl subtrahieren heisst: auf der Zahlengerade nach links gehen.';
    const st = [];
    if (op === '−') st.push('Subtraktion als Addition der Gegenzahl schreiben: ' + z(a) + ' + ' + k(d));
    st.push('Start bei ' + z(a) + ', dann ' + Math.abs(d) + ' Schritte nach ' + (d < 0 ? 'links' : 'rechts') + '.');
    st.push('Ergebnis: <strong>' + z(erg) + '</strong>');
    return {
      typ: 'zahl',
      frage: 'Berechnen Sie.' + term(z(a) + ' ' + op + ' ' + k(b)),
      antwort: erg,
      hinweis: hinweis,
      loesung: schritte(st) + zg({ min: -30, max: 30, beschriftung: 10, punkte: [{ x: a, text: z(a) }, { x: erg, text: z(erg), art: 'b' }], pfeile: [{ von: a, bis: erg }] })
    };
  }

  function betragGegenzahl() {
    const v = pick(['gegen', 'betrag', 'kleiner', 'groesser']);
    if (v === 'gegen') {
      const x = rndNZ(-20, 20);
      return {
        typ: 'zahl',
        frage: 'Wie lautet die Gegenzahl von ' + z(x) + '?',
        antwort: -x,
        hinweis: 'Die Gegenzahl liegt gleich weit von 0 entfernt, aber auf der anderen Seite.',
        loesung: '<p>Die Gegenzahl hat denselben Betrag und das andere Vorzeichen: <strong>' + z(-x) + '</strong>.</p>'
      };
    }
    if (v === 'betrag') {
      const x = rnd(-25, -1);
      return {
        typ: 'zahl',
        frage: 'Berechnen Sie den Betrag.' + term('|' + z(x) + '|'),
        antwort: -x,
        hinweis: 'Der Betrag ist der Abstand zur 0. Ein Abstand ist nie negativ.',
        loesung: '<p>' + z(x) + ' ist ' + (-x) + ' Einheiten von 0 entfernt. Also gilt |' + z(x) + '| = <strong>' + (-x) + '</strong>.</p>'
      };
    }
    if (v === 'kleiner') {
      const x = rnd(-10, 6), n = rnd(3, 12);
      return {
        typ: 'zahl',
        frage: 'Welche Zahl ist um ' + n + ' kleiner als ' + z(x) + '?',
        antwort: x - n,
        hinweis: '„Kleiner“ bedeutet: auf der Zahlengerade nach links gehen.',
        loesung: schritte([z(x) + ' − ' + n + ' = <strong>' + z(x - n) + '</strong>']) +
          zg({ min: -25, max: 10, beschriftung: 5, punkte: [{ x: x, text: z(x) }, { x: x - n, text: z(x - n), art: 'b' }], pfeile: [{ von: x, bis: x - n }] })
      };
    }
    const x = rnd(-20, -3), n = rnd(2, 15);
    return {
      typ: 'zahl',
      frage: 'Welche Zahl ist um ' + n + ' grösser als ' + z(x) + '?',
      antwort: x + n,
      hinweis: '„Grösser“ bedeutet: auf der Zahlengerade nach rechts gehen.',
      loesung: schritte([z(x) + ' + ' + n + ' = <strong>' + z(x + n) + '</strong>']) +
        zg({ min: -20, max: 15, beschriftung: 5, punkte: [{ x: x, text: z(x) }, { x: x + n, text: z(x + n), art: 'b' }], pfeile: [{ von: x, bis: x + n }] })
    };
  }

  /* ------------------------------------------------------------------ */
  /* Stufe 2 – Anwenden                                                  */
  /* ------------------------------------------------------------------ */

  function multDiv() {
    const op = pick(['·', ':']);
    let a = rndNZ(-12, 12), b = rndNZ(-12, 12);
    if (a > 0 && b > 0) { if (Math.random() < 0.5) a = -a; else b = -b; }
    if (op === '·') {
      const erg = a * b;
      return {
        typ: 'zahl',
        frage: 'Berechnen Sie.' + term(z(a) + ' · ' + k(b)),
        antwort: erg,
        hinweis: 'Gleiche Vorzeichen ergeben ein positives Ergebnis, verschiedene Vorzeichen ein negatives.',
        loesung: schritte([
          'Vorzeichen: ' + vorzeichenText(a, b),
          'Beträge multiplizieren: ' + Math.abs(a) + ' · ' + Math.abs(b) + ' = ' + Math.abs(erg),
          'Ergebnis: <strong>' + z(erg) + '</strong>'
        ])
      };
    }
    const p = a * b;
    return {
      typ: 'zahl',
      frage: 'Berechnen Sie.' + term(z(p) + ' : ' + k(b)),
      antwort: a,
      hinweis: 'Gleiche Vorzeichen ergeben ein positives Ergebnis, verschiedene Vorzeichen ein negatives.',
      loesung: schritte([
        'Vorzeichen: ' + vorzeichenText(p, b),
        'Beträge dividieren: ' + Math.abs(p) + ' : ' + Math.abs(b) + ' = ' + Math.abs(a),
        'Ergebnis: <strong>' + z(a) + '</strong>'
      ])
    };
  }

  function dreiGlieder() {
    let a, b, c, o1, o2;
    do {
      a = rndNZ(-20, 20); b = rndNZ(-15, 15); c = rndNZ(-15, 15);
      o1 = pick(['+', '−']); o2 = pick(['+', '−']);
    } while ([a, b, c].filter(function (x) { return x < 0; }).length < 2);
    const b2 = o1 === '+' ? b : -b, c2 = o2 === '+' ? c : -c;
    const r1 = a + b2, erg = r1 + c2;
    const st = [];
    if (o1 === '−' || o2 === '−') st.push('Subtraktionen als Addition der Gegenzahl schreiben: ' + z(a) + ' + ' + k(b2) + ' + ' + k(c2));
    st.push('Von links nach rechts: ' + z(a) + ' + ' + k(b2) + ' = ' + z(r1));
    st.push(z(r1) + ' + ' + k(c2) + ' = <strong>' + z(erg) + '</strong>');
    return {
      typ: 'zahl',
      frage: 'Berechnen Sie.' + term(z(a) + ' ' + o1 + ' ' + k(b) + ' ' + o2 + ' ' + k(c)),
      antwort: erg,
      hinweis: 'Schreiben Sie jede Subtraktion als Addition der Gegenzahl. Rechnen Sie dann von links nach rechts.',
      loesung: schritte(st)
    };
  }

  function punktVorStrich() {
    const op = pick(['+', '−']);
    const a = rndNZ(-20, 20);
    let b, c;
    do { b = rndNZ(-9, 9); c = rndNZ(-9, 9); } while ((b > 0 && c > 0) || Math.abs(b) === 1 || Math.abs(c) === 1);
    if (Math.random() < 0.5) {
      const prod = b * c, erg = op === '+' ? a + prod : a - prod;
      return {
        typ: 'zahl',
        frage: 'Berechnen Sie.' + term(z(a) + ' ' + op + ' ' + k(b) + ' · ' + k(c)),
        antwort: erg,
        hinweis: 'Punkt- vor Strichrechnung: Berechnen Sie zuerst das Produkt.',
        loesung: schritte([
          'Zuerst multiplizieren: ' + k(b) + ' · ' + k(c) + ' = ' + z(prod),
          'Dann: ' + z(a) + ' ' + op + ' ' + k(prod) + ' = <strong>' + z(erg) + '</strong>'
        ])
      };
    }
    const p = b * c, erg = op === '+' ? a + b : a - b;
    return {
      typ: 'zahl',
      frage: 'Berechnen Sie.' + term(z(a) + ' ' + op + ' ' + k(p) + ' : ' + k(c)),
      antwort: erg,
      hinweis: 'Punkt- vor Strichrechnung: Berechnen Sie zuerst den Quotienten.',
      loesung: schritte([
        'Zuerst dividieren: ' + k(p) + ' : ' + k(c) + ' = ' + z(b),
        'Dann: ' + z(a) + ' ' + op + ' ' + k(b) + ' = <strong>' + z(erg) + '</strong>'
      ])
    };
  }

  function ordnen() {
    let zahlen;
    do {
      zahlen = [];
      while (zahlen.length < 4) {
        const x = rnd(-30, 30);
        if (zahlen.indexOf(x) === -1) zahlen.push(x);
      }
    } while (zahlen.filter(function (x) { return x < 0; }).length < 2);
    const kleinste = pick([true, false]);
    const sortiert = zahlen.slice().sort(function (a, b) { return a - b; });
    const ziel = kleinste ? sortiert[0] : sortiert[3];
    return {
      typ: 'auswahl',
      frage: 'Welche Zahl ist am ' + (kleinste ? 'kleinsten' : 'grössten') + '?',
      optionen: shuffle(zahlen).map(function (x) { return { wert: String(x), text: z(x) }; }),
      antwort: String(ziel),
      hinweis: kleinste ? 'Die kleinste Zahl liegt auf der Zahlengerade ganz links.' : 'Die grösste Zahl liegt auf der Zahlengerade ganz rechts.',
      loesung: '<p>Geordnet: ' + sortiert.map(z).join(' &lt; ') + '</p><p>Die ' + (kleinste ? 'kleinste' : 'grösste') + ' Zahl ist <strong>' + z(ziel) + '</strong>.</p>'
    };
  }

  function abstand() {
    let a, b;
    do { a = rnd(-25, 15); b = rnd(-25, 15); } while (a === b || (a >= 0 && b >= 0));
    const lo = Math.min(a, b), hi = Math.max(a, b);
    return {
      typ: 'zahl',
      frage: 'Wie gross ist der Abstand zwischen ' + z(a) + ' und ' + z(b) + ' auf der Zahlengerade?',
      antwort: hi - lo,
      hinweis: 'Rechnen Sie: grössere Zahl minus kleinere Zahl.',
      loesung: schritte([z(hi) + ' − ' + k(lo) + ' = ' + z(hi) + ' + ' + k(-lo) + ' = <strong>' + (hi - lo) + '</strong>']) +
        zg({ min: -25, max: 15, beschriftung: 5, punkte: [{ x: lo, text: z(lo) }, { x: hi, text: z(hi), art: 'b' }], pfeile: [{ von: lo, bis: hi }] })
    };
  }

  /* ------------------------------------------------------------------ */
  /* Stufe 3 – Vertiefen                                                 */
  /* ------------------------------------------------------------------ */

  function temperatur() {
    let t0, r, h;
    do { t0 = rnd(2, 9); r = rnd(2, 4); h = rnd(3, 6); } while (t0 - r * h >= 0);
    const t1 = t0 - r * h;
    if (Math.random() < 0.5) {
      return {
        typ: 'zahl', einheit: '°C',
        frage: '<p>Um 18 Uhr zeigt das Thermometer ' + t0 + ' °C. Danach sinkt die Temperatur gleichmässig und erreicht nach ' + h + ' Stunden ' + z(t1) + ' °C.</p><p>Um wie viele Grad sinkt die Temperatur pro Stunde?</p>',
        antwort: r,
        hinweis: 'Berechnen Sie zuerst die gesamte Veränderung. Teilen Sie diese dann durch die Anzahl Stunden.',
        loesung: schritte([
          'Gesamte Veränderung: ' + z(t1) + ' − ' + t0 + ' = ' + z(t1 - t0) + ' °C',
          'Pro Stunde: ' + k(t1 - t0) + ' : ' + h + ' = ' + z(-r) + ' °C',
          'Die Temperatur sinkt um <strong>' + r + ' °C</strong> pro Stunde.'
        ])
      };
    }
    return {
      typ: 'zahl', einheit: '°C',
      frage: '<p>Um 18 Uhr zeigt das Thermometer ' + t0 + ' °C. Die Temperatur sinkt pro Stunde gleichmässig um ' + r + ' °C.</p><p>Welche Temperatur zeigt das Thermometer nach ' + h + ' Stunden?</p>',
      antwort: t1,
      hinweis: 'Berechnen Sie zuerst, um wie viel die Temperatur insgesamt sinkt.',
      loesung: schritte([
        'Gesamte Abnahme: ' + h + ' · ' + r + ' °C = ' + (h * r) + ' °C',
        'Neue Temperatur: ' + t0 + ' − ' + (h * r) + ' = <strong>' + z(t1) + ' °C</strong>'
      ])
    };
  }

  function konto() {
    const start = -rnd(5, 30) * 10, ein = rnd(15, 40) * 10, n = rnd(2, 4), betr = rnd(4, 9) * 10;
    const r1 = start + ein, end = r1 - n * betr;
    return {
      typ: 'zahl', einheit: 'Fr.',
      frage: '<p>Ein Konto weist einen Stand von Fr. ' + z(start) + ' auf. Es werden Fr. ' + ein + ' eingezahlt. Danach werden ' + n + ' Rechnungen zu je Fr. ' + betr + ' abgebucht.</p><p>Wie hoch ist der Kontostand danach?</p>',
      antwort: end,
      hinweis: 'Einzahlungen werden addiert, Abbuchungen subtrahiert. Berechnen Sie zuerst den Gesamtbetrag der Rechnungen.',
      loesung: schritte([
        'Nach der Einzahlung: ' + z(start) + ' + ' + ein + ' = ' + z(r1),
        'Rechnungen: ' + n + ' · ' + betr + ' = ' + (n * betr),
        'Neuer Stand: ' + z(r1) + ' − ' + (n * betr) + ' = <strong>Fr. ' + z(end) + '</strong>'
      ])
    };
  }

  function hoehe() {
    if (Math.random() < 0.5) {
      const d = rnd(8, 40) * 10, h = rnd(10, 60) * 10;
      return {
        typ: 'zahl', einheit: 'm',
        frage: '<p>Ein U-Boot befindet sich ' + d + ' m unter dem Meeresspiegel. Ein Helikopter fliegt genau darüber in ' + h + ' m Höhe.</p><p>Wie gross ist der Höhenunterschied zwischen den beiden?</p>',
        antwort: h + d,
        hinweis: 'Das U-Boot befindet sich auf −' + d + ' m. Rechnen Sie: obere Höhe minus untere Höhe.',
        loesung: schritte([
          'Positionen: Helikopter ' + h + ' m, U-Boot ' + z(-d) + ' m',
          h + ' − ' + k(-d) + ' = ' + h + ' + ' + d + ' = <strong>' + (h + d) + ' m</strong>'
        ])
      };
    }
    let a, b, c;
    do { a = rnd(5, 25); b = rnd(3, 15); c = rnd(5, 25); } while (c >= a + b);
    const erg = -a - b + c;
    return {
      typ: 'zahl', einheit: 'm',
      frage: '<p>Eine Taucherin befindet sich auf ' + z(-a) + ' m. Sie taucht zuerst ' + b + ' m tiefer und steigt dann ' + c + ' m auf.</p><p>Auf welcher Höhe (bezogen auf den Meeresspiegel) befindet sie sich danach?</p>',
      antwort: erg,
      hinweis: 'Tiefer tauchen bedeutet subtrahieren, aufsteigen bedeutet addieren.',
      loesung: schritte([
        z(-a) + ' − ' + b + ' = ' + z(-a - b),
        z(-a - b) + ' + ' + c + ' = <strong>' + z(erg) + ' m</strong>'
      ])
    };
  }

  function umkehr() {
    const f = pick(['plus', 'minus', 'mal', 'durch']);
    const box = '<span class="luecke">☐</span>';
    const x = rndNZ(-12, 12);
    let b, c, anzeige, st;
    if (f === 'plus') {
      do { b = rndNZ(-15, 15); } while (x > 0 && b > 0);
      c = x + b;
      anzeige = box + ' + ' + k(b) + ' = ' + z(c);
      st = ['☐ = ' + z(c) + ' − ' + k(b) + ' = <strong>' + z(x) + '</strong>', 'Probe: ' + z(x) + ' + ' + k(b) + ' = ' + z(c) + ' ✓'];
    } else if (f === 'minus') {
      do { b = rndNZ(-15, 15); } while (x > 0 && b > 0);
      c = x - b;
      anzeige = box + ' − ' + k(b) + ' = ' + z(c);
      st = ['☐ = ' + z(c) + ' + ' + k(b) + ' = <strong>' + z(x) + '</strong>', 'Probe: ' + z(x) + ' − ' + k(b) + ' = ' + z(c) + ' ✓'];
    } else if (f === 'mal') {
      do { b = rndNZ(-9, 9); } while (Math.abs(b) === 1 || (x > 0 && b > 0));
      c = b * x;
      anzeige = z(b) + ' · ' + box + ' = ' + z(c);
      st = ['☐ = ' + z(c) + ' : ' + k(b) + ' = <strong>' + z(x) + '</strong>', 'Probe: ' + z(b) + ' · ' + k(x) + ' = ' + z(c) + ' ✓'];
    } else {
      // Hier ist das Ergebnis c vorgegeben und ☐ = c · b.
      do { b = rndNZ(-9, 9); c = rndNZ(-10, 10); } while (Math.abs(b) === 1 || (b > 0 && c > 0));
      const y = c * b;
      return {
        typ: 'zahl',
        frage: 'Welche Zahl gehört in das Kästchen?' + term(box + ' : ' + k(b) + ' = ' + z(c)),
        antwort: y,
        hinweis: 'Die Umkehrung der Division ist die Multiplikation.',
        loesung: schritte(['☐ = ' + z(c) + ' · ' + k(b) + ' = <strong>' + z(y) + '</strong>', 'Probe: ' + z(y) + ' : ' + k(b) + ' = ' + z(c) + ' ✓'])
      };
    }
    return {
      typ: 'zahl',
      frage: 'Welche Zahl gehört in das Kästchen?' + term(anzeige),
      antwort: x,
      hinweis: 'Machen Sie die Rechnung rückgängig: Addition ↔ Subtraktion, Multiplikation ↔ Division.',
      loesung: schritte(st)
    };
  }

  const AUSSAGEN = [
    { t: 'Das Produkt zweier negativer Zahlen ist positiv.', w: true, e: 'Gleiche Vorzeichen ergeben ein positives Ergebnis, z. B. (−3) · (−5) = 15.' },
    { t: 'Die Summe zweier negativer Zahlen ist immer negativ.', w: true, e: 'Von einer negativen Zahl aus geht man noch weiter nach links, z. B. (−4) + (−6) = −10.' },
    { t: 'Die Differenz zweier negativer Zahlen ist immer negativ.', w: false, e: 'Gegenbeispiel: (−2) − (−5) = −2 + 5 = 3.' },
    { t: 'Das Produkt von drei negativen Zahlen ist negativ.', w: true, e: '(−2) · (−3) = 6 und 6 · (−4) = −24. Bei einer ungeraden Anzahl negativer Faktoren ist das Produkt negativ.' },
    { t: 'Der Betrag einer Zahl ist nie negativ.', w: true, e: 'Der Betrag ist ein Abstand zur 0, und ein Abstand ist nie negativ.' },
    { t: 'Eine Zahl und ihre Gegenzahl ergeben zusammen immer 0.', w: true, e: 'Zum Beispiel (−7) + 7 = 0.' },
    { t: 'Wenn man eine negative Zahl subtrahiert, wird das Ergebnis kleiner als die Ausgangszahl.', w: false, e: 'Das Ergebnis wird grösser: 4 − (−3) = 4 + 3 = 7.' },
    { t: '−10 ist grösser als −3, weil 10 grösser als 3 ist.', w: false, e: '−10 liegt auf der Zahlengerade links von −3. Also gilt −10 < −3.' },
    { t: 'Das Quadrat einer negativen Zahl ist positiv.', w: true, e: '(−4)² = (−4) · (−4) = 16.' },
    { t: 'Der Quotient aus einer positiven und einer negativen Zahl ist negativ.', w: true, e: 'Verschiedene Vorzeichen ergeben ein negatives Ergebnis, z. B. 18 : (−6) = −3.' },
    { t: 'Jede negative Zahl ist kleiner als jede positive Zahl.', w: true, e: 'Negative Zahlen liegen links von 0, positive rechts davon.' },
    { t: 'Die Gegenzahl einer Zahl ist immer negativ.', w: false, e: 'Die Gegenzahl von −6 ist 6, also positiv.' }
  ];

  function aussage() {
    const a = pick(AUSSAGEN);
    return {
      typ: 'auswahl',
      frage: 'Ist die folgende Aussage wahr oder falsch?<blockquote>' + MT.esc(a.t) + '</blockquote>',
      optionen: [{ wert: 'w', text: 'wahr' }, { wert: 'f', text: 'falsch' }],
      antwort: a.w ? 'w' : 'f',
      hinweis: 'Überprüfen Sie die Aussage an einem konkreten Zahlenbeispiel.',
      loesung: '<p>Die Aussage ist <strong>' + (a.w ? 'wahr' : 'falsch') + '</strong>. ' + MT.esc(a.e) + '</p>'
    };
  }

  /* ------------------------------------------------------------------ */

  MT.themen.push({
    id: 'ganze-zahlen',
    titel: 'Ganze Zahlen',
    lehrplan: 'MA.1 Zahl und Variable',
    kurz: 'Negative Zahlen verstehen, ordnen und mit ihnen rechnen: von der Zahlengerade bis zu Textaufgaben.',
    verfuegbar: true,
    einfuehrung: einfuehrung,
    stufen: {
      1: {
        titel: 'Grundlagen',
        beschreibung: 'Zahlen vergleichen und ablesen, Betrag und Gegenzahl, einfache Additionen und Subtraktionen.',
        generatoren: [vergleichen, ablesen, addSub, addSub, betragGegenzahl]
      },
      2: {
        titel: 'Anwenden',
        beschreibung: 'Multiplizieren und dividieren, Rechnungen mit mehreren Schritten, Punkt vor Strich, Zahlen ordnen.',
        generatoren: [multDiv, multDiv, dreiGlieder, punktVorStrich, ordnen, abstand]
      },
      3: {
        titel: 'Vertiefen',
        beschreibung: 'Textaufgaben aus dem Alltag, fehlende Zahlen bestimmen und Aussagen beurteilen.',
        generatoren: [temperatur, konto, hoehe, umkehr, umkehr, aussage]
      }
    }
  });
})(window.MT);
