# California Inpatient Capacity: 52-Week Rolling-Origin Evaluation Report

## 1. Executive Summary
This report documents the rigorous, rolling-origin evaluation of daily inpatient bed demand (`inpatient_beds_used`) across **52 weekly forecast origins** spanning **2023-04-30 through 2024-04-27** (364 evaluated forecast days per model).

### Evaluation Design & Data Scope:
- **Evaluation Window Geometry:** With spacing parameter `step = 7` days matching the forecast horizon `horizon = 7` days, the 52 forecast origins form a sequence of **contiguous, non-overlapping weekly evaluation windows** spanning exactly 364 consecutive calendar days (April 30, 2023, through April 27, 2024).
- **Macro-Level Aggregation:** The dataset represents **statewide aggregate inpatient-bed utilization** across approximately 400 licensed acute-care facilities in California, compiled through mandatory HHS reporting. It does not represent an individual hospital or clinical ward census.
- **Leakage Prevention Protocols:**
  1. Every forecast origin uses strictly historical training data prior to that cutoff ($T_k$).
  2. In-sample seasonal naive scale ($Q_{train}$) for MASE is computed strictly on training data at each origin.
  3. Multi-step forecasts for Ridge and XGBoost are generated **recursively** without accessing future ground truth.
  4. Total capacity ($C_t$) is omitted from predictive features to prevent contemporaneous capacity leakage.

---

## 2. Overall Aggregate Model Performance
Evaluated across **364 paired observations** (52 origins $\times$ 7 days):

| Model Architecture | Multi-Step Strategy | MAE (Beds) | RMSE (Beds) | MAPE (%) | MASE |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Weekly Seasonal Naive** | Lag-7 Persistence | **711.47** | **1053.72** | **1.48%** | **0.5646** |
| **Ridge Regression** | Recursive Autoregressive | **727.68** | **979.58** | **1.51%** | **0.5757** |
| **XGBoost Regressor** | Recursive Autoregressive | **639.26** | **939.64** | **1.33%** | **0.5072** |

---

## 3. Horizon-Specific Breakdown (Steps 1 through 7)
Tracking error compounding as the recursive forecast horizon extends:

| Horizon Step ($h$) | Seasonal Naive MAE | Ridge Recursive MAE | XGBoost Recursive MAE | Seasonal Naive MASE | Ridge MASE | XGBoost MASE |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Day 1 | 627.56 | 308.84 | 427.97 | 0.4976 | 0.2442 | 0.3396 |
| Day 2 | 678.62 | 503.65 | 564.41 | 0.5386 | 0.3969 | 0.4479 |
| Day 3 | 845.12 | 823.81 | 756.76 | 0.6677 | 0.6519 | 0.5981 |
| Day 4 | 758.63 | 969.23 | 747.02 | 0.5994 | 0.7664 | 0.5909 |
| Day 5 | 734.35 | 711.34 | 648.01 | 0.5831 | 0.5654 | 0.5138 |
| Day 6 | 686.96 | 827.79 | 665.32 | 0.5469 | 0.6545 | 0.5286 |
| Day 7 | 649.04 | 949.06 | 665.33 | 0.5187 | 0.7508 | 0.5314 |

---

## 4. Key Empirical Findings & Methodological Limitations
1. **Longitudinal Robustness Across a Full Year:** Unlike a single 7-day holdout, evaluating 52 origins encompasses autumn surges, winter peaks, and spring lulls across California acute-care facilities.
2. **Error Growth by Horizon:** Autoregressive ML models compound error as the recursive horizon advances from Step 1 to Step 7. Ridge regression excels at Day 1 (MAE: 308.84 beds) but degrades over the horizon (Day 7 MAE: 949.06 beds), whereas XGBoost maintains tighter stability across the week (MAE: 427.97 to 665.33 beds).
3. **MASE Benchmarking:** MASE scores relative to in-sample seasonal scaling confirm whether machine learning provides substantial advantages over periodic persistence ($\text{MASE} \in [0.507, 0.576]$ across all models).
4. **Statewide Aggregation Limitation:** Statewide aggregation provides macro-level capacity surveillance across ~400 facilities, but masks facility-specific variance, localized bed shortages, and county-level supply-demand mismatches (e.g., urban trauma centers vs. rural community hospitals).
5. **Static Capacity Horizon Assumption:** During each 7-day forecast horizon, total capacity is anchored to the observed value at cutoff $T_k$. In actual clinical practice, staffed bed capacity fluctuates contemporaneously due to staffing adjustments, weekend shift rosters, and surge ward activations.

---

## 5. Artifacts and Data Provenance
- Metrics JSON: `/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/rolling_evaluation/rolling_experiment_metrics.json`
- Detailed Predictions CSV: `/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/rolling_evaluation/rolling_forecast_predictions.csv`
- Horizon Metrics CSV: `/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/rolling_evaluation/rolling_horizon_metrics.csv`
- Per-Origin Summary CSV: `/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/rolling_evaluation/rolling_origin_summary.csv`
- Horizon Performance Plot: `/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/rolling_evaluation/rolling_horizon_comparison.png`
