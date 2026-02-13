#!/usr/bin/env python3
"""
Clinical trial analysis: compute and display relative frequency of cell populations.
Run with: python analysis.py
"""

import csv
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RESULT_DIR = SCRIPT_DIR / "result"
DB_PATH = RESULT_DIR / "cell_count.db"
OUTPUT_PATH = RESULT_DIR / "frequency_summary.csv"

CELL_POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def compute_frequency_summary(conn: sqlite3.Connection) -> list[dict]:
    """
    Compute relative frequency of each cell type in each sample.
    Returns a list of dicts with keys: sample, total_count, population, count, percentage.
    """
    cursor = conn.execute(
        "SELECT sample, b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte FROM samples"
    )
    rows = []
    for row in cursor.fetchall():
        sample = row[0]
        counts = dict(zip(CELL_POPULATIONS, row[1:]))
        total_count = sum(counts.values())
        for pop in CELL_POPULATIONS:
            count = counts[pop]
            percentage = (count / total_count * 100) if total_count > 0 else 0.0
            rows.append({
                "sample": sample,
                "total_count": total_count,
                "population": pop,
                "count": count,
                "percentage": round(percentage, 4),
            })
    return rows


def display_summary(rows: list[dict], max_display: int = 30) -> None:
    print("Relative frequency of each cell type per sample:")
    print("=" * 90)
    print(f"{'sample':<12} {'total_count':>12} {'population':<12} {'count':>8} {'percentage':>10}")
    print("-" * 90)
    for r in rows[:max_display]:
        print(f"{r['sample']:<12} {r['total_count']:>12} {r['population']:<12} {r['count']:>8} {r['percentage']:>10.4f}%")
    if len(rows) > max_display:
        print("...")
        print(f"(showing first {max_display} of {len(rows):,} rows)")
    print("=" * 90)
    print(f"Total rows: {len(rows):,}")


def save_summary_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sample", "total_count", "population", "count", "percentage"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = compute_frequency_summary(conn)
        display_summary(rows)
        save_summary_csv(rows, OUTPUT_PATH)
        print(f"\nFull summary saved to {OUTPUT_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
