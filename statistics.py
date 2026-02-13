#!/usr/bin/env python3
"""
Part 3: Statistical analysis - compare responders vs non-responders (melanoma + miraclib).
Run with: python statistics.py
"""

import os
import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(SCRIPT_DIR / ".matplotlib_cache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

RESULT_DIR = SCRIPT_DIR / "result"
DB_PATH = RESULT_DIR / "cell_count.db"
BOXPLOT_PATH = RESULT_DIR / "responder_comparison_boxplot.png"

CELL_POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def load_melanoma_miraclib_data(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """
    Load PBMC samples from melanoma patients on miraclib.
    Returns (responder_samples, non_responder_samples)
    """
    query = """
        SELECT s.sample, sub.response,
               s.b_cell, s.cd8_t_cell, s.cd4_t_cell, s.nk_cell, s.monocyte
        FROM samples s
        JOIN subjects sub ON s.project = sub.project AND s.subject = sub.subject
        WHERE sub.condition = 'melanoma'
          AND sub.treatment = 'miraclib'
          AND sub.response IN ('yes', 'no')
          AND s.sample_type = 'PBMC'
    """
    cursor = conn.execute(query)
    responders = []
    non_responders = []
    for row in cursor.fetchall():
        sample, response, *counts = row
        total = sum(counts)
        sample_data = {"sample": sample}
        for pop, count in zip(CELL_POPULATIONS, counts):
            pct = (count / total * 100) if total > 0 else 0.0
            sample_data[pop] = pct
        if response == "yes":
            responders.append(sample_data)
        else:
            non_responders.append(sample_data)
    return responders, non_responders


def run_statistical_tests(
    responders: list[dict],
    non_responders: list[dict],
) -> list[dict]:
    """
    Mann-Whitney U test (non-parametric) for each population.
    Returns list of dicts with population, statistic, p_value, significant.
    """
    results = []
    for pop in CELL_POPULATIONS:
        resp_vals = [r[pop] for r in responders]
        non_resp_vals = [r[pop] for r in non_responders]
        stat, p_value = stats.mannwhitneyu(resp_vals, non_resp_vals, alternative="two-sided")
        results.append({
            "population": pop,
            "statistic": stat,
            "p_value": p_value,
            "significant": p_value < 0.05,
            "responder_mean": sum(resp_vals) / len(resp_vals),
            "responder_median": sorted(resp_vals)[len(resp_vals) // 2],
            "non_responder_mean": sum(non_resp_vals) / len(non_resp_vals),
            "non_responder_median": sorted(non_resp_vals)[len(non_resp_vals) // 2],
        })
    return results


def create_boxplot(
    responders: list[dict],
    non_responders: list[dict],
    output_path: Path,
) -> None:
    """boxplot comparing responders vs non-responders for each cell population."""
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    axes = axes.flatten()

    for idx, pop in enumerate(CELL_POPULATIONS):
        ax = axes[idx]
        resp_vals = [r[pop] for r in responders]
        non_resp_vals = [r[pop] for r in non_responders]
        bp = ax.boxplot(
            [non_resp_vals, resp_vals],
            tick_labels=["Non-responders", "Responders"],
            patch_artist=True,
        )
        bp["boxes"][0].set_facecolor("lightcoral")
        bp["boxes"][1].set_facecolor("lightgreen")
        ax.set_title(pop.replace("_", " ").title())
        ax.set_ylabel("Relative frequency (%)")
        ax.grid(axis="y", alpha=0.3)

    # Hide the last subplot (2x3 = 6, we have 5 populations)
    axes[5].set_visible(False)

    fig.suptitle(
        "Cell Population Frequencies: Melanoma + Miraclib (PBMC)\n"
        "Responders vs Non-responders",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Boxplot saved to {output_path}")


def print_statistical_report(results: list[dict]) -> None:
    print("\n" + "=" * 80)
    print("STATISTICAL ANALYSIS: Responders vs Non-responders (Melanoma + Miraclib, PBMC)")
    print("=" * 80)
    print("Test: Mann-Whitney U (two-sided), α = 0.05")
    print("-" * 80)
    print(f"{'Population':<14} {'Resp mean':>10} {'Non-resp mean':>12} {'U statistic':>12} {'p-value':>10} {'Significant':>12}")
    print("-" * 80)
    for r in results:
        sig = "Yes" if r["significant"] else "No"
        print(f"{r['population']:<14} {r['responder_mean']:>10.2f}% {r['non_responder_mean']:>12.2f}% {r['statistic']:>12.0f} {r['p_value']:>10.4f} {sig:>12}")
    print("-" * 80)
    sig_pops = [r["population"] for r in results if r["significant"]]
    if sig_pops:
        print(f"\nPopulations with significant difference (p < 0.05): {', '.join(sig_pops)}")
    else:
        print("\nNo populations show statistically significant differences at α = 0.05.")
    print("=" * 80)


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        responders, non_responders = load_melanoma_miraclib_data(conn)
        print(f"Responders: {len(responders)} samples")
        print(f"Non-responders: {len(non_responders)} samples")

        results = run_statistical_tests(responders, non_responders)
        print_statistical_report(results)

        create_boxplot(responders, non_responders, BOXPLOT_PATH)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
