-- Nur nötig, falls api.php die Datenbank nicht selbst erweitern darf.
-- Ergänzt bestehende Installationen um Übungen mit Zeit statt Gewicht.
ALTER TABLE exercises ADD COLUMN mode VARCHAR(10) NOT NULL DEFAULT 'weight' AFTER name;
ALTER TABLE sets MODIFY weight_kg DECIMAL(6,2) NULL, ADD COLUMN duration_s INT UNSIGNED NULL AFTER reps;
