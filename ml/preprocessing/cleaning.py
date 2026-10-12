import os
import pandas as pd
import numpy as np

def clean_nhs_beds(file_path, output_path):
    """
    Cleans the monthly NHS England bed publication Excel sheet.
    Renames columns to snake_case, parses months, and saves to CSV.
    """
    print(f"Cleaning NHS Beds data from: {file_path}")
    # Read Excel, skipping metadata header rows
    df = pd.read_excel(file_path, sheet_name='TS - All Acutes', header=12)
    
    # Remove metadata columns and empty rows
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df = df.dropna(subset=['Month'])
    
    # Clean column names to snake_case
    def rename_col(col):
        col_clean = str(col).lower().strip()
        col_clean = col_clean.replace('&', '_and_')
        col_clean = col_clean.replace(' ', '_')
        col_clean = col_clean.replace('__', '_')
        col_clean = col_clean.replace('+', '_plus')
        col_clean = col_clean.replace('.', '_')
        col_clean = col_clean.replace('%', 'pct')
        col_clean = col_clean.replace('(', '').replace(')', '')
        # Handle duplicate columns like '7 or more days.1'
        if 'or_more_days_1' in col_clean:
            col_clean = col_clean.replace('or_more_days_1', 'or_more_days_pct')
        elif 'or_more_days' in col_clean:
            # Check if it was percentage in row 11
            if 'pct' in col_clean or 'percent' in col_clean:
                col_clean = col_clean + '_pct'
        return col_clean.replace('__', '_')

    df.columns = [rename_col(c) for c in df.columns]
    
    # Check for duplicate column names and resolve them
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols == dup] = [f"{dup}_{i}" if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols

    # Parse Month (e.g. "December 2020" -> "2020-12-01")
    df['date'] = pd.to_datetime(df['month'], format='%B %Y')
    df = df.sort_values('date')
    
    # Keep date first and drop month column
    df = df.drop(columns=['month'])
    cols = ['date'] + [c for c in df.columns if c != 'date']
    df = df[cols]
    
    # Linear interpolation for any missing values in long-stay columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].interpolate(method='linear').fillna(method='bfill')
    
    # Save to processed folder
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"  Saved clean NHS Beds data to: {output_path} ({len(df)} rows)")
    return df

def find_densest_window(df, date_col, value_col, window_days=180):
    """
    Finds the continuous time window of size `window_days` with the maximum sum of values.
    Returns the start and end dates.
    """
    df = df.sort_values(date_col)
    # Set index for rolling sum
    df_temp = df.set_index(date_col)
    # Reindex to daily to ensure continuous dates for rolling
    full_range = pd.date_range(start=df_temp.index.min(), end=df_temp.index.max(), freq='D')
    df_temp = df_temp.reindex(full_range, fill_value=0)
    
    # Rolling sum of window
    rolling_sum = df_temp[value_col].rolling(window=f"{window_days}D", closed='right').sum()
    best_end_date = rolling_sum.idxmax()
    best_start_date = best_end_date - pd.Timedelta(days=window_days - 1)
    
    print(f"  Densest {window_days}-day window found: {best_start_date.date()} to {best_end_date.date()} (sum: {rolling_sum.max()})")
    return best_start_date, best_end_date

def clean_daily_demand(file_path, output_path, value_col, is_icu=True, window_days=180):
    """
    Cleans daily demand datasets.
    Reindexes to fill missing calendar days with 0, isolates the densest continuous window of activity, and saves to CSV.
    """
    print(f"Cleaning Daily Demand data from: {file_path}")
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Reindex to a complete daily calendar range to handle gaps
    min_date = df['date'].min()
    max_date = df['date'].max()
    full_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    
    df = df.set_index('date').reindex(full_dates, fill_value=0).reset_index().rename(columns={'index': 'date'})
    
    # Find the densest window of activity to train models on
    start_date, end_date = find_densest_window(df, 'date', value_col, window_days=window_days)
    
    # Crop to the densest window
    df_clean = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
    
    # Reset index and save
    df_clean.to_csv(output_path, index=False)
    print(f"  Saved clean daily data to: {output_path} ({len(df_clean)} rows)")
    return df_clean

if __name__ == "__main__":
    # Test/Run locally if invoked directly
    raw_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/raw"
    proc_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed"
    
    clean_nhs_beds(
        os.path.join(raw_dir, "Beds-publication-Timeseries-March-2020-July-2026.xlsx"),
        os.path.join(proc_dir, "beds_monthly_processed.csv")
    )
    clean_daily_demand(
        os.path.join(raw_dir, "icu_daily_demand.csv"),
        os.path.join(proc_dir, "icu_daily_processed.csv"),
        'occupied_beds',
        is_icu=True,
        window_days=180
    )
    clean_daily_demand(
        os.path.join(raw_dir, "ed_daily_demand.csv"),
        os.path.join(proc_dir, "ed_daily_processed.csv"),
        'arrivals',
        is_icu=False,
        window_days=180
    )
