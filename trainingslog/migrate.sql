-- Nur nötig, falls api.php die Datenbank nicht selbst erweitern darf.
-- Jeden Block nur ausführen, wenn die Spalte noch fehlt (sonst meldet MySQL „Duplicate column“).

-- 1) Übungen mit Zeit statt Gewicht
ALTER TABLE exercises ADD COLUMN mode VARCHAR(10) NOT NULL DEFAULT 'weight' AFTER name;
ALTER TABLE sets MODIFY weight_kg DECIMAL(6,2) NULL, ADD COLUMN duration_s INT UNSIGNED NULL AFTER reps;

-- 2) Trainingsdauer (Start- und Endzeit)
ALTER TABLE workouts ADD COLUMN start_time TIME NULL AFTER workout_date, ADD COLUMN end_time TIME NULL AFTER start_time;

-- 3) Tagesform, Körpergewicht und Trainingspläne
ALTER TABLE workouts ADD COLUMN rpe TINYINT UNSIGNED NULL, ADD COLUMN body_weight DECIMAL(5,2) NULL, ADD COLUMN plan_id INT UNSIGNED NULL;
CREATE TABLE IF NOT EXISTS plans (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS plan_exercises (
  plan_id INT UNSIGNED NOT NULL,
  exercise_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (plan_id, exercise_id),
  CONSTRAINT fk_pe_plan FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
  CONSTRAINT fk_pe_exercise FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4) Ausdauer: Distanz pro Eintrag und die Übungen Fahrradfahren / Joggen
ALTER TABLE sets ADD COLUMN distance_km DECIMAL(7,2) NULL AFTER duration_s;
INSERT IGNORE INTO exercises (name, mode, sort_order) VALUES ('Fahrradfahren', 'cardio', 1000), ('Joggen', 'cardio', 1010);
