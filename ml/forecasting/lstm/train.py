import os
import json
import random
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

from preprocessing import scale_data, create_sequences
from model import LSTMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Set random seeds for reproducibility
def set_seeds(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def safe_mape(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    non_zero = y_true != 0
    if not np.any(non_zero):
        return 0.0
    return np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero]))

def train_lstm_model(input_path, output_path, target_col, forecast_horizon=7, seq_len=7, model_name="icu"):
    """
    Preprocesses data, splits into train/validation/test chronologically,
    trains the LSTM model in PyTorch with early stopping and checkpointing,
    and returns metrics and loss history.
    """
    print(f"\n--- Training LSTM for {model_name} (Target: {target_col}) ---")
    set_seeds()
    
    # 1. Load Data
    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    data = df[target_col].values.astype(np.float32)
    
    # 2. Chronological Splits
    # Test set is the last forecast_horizon days (7 days)
    test_data = data[-forecast_horizon:]
    train_val_data = data[:-forecast_horizon]
    
    # Scale data (Fit strictly on train_val)
    train_val_scaled, test_scaled, scaler = scale_data(train_val_data, test_data)
    
    # Within train_val, split into Train (first 153 days) and Validation (remaining 20 days)
    # This aligns with the 180-day overall structure
    train_data_scaled = train_val_scaled[:-20]
    val_data_scaled = train_val_scaled[-27:] # Include historical window of 7 days before val start
    
    # Generate Sequences
    X_train, y_train = create_sequences(train_data_scaled, seq_len=seq_len, horizon=forecast_horizon)
    X_val, y_val = create_sequences(val_data_scaled, seq_len=seq_len, horizon=forecast_horizon)
    
    # Number of sequences generated
    print(f"  Training sequences: {len(X_train)}")
    print(f"  Validation sequences: {len(X_val)}")
    
    # Convert to PyTorch Tensors
    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32)
    X_val_t = torch.tensor(X_val, dtype=torch.float32)
    y_val_t = torch.tensor(y_val, dtype=torch.float32)
    
    # DataLoaders
    batch_size = 16
    train_dataset = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False) # Chronological sequences
    
    # 3. Model Definition
    model = LSTMRegressor(
        input_size=1,
        hidden_size=16,
        num_layers=1,
        dropout=0.2,
        horizon=forecast_horizon
    )
    
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005)
    
    # 4. Training Loop with Early Stopping & Checkpointing
    epochs = 150
    best_val_loss = float('inf')
    early_stopping_patience = 20
    epochs_no_improve = 0
    
    train_losses = []
    val_losses = []
    
    checkpoint_dir = "checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, f"best_{model_name}_lstm.pth")
    
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_train_loss = 0.0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            epoch_train_loss += loss.item() * X_batch.size(0)
            
        epoch_train_loss /= len(X_train_t)
        train_losses.append(epoch_train_loss)
        
        # Validation Loss
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val_t)
            epoch_val_loss = criterion(val_outputs, y_val_t).item()
            val_losses.append(epoch_val_loss)
            
        if epoch % 10 == 0 or epoch == 1:
            print(f"  Epoch {epoch:03d}/{epochs:03d} | Train Loss: {epoch_train_loss:.6f} | Val Loss: {epoch_val_loss:.6f}")
            
        # Checkpoint (Save model if val loss improves)
        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            torch.save(model.state_dict(), checkpoint_path)
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            
        # Early Stopping
        if epochs_no_improve >= early_stopping_patience:
            print(f"  Early stopping triggered at epoch {epoch}. Best Val Loss: {best_val_loss:.6f}")
            break
            
    # Load best model for evaluation
    print(f"  Loading best model from {checkpoint_path}")
    model.load_state_dict(torch.load(checkpoint_path))
    model.eval()
    
    # 5. Forecasting the Test Window
    # The input to forecast the test window is the last seq_len days of train_val data
    test_input_raw = train_val_data[-seq_len:]
    test_input_scaled = scaler.transform(test_input_raw.reshape(-1, 1)).flatten()
    
    test_input_t = torch.tensor(test_input_scaled, dtype=torch.float32).view(1, seq_len, 1)
    
    with torch.no_grad():
        test_pred_scaled = model(test_input_t).numpy().flatten()
        
    # Inverse Scale
    test_pred_raw = scaler.inverse_transform(test_pred_scaled.reshape(-1, 1)).flatten()
    # Clip negative values
    test_pred_raw = np.clip(test_pred_raw, 0, None)
    
    # 6. Calculate Metrics
    y_test_true = test_data
    mae = float(mean_absolute_error(y_test_true, test_pred_raw))
    rmse = float(np.sqrt(mean_squared_error(y_test_true, test_pred_raw)))
    mape = float(safe_mape(y_test_true, test_pred_raw))
    
    print(f"  Test Metrics - MAE: {mae:.4f}, RMSE: {rmse:.4f}, MAPE: {mape:.4f}")
    
    # Save predictions
    test_dates = df['date'].iloc[-forecast_horizon:]
    predictions_df = pd.DataFrame({
        'date': test_dates,
        'actual': y_test_true,
        'predicted': test_pred_raw
    })
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    predictions_df.to_csv(output_path, index=False)
    print(f"  Saved predictions to: {output_path}")
    
    return {
        'metrics': {
            'mae': mae,
            'rmse': rmse,
            'mape': mape
        },
        'loss_history': {
            'train': train_losses,
            'val': val_losses
        }
    }

if __name__ == "__main__":
    proc_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed"
    interim_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/interim"
    metrics_path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/ml/forecasting/lstm/metrics.json"
    loss_history_path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/ml/forecasting/lstm/loss_history.json"
    
    icu_results = train_lstm_model(
        os.path.join(proc_dir, "icu_daily_processed.csv"),
        os.path.join(interim_dir, "lstm_icu_forecast.csv"),
        target_col='occupied_beds',
        seq_len=7,
        model_name="icu"
    )
    
    ed_results = train_lstm_model(
        os.path.join(proc_dir, "ed_daily_processed.csv"),
        os.path.join(interim_dir, "lstm_ed_forecast.csv"),
        target_col='arrivals',
        seq_len=7,
        model_name="ed"
    )
    
    metrics = {
        'icu': icu_results['metrics'],
        'ed': ed_results['metrics']
    }
    
    loss_histories = {
        'icu': icu_results['loss_history'],
        'ed': ed_results['loss_history']
    }
    
    # Save Metrics JSON
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=4)
    print(f"\nSaved metrics to: {metrics_path}")
    
    # Save Loss Histories JSON
    with open(loss_history_path, 'w') as f:
        json.dump(loss_histories, f, indent=4)
    print(f"Saved loss histories to: {loss_history_path}")
