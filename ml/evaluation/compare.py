import os
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

def safe_mape(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    non_zero = y_true != 0
    if not np.any(non_zero):
        return 0.0
    return np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero]))

def check_comparability(prophet_path, xgboost_path, lstm_path):
    """
    Verifies that the date indices and actual target values are identical.
    """
    df_p = pd.read_csv(prophet_path)
    df_x = pd.read_csv(xgboost_path)
    df_l = pd.read_csv(lstm_path)
    
    # Sort by date
    df_p = df_p.sort_values('date').reset_index(drop=True)
    df_x = df_x.sort_values('date').reset_index(drop=True)
    df_l = df_l.sort_values('date').reset_index(drop=True)
    
    # 1. Check lengths
    if not (len(df_p) == len(df_x) == len(df_l) == 7):
        return False, "Evaluation periods have different lengths (expected 7 days)."
        
    # 2. Check date strings
    if not (df_p['date'].equals(df_x['date']) and df_p['date'].equals(df_l['date'])):
        return False, "Dates do not match across forecasts."
        
    # 3. Check actual target values
    if not (np.allclose(df_p['actual'], df_x['actual']) and np.allclose(df_p['actual'], df_l['actual'])):
        return False, "Actual target values do not match across forecasts."
        
    return True, (df_p, df_x, df_l)

def evaluate_model(df, model_name, target_name):
    actual = df['actual']
    predicted = df['predicted']
    
    mae = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    mape = safe_mape(actual, predicted)
    
    errors = np.abs(actual - predicted)
    min_err = np.min(errors)
    max_err = np.max(errors)
    std_err = np.std(errors)
    
    return {
        'target': target_name,
        'model': model_name,
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'min_abs_error': min_err,
        'max_abs_error': max_err,
        'std_abs_error': std_err
    }

def run_comparison():
    interim_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/interim"
    eval_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/ml/evaluation"
    
    targets = {
        'icu': {
            'target_name': 'icu_occupancy',
            'prophet': os.path.join(interim_dir, 'prophet_icu_forecast.csv'),
            'xgboost': os.path.join(interim_dir, 'xgboost_icu_forecast.csv'),
            'lstm': os.path.join(interim_dir, 'lstm_icu_forecast.csv')
        },
        'ed': {
            'target_name': 'ed_arrivals',
            'prophet': os.path.join(interim_dir, 'prophet_ed_forecast.csv'),
            'xgboost': os.path.join(interim_dir, 'xgboost_ed_forecast.csv'),
            'lstm': os.path.join(interim_dir, 'lstm_ed_forecast.csv')
        }
    }
    
    results = []
    
    for key, paths in targets.items():
        is_comparable, result_or_err = check_comparability(
            paths['prophet'], paths['xgboost'], paths['lstm']
        )
        if not is_comparable:
            print(f"Error checking comparability for {key}: {result_or_err}")
            continue
            
        df_p, df_x, df_l = result_or_err
        
        # Evaluate each
        results.append(evaluate_model(df_p, 'Prophet', paths['target_name']))
        results.append(evaluate_model(df_x, 'XGBoost', paths['target_name']))
        results.append(evaluate_model(df_l, 'LSTM', paths['target_name']))
        
    df_results = pd.DataFrame(results)
    
    # Calculate ranks grouped by target
    df_results['mae_rank'] = df_results.groupby('target')['mae'].rank(ascending=True, method='min').astype(int)
    df_results['rmse_rank'] = df_results.groupby('target')['rmse'].rank(ascending=True, method='min').astype(int)
    
    # Save comparison CSV
    os.makedirs(eval_dir, exist_ok=True)
    csv_path = os.path.join(eval_dir, 'model_comparison.csv')
    df_results.to_csv(csv_path, index=False)
    
    print("Consolidated Model Comparison Results:")
    print(df_results[['target', 'model', 'mae', 'rmse', 'mape', 'mae_rank', 'rmse_rank']])
    print(f"\nSaved consolidated metrics to: {csv_path}")

if __name__ == "__main__":
    run_comparison()
