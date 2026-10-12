import React, { useState } from 'react';
import { 
  ResponsiveContainer, 
  LineChart, 
  CartesianGrid, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  Line 
} from 'recharts';
import { ShieldAlert, Award, Calendar, HelpCircle, Activity } from 'lucide-react';

const getUnitLabels = (resourceName) => {
  if (resourceName.includes("ICU") || resourceName.includes("General") || resourceName.includes("Emergency")) {
    return { forecast: "bed-equivalents", operational: "bed", plural: "beds" };
  }
  if (resourceName.includes("Oxygen")) {
    return { forecast: "L", operational: "L", plural: "L" };
  }
  if (resourceName.includes("Blood")) {
    return { forecast: "units", operational: "unit", plural: "units" };
  }
  if (resourceName.includes("Staff")) {
    return { forecast: "FTE", operational: "staff member", plural: "staff" };
  }
  if (resourceName.includes("Ambulance")) {
    return { forecast: "vehicle-equivalents", operational: "ambulance", plural: "ambulances" };
  }
  return { forecast: "units", operational: "unit", plural: "units" };
};

export default function MultiResourceForecasting({ 
  multiData, 
  selectedModel, 
  setSelectedModel 
}) {
  const [selectedResource, setSelectedResource] = useState('ICU Demand');
  
  const resourcesDict = multiData?.resources || {};

  const getRiskBadgeClass = (risk) => {
    const r = risk?.toUpperCase();
    if (r === 'CRITICAL') return 'badge badge-high'; // Red background
    if (r === 'HIGH') return 'badge badge-high'; // Red background
    if (r === 'MEDIUM') return 'badge badge-medium'; // Orange
    return 'badge badge-low'; // Green
  };

  const getRiskColor = (risk) => {
    const r = risk?.toUpperCase();
    if (r === 'CRITICAL') return 'var(--danger-red)';
    if (r === 'HIGH') return 'var(--danger-red)';
    if (r === 'MEDIUM') return 'var(--warning-amber)';
    return 'var(--success-green)';
  };

  const handleCardClick = (resName) => {
    setSelectedResource(resName);
  };

  const activeResourceData = resourcesDict[selectedResource] || null;
  const activePredictions = activeResourceData?.predictions || [];
  
  // Format data for chart rendering
  const chartData = activePredictions.map(p => ({
    ...p,
    displayDate: new Date(p.date).toLocaleDateString(undefined, { 
      month: 'short', 
      day: 'numeric' 
    }),
    Forecast: parseFloat((p.predicted_value !== undefined ? p.predicted_value : p.predicted_demand).toFixed(2)),
    Requirement: p.operational_requirement !== undefined ? p.operational_requirement : Math.ceil(p.predicted_demand),
    Capacity: parseFloat((p.capacity_or_stock !== undefined ? p.capacity_or_stock : p.capacity).toFixed(2))
  }));

  // Get current state metrics (using Peak prediction value across the 7 days)
  const getCardMetrics = (resData) => {
    const preds = resData?.predictions || [];
    if (preds.length === 0) return { peakForecast: 0, operationalRequirement: 0, capacity: 0, operationalGap: 0, maxRisk: 'LOW', isSim: true };
    
    // Find peak prediction
    const peakVal = Math.max(...preds.map(p => p.predicted_value || p.predicted_demand));
    const targetPred = preds.find(p => (p.predicted_value || p.predicted_demand) === peakVal) || preds[0];
    
    return {
      peakForecast: targetPred.predicted_value || targetPred.predicted_demand || peakVal,
      operationalRequirement: targetPred.operational_requirement !== undefined ? targetPred.operational_requirement : Math.ceil(peakVal),
      capacity: targetPred.capacity_or_stock !== undefined ? targetPred.capacity_or_stock : (targetPred.capacity || 0),
      operationalGap: targetPred.operational_gap !== undefined ? targetPred.operational_gap : (targetPred.resource_gap || 0),
      maxRisk: targetPred.risk_level || 'LOW',
      isSim: resData.is_simulated
    };
  };

  // Compile daily rows across all seven resources for the 7-day table
  const tableRows = [];
  const resourceNames = [
    "ICU Demand", "General Bed Demand", "Emergency Bed Demand",
    "Oxygen Demand", "Blood Demand", "Staff Requirement", "Ambulance Requirement"
  ];
  
  if (activePredictions.length > 0) {
    for (let i = 0; i < activePredictions.length; i++) {
      const rowDate = activePredictions[i].date;
      const displayDate = new Date(rowDate).toLocaleDateString(undefined, { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      });
      
      const rowObj = { date: displayDate, rawDate: rowDate };
      
      resourceNames.forEach(res => {
        const resData = resourcesDict[res];
        const predObj = resData?.predictions?.[i] || null;
        rowObj[res] = {
          op: predObj?.operational_requirement !== undefined ? predObj.operational_requirement : 0,
          raw: predObj?.predicted_value !== undefined ? predObj.predicted_value : (predObj?.predicted_demand || 0)
        };
      });
      tableRows.push(rowObj);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Configuration Header */}
      <div className="panel-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: '600' }}>Multi-Resource Forecasting Controls</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Analyze 7-day daily forecasts across multiple operational resources.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: '500' }}>Selected Model:</label>
          <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
            <option value="XGBoost">XGBoost (Operational)</option>
            <option value="Prophet">Prophet</option>
            <option value="LSTM">PyTorch LSTM</option>
          </select>
        </div>
      </div>

      {/* Cards Grid */}
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: '1rem' }}>
        {Object.keys(CAPACITIES).map((resName) => {
          const resData = resourcesDict[resName];
          const metrics = getCardMetrics(resData);
          const isSelected = selectedResource === resName;
          const labels = getUnitLabels(resName);

          return (
            <div 
              key={resName}
              className="summary-card"
              onClick={() => handleCardClick(resName)}
              style={{
                cursor: 'pointer',
                border: isSelected ? '2px solid var(--primary-blue)' : '1px solid var(--border-color)',
                backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.05)' : 'var(--bg-card)',
                transition: 'all 0.2s ease',
                position: 'relative'
              }}
            >
              <div className="card-header">
                <span className="card-label" style={{ color: isSelected ? 'var(--primary-blue-hover)' : 'var(--text-muted)', fontWeight: '700' }}>
                  {resName}
                </span>
                {metrics.isSim ? (
                  <span style={{ fontSize: '0.65rem', color: 'var(--warning-amber)', backgroundColor: 'rgba(245, 158, 11, 0.1)', padding: '0.2rem 0.4rem', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.2)', fontWeight: '600' }}>
                    SIMULATED / PROTOTYPE
                  </span>
                ) : (
                  <span style={{ fontSize: '0.65rem', color: 'var(--success-green)', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '0.2rem 0.4rem', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.2)', fontWeight: '600' }}>
                    REAL / SOURCE-DERIVED
                  </span>
                )}
              </div>

              {/* Quantized displays */}
              <div style={{ margin: '0.75rem 0', display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
                
                {/* Operational Requirement */}
                <div>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '600' }}>
                    Operational Requirement
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <div className="card-value" style={{ fontSize: '1.45rem', fontWeight: '700', color: 'var(--text-main)' }}>
                      {resName === "Oxygen Demand" ? metrics.operationalRequirement.toFixed(2) : metrics.operationalRequirement}{' '}
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>
                        {metrics.operationalRequirement === 1 ? labels.operational : labels.plural}
                      </span>
                    </div>
                    <span className={getRiskBadgeClass(metrics.maxRisk)}>
                      {metrics.maxRisk}
                    </span>
                  </div>
                </div>

                {/* Raw Forecast */}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', backgroundColor: 'rgba(15, 23, 42, 0.2)', padding: '0.35rem 0.5rem', borderRadius: '4px' }}>
                  <span>Raw ML Forecast:</span>
                  <span style={{ color: 'var(--text-main)', fontWeight: '600' }}>
                    {metrics.peakForecast.toFixed(2)} {labels.forecast}
                  </span>
                </div>

              </div>

              {/* Capacity and Gap details */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Capacity / Stock:</span>
                  <span style={{ color: 'var(--text-main)', fontWeight: '500' }}>
                    {metrics.capacity.toFixed(0)} {resName === "Oxygen Demand" ? "L" : (metrics.capacity === 1 ? labels.operational : labels.plural)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Operational Gap:</span>
                  <span style={{ 
                    color: metrics.operationalGap < 0 ? 'var(--danger-red)' : 'var(--success-green)', 
                    fontWeight: '700' 
                  }}>
                    {metrics.operationalGap < 0 
                      ? `${Math.abs(metrics.operationalGap)} ${Math.abs(metrics.operationalGap) === 1 ? labels.operational : labels.plural} deficit`
                      : `${metrics.operationalGap} ${metrics.operationalGap === 1 ? labels.operational : labels.plural} surplus`
                    }
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Chart & Recommendations Detail section */}
      {activeResourceData && (
        <div className="forecasts-comparison-grid">
          
          {/* Chart Panel */}
          <div className="panel-card">
            <h4 style={{ fontSize: '1.05rem', color: 'var(--text-main)', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              {selectedResource} &mdash; 7-Day Forecast & Quantization Trend
            </h4>

            {activeResourceData.is_simulated && (
              <div className="info-note" style={{ marginBottom: '1rem', borderLeftColor: 'var(--warning-amber)', backgroundColor: 'rgba(245, 158, 11, 0.04)' }}>
                <strong>Prototype / Simulated Data Notice:</strong> The historical data for this resource is mathematically simulated based on standard hospital load indices. Never use these values for diagnostic decision paths.
              </div>
            )}

            <div className="chart-container" style={{ height: '280px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="displayDate" stroke="var(--text-muted)" style={{ fontSize: '0.75rem' }} />
                  <YAxis stroke="var(--text-muted)" style={{ fontSize: '0.75rem' }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'var(--bg-card)', 
                      borderColor: 'var(--border-color)',
                      color: 'var(--text-main)',
                      borderRadius: '6px'
                    }} 
                  />
                  <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
                  
                  {/* Capacity line */}
                  <Line 
                    type="monotone" 
                    dataKey="Capacity" 
                    stroke="var(--danger-red)" 
                    strokeWidth={2} 
                    strokeDasharray="4 4" 
                    name="Available Capacity"
                  />

                  {/* Operational Requirement line */}
                  <Line 
                    type="step" 
                    dataKey="Requirement" 
                    stroke="var(--success-green)" 
                    strokeWidth={2.5} 
                    name="Operational Requirement"
                  />
                  
                  {/* Raw Forecast line */}
                  <Line 
                    type="monotone" 
                    dataKey="Forecast" 
                    stroke="var(--primary-blue)" 
                    strokeWidth={3} 
                    activeDot={{ r: 8 }} 
                    name="Raw Forecast"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              {activeResourceData.mae !== null ? (
                <span>Model Evaluation MAE: {activeResourceData.mae.toFixed(4)}</span>
              ) : (
                <span style={{ fontStyle: 'italic' }}>MAE: N/A (Simulated projection)</span>
              )}
              {activeResourceData.rmse !== null ? (
                <span>Model Evaluation RMSE: {activeResourceData.rmse.toFixed(4)}</span>
              ) : (
                <span style={{ fontStyle: 'italic' }}>RMSE: N/A (Simulated projection)</span>
              )}
            </div>
          </div>

          {/* Recommendations Panel */}
          <div className="panel-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h4 style={{ fontSize: '1.05rem', color: 'var(--text-main)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              Active Recommendation & Decision Engine Triggers
            </h4>

            <div className="info-note" style={{ borderLeftColor: 'var(--warning-amber)' }}>
              <strong>Administrative Warning:</strong> The suggestion below is strictly logistical. It does not dictate medical diagnosis or care schedules.
            </div>

            {chartData.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
                <div style={{ padding: '1rem', border: '1px solid var(--border-color)', borderRadius: '6px', backgroundColor: 'var(--bg-main)' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '600' }}>
                    Resource status trigger:
                  </span>
                  <div style={{ marginTop: '0.25rem', fontSize: '0.9rem', color: 'var(--text-main)' }}>
                    {chartData[0].trigger}
                  </div>
                </div>

                <div style={{ padding: '1rem', border: '1px solid var(--border-color)', borderRadius: '6px', borderLeft: `4px solid ${getRiskColor(chartData[0].risk_level)}`, backgroundColor: 'var(--bg-main)' }}>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '600' }}>
                    Logistical recommendation:
                  </span>
                  <div style={{ marginTop: '0.25rem', fontSize: '0.95rem', fontWeight: '600', color: 'var(--text-main)' }}>
                    {chartData[0].recommendation}
                  </div>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.8rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Data Classification:</span>
                    <strong style={{ color: activeResourceData.is_simulated ? 'var(--warning-amber)' : 'var(--success-green)' }}>
                      {activeResourceData.is_simulated ? "SIMULATED / PROTOTYPE" : "REAL / SOURCE-DERIVED"}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Derivation Source:</span>
                    <span style={{ color: 'var(--text-main)' }}>{activeResourceData.source}</span>
                  </div>
                  {activeResourceData.assumption && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', marginTop: '0.25rem', padding: '0.5rem', backgroundColor: 'rgba(15, 23, 42, 0.3)', borderRadius: '4px' }}>
                      <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: '600' }}>Formulation / Explicit Assumption:</span>
                      <span style={{ color: 'var(--text-main)', fontSize: '0.75rem' }}>{activeResourceData.assumption}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

        </div>
      )}

      {/* 7-Day Forecast Table */}
      {tableRows.length > 0 && (
        <div className="panel-card" style={{ marginTop: '1rem' }}>
          <h4 style={{ fontSize: '1.05rem', color: 'var(--text-main)', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
            7-Day Resource Forecasts & Quantization Grid
          </h4>
          <div style={{ overflowX: 'auto' }}>
            <table className="alerts-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                  <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Date</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>ICU Beds</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>General Beds</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Emergency Beds</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Oxygen (L)</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Blood (Units)</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Staff (Count)</th>
                  <th style={{ padding: '0.75rem 0.5rem', fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Ambulances</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map((row, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)', height: '40px' }}>
                    <td style={{ padding: '0.5rem', fontSize: '0.85rem', fontWeight: '600' }}>{row.date}</td>
                    
                    {/* ICU Beds */}
                    <td style={{ padding: '0.5rem', fontSize: '0.85rem' }}>
                      <span style={{ fontWeight: '700' }}>{row["ICU Demand"].op}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>({row["ICU Demand"].raw.toFixed(2)})</span>
                    </td>

                    {/* General Beds */}
                    <td style={{ padding: '0.5rem', fontSize: '0.85rem' }}>
                      <span style={{ fontWeight: '700' }}>{row["General Bed Demand"].op}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>({row["General Bed Demand"].raw.toFixed(2)})</span>
                    </td>

                    {/* Emergency Beds */}
                    <td style={{ padding: '0.5rem', fontSize: '0.85rem' }}>
                      <span style={{ fontWeight: '700' }}>{row["Emergency Bed Demand"].op}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>({row["Emergency Bed Demand"].raw.toFixed(2)})</span>
                    </td>

                    {/* Oxygen (L) */}
                    <td style={{ padding: '0.5rem', fontSize: '0.85rem', fontWeight: '600' }}>
                      {row["Oxygen Demand"].op.toFixed(2)} L
                    </td>

                    {/* Blood (Units) */}
                    <td style={{ padding: '0.5rem', fontSize: '0.85rem' }}>
                      <span style={{ fontWeight: '700' }}>{row["Blood Demand"].op}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>({row["Blood Demand"].raw.toFixed(2)})</span>
                    </td>

                    {/* Staff (Count) */}
                    <td style={{ padding: '0.5rem', fontSize: '0.85rem' }}>
                      <span style={{ fontWeight: '700' }}>{row["Staff Requirement"].op}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>({row["Staff Requirement"].raw.toFixed(2)} FTE)</span>
                    </td>

                    {/* Ambulances */}
                    <td style={{ padding: '0.5rem', fontSize: '0.85rem' }}>
                      <span style={{ fontWeight: '700' }}>{row["Ambulance Requirement"].op}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>({row["Ambulance Requirement"].raw.toFixed(2)})</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
    </div>
  );
}

// Dummy object to support maps rendering when data is slow/empty
const CAPACITIES = {
  "ICU Demand": 2.0,
  "General Bed Demand": 25.0,
  "Emergency Bed Demand": 8.0,
  "Oxygen Demand": 100.0,
  "Blood Demand": 10.0,
  "Staff Requirement": 12.0,
  "Ambulance Requirement": 5.0
};
