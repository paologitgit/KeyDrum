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
    // true = genaue Fehlermeldung der Datenbank anzeigen (nur zur Fehlersuche einschalten).
    'debug' => false,
];
