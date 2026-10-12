# Model Comparison and Evaluation Report

This document reports the comparative performance of the three forecasting models (**Prophet**, **XGBoost**, and **LSTM**) trained to predict daily hospital resource demand for the next **7 days**.

---

## 1. Metrics Comparison Table
All metrics were evaluated using chronological splitting on the exact same unseen test window (final 7 days of their respective 180-day continuous period):

* **ICU Test Period:** 2137-10-11 to 2137-10-17
* **ED Test Period:** 2148-01-19 to 2148-01-25

| Target Variable | Model | MAE | RMSE | MAPE | Min Abs Error | Max Abs Error | Std Dev of Error |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ICU Occupancy** | Prophet | 0.6198 | 0.6339 | 67.20% | 0.2030 | 1.1399 | 0.3541 |
| **ICU Occupancy** | **XGBoost** | **0.5940** | **0.6192** | **65.90%** | **0.1804** | **1.2185** | **0.3702** |
| **ICU Occupancy** | LSTM | 0.7164 | 0.7477 | 80.37% | 0.3205 | 1.1891 | 0.3204 |
| | | | | | | | |
| **ED Arrivals** | Prophet | 0.3170 | 0.5042 | 93.47% | 0.1030 | 1.1399 | 0.3802 |
| **ED Arrivals** | **XGBoost** | **0.2891** | 0.5293 | 99.02% | **0.0210** | 1.2891 | 0.4429 |
| **ED Arrivals** | LSTM | 0.3049 | **0.5042** | 93.96% | 0.1042 | **1.1042** | **0.3601** |

---

## 2. Model Rankings Matrix

| Target Variable | Metric | 1st Place | 2nd Place | 3rd Place |
| :--- | :---: | :---: | :---: | :---: |
| **ICU Occupancy** | MAE | XGBoost (0.5940) | Prophet (0.6198) | LSTM (0.7164) |
| **ICU Occupancy** | RMSE | XGBoost (0.6192) | Prophet (0.6339) | LSTM (0.7477) |
| | | | | |
| **ED Arrivals** | MAE | XGBoost (0.2891) | LSTM (0.3049) | Prophet (0.3170) |
| **ED Arrivals** | RMSE | LSTM (0.5042) | Prophet (0.5042) | XGBoost (0.5293) |

---

## 3. Best Model Determinations

### A. ICU Bed Occupancy
* **Best Model:** **XGBoost**
* **Rationale:** XGBoost achieved the lowest MAE (0.5940 beds) and the lowest RMSE (0.6192 beds) among all evaluated models. It is the clear, consistent winner across both metrics.

### B. ED Arrivals
* **Best Model (Conflict):** **XGBoost** (on MAE) vs. **LSTM / Prophet** (on RMSE).
* **Analysis of Conflict:**
  - **XGBoost** achieves the lowest Mean Absolute Error (**MAE = 0.2891**).
  - **LSTM** and **Prophet** achieve the lowest Root Mean Squared Error (**RMSE = 0.5042**).
  - This metric conflict occurs because XGBoost makes very small errors on most days but commits a single larger error on one day (maximum absolute error of 1.2891 patients). Because RMSE squares the errors before averaging, it heavily penalizes this single large deviation.
  - **Operational Selection Decision:** For resource planning, **MAE** is preferred because it represents the average absolute error directly in patient counts. Under-predicting or over-predicting ED visits is best measured on average. Therefore, we select **XGBoost** as our primary operational model, but document this conflict as a project design decision.

---

## 4. Research Conclusions
* **ICU Occupancy:** For ICU occupancy, XGBoost achieved the lowest MAE and RMSE among the evaluated models, showing the value of incorporating supervised lag and rolling window features.
* **ED Arrivals:** For ED arrivals, XGBoost achieved the lowest MAE, while Prophet and LSTM achieved equal RMSE values. The deep learning LSTM model did not outperform the simpler XGBoost baseline, primarily due to the limited training data size.
