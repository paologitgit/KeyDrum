-- Nur nötig, falls api.php die Datenbank nicht selbst erweitern darf.
-- Jeden Block nur ausführen, wenn die Spalte noch fehlt (sonst meldet MySQL „Duplicate column“).

-- 1) Übungen mit Zeit statt Gewicht
ALTER TABLE exercises ADD COLUMN mode VARCHAR(10) NOT NULL DEFAULT 'weight' AFTER name;
ALTER TABLE sets MODIFY weight_kg DECIMAL(6,2) NULL, ADD COLUMN duration_s INT UNSIGNED NULL AFTER reps;

-- 2) Trainingsdauer (Start- und Endzeit)
ALTER TABLE workouts ADD COLUMN start_time TIME NULL AFTER workout_date, ADD COLUMN end_time TIME NULL AFTER start_time;
