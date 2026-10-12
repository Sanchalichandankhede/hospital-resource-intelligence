import os
import pandas as pd

def get_top_shap_features(shap_local_path, num_features=3):
    """
    Reads the local SHAP explanation file and returns a string summary
    of the top features that contributed to the model output.
    """
    if not os.path.exists(shap_local_path):
        return "SHAP local explainability unavailable."
        
    df_shap = pd.read_csv(shap_local_path)
    # df_shap is already sorted by absolute contribution descending
    top_rows = df_shap.head(num_features)
    
    triggers = []
    for _, row in top_rows.iterrows():
        feat = row['feature']
        val = float(row['value'])
        contrib = float(row['contribution'])
        direction = "+" if contrib >= 0 else "-"
        triggers.append(f"{feat}={val:.1f} ({direction}{abs(contrib):.2f})")
        
    return "Model prediction influenced by: " + ", ".join(triggers)

def generate_recommendations():
    alerts_csv = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/alerts/resource_alerts.csv"
    recs_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/recommendations"
    shap_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/explainability/shap"
    
    if not os.path.exists(alerts_csv):
        raise FileNotFoundError(f"Resource alerts file not found at: {alerts_csv}")
        
    df_alerts = pd.read_csv(alerts_csv)
    records = []
    
    for _, row in df_alerts.iterrows():
        date = row['date']
        res = row['resource']
        risk = row['risk_level']
        pred = row['predicted_demand']
        cap = row['available_capacity']
        gap = row['capacity_gap']
        
        # Determine recommendation text
        if risk == "LOW":
            rec = "Current predicted demand is within available capacity. Continue routine monitoring."
            trigger = "Predicted demand matches safe operational thresholds."
        elif risk == "MEDIUM":
            rec = "Predicted demand is approaching available capacity. Review current bed availability and prepare additional capacity if required."
            # Retrieve SHAP explainability triggers if ICU or ED
            shap_path = os.path.join(shap_dir, "icu_local.csv" if "ICU" in res else "ed_local.csv")
            trigger = get_top_shap_features(shap_path, num_features=3)
        elif risk == "HIGH":
            rec = "Predicted demand exceeds available capacity. Review bed allocation and activate appropriate capacity-management procedures."
            # Retrieve SHAP explainability triggers if ICU or ED
            shap_path = os.path.join(shap_dir, "icu_local.csv" if "ICU" in res else "ed_local.csv")
            trigger = get_top_shap_features(shap_path, num_features=3)
        else:
            rec = "Invalid risk state. Perform manual capacity verification."
            trigger = "Unknown risk state."
            
        records.append({
            'date': date,
            'resource': res,
            'risk_level': risk,
            'recommendation': rec,
            'trigger': trigger,
            'model': 'XGBoost'
        })
        
    df_recs = pd.DataFrame(records)
    
    os.makedirs(recs_dir, exist_ok=True)
    recs_csv = os.path.join(recs_dir, "recommendations.csv")
    df_recs.to_csv(recs_csv, index=False)
    
    print(f"\nGenerated {len(df_recs)} resource recommendations. Saved to: {recs_csv}")
    print("\nSample Recommendations Summary:")
    print(df_recs[['date', 'resource', 'risk_level', 'recommendation', 'trigger']])

if __name__ == "__main__":
    generate_recommendations()
