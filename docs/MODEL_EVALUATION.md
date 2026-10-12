# Model Evaluation Guide (Viva Preparation)

This guide translates our technical model evaluation results into simple, accessible explanations to help you succeed in your B.Tech project viva presentation.

---

## 1. Why do we compare different models?
In machine learning, there is no single model that works best for every problem (known as the *No Free Lunch Theorem*).
We compare:
1. **Univariate statistical models (Prophet):** Excellent at detecting baseline weekly/monthly seasonal patterns but cannot utilize external features.
2. **Supervised machine learning (XGBoost):** Excellent at exploiting short-term numerical patterns (lags, rolling averages) and highly robust on small datasets.
3. **Deep learning sequence networks (LSTM):** Capable of learning complex, non-linear hidden states but require massive training datasets to generalize.

By evaluating all three, we ensure our selection is based on empirical, objective measurements rather than arbitrary choice.

---

## 2. What do the error metrics mean?

### A. Mean Absolute Error (MAE)
* **Simple Definition:** The average size of the model's errors, regardless of direction (under- or over-predicting).
* **Formula:**
  $$\text{MAE} = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$
* **Meaning in our Project:** An ICU MAE of `0.5940` means that, on average, our model's daily bed occupancy predictions are off by approximately **0.6 beds**.
* **Why it's preferred for managers:** It is expressed directly in the physical unit of the resource (beds or patients), making it easy to interpret.

### B. Root Mean Squared Error (RMSE)
* **Simple Definition:** The square root of the average of squared errors.
* **Formula:**
  $$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$$
* **Meaning in our Project:** Because it squares the errors before averaging, RMSE penalizes larger errors much more heavily than smaller errors.
* **Why it's useful:** It tells us if our model is making occasional "critical misses" (large errors) which would be highly dangerous in a hospital setting where a sudden bed shortage can be catastrophic.

---

## 3. Why is chronological testing important?
* **Concept:** We split time-series datasets strictly based on time (e.g. training on the first 173 days, testing on the last 7 days), rather than random shuffling.
* **Why we do it:** Time series observations are ordered. If we randomly shuffle data, we would use tomorrow's data to predict yesterday's data, which is impossible in the real world and leads to **data leakage** (making the model look artificially accurate during testing, only to fail in production).

---

## 4. Why did the Deep Learning LSTM model not win?
* **Core Reason:** **Data size limitations.**
* **Explanation for Examiners:** LSTMs have hundreds or thousands of trainable weights. To adjust these weights without overfitting, deep learning models require thousands of training sequences. Because our demo dataset generated only **140 training sequences**, the LSTM model overfitted the training data and generalized poorly on the unseen 7-day test window, yielding higher error rates than the tree-based XGBoost model.

---

## 5. How did we resolve the metric conflict for ED Arrivals?
* **The Conflict:** XGBoost achieved the best **MAE** (0.2891), but LSTM/Prophet achieved the best **RMSE** (0.5042).
* **Explanation:** XGBoost made tiny errors on 6 days but a single larger error on 1 day. This single larger error was heavily penalized by RMSE's squaring operation.
* **Our Project Decision:** For hospital capacity planning, we prioritize average absolute deviations (MAE) to maintain stable baseline staffing, but document this metric conflict as a strategic project decision.
