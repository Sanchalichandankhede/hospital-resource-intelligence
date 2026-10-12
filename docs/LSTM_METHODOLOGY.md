# LSTM Forecasting Methodology

This document provides a comprehensive academic explanation of the **Long Short-Term Memory (LSTM)** deep-learning forecasting model implemented in the platform, covering its architecture, training, and critical limitations.

---

## 1. What is an LSTM?
A **Long Short-Term Memory (LSTM)** network is a specialized type of Recurrent Neural Network (RNN) designed to process sequential data and learn long-term dependencies. 

Traditional RNNs suffer from the **vanishing gradient problem**, where gradients shrink exponentially during backpropagation through time, preventing the model from learning patterns from older time steps. LSTMs solve this by introducing a **Cell State** ($c_t$) that acts as a conveyer belt running straight down the sequence, and three specialized multiplicative **gates** that control information flow:

* **Forget Gate ($f_t$):** Controls how much of the previous cell state should be discarded.
  $$f_t = \sigma(W_f \cdot [h_{t-1}, x_t] + b_f)$$
* **Input Gate ($i_t$):** Controls what new information from the current input should be stored in the cell state.
  $$i_t = \sigma(W_i \cdot [h_{t-1}, x_t] + b_i)$$
  $$\tilde{c}_t = \tanh(W_c \cdot [h_{t-1}, x_t] + b_c)$$
* **Cell State Update ($c_t$):**
  $$c_t = f_t \odot c_{t-1} + i_t \odot \tilde{c}_t$$
* **Output Gate ($o_t$):** Controls what information from the updated cell state should be output as the hidden state ($h_t$).
  $$o_t = \sigma(W_o \cdot [h_{t-1}, x_t] + b_o)$$
  $$h_t = o_t \odot \tanh(c_t)$$

*(where $\sigma$ represents the sigmoid function, and $\odot$ represents element-wise multiplication).*

---

## 2. Why is LSTM Suitable for Hospital Resource Demand?
Hospital bed occupancy and patient arrivals are time-dependent sequences containing:
- **Autocorrelation:** Today's bed occupancy depends heavily on yesterday's occupancy.
- **Weekly Seasonality:** Admissions fluctuate between weekends and weekdays.
LSTMs are mathematically capable of maintaining an internal "memory" state of these temporal cycles, making them highly effective sequence modelers.

---

## 3. Sequence Input Structure (Sequence-to-Sequence)
To forecast the next 7 days, we formulate a supervised learning sequence mapping:
* **Input Window (Sequence Length $T = 7$):** The preceding 7 days of daily occupied counts/arrivals:
  $$X = [y_{t-7}, y_{t-6}, \dots, y_{t-1}]$$
* **Output Horizon (Size = 7):** The subsequent 7 days of daily demand (the forecast horizon):
  $$\hat{y} = [\hat{y}_{t}, \hat{y}_{t+1}, \dots, \hat{y}_{t+6}]$$

By using a 7-day input window, the network learns to read a full weekly cycle and project the immediate 7 days ahead.

---

## 4. Model Architecture
Due to our small dataset, we designed a lightweight network to minimize parameter count:
1. **Input Layer:** Sequence of shape `(Batch Size, 7, 1)`.
2. **LSTM Layer:** 1 layer with `hidden_size=16` containing a single LSTM cell. batch_first is set to True.
3. **Dropout Layer:** A dropout rate of `0.2` applied to prevent overfitting by randomly setting 20% of activation weights to zero during training.
4. **Fully Connected (FC) Output Layer:** A linear layer of shape `(16, 7)` mapping the final hidden state of the LSTM to the 7-day prediction vector.

---

## 5. Training and Optimization
* **Loss Function:** Mean Squared Error (MSE Loss) representing the squared differences between predicted and actual demand.
* **Optimizer:** Adam optimizer (with a learning rate of `0.005`) for adaptive gradient descent.
* **Chronological Validation Split:**
  - Training set: First 153 days (yielding 140 training sequences).
  - Validation set: Remaining 20 days (yielding 14 sequences).
* **Early Stopping & Checkpointing:** We check the validation MSE loss at the end of each epoch. If the validation loss fails to decrease for 20 consecutive epochs, training terminates early to prevent overfitting. The model weight state with the lowest validation loss is checkpointed as `best_lstm.pth`.

---

## 6. Critical Limitations (For Viva discussion)
During your viva presentation, it is vital to discuss the following limitations:
1. **Sparsity & Small Data Constraints:** With only 180 days of daily data, our training pipeline generates only **140 training sequences**. Neural networks typically require thousands of sequence samples to generalize.
2. **Overfitting:** Because the network has more parameters relative to the size of the dataset, it is prone to memorizing the training sequence rather than learning underlying temporal structures. This explains why **XGBoost** (a simpler tree-based model) achieved lower error metrics on the test set.
3. **No Magical "Deep Learning Advantage":** In data science, deep learning is not a magic solution. For small, sparse time-series, linear models, Prophet, or boosted trees (XGBoost) are mathematically and practically more robust.
