import numpy as np
from sklearn.preprocessing import MinMaxScaler

def scale_data(train_data, test_data):
    """
    Fits a MinMaxScaler strictly on the train data, and applies it to transform both train and test.
    Returns scaled train_data, scaled test_data, and the fitted scaler.
    """
    scaler = MinMaxScaler()
    # Reshape data to 2D for scaler
    train_reshaped = train_data.reshape(-1, 1)
    test_reshaped = test_data.reshape(-1, 1)
    
    # Fit strictly on train
    scaler.fit(train_reshaped)
    
    train_scaled = scaler.transform(train_reshaped).flatten()
    test_scaled = scaler.transform(test_reshaped).flatten()
    return train_scaled, test_scaled, scaler

def create_sequences(data, seq_len=7, horizon=7):
    """
    Creates input sequences (length seq_len) and target outputs (length horizon) from a 1D array.
    Returns:
      X: shape (N_samples, seq_len, 1)
      y: shape (N_samples, horizon)
    """
    X = []
    y = []
    # Loop up to the point where the last target sequence fits
    for i in range(len(data) - seq_len - horizon + 1):
        X.append(data[i : i + seq_len])
        y.append(data[i + seq_len : i + seq_len + horizon])
    return np.array(X)[..., np.newaxis], np.array(y)
