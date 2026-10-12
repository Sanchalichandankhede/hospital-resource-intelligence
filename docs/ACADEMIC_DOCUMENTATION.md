# Multi-Resource Forecasting, Validation & Model Rigor

This documentation explains the mathematical, statistical, and operational foundations of the Multi-Resource Forecasting Expansion, including the separation of raw forecasts and operational quantization.

---

## 1. Forecast vs. Simulation Targets

We classify the seven capacity targets under two distinct categories to maintain scientific transparency:

### A. Real / Source-Derived Forecasting Target
* **ICU Demand (Beds):** Genuinely forecast using independent time-series models. Trained directly on historical actual daily telemetry (`icu_occupancy`) from [`icu_daily_processed.csv`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/data/processed/icu_daily_processed.csv).

### B. Derived / Simulated Projections
These resources do not have independent historical daily target observations and are calculated by dynamically applying operational hospital planning assumptions to the core predictions:
* **General Bed Demand:** Mapped to monthly beds baseline statistics.
* **Emergency Bed Demand:** Mapped to daily Emergency Department patient arrivals predictions.
* **Oxygen Demand:** Mapped to bed occupancy.
* **Blood Demand:** Mapped to daily Emergency arrivals.
* **Staff Requirement:** Mapped to bed occupancy.
* **Ambulance Requirement:** Mapped to Emergency arrivals.

---

## 2. Dynamic Formulation & Assumptions

The mathematical formulas mapping core forecasts to simulated targets are:

$$\text{General Bed Demand} = 18.0 + (\text{ICU Bed Prediction} \times 2.0)$$
$$\text{Emergency Bed Demand} = \text{ED Arrivals Prediction} \times 0.25$$
$$\text{Oxygen Demand (Liters)} = (\text{ICU Bed Prediction} \times 15.0) + (\text{Emergency Bed Prediction} \times 5.0)$$
$$\text{Blood Demand (Units)} = \text{ED Arrivals Prediction} \times 0.20$$
$$\text{Staff Requirement (FTE)} = (\text{ICU Bed Prediction} \times 1.5) + (\text{Emergency Bed Prediction} \times 0.5)$$
$$\text{Ambulance Requirement (Cars)} = \text{ED Arrivals Prediction} \times 0.15$$

### Why These Assumptions Are Necessary
Hospitals lack real-time sensors for every item. In the absence of direct inventory datasets, resource requirement projections must be estimated using standard administrative multipliers linked to core patient volumes.

---

## 3. Continuous Forecasts vs. Physical Operational Resources

### Why ML Forecasts Can Be Fractional
Machine learning regression models (such as XGBoost, Prophet, and LSTMs) predict output targets as continuous real numbers ($x \in \mathbb{R}$). These predictions represent statistical expected values (e.g. an expectation of `0.45` occupied beds or `0.68` full-time equivalent staffing units).

### The Concept of Operational Quantization
While a fractional statistical output is useful for mathematical evaluations, it cannot be physically allocated (e.g., a hospital cannot admit a patient to `0.45` of a physical bed). Therefore, the system enforces a clean separation between:
1. **Raw Model Forecast:** Continuous mathematical estimate representing resource load equivalents (e.g. `0.45 bed-equivalents`, `0.68 FTE`).
2. **Operational Resource Requirement:** Discrete integer values representing the actual count of physical resources needed for capacity planning (e.g. `1 bed`, `1 staff member`).

### Ceiling Mapping Rule for Physical Resources
For physical count assets (beds, blood packages, staff, ambulances), any positive fractional demand requires rounding up to ensure safe margins. We apply the ceiling function:

$$\text{Operational Requirement} = \begin{cases} 0 & \text{if forecast } \le 0 \\ \lceil \text{forecast} \rceil & \text{if forecast } > 0 \end{cases}$$

This ensures that a demand of `0.01` beds allocates `1` whole bed rather than `0` (which would cause a shortage), while preserving `0` requirements when predicted demand is zero or negative.

*Oxygen remains continuous because it is measured in continuous volume (Liters) rather than individual discrete items.*

---

## 4. Model Evaluation Safety & Metrics

### Why Raw Predictions Must Remain Unchanged
To accurately validate ML model parameters, evaluation metrics (MAE, RMSE, MAPE) must match the raw continuous outputs against raw actual values. Using quantized integers for metrics calculation would distort the error metrics, introducing false steps that ruin evaluation integrity.

$$\text{MAE} = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$

Here, $\hat{y}_i$ is the raw predicted value, not the quantized operational requirement.

*Evaluation metrics are only computed for targets where actual historical values exist (ICU Demand).*

---

## 5. Capacity Management, Shortages & Explainability Attributions

### Operational Shortage Planning
To check shortages and assign risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), the platform compares available capacities against the **operational whole-number requirements** (for discrete targets) or continuous requirements (for Oxygen).
* **Operational Gap** is defined as:
  $$\text{Operational Gap} = \text{Capacity} - \text{Operational Requirement}$$
* A negative gap indicates a physical deficit (shortage), triggering alerts and recommendations.

### Explainability (XAI) Attribution Disclaimers
Attribution coefficients (such as SHAP feature importance or LIME coefficients) evaluate the mathematical inputs driving the **raw machine learning outputs** (attributing contribution weights to lag inputs). Ceil operations are planning transformations applied *after* the model prediction, and are not factored into the model feature weights.
