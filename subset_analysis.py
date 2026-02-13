#!/usr/bin/env python3
"""
Part 4: Data subset analysis - melanoma PBMC baseline samples on miraclib.
Run with: python subset_analysis.py
"""

import csv
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RESULT_DIR = SCRIPT_DIR / "result"
DB_PATH = RESULT_DIR / "cell_count.db"
OUTPUT_PATH = RESULT_DIR / "subset_analysis_summary.csv"


def run_subset_analysis(conn: sqlite3.Connection) -> dict:
    """
    Query melanoma PBMC baseline samples (time_from_treatment_start=0) on miraclib.
    Returns aggregated counts: samples per project, subjects by response, subjects by sex.
    """
    base_query = """
        SELECT s.sample, s.project, s.subject, sub.response, sub.sex
        FROM samples s
        JOIN subjects sub ON s.project = sub.project AND s.subject = sub.subject
        WHERE sub.condition = 'melanoma'
          AND sub.treatment = 'miraclib'
          AND s.sample_type = 'PBMC'
          AND s.time_from_treatment_start = 0
    """

    cursor = conn.execute(base_query)
    rows = cursor.fetchall()

    # Samples per project
    samples_per_project: dict[str, int] = {}
    # Subjects by response (distinct subjects)
    subjects_by_response: dict[str, set[tuple[str, str]]] = {"yes": set(), "no": set()}
    # Subjects by sex (distinct subjects)
    subjects_by_sex: dict[str, set[tuple[str, str]]] = {"M": set(), "F": set()}

    for sample, project, subject, response, sex in rows:
        key = (project, subject)
        samples_per_project[project] = samples_per_project.get(project, 0) + 1
        if response in ("yes", "no"):
            subjects_by_response[response].add(key)
        subjects_by_sex[sex].add(key)

    return {
        "rows": rows,
        "samples_per_project": samples_per_project,
        "subjects_by_response": {k: len(v) for k, v in subjects_by_response.items()},
        "subjects_by_sex": {k: len(v) for k, v in subjects_by_sex.items()},
        "total_samples": len(rows),
    }


def display_results(results: dict) -> None:
    print("\n" + "=" * 70)
    print("PART 4: Melanoma PBMC Baseline Samples (time=0) on Miraclib")
    print("=" * 70)
    print(f"Total samples: {results['total_samples']}")
    print()
    print("Samples per project:")
    print("-" * 40)
    for project, count in sorted(results["samples_per_project"].items()):
        print(f"  {project}: {count}")
    print()
    print("Subjects by response:")
    print("-" * 40)
    for response, count in sorted(results["subjects_by_response"].items()):
        label = "Responders" if response == "yes" else "Non-responders"
        print(f"  {label}: {count}")
    print()
    print("Subjects by sex:")
    print("-" * 40)
    for sex, count in sorted(results["subjects_by_sex"].items()):
        label = "Male" if sex == "M" else "Female"
        print(f"  {label}: {count}")
    print("=" * 70)


def save_results_csv(results: dict, path: Path) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    # Save sample-level data
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sample", "project", "subject", "response", "sex"])
        writer.writerows(results["rows"])

    # Append summary section
    summary_path = path.parent / "subset_analysis_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Melanoma PBMC Baseline (time=0) on Miraclib - Summary\n")
        f.write("=" * 50 + "\n")
        f.write(f"Total samples: {results['total_samples']}\n\n")
        f.write("Samples per project:\n")
        for project, count in sorted(results["samples_per_project"].items()):
            f.write(f"  {project}: {count}\n")
        f.write("\nSubjects by response:\n")
        for response, count in sorted(results["subjects_by_response"].items()):
            label = "Responders" if response == "yes" else "Non-responders"
            f.write(f"  {label}: {count}\n")
        f.write("\nSubjects by sex:\n")
        for sex, count in sorted(results["subjects_by_sex"].items()):
            label = "Male" if sex == "M" else "Female"
            f.write(f"  {label}: {count}\n")


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        results = run_subset_analysis(conn)
        display_results(results)
        save_results_csv(results, OUTPUT_PATH)
        print(f"\nSample list saved to {OUTPUT_PATH}")
        print(f"Summary saved to {RESULT_DIR / 'subset_analysis_summary.txt'}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
