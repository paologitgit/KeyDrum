<?php
// Kopieren nach config.php und Zugangsdaten eintragen.
// config.php gehört NICHT ins Repository (siehe .gitignore).
return [
    'db_host' => 'localhost',
    'db_name' => 'trainingslog',
    'db_user' => 'trainingslog',
    'db_pass' => 'BITTE_AENDERN',
    // Einfacher Zugriffsschutz: gleicher Wert wird beim ersten Öffnen der App abgefragt.
    // Leer lassen = kein Schutz (nur für lokale Tests empfohlen).
    'app_token' => 'BITTE_AENDERN',
    // Optional: KI-Auswertung der Trainings. Einen der beiden Wege wählen; leer lassen = Funktion aus.
    // a) Über OpenRouter (openrouter.ai, Schlüssel beginnt mit sk-or-…). Läuft ohne Zusatzordner und ab PHP 7.4.
    //    Ist hier ein Schlüssel eingetragen, wird OpenRouter verwendet.
    'openrouter_api_key' => '',
    //    Modell-Kennung genau wie auf openrouter.ai/models angegeben, z. B. anthropic/claude-opus-5.5
    'openrouter_model' => 'anthropic/claude-opus-5.5',
    // b) Direkt bei Anthropic (Claude Console, beginnt mit sk-ant-…). Braucht PHP 8.2+ und den Ordner claude/vendor.
    'anthropic_api_key' => '',
    // true = genaue Fehlermeldung der Datenbank anzeigen (nur zur Fehlersuche einschalten).
    'debug' => false,
];
