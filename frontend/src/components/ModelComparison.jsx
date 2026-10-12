import React from 'react';
import { Award, Info, BarChart3, CheckCircle2 } from 'lucide-react';

export default function ModelComparison({ performanceMetrics = [] }) {
  const icuMetrics = performanceMetrics.filter(m => m.target === "icu_occupancy");
  const edMetrics = performanceMetrics.filter(m => m.target === "ed_arrivals");

  const icuWinner = icuMetrics.find(m => m.rank === 1) || icuMetrics.reduce((prev, curr) => (prev && prev.mae < curr.mae) ? prev : curr, null);
  const edWinner = edMetrics.find(m => m.rank === 1) || edMetrics.reduce((prev, curr) => (prev && prev.mae < curr.mae) ? prev : curr, null);

  const getModelDescription = (modelName) => {
    const m = modelName.toLowerCase();
    if (m.includes("xgboost")) {
      return "XGBoost Regressor (Operational Baseline): Gradient-boosted decision tree ensemble leveraging autoregressive lag features, calendar signals, and rolling statistics.";
    }
    if (m.includes("prophet")) {
      return "Facebook Prophet: Decomposable additive time-series forecasting model configured for linear trend and weekly seasonality components.";
    }
    if (m.includes("lstm")) {
      return "PyTorch LSTM: Deep neural recurrent network learning temporal sequence memory across historical admission vectors.";
    }
    return "Time Series Machine Learning Model.";
  };

  const renderPerformanceTable = (metrics, targetTitle, winner) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', flexGrow: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid var(--border-color)', paddingBottom: '0.4rem' }}>
        <h4 style={{ fontSize: '1rem', color: 'var(--primary-blue)', margin: 0, fontWeight: 700 }}>
          {targetTitle}
        </h4>
        <span className="badge badge-prov">Target Metric: MAE</span>
      </div>
      
      {metrics.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No benchmark data loaded.</div>
      ) : (
        <>
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Model Architecture</th>
                  <th>MAE</th>
                  <th>RMSE</th>
                  <th>Status</th>
                  <th>Benchmark Rank</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((m, idx) => {
                  const isWinner = winner && m.model === winner.model;
                  const isOperational = m.model === 'XGBoost';
                  return (
                    <tr key={idx} style={{ backgroundColor: isWinner ? 'var(--primary-blue-light)' : 'transparent' }}>
                      <td style={{ fontWeight: 600 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>{m.model}</span>
                          {isOperational && (
                            <span className="badge badge-sufficient" style={{ fontSize: '0.65rem' }}>
                              Operational Model
                            </span>
                          )}
                          {isWinner && <Award size={14} color="#D97706" />}
                        </div>
                      </td>
                      <td><strong>{m.mae.toFixed(4)}</strong></td>
                      <td>{m.rmse.toFixed(4)}</td>
                      <td>
                        <span className="badge badge-low" style={{ fontSize: '0.7rem' }}>
                          <CheckCircle2 size={11} /> Validated
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${m.rank === 1 ? 'badge-sufficient' : 'badge-prov'}`} style={{ fontWeight: 700 }}>
                          #{m.rank || idx + 1}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          
          {winner && (
            <div style={{ padding: '0.65rem 0.85rem', backgroundColor: 'var(--success-bg)', borderRadius: '4px', borderLeft: '3px solid var(--success-green)', fontSize: '0.8rem', color: 'var(--success-green)' }}>
              <strong>Best Accuracy Benchmark:</strong> <strong>{winner.model}</strong> achieved lowest Mean Absolute Error ({winner.mae.toFixed(4)}).
            </div>
          )}
        </>
      )}
    </div>
  );

  return (
    <div className="panel-card panel-card-accent-blue" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="chart-header">
        <div>
          <h3 className="chart-title">
            <BarChart3 size={20} color="var(--primary-blue)" />
            Model Performance &amp; Comparative Benchmarks
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Empirical accuracy comparison across Prophet, XGBoost, and PyTorch LSTM models
          </span>
        </div>
      </div>

      <div className="info-note">
        <strong>Operational Selection:</strong> <strong>XGBoost</strong> is configured as the active primary operational forecasting model. MAE (Mean Absolute Error) is the primary ranking criterion because it directly measures variance in whole operational units (beds &amp; patients).
      </div>

      {/* Comparison Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '1.25rem' }}>
        {renderPerformanceTable(icuMetrics, "ICU Bed Occupancy Forecasts", icuWinner)}
        {renderPerformanceTable(edMetrics, "Emergency Department Arrivals Forecasts", edWinner)}
      </div>

      {/* Model Architectures Section */}
      <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
        <h4 style={{ fontSize: '0.95rem', color: 'var(--text-main)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Info size={16} color="var(--primary-blue)" /> Evaluated Model Architectures
        </h4>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {["XGBoost", "Prophet", "LSTM"].map((m, idx) => (
            <div key={idx} style={{ padding: '0.75rem 1rem', backgroundColor: 'var(--bg-card-alt)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <strong style={{ color: 'var(--primary-blue)', fontSize: '0.9rem' }}>{m}</strong>
                {m === 'XGBoost' && <span className="badge badge-sufficient" style={{ fontSize: '0.65rem' }}>Active Engine</span>}
              </div>
              <p style={{ marginTop: '0.25rem', color: 'var(--text-body)', fontSize: '0.825rem' }}>
                {getModelDescription(m)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
