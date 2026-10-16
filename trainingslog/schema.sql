-- Trainingslog – MySQL/MariaDB-Schema
-- Import: mysql -u USER -p DATENBANK < schema.sql

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS exercises (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  mode        VARCHAR(10) NOT NULL DEFAULT 'weight',   -- 'weight' = kg × Wdh., 'time' = Dauer
  sort_order  INT NOT NULL DEFAULT 0,
  active      TINYINT(1) NOT NULL DEFAULT 1,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_exercise_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workouts (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  workout_date  DATE NOT NULL,
  start_time    TIME NULL,
  end_time      TIME NULL,
  note          VARCHAR(255) NULL,
  rpe           TINYINT UNSIGNED NULL,          -- Tagesform 1–10
  body_weight   DECIMAL(5,2) NULL,              -- Körpergewicht in kg
  plan_id       INT UNSIGNED NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_workout_date (workout_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sets (
  id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  workout_id   INT UNSIGNED NOT NULL,
  exercise_id  INT UNSIGNED NOT NULL,
  set_no       SMALLINT UNSIGNED NOT NULL,
  weight_kg    DECIMAL(6,2) NULL,
  reps         SMALLINT UNSIGNED NULL,
  duration_s   INT UNSIGNED NULL,
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_sets_exercise (exercise_id, workout_id),
  CONSTRAINT fk_sets_workout  FOREIGN KEY (workout_id)  REFERENCES workouts(id)  ON DELETE CASCADE,
  CONSTRAINT fk_sets_exercise FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS plans (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS plan_exercises (
  plan_id      INT UNSIGNED NOT NULL,
  exercise_id  INT UNSIGNED NOT NULL,
  PRIMARY KEY (plan_id, exercise_id),
  CONSTRAINT fk_pe_plan     FOREIGN KEY (plan_id)     REFERENCES plans(id)     ON DELETE CASCADE,
  CONSTRAINT fk_pe_exercise FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO exercises (name, sort_order) VALUES
  ('Deadlift', 10),
  ('Latzug', 20),
  ('Sitting Row', 30),
  ('Pull-up', 40),
  ('Bankdrücken', 50),
  ('Bizeps', 60),
  ('Schulter seitlich', 70),
  ('Rücken', 80),
  ('Butterfly reverse', 90);
