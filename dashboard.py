#!/usr/bin/env python3
"""
Interactive dashboard
Run with: streamlit run dashboard.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

SCRIPT_DIR = Path(__file__).resolve().parent
RESULT_DIR = SCRIPT_DIR / "result"
DB_PATH = RESULT_DIR / "cell_count.db"

CELL_POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def load_frequency_summary() -> pd.DataFrame:
    """Load Part 2 frequency summary from CSV."""
    path = RESULT_DIR / "frequency_summary.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_subset_analysis() -> dict:
    """Load Part 4 subset analysis from database."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT s.sample, s.project, s.subject, sub.response, sub.sex
        FROM samples s
        JOIN subjects sub ON s.project = sub.project AND s.subject = sub.subject
        WHERE sub.condition = 'melanoma'
          AND sub.treatment = 'miraclib'
          AND s.sample_type = 'PBMC'
          AND s.time_from_treatment_start = 0
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    samples_per_project = df.groupby("project").size().to_dict()
    subjects_by_response = df.drop_duplicates(["project", "subject"]).groupby("response").size()
    subjects_by_sex = df.drop_duplicates(["project", "subject"]).groupby("sex").size()

    return {
        "df": df,
        "samples_per_project": samples_per_project,
        "subjects_by_response": subjects_by_response,
        "subjects_by_sex": subjects_by_sex,
        "total_samples": len(df),
    }


def load_statistical_results() -> list[dict]:
    """Compute statistical results from database (Part 3)."""
    from scipy import stats

    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT s.sample, sub.response, s.b_cell, s.cd8_t_cell, s.cd4_t_cell, s.nk_cell, s.monocyte
        FROM samples s
        JOIN subjects sub ON s.project = sub.project AND s.subject = sub.subject
        WHERE sub.condition = 'melanoma' AND sub.treatment = 'miraclib'
          AND sub.response IN ('yes', 'no') AND s.sample_type = 'PBMC'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    responders = df[df["response"] == "yes"]
    non_responders = df[df["response"] == "no"]

    results = []
    for pop in CELL_POPULATIONS:
        resp_vals = responders[pop].values
        non_resp_vals = non_responders[pop].values
        total_resp = responders[[c for c in CELL_POPULATIONS]].sum(axis=1)
        total_non = non_responders[[c for c in CELL_POPULATIONS]].sum(axis=1)
        resp_pct = (resp_vals / total_resp.values) * 100
        non_pct = (non_resp_vals / total_non.values) * 100
        stat, p_value = stats.mannwhitneyu(resp_pct, non_pct, alternative="two-sided")
        results.append({
            "population": pop.replace("_", " ").title(),
            "responder_mean": resp_pct.mean(),
            "non_responder_mean": non_pct.mean(),
            "p_value": p_value,
            "significant": p_value < 0.05,
        })
    return results


def main() -> None:
    st.set_page_config(
        page_title="Clinical Trial Analysis Dashboard",
        page_icon="🔬",
        layout="wide",
    )

    st.title("My Clinical Trial Analysis Dashboard")
    st.markdown("*Immune cell population analysis for drug response prediction*")

    # Check if results exist
    if not DB_PATH.exists():
        st.error("No database found. Run `python load_data.py` first, then `python analysis.py`.")
        return

    # Sidebar navigation
    st.sidebar.header("Navigation")
    section = st.sidebar.radio(
        "Select section",
        ["Overview", "Frequency Summary", "Statistical Analysis", "Subset Analysis"],
    )

    # --- Overview ---
    if section == "Overview":
        st.header("Overview")
        freq_df = load_frequency_summary()
        subset = load_subset_analysis()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total samples", f"{len(freq_df) // 5:,}" if len(freq_df) > 0 else "—", help="Unique samples")
        with col2:
            st.metric("Frequency rows", f"{len(freq_df):,}" if len(freq_df) > 0 else "—", help="Sample × population")
        with col3:
            st.metric("Baseline subset", f"{subset['total_samples']:,}", help="Melanoma PBMC baseline on miraclib")
        with col4:
            sig = [r for r in load_statistical_results() if r["significant"]]
            st.metric("Significant populations", len(sig), help="p < 0.05 responders vs non-responders")

        st.info("Run the analysis scripts to refresh results: `load_data.py` → `analysis.py` → `statistics.py` → `subset_analysis.py`")

    # --- Part 2: Frequency Summary ---
    elif section == "Frequency Summary":
        st.header("Part 2: Cell Population Relative Frequencies")
        st.markdown("Relative frequency of each immune cell type in each sample.")

        freq_df = load_frequency_summary()
        if freq_df.empty:
            st.warning("No frequency summary found. Run `python analysis.py` first.")
        else:
            pop_filter = st.multiselect(
                "Filter by population",
                options=freq_df["population"].unique(),
                default=freq_df["population"].unique(),
            )
            sample_filter = st.text_input("Filter by sample (e.g. sample00000)", "")
            filtered = freq_df[freq_df["population"].isin(pop_filter)]
            if sample_filter:
                filtered = filtered[filtered["sample"].str.contains(sample_filter, case=False)]

            st.dataframe(
                filtered.head(500).style.format({"percentage": "{:.2f}%"}),
                use_container_width=True,
            )
            st.caption(f"Showing up to 500 of {len(filtered):,} rows. Use filters to narrow down.")

    # --- Part 3: Statistical Analysis ---
    elif section == "Statistical Analysis":
        st.header("Part 3: Responders vs Non-responders")
        st.markdown("Melanoma patients on miraclib (PBMC). Mann-Whitney U test, α = 0.05.")

        boxplot_path = RESULT_DIR / "responder_comparison_boxplot.png"
        if boxplot_path.exists():
            st.image(str(boxplot_path), use_container_width=True)

        stats_results = load_statistical_results()
        stats_df = pd.DataFrame(stats_results)
        stats_df["Significant"] = stats_df["significant"].map({True: "Yes", False: "No"})
        stats_df = stats_df[["population", "responder_mean", "non_responder_mean", "p_value", "Significant"]]
        stats_df.columns = ["Population", "Responder mean (%)", "Non-responder mean (%)", "p-value", "Significant"]

        st.dataframe(
            stats_df.style.format({
                "Responder mean (%)": "{:.2f}",
                "Non-responder mean (%)": "{:.2f}",
                "p-value": "{:.4f}",
            }),
            use_container_width=True,
        )
        sig_pops = [r["population"] for r in stats_results if r["significant"]]
        if sig_pops:
            st.success(f"**Significant difference (p < 0.05):** {', '.join(sig_pops)}")

    # --- Part 4: Subset Analysis ---
    elif section == "Subset Analysis":
        st.header("Part 4: Melanoma PBMC Baseline (time=0) on Miraclib")
        st.markdown("Samples at baseline from patients treated with miraclib.")

        subset = load_subset_analysis()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Samples per project")
            proj_df = pd.DataFrame(
                list(subset["samples_per_project"].items()),
                columns=["Project", "Samples"],
            )
            proj_chart = proj_df.set_index("Project")
            st.bar_chart(proj_chart)
        with col2:
            st.subheader("Subjects by response")
            resp_df = subset["subjects_by_response"].to_frame("Subjects").reset_index()
            resp_df["response"] = resp_df["response"].map({"yes": "Responders", "no": "Non-responders"})
            resp_chart = resp_df.set_index("response")
            st.bar_chart(resp_chart)
        with col3:
            st.subheader("Subjects by sex")
            sex_df = subset["subjects_by_sex"].to_frame("Subjects").reset_index()
            sex_df["sex"] = sex_df["sex"].map({"M": "Male", "F": "Female"})
            sex_chart = sex_df.set_index("sex")
            st.bar_chart(sex_chart)

        st.metric("Total baseline samples", subset["total_samples"])

        with st.expander("View sample list"):
            st.dataframe(subset["df"], use_container_width=True)


if __name__ == "__main__":
    main()
