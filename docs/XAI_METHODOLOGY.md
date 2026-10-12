# Explainable AI (XAI) Methodology

This document provides a comprehensive academic guide to the explainability methods (**SHAP** and **LIME**) implemented in our platform to understand and interpret our primary operational forecasting model (XGBoost).

---

## 1. Shapley Additive exPlanations (SHAP)

### A. What it is and Why it is Used
**SHAP** is a game-theoretic approach to explaining the output of any machine learning model. It connects optimal credit allocation with local explanations using **Shapley values** from cooperative game theory. 
In our context:
- The **"game"** is predicting hospital resource demand.
- The **"players"** are the input features (e.g. `lag_1`, `rolling_mean_7`, `day_of_week`).
- The **"payout"** is the difference between the model's actual prediction and its baseline expected value (average prediction over the training set).

SHAP is mathematically unique because it is the only local feature attribution method that satisfies four fundamental properties: **Efficiency**, **Symmetry**, **Dummy (Null Player)**, and **Additivity**.

### B. Global vs. Local Interpretation
- **Global Interpretation:** Measures feature importance across the entire dataset. For each feature, we compute the mean of the absolute SHAP values across all samples:
  $$\text{Global Importance}_j = \frac{1}{N} \sum_{i=1}^{N} |\phi_j^{(i)}|$$
  This tells us which features are most influential overall.
- **Local Interpretation:** Explains a single daily prediction. The prediction is represented as the sum of feature attributions added to the base value:
  $$f(x) = \phi_0 + \sum_{j=1}^{M} \phi_j$$
  - **Positive SHAP value ($\phi_j > 0$):** The feature value pushed the prediction **higher** than the model's baseline average.
  - **Negative SHAP value ($\phi_j < 0$):** The feature value pushed the prediction **lower** than the model's baseline average.

---

## 2. Local Interpretable Model-Agnostic Explanations (LIME)

### A. What it is and Why it is Used
**LIME** is a model-agnostic method that explains individual predictions by approximating the complex machine learning model locally with an interpretable surrogate model (usually a simple Ridge linear regressor).

### B. How the Local Surrogate works
1. **Perturbation:** LIME selects the instance to explain ($x$) and generates a perturbed dataset of samples around it.
2. **Prediction:** It retrieves model predictions for these perturbed samples.
3. **Weighting:** It weights the perturbed samples based on their proximity to the original instance using a distance metric (similarity kernel).
4. **Local Fit:** It trains a simple linear model on these weighted perturbations.
5. **Explanation:** The weights (coefficients) of the local linear model represent the feature contributions for that specific instance.

---

## 3. Comparative Summary: SHAP vs. LIME

| Feature / Property | SHAP | LIME |
| :--- | :--- | :--- |
| **Mathematical Basis** | Cooperative Game Theory (Shapley Values) | Local Linear Surrogate Regression |
| **Global Explanations** | Yes (Built by aggregating local attributions) | No (LIME is strictly local) |
| **Consistency** | Guaranteed (Satisfies game-theoretic axioms) | Not guaranteed (Heuristic perturbations can cause instability) |
| **Execution Speed** | Moderate to Slow (Calculates marginal contributions) | Fast (Builds simple local linear models) |
| **Interpretation** | How much the feature value shifted the prediction relative to the average | How the prediction changes if we make small adjustments around this sample |

Neither model is universally superior. **SHAP** provides solid theoretical guarantees and consistent global/local mappings, whereas **LIME** is highly intuitive for local perturbations and executes faster.

---

## 4. Critical Academic Interpretations (For Viva)

### A. Association vs. Causation
During your viva presentation, you must be extremely careful not to confuse model association with real-world causality:
> [!WARNING]
> **Important Distinction:**
> If SHAP indicates that `occupied_beds_lag_1` has a positive contribution of `+0.31` beds, **do NOT say:** *"Yesterday's high bed occupancy causes today's bed demand to increase."*
> **Instead, say:** *"Yesterday's high bed occupancy had a positive association in the model, pushing the model's prediction higher relative to its average baseline."*
> SHAP and LIME explain the **model's internal decision logic**, not the physical causal links of the hospital workflow.

### B. Feature Importance Consistency
You might notice that the global SHAP rankings differ from XGBoost's built-in feature importances:
- **XGBoost Built-in Importance** measures **gain** (the reduction in training loss split criteria). If a feature is used in early tree splits to partition large groups, it gets a high score, even if its final numeric contribution is small.
- **SHAP Global Importance** measures the average absolute output shift in target units (beds/patients).
Because they measure completely different concepts, their rankings will not be identical, which is expected and methodologically sound.

### C. Small-Data Limitations
With only 180 observations, feature rankings are highly sensitive to small changes in data. A single abnormal day can significantly skew the explanations. Therefore:
1. Explainability metrics must be interpreted as descriptive summaries of the model's current behavior rather than universal hospital truths.
2. Explanations should not be generalized to other facilities.
