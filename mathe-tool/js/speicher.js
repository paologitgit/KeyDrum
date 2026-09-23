/* Lernstand im Browser (localStorage) sowie Export und Import als JSON-Datei. */
(function (MT) {
  'use strict';

  const SCHLUESSEL = 'mathe-tool-fortschritt-v1';
  MT.ZIEL = { anzahl: 10, richtig: 8 }; // 8 der letzten 10 Aufgaben im ersten Versuch richtig

  let daten = null;
  let speicherOk = true;

  function leer() {
    return { version: 1, themen: {} };
  }

  function ganzzahl(v) {
    v = Number(v);
    return Number.isFinite(v) && v >= 0 ? Math.floor(v) : 0;
  }

  /** Übernimmt nur bekannte Felder mit gültigen Werten (wichtig beim Import). */
  function bereinigen(d) {
    const out = leer();
    if (!d || typeof d !== 'object' || !d.themen || typeof d.themen !== 'object') return out;
    Object.keys(d.themen).forEach(function (id) {
      if (!/^[a-z0-9-]{1,40}$/.test(id)) return;
      const t = d.themen[id];
      if (!t || typeof t !== 'object') return;
      const neu = { einfuehrungGelesen: !!t.einfuehrungGelesen, stufen: {} };
      ['1', '2', '3'].forEach(function (n) {
        const s = t.stufen && t.stufen[n];
        if (!s || typeof s !== 'object') return;
        neu.stufen[n] = {
          versuche: ganzzahl(s.versuche),
          richtig: ganzzahl(s.richtig),
          letzte: Array.isArray(s.letzte) ? s.letzte.slice(-MT.ZIEL.anzahl).map(function (v) { return v ? 1 : 0; }) : [],
          abgeschlossen: !!s.abgeschlossen,
          freigeschaltet: !!s.freigeschaltet
        };
      });
      out.themen[id] = neu;
    });
    return out;
  }

  function laden() {
    if (daten) return daten;
    try {
      const roh = window.localStorage.getItem(SCHLUESSEL);
      daten = roh ? bereinigen(JSON.parse(roh)) : leer();
    } catch (e) {
      speicherOk = false;
      daten = leer();
    }
    return daten;
  }

  function sichern() {
    try {
      window.localStorage.setItem(SCHLUESSEL, JSON.stringify(daten));
      speicherOk = true;
    } catch (e) {
      speicherOk = false;
    }
  }

  function thema(id) {
    const d = laden();
    if (!d.themen[id]) d.themen[id] = { einfuehrungGelesen: false, stufen: {} };
    return d.themen[id];
  }

  function stufe(id, n) {
    const t = thema(id);
    if (!t.stufen[n]) t.stufen[n] = { versuche: 0, richtig: 0, letzte: [], abgeschlossen: false, freigeschaltet: false };
    return t.stufen[n];
  }

  MT.speicher = {
    stufe: stufe,

    verfuegbar: function () {
      laden();
      return speicherOk;
    },

    einfuehrungGelesen: function (id) {
      return !!thema(id).einfuehrungGelesen;
    },

    markiereEinfuehrung: function (id) {
      thema(id).einfuehrungGelesen = true;
      sichern();
    },

    stufeOffen: function (id, n) {
      if (n === 1) return true;
      return stufe(id, n - 1).abgeschlossen || stufe(id, n).freigeschaltet;
    },

    freischalten: function (id, n) {
      stufe(id, n).freigeschaltet = true;
      sichern();
    },

    /** Erfasst ein Ergebnis. Gibt true zurück, wenn die Stufe dadurch neu abgeschlossen wurde. */
    erfassen: function (id, n, richtig) {
      const s = stufe(id, n);
      s.versuche++;
      if (richtig) s.richtig++;
      s.letzte.push(richtig ? 1 : 0);
      if (s.letzte.length > MT.ZIEL.anzahl) s.letzte.shift();
      let neu = false;
      const summe = s.letzte.reduce(function (a, b) { return a + b; }, 0);
      if (!s.abgeschlossen && s.letzte.length >= MT.ZIEL.anzahl && summe >= MT.ZIEL.richtig) {
        s.abgeschlossen = true;
        neu = true;
      }
      sichern();
      return neu;
    },

    exportieren: function () {
      const inhalt = Object.assign({ exportiert: new Date().toISOString() }, laden());
      const blob = new Blob([JSON.stringify(inhalt, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mathe-fortschritt-' + new Date().toISOString().slice(0, 10) + '.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    },

    /** Wirft einen Fehler, wenn der Text kein gültiger Lernstand ist. */
    importieren: function (text) {
      const roh = JSON.parse(text);
      if (!roh || roh.version !== 1 || typeof roh.themen !== 'object') {
        throw new Error('Die Datei enthält keinen gültigen Lernstand.');
      }
      daten = bereinigen(roh);
      sichern();
    },

    zuruecksetzen: function () {
      daten = leer();
      sichern();
    }
  };
})(window.MT);
