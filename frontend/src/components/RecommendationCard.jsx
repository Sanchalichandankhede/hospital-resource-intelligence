import React, { useState } from 'react';
import { 
  ClipboardList, 
  ShieldAlert, 
  CheckCircle2, 
  ArrowRight,
  Bed,
  Wind,
  Droplet,
  Users,
  Truck,
  Info
} from 'lucide-react';

export default function RecommendationCard({ recommendations = [], onSelectResource }) {
  const [selectedCategory, setSelectedCategory] = useState('All');

  const resourceCategories = [
    { id: 'All', label: 'All Resources', icon: ClipboardList },
    { id: 'Beds', label: 'Beds', icon: Bed },
    { id: 'Oxygen', label: 'Oxygen', icon: Wind },
    { id: 'Blood', label: 'Blood', icon: Droplet },
    { id: 'Staff', label: 'Staff', icon: Users },
    { id: 'Ambulance', label: 'Ambulance', icon: Truck }
  ];

  const mapCategory = (rec) => {
    const text = (rec.resource + ' ' + rec.recommendation).toLowerCase();
    if (text.includes('bed') || text.includes('icu')) return 'Beds';
    if (text.includes('oxygen') || text.includes('cylinder')) return 'Oxygen';
    if (text.includes('blood')) return 'Blood';
    if (text.includes('staff') || text.includes('nurse') || text.includes('doctor')) return 'Staff';
    if (text.includes('ambulance') || text.includes('dispatch') || text.includes('ed')) return 'Ambulance';
    return 'Beds';
  };

  const mapTabId = (cat) => {
    return cat.toLowerCase();
  };

  const filteredRecs = selectedCategory === 'All' 
    ? recommendations 
    : recommendations.filter(r => mapCategory(r) === selectedCategory);

  return (
    <div className="panel-card">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Administrative &amp; Logistical Capacity Recommendations</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Operational response suggestions based on 7-day predictive bottleneck indicators
          </span>
        </div>
      </div>

      <div className="info-note" style={{ marginBottom: '1.25rem' }}>
        <strong>Administrative Notice:</strong> All recommendations are administrative and logistical operational guidelines only (e.g. inventory restock, shift rosters). They do not constitute clinical diagnosis or medical treatment directives.
      </div>

      {/* Category Pills */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
        {resourceCategories.map(cat => {
          const Icon = cat.icon;
          return (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`btn-secondary ${selectedCategory === cat.id ? 'btn-primary' : ''}`}
              style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Icon size={14} />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      {filteredRecs.length === 0 ? (
        <div className="loader-wrapper" style={{ padding: '2rem' }}>
          <CheckCircle2 size={32} color="var(--success-green)" />
          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>No administrative actions required for current threshold parameters.</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {filteredRecs.map((rec) => {
            const dateStr = new Date(rec.date).toLocaleDateString(undefined, { 
              month: 'short', 
              day: 'numeric',
              year: 'numeric'
            });
            const cat = mapCategory(rec);
            const isHigh = rec.risk_level === 'HIGH' || rec.risk_level === 'CRITICAL';

            return (
              <div 
                key={rec.id}
                style={{
                  border: '1px solid var(--border-color)',
                  borderLeft: `4px solid ${isHigh ? 'var(--danger-red)' : 'var(--primary-blue)'}`,
                  borderRadius: '6px',
                  backgroundColor: '#FFFFFF',
                  boxShadow: 'var(--shadow-xs)',
                  overflow: 'hidden'
                }}
              >
                <div style={{ padding: '0.75rem 1rem', background: 'var(--bg-card-alt)', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: 700, color: 'var(--primary-blue)', fontSize: '0.85rem' }}>
                      {cat.toUpperCase()} RESOURCE
                    </span>
                    <span className={`badge ${isHigh ? 'badge-high' : 'badge-low'}`}>
                      {rec.risk_level} RISK
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target: {dateStr}</span>
                </div>

                <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                      Operational Recommendation:
                    </span>
                    <p style={{ fontSize: '0.925rem', color: 'var(--text-main)', fontWeight: 500, marginTop: '0.15rem' }}>
                      {rec.recommendation}
                    </p>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                      <strong>Trigger Condition:</strong> {rec.trigger}
                    </div>

                    {onSelectResource && (
                      <button 
                        className="view-details-btn"
                        onClick={() => onSelectResource(mapTabId(cat))}
                      >
                        <span>Manage {cat}</span>
                        <ArrowRight size={13} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
