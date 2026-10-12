import torch
import torch.nn as nn

class LSTMRegressor(nn.Module):
    def __init__(self, input_size=1, hidden_size=16, num_layers=1, dropout=0.2, horizon=7):
        super(LSTMRegressor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM Layer
        # batch_first=True makes input shape: (batch, seq_len, input_size)
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        
        # Dropout Layer
        self.dropout = nn.Dropout(p=dropout)
        
        # Fully Connected Output Layer (predicts next 'horizon' days)
        self.fc = nn.Linear(hidden_size, horizon)
        
    def forward(self, x):
        # Initialize hidden and cell states with zeros
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        # Forward pass through LSTM
        # out shape: (batch_size, seq_len, hidden_size)
        out, (hn, cn) = self.lstm(x, (h0, c0))
        
        # Extract the hidden state of the final time step
        # out[:, -1, :] shape: (batch_size, hidden_size)
        last_out = out[:, -1, :]
        
        # Apply dropout
        last_out = self.dropout(last_out)
        
        # Fully connected layer maps to 7 outputs
        # prediction shape: (batch_size, horizon)
        prediction = self.fc(last_out)
        return prediction
