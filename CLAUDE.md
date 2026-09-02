# CLAUDE.md — English Learning App (B1 Preliminary)

Diese Datei enthält die verbindlichen Regeln für die Arbeit an diesem Projekt.
Sie gilt für alle Sitzungen, auch wenn im Chat nicht ausdrücklich darauf verwiesen wird.

---

## 1. Projektziel

Eine Lern-App für Englisch auf Niveau **B1 (CEFR)**, deren gesamter Wortschatz auf der
**Cambridge B1 Preliminary Vocabulary List (from 2020)** beruht.

Drei Übungsbereiche, gleichwertig:

1. **Wortschatz** – Wörter aufbauen, festigen, abrufen.
2. **Leseverstehen** – Texte lesen und in Aufgabenformaten verarbeiten.
3. **Schreiben** – eigene Texte verfassen und strukturiert überarbeiten.

Alles läuft **vollständig offline**.

---

## 2. Quelle: die Vokabelliste

Die Datei `docs/source/b1-preliminary-2020-vocabulary-list.pdf` ist die **einzige
massgebende Wortschatzquelle**. Struktur des Dokuments:

| Seiten | Inhalt |
|--------|--------|
| 1–3 | Titel, Einleitung, Abkürzungsverzeichnis |
| 4–39 | Alphabetische Liste, rund 3'200 Stichwörter |
| 40 | Appendix 1 – Wortgruppen (Kardinal-/Ordinalzahlen, Wochentage, Monate, Jahreszeiten, Länder/Nationalitäten/Sprachen, Kontinente) |
| 41–51 | Appendix 2 – 22 Themenlisten (Clothes and Accessories, Colours, Communications and Technology, Education, Entertainment and Media, Environment, Food and Drink, Health/Medicine and Exercise, Hobbies and Leisure, House and Home, Language, Places: Buildings, Places: Countryside, Places: Town and City, Services, Shopping, Sport, The Natural World, Time, Travel and Transport, Weather, Work and Jobs) |

Eintragsformat der Liste: `headword (Wortart)`, darunter eingerückt optionale
Beispiele oder Kollokationen, z. B. `application (n)` → `job application`, `application form`.
Abkürzungen gemäss S. 3: `n, v, adj, adv, prep, prep phr, conj, det, pron, phr, phr v, av, mv, abbrev, pl, Br Eng, Am Eng`.

**Regeln:**

- Das PDF wird **nie verändert**. Extraktion erfolgt über ein versioniertes Skript
  (`tools/extract_vocabulary.py`) in eine geprüfte Datendatei; die Datendatei wird
  mitversioniert, damit der Build ohne PDF-Werkzeuge auskommt.
- Die Extraktion ist **reproduzierbar**: gleiches PDF → gleiches Ergebnis (stabile Sortierung, keine Zufallswerte).
- Manuelle Korrekturen an extrahierten Daten kommen in eine separate, kommentierte
  Overlay-Datei, nie direkt in die generierte Datei.
- **Kein Wort in einer Übung, das nicht in Liste oder Appendices steht.** Ausnahmen
  (Eigennamen, Funktionswörter in Aufgabenstellungen) werden in einer Whitelist geführt.
- Herkunft und Urheberrecht (© UCLES 2018) werden in der App sichtbar genannt. Die
  Liste ist Grundlage, nicht Produkt: Wir veröffentlichen keine reine Abschrift des PDF.

---

## 3. Zielgruppe und Ton

**Motivierte erwachsene Lernende**, die selbstständig arbeiten und wissen wollen, wo sie stehen.

- Deutsche Oberflächen- und Hilfetexte in der **Höflichkeitsform (Sie)**.
- **Nicht belehrend, nicht kindlich.** Kein Duzen, keine Ausrufezeichen-Rhetorik,
  keine Emoji-Konfetti, keine „Super gemacht!"-Sprache, keine Maskottchen.
- Rückmeldungen sind **sachlich und konkret**: was war richtig, was nicht, warum,
  was folgt daraus. Statt „Leider falsch" → „*advice* ist ein unzählbares Nomen; korrekt: *some advice*."
- Erwachsene dürfen selbst steuern: Lernende können Übungen überspringen, Lösungen
  einsehen, Wiederholungsintervalle anpassen und Themen frei wählen. Nichts wird erzwungen.
- Fortschritt wird **transparent und ehrlich** dargestellt (Abdeckung, Trefferquote,
  fällige Wiederholungen) – keine geschönten Zahlen, keine künstlichen Belohnungssysteme.

---

## 4. Arbeitsweise (Regeln für Claude)

1. **Fragen stellen.** Bei unklaren Anforderungen wird nachgefragt, statt zu raten.
   Lieber eine präzise Frage zu viel als eine falsche Annahme. Fragen werden gebündelt
   gestellt, mit einer Empfehlung versehen und – wo möglich – als Auswahl formuliert.
2. **Pläne im Vorfeld erklären.** Vor jeder nicht-trivialen Änderung (neues Feature,
   neues Datenformat, Umbau, neue Abhängigkeit) zuerst in wenigen Sätzen darlegen:
   Ziel, betroffene Dateien, Vorgehen, Auswirkungen, Alternativen. Erst nach
   Rückmeldung umsetzen. Trivial sind: Tippfehler, Formatierung, kleine Bugfixes.
3. **Didaktische Entscheidungen gehören der Lehrperson.** Aufgabenformate,
   Progression, Bewertungslogik und Formulierungen werden vorgeschlagen, nicht gesetzt.
4. **Kleine Schritte.** Ein Thema pro Änderung, lauffähiger Stand nach jedem Schritt.
5. **Kein ungefragter Zusatzumfang.** Keine zusätzlichen Features, Abhängigkeiten
   oder Refactorings ohne Absprache.
6. **Kommunikationssprache ist Deutsch (Sie-Form).** Code, Bezeichner, Commit-Messages
   und technische Dokumentation auf Englisch.
7. **Ehrlich berichten.** Was nicht getestet oder nicht fertig ist, wird benannt.
   Keine Fortschrittsmeldung ohne tatsächliche Prüfung.

---

## 5. Offline-First (harte Regeln)

Die App muss ohne jede Netzverbindung vollständig funktionieren – dauerhaft, nicht nur
im Notbetrieb.

- **Keine Netzwerkaufrufe zur Laufzeit.** Kein CDN, keine Web-Fonts von aussen, keine
  Analytics, keine Crash-Reports, keine Lizenz- oder Update-Prüfung.
- **Kein Sprachmodell zur Laufzeit.** Alle Texte, Aufgaben, Musterlösungen und
  Erklärungen werden vorab erzeugt, redaktionell geprüft und mitgeliefert.
  KI-Unterstützung findet in der Entwicklung statt, nicht im Betrieb der App.
- **Alle Ressourcen liegen lokal**: Wortdaten, Texte, Audio, Bilder, Schriften, Bibliotheken.
- **Lokale Datenhaltung.** Lernstand bleibt auf dem Gerät. Sicherung und Umzug per
  Export/Import einer einzelnen Datei (JSON), von Hand auslösbar.
- **Der Build läuft ohne Netz.** Abhängigkeiten sind gepinnt und eingecheckt bzw. lokal
  vorhanden; ein Build im abgeschotteten Container muss durchlaufen.
- Neue Abhängigkeiten sind begründungspflichtig: Was leistet sie, wie gross ist sie,
  läuft sie offline, was kostet ein Verzicht?
- Es gibt einen automatisierten Test, der bei jedem Build **prüft, dass keine externen
  URLs referenziert werden**.

---

## 6. Übungsbereiche

### 6.1 Wortschatz
- Datenbasis pro Eintrag: Stichwort, Wortart(en), Beispiele aus der Liste, Themenzuordnung(en) aus Appendix 2.
- Übungstypen (Auswahl wird gemeinsam festgelegt): Erkennen (EN→DE), Produzieren (DE→EN),
  Lückensatz im Kontext, Kollokationen, Wortfamilien, Zuordnung zu Themenfeldern, Hörschreibung.
- **Wörter werden immer im Satzkontext gezeigt**, nie als blosse Vokabelpaare.
- Wiederholung nach einem nachvollziehbaren Verfahren (z. B. Leitner mit festen
  Intervallen). Das Verfahren wird dokumentiert und ist für Lernende einsehbar.
- Mehrere korrekte Antworten sind zuzulassen (Synonyme, Br/Am Eng, Gross-/Kleinschreibung, Tippfehlertoleranz nach vereinbarter Regel).

### 6.2 Leseverstehen
- Texte werden für die App verfasst oder redaktionell angepasst, mit Angabe von Länge,
  Textsorte und Themenfeld.
- **Wortschatz-Abdeckung ist prüfbar**: Ein Skript meldet jedes Wort eines Textes, das
  nicht auf der Liste steht. Zielwert und erlaubte Ausnahmen werden festgelegt.
- Aufgabenformate orientieren sich an den B1-Preliminary-Formaten
  (Multiple Choice, Zuordnung, Lücken, Richtig/Falsch), ohne Prüfungsmaterial zu kopieren.
- Jede Aufgabe hat eine Lösung **mit Begründung und Textstelle**, nicht nur einen Lösungsbuchstaben.

### 6.3 Schreiben
- Aufgaben in realistischen Textsorten: E-Mail, Nachricht, Bericht, kurze Geschichte,
  Stellungnahme – mit Situation, Adressat, Umfang.
- Offline gibt es **keine automatische Korrektur, die es nicht geben kann.** Stattdessen:
  Kriterienraster (Inhalt, Aufbau, Wortschatz, Sprache), Selbstprüfliste, Musterlösung
  mit Kommentaren, mechanische Prüfungen (Wortzahl, Wiederholungen, Wortschatz-Abdeckung,
  Zielstrukturen), Möglichkeit zur Überarbeitung mit Versionsvergleich.
- Automatische Hinweise werden klar als **maschinelle Prüfung** ausgewiesen, nie als Bewertung.
- Eigene Texte lassen sich exportieren (z. B. für die Besprechung im Unterricht).

---

## 7. Inhaltliche Leitplanken

- Niveau durchgehend **B1**; Struktur und Länge werden dokumentiert und geprüft.
- **Britisches Englisch als Standard**, amerikanische Varianten werden gekennzeichnet,
  wo die Liste sie führt (`Br Eng` / `Am Eng`).
- **Sensible Themen bleiben aussen vor** – analog zur Vorgabe der Liste (u. a. Krieg,
  Politik, Religion, Gewalt, Krankheit als Schicksalsschlag, Tod, Diskriminierung).
  Inhalte sind für erwachsene Lernende in Kursen jederzeit unbedenklich.
- Inhalte sind **erwachsenengerecht**: Arbeitswelt, Reisen, Wohnen, Gesundheit,
  Konsum, Freizeit, Technik – keine Schulkinder-Szenarien.
- Vielfalt bei Namen, Rollen und Herkunft der Figuren, ohne Klischees.
- Jeder ausgelieferte Text ist redaktionell geprüft; nicht geprüfte Inhalte werden als
  Entwurf gekennzeichnet und nicht ausgeliefert.

---

## 8. Technische Leitplanken

- **Datenmodell zuerst**: Wortdaten, Aufgaben und Lernstand sind getrennt und
  versioniert; jede Datendatei trägt eine Schema-Version.
- Inhalte liegen **als Daten vor, nicht im Code**. Neue Übungen entstehen durch neue
  Datendateien, nicht durch neue Codepfade.
- **Trennung** von Datenzugriff, Lernlogik und Oberfläche; Lernlogik ist ohne UI testbar.
- **Tests** für: Extraktion, Wortschatz-Abdeckung, Wiederholungsalgorithmus,
  Antwortbewertung, Offline-Prüfung, Import/Export. Fehler zuerst durch einen Test belegen, dann beheben.
- **Barrierefreiheit**: Tastaturbedienung, sichtbarer Fokus, ausreichende Kontraste,
  skalierbare Schrift, sinnvolle Beschriftungen. Kein Bedienelement nur per Farbe unterscheidbar.
- **Robustheit**: Der Lernstand darf durch Abstürze oder Schliessen nicht verloren gehen;
  Schreibvorgänge sind atomar, Migrationen zwischen Schema-Versionen sind vorhanden.
- Code englisch, sprechende Namen, Kommentare nur dort, wo das Warum nicht offensichtlich ist.

---

## 9. Datenschutz

- Keine Konten, keine Registrierung, keine Cloud, keine Telemetrie.
- Es werden nur Daten gespeichert, die für den Lernstand nötig sind.
- Lernende können ihre Daten jederzeit einsehen, exportieren und vollständig löschen.

---

## 10. Definition of Done

Eine Änderung gilt als fertig, wenn:

1. der geplante Umfang umgesetzt und abgesprochen ist,
2. Tests vorhanden sind und lokal durchlaufen,
3. die App im Flugmodus / ohne Netz vollständig funktioniert,
4. neue Inhalte die Wortschatzprüfung bestehen,
5. deutsche Texte in der Sie-Form und im vereinbarten Ton verfasst sind,
6. dokumentiert ist, was sich für Lernende ändert.

---

## 11. Offene Entscheidungen

Diese Punkte sind noch **nicht entschieden**. Bis zur Klärung wird hier nichts
implementiert; Annahmen werden ausdrücklich als solche gekennzeichnet.

- [ ] **Plattform und Technik**: Web-App/PWA, Desktop-Anwendung oder mobile App?
- [ ] **Sprache der Oberfläche**: zweisprachig Deutsch–Englisch oder einsprachig Englisch?
- [ ] **Übersetzungen**: Woher kommen die deutschen Bedeutungen der rund 3'200 Stichwörter (Lizenzfrage)?
- [ ] **Nutzungsform**: reines Selbstlernen oder auch Einsatz im Kurs (Auswertung, Export für die Lehrperson)?
- [ ] **Umfang Version 1**: Welcher der drei Bereiche startet zuerst?
- [ ] **Ort des Projekts**: eigenes Repository oder Unterordner in diesem Repository (enthält bisher das unabhängige Projekt `KeyBand`)?
- [ ] **Audio**: Aussprache der Stichwörter gewünscht? Offline bedeutet mitgelieferte Audiodateien.
