import React from 'react';
import { HelpCircle, ChevronRight, ShieldAlert, Brain, Info } from 'lucide-react';

export default function ExplanationChart({
  explanations = [],
  selectedResource,
  setSelectedResource,
  selectedMethod,
  setSelectedMethod,
  explanationDate
}) {
  
  const handleResourceChange = (e) => {
    setSelectedResource(e.target.value);
  };

  const handleMethodChange = (e) => {
    setSelectedMethod(e.target.value);
  };

  const maxAbsContrib = explanations.length > 0 
    ? Math.max(...explanations.map(e => Math.abs(e.contribution)), 0.00001)
    : 1;

  const dateStr = explanationDate 
    ? new Date(explanationDate).toLocaleDateString(undefined, { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric'
      })
    : '';

  return (
    <div className="panel-card panel-card-accent-blue">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">
            <Brain size={20} color="var(--primary-blue)" />
            Explainable AI (XAI) &mdash; Forecast Attribution
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Transparent machine learning feature attributions and local prediction factors
          </span>
        </div>
        
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <select value={selectedResource} onChange={handleResourceChange} style={{ fontSize: '0.85rem' }}>
            <option value="ICU Beds">ICU Beds (Occupancy Target)</option>
            <option value="ED Arrivals">ED Arrivals (Daily Volume)</option>
          </select>
          
          <select value={selectedMethod} onChange={handleMethodChange} style={{ fontSize: '0.85rem' }}>
            <option value="SHAP">SHAP Local Attribution</option>
            <option value="LIME">LIME Local Attribution</option>
          </select>
        </div>
      </div>

      {/* Model Prediction vs Operational Transformation Callout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
        <div style={{ background: 'var(--primary-blue-light)', border: '1px solid var(--primary-blue-border)', borderRadius: '6px', padding: '0.85rem 1rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary-blue)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            MODEL PREDICTION (Statistical ML)
          </div>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-body)' }}>
            Raw machine learning regression output (e.g. XGBoost/LSTM target weights). These feature contributions below explain why the algorithmic forecast was generated.
          </p>
        </div>

        <div style={{ background: 'var(--accent-gold-light)', border: '1px solid var(--accent-gold-border)', borderRadius: '6px', padding: '0.85rem 1rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#B45309', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            OPERATIONAL TRANSFORMATION (Planning Layer)
          </div>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-body)' }}>
            Operational whole-number ceiling rounding (e.g. converting 0.45 beds to 1 bed) is a hospital administrative planning rule applied on top of the model results, not an internal feature weight.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Active Target Date: <strong>{dateStr || 'Oct 17, 2137'}</strong>
        </div>

        <div style={{ display: 'flex', gap: '1.25rem', fontSize: '0.8rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '2px', backgroundColor: 'var(--primary-blue)' }}></div>
            <span style={{ color: 'var(--text-body)' }}>Positive factor (+ pushes demand higher)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '2px', backgroundColor: '#64748B' }}></div>
            <span style={{ color: 'var(--text-body)' }}>Negative factor (- moderates demand)</span>
          </div>
        </div>
      </div>

      {explanations.length === 0 ? (
        <div className="loader-wrapper" style={{ padding: '2rem' }}>
          <span>No explainability records found for selection.</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {explanations.map((exp, idx) => {
            const isPositive = exp.direction === 1 || exp.contribution >= 0;
            const fillWidth = `${(Math.abs(exp.contribution) / maxAbsContrib) * 100}%`;
            const fillColor = isPositive ? 'var(--primary-blue)' : '#64748B';

            return (
              <div className="xai-bullet-bar" key={idx}>
                <div className="xai-bar-label" title={exp.feature}>
                  {exp.feature}
                </div>
                
                <div style={{ width: '70px', fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                  val: {typeof exp.feature_value === 'number' ? exp.feature_value.toFixed(1) : exp.feature_value}
                </div>
                
                <div className="xai-bar-track">
                  <div 
                    className="xai-bar-fill" 
                    style={{ 
                      width: fillWidth, 
                      backgroundColor: fillColor,
                      transition: 'width 0.3s ease' 
                    }}
                  ></div>
                </div>
                
                <div className="xai-bar-value" style={{ color: isPositive ? 'var(--primary-blue)' : 'var(--text-muted)' }}>
                  {isPositive ? '+' : ''}{exp.contribution.toFixed(4)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
