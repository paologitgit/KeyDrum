/* Navigation (über den Hash in der Adresse), Ansichten und Ablauf der Übungen. */
(function (MT) {
  'use strict';

  const app = document.getElementById('app');
  const esc = MT.esc, z = MT.z;

  function thema(id) {
    return MT.themen.find(function (t) { return t.id === id; });
  }

  function pfad(teile) {
    return '<nav class="pfad" aria-label="Navigation">' + teile.join(' <span aria-hidden="true">›</span> ') + '</nav>';
  }

  /* ---------------------------------------------------------------- */
  /* Routing                                                           */
  /* ---------------------------------------------------------------- */

  function route() {
    const h = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean);
    window.scrollTo(0, 0);
    const t = h[0] === 'thema' ? thema(h[1]) : null;
    if (t && t.verfuegbar) {
      if (h[2] === 'einfuehrung') return zeigeEinfuehrung(t);
      if (h[2] === 'stufe' && ['1', '2', '3'].indexOf(h[3]) !== -1) {
        const n = Number(h[3]);
        if (MT.speicher.stufeOffen(t.id, n)) return zeigeUebung(t, n);
      }
      return zeigeThema(t);
    }
    zeigeStart();
  }

  /* ---------------------------------------------------------------- */
  /* Startseite                                                        */
  /* ---------------------------------------------------------------- */

  function fortschrittsLeiste(t) {
    const teile = ['<span class="pille' + (MT.speicher.einfuehrungGelesen(t.id) ? ' fertig' : '') + '">Einführung</span>'];
    [1, 2, 3].forEach(function (n) {
      const s = MT.speicher.stufe(t.id, n);
      const kl = s.abgeschlossen ? ' fertig' : (s.versuche > 0 ? ' begonnen' : '');
      teile.push('<span class="pille' + kl + '">Stufe ' + n + '</span>');
    });
    return '<div class="pillen" aria-label="Fortschritt">' + teile.join('') + '</div>';
  }

  function zeigeStart() {
    let html =
      '<h1>Mathematik 1. Sek</h1>' +
      '<p class="lead">Übungen zu drei Themen der 1. Sekundarstufe nach Lehrplan 21. Jedes Thema beginnt mit einer Einführung. Danach üben Sie in drei Stufen: Grundlagen, Anwenden, Vertiefen.</p>';

    if (!MT.speicher.verfuegbar()) {
      html += '<div class="rm hinweis">Ihr Browser erlaubt derzeit keine Speicherung (z. B. im privaten Modus). Sie können üben, der Fortschritt geht beim Schliessen aber verloren.</div>';
    }

    html += '<div class="themen">';
    MT.themen.forEach(function (t) {
      if (t.verfuegbar) {
        html +=
          '<a class="karte thema-karte" href="#/thema/' + t.id + '">' +
          '<span class="etikett">' + esc(t.lehrplan) + '</span>' +
          '<h2>' + esc(t.titel) + '</h2><p>' + esc(t.kurz) + '</p>' + fortschrittsLeiste(t) + '</a>';
      } else {
        html +=
          '<div class="karte thema-karte gesperrt" aria-disabled="true">' +
          '<span class="etikett">' + esc(t.lehrplan) + '</span>' +
          '<h2>' + esc(t.titel) + '</h2><p>' + esc(t.kurz) + '</p><p class="status">In Vorbereitung</p></div>';
      }
    });
    html += '</div>';

    html +=
      '<section class="karte sicherung">' +
      '<h2>Ihr Fortschritt</h2>' +
      '<p>Der Fortschritt wird automatisch in diesem Browser gespeichert. Auf einem anderen Gerät oder in einem anderen Browser ist er nicht verfügbar. ' +
      'Mit einer Sicherungsdatei können Sie ihn übertragen.</p>' +
      '<div class="knopf-reihe">' +
      '<button type="button" class="knopf" id="export">Fortschritt exportieren</button>' +
      '<label class="knopf">Fortschritt importieren<input type="file" id="import" accept=".json,application/json" hidden></label>' +
      '<button type="button" class="knopf leise" id="reset">Zurücksetzen</button>' +
      '</div><div id="sicherung-meldung" aria-live="polite"></div></section>';

    app.innerHTML = html;

    const meldung = document.getElementById('sicherung-meldung');
    document.getElementById('export').addEventListener('click', function () {
      MT.speicher.exportieren();
    });
    document.getElementById('import').addEventListener('change', function (e) {
      const datei = e.target.files && e.target.files[0];
      if (!datei) return;
      const leser = new FileReader();
      leser.onload = function () {
        try {
          MT.speicher.importieren(String(leser.result));
          zeigeStart();
          document.getElementById('sicherung-meldung').innerHTML = '<div class="rm gut">Der Fortschritt wurde importiert.</div>';
        } catch (err) {
          meldung.innerHTML = '<div class="rm fehler">Die Datei konnte nicht gelesen werden. Bitte wählen Sie eine Sicherungsdatei, die mit diesem Tool exportiert wurde.</div>';
        }
      };
      leser.readAsText(datei);
    });
    document.getElementById('reset').addEventListener('click', function () {
      if (window.confirm('Möchten Sie den gesamten Fortschritt in diesem Browser löschen? Dies lässt sich nicht rückgängig machen.')) {
        MT.speicher.zuruecksetzen();
        zeigeStart();
      }
    });
  }

  /* ---------------------------------------------------------------- */
  /* Themenseite                                                       */
  /* ---------------------------------------------------------------- */

  function zeigeThema(t) {
    const gelesen = MT.speicher.einfuehrungGelesen(t.id);
    let html =
      pfad(['<a href="#/">Übersicht</a>', esc(t.titel)]) +
      '<span class="etikett">' + esc(t.lehrplan) + '</span>' +
      '<h1>' + esc(t.titel) + '</h1><p class="lead">' + esc(t.kurz) + '</p>' +
      '<div class="stufen">' +
      '<div class="karte stufe-karte">' +
      '<div><h2>Einführung</h2><p>Erklärungen, interaktive Darstellungen und durchgerechnete Beispiele.</p>' +
      '<p class="status' + (gelesen ? ' fertig' : '') + '">' + (gelesen ? 'Gelesen' : 'Noch nicht gelesen') + '</p></div>' +
      '<a class="knopf' + (gelesen ? '' : ' primaer') + '" href="#/thema/' + t.id + '/einfuehrung">Einführung öffnen</a></div>';

    [1, 2, 3].forEach(function (n) {
      const cfg = t.stufen[n], s = MT.speicher.stufe(t.id, n), offen = MT.speicher.stufeOffen(t.id, n);
      let status;
      if (s.abgeschlossen) status = '<p class="status fertig">Abgeschlossen · ' + s.versuche + ' Aufgaben bearbeitet</p>';
      else if (!offen) status = '<p class="status">Wird freigeschaltet, sobald Stufe ' + (n - 1) + ' abgeschlossen ist.</p>';
      else if (s.versuche > 0) status = '<p class="status begonnen">In Arbeit · ' + s.versuche + ' Aufgaben bearbeitet</p>';
      else status = '<p class="status">Bereit</p>';

      html +=
        '<div class="karte stufe-karte' + (offen ? '' : ' gesperrt') + '">' +
        '<div><h2>Stufe ' + n + ': ' + esc(cfg.titel) + '</h2><p>' + esc(cfg.beschreibung) + '</p>' + status + '</div>' +
        (offen
          ? '<a class="knopf primaer" href="#/thema/' + t.id + '/stufe/' + n + '">' + (s.versuche ? 'Weiter üben' : 'Üben') + '</a>'
          : '<button type="button" class="knopf leise" data-freischalten="' + n + '">Trotzdem öffnen</button>') +
        '</div>';
    });

    html += '</div><p class="klein">Eine Stufe gilt als abgeschlossen, wenn Sie von den letzten ' + MT.ZIEL.anzahl + ' Aufgaben mindestens ' + MT.ZIEL.richtig + ' im ersten Versuch richtig gelöst haben.</p>';
    app.innerHTML = html;

    app.querySelectorAll('[data-freischalten]').forEach(function (b) {
      b.addEventListener('click', function () {
        const n = Number(b.getAttribute('data-freischalten'));
        if (window.confirm('Stufe ' + n + ' ist noch gesperrt. Möchten Sie sie trotzdem öffnen?')) {
          MT.speicher.freischalten(t.id, n);
          location.hash = '#/thema/' + t.id + '/stufe/' + n;
        }
      });
    });
  }

  /* ---------------------------------------------------------------- */
  /* Einführung                                                        */
  /* ---------------------------------------------------------------- */

  function zeigeEinfuehrung(t) {
    const abschnitte = t.einfuehrung;
    let html =
      pfad(['<a href="#/">Übersicht</a>', '<a href="#/thema/' + t.id + '">' + esc(t.titel) + '</a>', 'Einführung']) +
      '<h1>' + esc(t.titel) + ': Einführung</h1>' +
      '<nav class="karte inhalt" aria-label="Inhalt"><h2>Inhalt</h2><ol>' +
      abschnitte.map(function (a, i) { return '<li><button type="button" class="link" data-ziel="' + i + '">' + esc(a.titel) + '</button></li>'; }).join('') +
      '</ol></nav>';

    abschnitte.forEach(function (a, i) {
      html += '<section class="karte abschnitt" id="abschnitt-' + i + '"><h2>' + (i + 1) + '. ' + esc(a.titel) + '</h2>' + a.html +
        (a.widget ? '<div class="widget" data-widget="' + i + '"></div>' : '') + '</section>';
    });

    html += '<div class="ende"><button type="button" class="knopf primaer" id="fertig">Einführung abschliessen und mit Stufe 1 beginnen</button></div>';
    app.innerHTML = html;

    abschnitte.forEach(function (a, i) {
      if (a.widget) a.widget(app.querySelector('[data-widget="' + i + '"]'));
    });
    app.querySelectorAll('[data-ziel]').forEach(function (b) {
      b.addEventListener('click', function () {
        document.getElementById('abschnitt-' + b.getAttribute('data-ziel')).scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    document.getElementById('fertig').addEventListener('click', function () {
      MT.speicher.markiereEinfuehrung(t.id);
      location.hash = '#/thema/' + t.id + '/stufe/1';
    });
  }

  /* ---------------------------------------------------------------- */
  /* Übung                                                             */
  /* ---------------------------------------------------------------- */

  /** Liest eine ganze Zahl; akzeptiert auch −, –, Leerzeichen und Klammern. Gibt null bei ungültiger Eingabe. */
  function leseZahl(s) {
    s = String(s).trim().replace(/[−–—]/g, '-').replace(/\s+/g, '').replace(/^\((.*)\)$/, '$1').replace(/^\+/, '');
    if (!/^-?\d{1,7}$/.test(s)) return null;
    const n = parseInt(s, 10);
    return n === 0 ? 0 : n; // −0 vermeiden
  }

  function zeigeUebung(t, n) {
    const cfg = t.stufen[n];
    app.innerHTML =
      pfad(['<a href="#/">Übersicht</a>', '<a href="#/thema/' + t.id + '">' + esc(t.titel) + '</a>', 'Stufe ' + n]) +
      '<h1>Stufe ' + n + ': ' + esc(cfg.titel) + '</h1>' +
      '<p class="lead">' + esc(cfg.beschreibung) + '</p>' +
      '<div class="stand" id="stand"></div>' +
      '<div id="meldung" aria-live="polite"></div>' +
      '<section class="karte aufgabe" id="aufgabe"></section>';

    const standEl = document.getElementById('stand');
    const meldungEl = document.getElementById('meldung');
    const box = document.getElementById('aufgabe');
    let letzter = -1;

    function zeichneStand() {
      const s = MT.speicher.stufe(t.id, n);
      const summe = s.letzte.reduce(function (a, b) { return a + b; }, 0);
      let punkte = '';
      for (let i = 0; i < MT.ZIEL.anzahl; i++) {
        const v = s.letzte[i];
        punkte += '<span class="punkt' + (v === 1 ? ' gut' : v === 0 ? ' falsch' : '') + '"></span>';
      }
      standEl.innerHTML =
        '<div class="punkte" role="img" aria-label="' + summe + ' von ' + s.letzte.length + ' der letzten Aufgaben richtig">' + punkte + '</div>' +
        '<div class="stand-text">' +
        (s.abgeschlossen
          ? '<strong>Stufe abgeschlossen.</strong> Sie können hier weiter üben.'
          : 'Letzte ' + MT.ZIEL.anzahl + ' Aufgaben: ' + summe + ' im ersten Versuch richtig. Ziel: ' + MT.ZIEL.richtig + '.') +
        '</div>';
    }

    function neueAufgabe() {
      const g = cfg.generatoren;
      let i;
      do { i = Math.floor(Math.random() * g.length); } while (g.length > 1 && g[i] === g[letzter]);
      letzter = i;
      zeigeAufgabe(g[i]());
    }

    function zeigeAufgabe(a) {
      const maxVersuche = a.typ === 'auswahl' && a.optionen.length <= 2 ? 1 : 2;
      let versuch = 1, fertig = false;

      let eingabe;
      if (a.typ === 'zahl') {
        eingabe =
          '<form class="eingabe-zeile" novalidate autocomplete="off">' +
          '<button type="button" class="knopf vorzeichen" title="Vorzeichen wechseln" aria-label="Vorzeichen wechseln">±</button>' +
          '<input type="text" inputmode="numeric" class="zahl-eingabe" aria-label="Ihre Antwort" spellcheck="false">' +
          (a.einheit ? '<span class="einheit">' + esc(a.einheit) + '</span>' : '') +
          '<button type="submit" class="knopf primaer">Prüfen</button></form>';
      } else {
        eingabe = '<div class="optionen">' + a.optionen.map(function (o) {
          return '<button type="button" class="option" data-wert="' + esc(o.wert) + '">' + esc(o.text) + '</button>';
        }).join('') + '</div>';
      }

      box.innerHTML =
        '<div class="frage">' + a.frage + '</div>' +
        (a.bild ? '<div class="bild">' + a.bild + '</div>' : '') +
        eingabe +
        '<div class="rueckmeldung" aria-live="polite"></div>' +
        '<div class="weiter-zeile" hidden><button type="button" class="knopf primaer weiter">Nächste Aufgabe</button></div>';

      const rm = box.querySelector('.rueckmeldung');
      const weiter = box.querySelector('.weiter');
      const feld = box.querySelector('.zahl-eingabe');

      function antwortText() {
        if (a.typ === 'zahl') return z(a.antwort) + (a.einheit ? ' ' + esc(a.einheit) : '');
        const o = a.optionen.find(function (o) { return o.wert === a.antwort; });
        return esc(o ? o.text : a.antwort);
      }

      function abschliessen(richtigImErsten) {
        fertig = true;
        const neu = MT.speicher.erfassen(t.id, n, richtigImErsten);
        box.querySelectorAll('input, form button, .option').forEach(function (e) {
          e.disabled = true;
          if (e.getAttribute('data-wert') === a.antwort) e.classList.add('gut');
        });
        box.querySelector('.weiter-zeile').hidden = false;
        weiter.focus({ preventScroll: true });
        zeichneStand();
        if (neu) {
          meldungEl.innerHTML = n < 3
            ? '<div class="rm gut"><strong>Sie haben Stufe ' + n + ' abgeschlossen.</strong> Stufe ' + (n + 1) + ' ist jetzt freigeschaltet. <a href="#/thema/' + t.id + '/stufe/' + (n + 1) + '">Zu Stufe ' + (n + 1) + '</a></div>'
            : '<div class="rm gut"><strong>Sie haben alle drei Stufen dieses Themas abgeschlossen.</strong> Sie können hier weiter üben oder <a href="#/">zur Übersicht</a> zurückkehren.</div>';
        }
      }

      function pruefe(wert) {
        if (fertig) return;
        const richtig = wert === a.antwort;
        if (richtig) {
          rm.innerHTML =
            '<div class="rm gut"><strong>Richtig.</strong>' + (versuch > 1 ? ' Im zweiten Versuch gelöst.' : '') + '</div>' +
            '<details class="loesung"><summary>Lösungsweg ansehen</summary>' + a.loesung + '</details>';
          abschliessen(versuch === 1);
        } else if (versuch < maxVersuche) {
          versuch++;
          rm.innerHTML = '<div class="rm hinweis"><strong>Noch nicht richtig.</strong> ' + a.hinweis + ' Versuchen Sie es noch einmal.</div>';
          if (feld) { feld.select(); feld.focus(); }
        } else {
          rm.innerHTML =
            '<div class="rm fehler"><strong>Leider nicht richtig.</strong> Die richtige Antwort lautet: <strong>' + antwortText() + '</strong></div>' +
            '<div class="loesung offen"><h3>Lösungsweg</h3>' + a.loesung + '</div>';
          abschliessen(false);
        }
      }

      if (a.typ === 'zahl') {
        box.querySelector('form').addEventListener('submit', function (e) {
          e.preventDefault();
          const w = leseZahl(feld.value);
          if (w === null) {
            rm.innerHTML = '<div class="rm hinweis">Bitte geben Sie eine ganze Zahl ein, zum Beispiel −12.</div>';
            feld.focus();
            return;
          }
          pruefe(w);
        });
        box.querySelector('.vorzeichen').addEventListener('click', function () {
          const v = feld.value.trim();
          feld.value = /^[-−–]/.test(v) ? v.replace(/^[-−–]\s*/, '') : '−' + v;
          feld.focus();
        });
        feld.focus({ preventScroll: true });
      } else {
        box.querySelectorAll('.option').forEach(function (b) {
          b.addEventListener('click', function () {
            const w = b.getAttribute('data-wert');
            if (w === a.antwort) b.classList.add('gut');
            else { b.classList.add('falsch'); b.disabled = true; }
            pruefe(w);
          });
        });
      }

      weiter.addEventListener('click', function () {
        meldungEl.innerHTML = '';
        neueAufgabe();
        box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    }

    zeichneStand();
    neueAufgabe();
  }

  window.addEventListener('hashchange', route);
  route();
})(window.MT);
