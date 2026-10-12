import React from 'react';
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

export default function ForecastChart({ 
  forecastData, 
  selectedModel, 
  setSelectedModel, 
  title, 
  yAxisLabel 
}) {
  const predictions = forecastData?.predictions || [];
  
  // Format dates for display in chart and ensure whole integers for operational demands
  const formattedData = predictions.map(p => ({
    ...p,
    displayDate: new Date(p.date).toLocaleDateString(undefined, { 
      month: 'short', 
      day: 'numeric' 
    }),
    'Forecasted Demand': Math.ceil(p.predicted_demand),
    'Actual Demand': p.actual_demand !== null ? Math.ceil(p.actual_demand) : null
  }));

  const handleModelChange = (e) => {
    setSelectedModel(e.target.value);
  };

  return (
    <div className="panel-card panel-card-accent-blue">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">{title}</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            7-Day Model Forecast Horizon (Whole Integer Operational Units)
          </span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>Model:</label>
          <select value={selectedModel} onChange={handleModelChange}>
            <option value="XGBoost">XGBoost (Operational)</option>
            <option value="Prophet">Facebook Prophet</option>
            <option value="LSTM">PyTorch LSTM</option>
          </select>
        </div>
      </div>
      
      {formattedData.length === 0 ? (
        <div className="loader-wrapper">
          <span>No forecast data available for selection.</span>
        </div>
      ) : (
        <>
          <div style={{ height: '280px', width: '100%', marginBottom: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={formattedData}
                margin={{ top: 10, right: 25, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis 
                  dataKey="displayDate" 
                  stroke="#64748B"
                  style={{ fontSize: '0.75rem' }} 
                />
                <YAxis 
                  stroke="#64748B"
                  style={{ fontSize: '0.75rem' }} 
                  label={{ 
                    value: yAxisLabel, 
                    angle: -90, 
                    position: 'insideLeft', 
                    style: { fill: '#64748B', fontSize: '0.75rem' } 
                  }} 
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#FFFFFF', 
                    borderColor: '#E2E8F0',
                    borderRadius: '6px',
                    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
                  }} 
                />
                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '8px' }} />
                
                {/* Actual Demand: Royal Blue solid line */}
                <Line
                  type="monotone"
                  dataKey="Actual Demand"
                  stroke="#1455C0"
                  strokeWidth={2.5}
                  connectNulls
                  name="Historical Actual"
                />
                
                {/* Forecasted Demand: Gold dashed line */}
                <Line
                  type="monotone"
                  dataKey="Forecasted Demand"
                  stroke="#F4C430"
                  strokeWidth={3}
                  strokeDasharray="5 5"
                  name="Predicted Demand"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 7-Day Day-by-Day Table */}
          <div className="table-responsive" style={{ maxHeight: '160px' }}>
            <table>
              <thead>
                <tr>
                  {formattedData.slice(0, 7).map((d, idx) => (
                    <th key={idx} style={{ textAlign: 'center' }}>
                      {idx === 0 ? 'Today' : `Day ${idx + 1}`}
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                        {d.displayDate}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {formattedData.slice(0, 7).map((d, idx) => (
                    <td key={idx} style={{ textAlign: 'center', fontWeight: 700, color: 'var(--primary-blue)' }}>
                      {d['Forecasted Demand']} {yAxisLabel}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
