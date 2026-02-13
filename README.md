# TeikoTech

Clinical trial analysis for immune cell populations and drug response prediction. Analyze how drug candidates affect immune cell populations and predict treatment response.

## Running the Code (GitHub Codespaces)

### Prerequisites

```bash
pip install -r requirements.txt
```

### Reproduce All Outputs

Run the scripts in order (each depends on prior outputs):

```bash
# 1. Load CSV into database (creates result/cell_count.db)
python load_data.py

# 2. Compute frequency summary (creates result/frequency_summary.csv)
python analysis.py

# 3. Statistical analysis: responders vs non-responders (creates result/responder_comparison_boxplot.png)
python statistics.py

# 4. Subset analysis: melanoma baseline on miraclib (creates result/subset_analysis_summary.csv, .txt)
python subset_analysis.py

# 5. Interactive dashboard
streamlit run dashboard.py
```

### Dashboard in Codespaces

When you run `streamlit run dashboard.py`, Codespaces will detect port 8501 and show a notification to open the app in your browser. Alternatively, use the **Ports** tab to open the forwarded URL for port 8501.

**Dashboard link (after starting):** `https://<your-codespace>-8501.app.github.dev` (or the URL shown in the port-forwarding notification)

---

## Database Schema

### Tables

| Table     | Primary Key     | Purpose |
|----------|------------------|---------|
| `subjects` | (project, subject) | Trial participants: demographics, condition, treatment, response |
| `samples`  | sample            | Individual measurements: sample metadata + immune cell counts |

### Schema Definition

```
subjects (project, subject, condition, age, sex, treatment, response)
  └── PRIMARY KEY (project, subject)

samples (sample, project, subject, sample_type, time_from_treatment_start,
         b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte)
  └── PRIMARY KEY (sample)
  └── FOREIGN KEY (project, subject) → subjects
```

### Design Rationale

- **Normalization:** Subject-level attributes (condition, age, sex, treatment, response) are stored once in `subjects`. Each subject has multiple samples over time (baseline, day 7, day 14), so splitting avoids repeating ~50 bytes per row across thousands of samples.
- **Referential integrity:** The foreign key ensures every sample links to a valid subject.
- **Indexes:** Indexes on `condition`, `treatment`, `response`, `time_from_treatment_start`, and `(project, subject)` speed up analytical queries (e.g. “melanoma + miraclib”, “baseline only”).

### Scalability

With hundreds of projects and thousands of samples:

- **Query performance:** Indexes allow fast filtering by condition, treatment, and time point without full scans.
- **Storage:** Normalization reduces redundancy; typical sample rows are ~80 bytes.
- **Analytics:** The schema supports common analyses: frequency summaries, responder vs non-responder comparisons, and project/condition/treatment subsets.
- **Future growth:** You can add tables for projects, assays, or cell types; `samples` remains the central fact table for measurements.

---

## Code Structure

```
TeikoTech/
├── data/
│   └── cell-count.csv          # Input data
├── result/                     # All outputs (created by scripts)
│   ├── cell_count.db           # SQLite database
│   ├── frequency_summary.csv
│   ├── responder_comparison_boxplot.png
│   └── subset_analysis_summary.csv
├── load_data.py                # Part 1: DB schema + load CSV
├── analysis.py                 # Part 2: Frequency summary
├── statistics.py               # Part 3: Responders vs non-responders
├── subset_analysis.py          # Part 4: Baseline subset analysis
├── dashboard.py                # Interactive Streamlit dashboard
├── requirements.txt
└── README.md
```

### Design Rationale

- **Modular scripts:** Each script does one job. They can be run in sequence or reused by other tools.
- **Shared data flow:** `load_data.py` creates the DB; all other scripts read from `result/cell_count.db` and write outputs to `result/`.
- **Dashboard reads outputs:** The dashboard loads CSVs, DB, and images from `result/`, so it reflects the latest analysis without recomputing.
- **No CLI arguments:** Scripts run with `python script.py` for simplicity and reproducibility.

---

## Dashboard

Start the dashboard with:

```bash
streamlit run dashboard.py
```

**Access:** Open the URL shown in the terminal (typically http://localhost:8501). In GitHub Codespaces, use the forwarded port URL (e.g. `https://...-8501.app.github.dev`).

The dashboard includes:
- **Overview** — Key metrics from the analysis
- **Part 2** — Filterable table of cell population frequencies
- **Part 3** — Boxplot and statistical test results (responders vs non-responders)
- **Part 4** — Bar charts for baseline subset (samples per project, response, sex)
