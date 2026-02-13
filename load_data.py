#!/usr/bin/env python3
"""
Part 1: Load cell-count.csv into a SQLite database for clinical trial analysis.
Run with: python load_data.py
"""

import csv
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RESULT_DIR = SCRIPT_DIR / "result"
CSV_PATH = SCRIPT_DIR / "data" / "cell-count.csv"
DB_PATH = RESULT_DIR / "cell_count.db"


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        -- Subjects: trial participants with demographics and treatment info
        CREATE TABLE IF NOT EXISTS subjects (
            project TEXT NOT NULL,
            subject TEXT NOT NULL,
            condition TEXT NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            treatment TEXT NOT NULL,
            response TEXT,
            PRIMARY KEY (project, subject)
        );

        -- Samples: individual measurements with immune cell counts
        CREATE TABLE IF NOT EXISTS samples (
            sample TEXT PRIMARY KEY,
            project TEXT NOT NULL,
            subject TEXT NOT NULL,
            sample_type TEXT NOT NULL,
            time_from_treatment_start INTEGER NOT NULL,
            b_cell INTEGER NOT NULL,
            cd8_t_cell INTEGER NOT NULL,
            cd4_t_cell INTEGER NOT NULL,
            nk_cell INTEGER NOT NULL,
            monocyte INTEGER NOT NULL,
            FOREIGN KEY (project, subject) REFERENCES subjects(project, subject)
        );

        -- Indexes for common analytical queries
        CREATE INDEX IF NOT EXISTS idx_subjects_condition ON subjects(condition);
        CREATE INDEX IF NOT EXISTS idx_subjects_treatment ON subjects(treatment);
        CREATE INDEX IF NOT EXISTS idx_subjects_response ON subjects(response);
        CREATE INDEX IF NOT EXISTS idx_samples_project_subject ON samples(project, subject);
        CREATE INDEX IF NOT EXISTS idx_samples_time ON samples(time_from_treatment_start);
        CREATE INDEX IF NOT EXISTS idx_samples_subject_time ON samples(project, subject, time_from_treatment_start);
    """)


def load_data(conn: sqlite3.Connection) -> None:
    subjects_seen: set[tuple[str, str]] = set()
    subject_rows: list[tuple] = []
    sample_rows: list[tuple] = []

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project = row["project"]
            subject = row["subject"]
            subject_key = (project, subject)

            # Collect unique subjects
            if subject_key not in subjects_seen:
                subjects_seen.add(subject_key)
                subject_rows.append((
                    project,
                    subject,
                    row["condition"],
                    int(row["age"]),
                    row["sex"],
                    row["treatment"],
                    row["response"] if row["response"] else None,
                ))

            # Collect all samples
            sample_rows.append((
                row["sample"],
                project,
                subject,
                row["sample_type"],
                int(row["time_from_treatment_start"]),
                int(row["b_cell"]),
                int(row["cd8_t_cell"]),
                int(row["cd4_t_cell"]),
                int(row["nk_cell"]),
                int(row["monocyte"]),
            ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO subjects
        (project, subject, condition, age, sex, treatment, response)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        subject_rows,
    )

    conn.executemany(
        """
        INSERT OR REPLACE INTO samples
        (sample, project, subject, sample_type, time_from_treatment_start,
         b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        sample_rows,
    )


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        load_data(conn)
        conn.commit()
        print(f"Successfully loaded data into {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
