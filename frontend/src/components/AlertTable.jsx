import React from 'react';
import { ShieldAlert, AlertTriangle, AlertCircle, ShieldCheck, ArrowRight } from 'lucide-react';

export default function AlertTable({ 
  alerts = [], 
  filterResource, 
  setFilterResource, 
  filterRisk, 
  setFilterRisk, 
  filterStartDate, 
  setFilterStartDate, 
  filterEndDate, 
  setFilterEndDate,
  onSelectResource
}) {
  
  const getRiskBadge = (level) => {
    const l = level ? level.toUpperCase() : 'LOW';
    if (l === "CRITICAL") {
      return (
        <span className="badge badge-critical">
          <ShieldAlert size={12} /> Critical
        </span>
      );
    }
    if (l === "HIGH") {
      return (
        <span className="badge badge-high">
          <ShieldAlert size={12} /> High
        </span>
      );
    }
    if (l === "MEDIUM") {
      return (
        <span className="badge badge-medium">
          <AlertTriangle size={12} /> Medium
        </span>
      );
    }
    return (
      <span className="badge badge-low">
        <ShieldCheck size={12} /> Low
      </span>
    );
  };

  const getResourceUnit = (resName) => {
    if (!resName) return 'units';
    const r = resName.toLowerCase();
    if (r.includes('oxygen')) return 'Liters';
    if (r.includes('blood')) return 'Units';
    if (r.includes('bed') || r.includes('icu')) return 'Beds';
    if (r.includes('staff')) return 'FTE';
    if (r.includes('ambulance')) return 'Vehicles';
    if (r.includes('arrival') || r.includes('ed')) return 'Arrivals';
    return 'units';
  };

  const isContinuousResource = (resName) => {
    if (!resName) return false;
    const r = resName.toLowerCase();
    return r.includes('oxygen');
  };

  const formatResourceValue = (resName, val) => {
    if (val === null || val === undefined || isNaN(val)) return '—';
    if (isContinuousResource(resName)) {
      return parseFloat(val).toFixed(2);
    }
    return Math.ceil(val).toString();
  };

  const mapResourceToTab = (resName) => {
    if (!resName) return 'overview';
    const r = resName.toLowerCase();
    if (r.includes('bed') || r.includes('icu')) return 'beds';
    if (r.includes('oxygen')) return 'oxygen';
    if (r.includes('blood')) return 'blood';
    if (r.includes('staff')) return 'staff';
    if (r.includes('ambulance') || r.includes('ed')) return 'ambulance';
    return 'overview';
  };

  return (
    <div className="panel-card">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Resource Shortage &amp; Capacity Risk Alerts</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Real-time threshold surveillance and predictive bottleneck identification
          </span>
        </div>
      </div>
      
      {/* Filters Row */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.25rem', alignItems: 'center' }}>
        <div>
          <select 
            value={filterResource || ''} 
            onChange={(e) => setFilterResource(e.target.value || null)}
            style={{ fontSize: '0.825rem' }}
          >
            <option value="">All Resources</option>
            <option value="ICU Beds">ICU Beds</option>
            <option value="ED Arrivals">ED Arrivals</option>
            <option value="General Bed Demand">General Beds</option>
            <option value="Emergency Bed Demand">Emergency Beds</option>
            <option value="Oxygen Demand">Oxygen Demand</option>
            <option value="Blood Demand">Blood Demand</option>
            <option value="Staff Requirement">Staff Requirement</option>
            <option value="Ambulance Requirement">Ambulance Requirement</option>
          </select>
        </div>
        
        <div>
          <select 
            value={filterRisk || ''} 
            onChange={(e) => setFilterRisk(e.target.value || null)}
            style={{ fontSize: '0.825rem' }}
          >
            <option value="">All Risk Levels</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>From:</span>
          <input 
            type="date" 
            value={filterStartDate || ''} 
            onChange={(e) => setFilterStartDate(e.target.value || null)} 
            style={{ fontSize: '0.825rem', padding: '0.35rem 0.5rem' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>To:</span>
          <input 
            type="date" 
            value={filterEndDate || ''} 
            onChange={(e) => setFilterEndDate(e.target.value || null)} 
            style={{ fontSize: '0.825rem', padding: '0.35rem 0.5rem' }}
          />
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="loader-wrapper" style={{ padding: '2rem' }}>
          <ShieldCheck size={32} color="var(--success-green)" />
          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>No capacity shortage alerts detected for current horizon.</span>
        </div>
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Resource</th>
                <th>Predicted Demand</th>
                <th>Available Capacity</th>
                <th>Capacity Gap</th>
                <th>Risk Level</th>
                <th>Action &amp; Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => {
                const isSimulated = alert.is_capacity_simulated;
                const capacityVal = isSimulated ? alert.simulated_capacity : alert.actual_capacity;
                const dateStr = new Date(alert.date).toLocaleDateString(undefined, { 
                  month: 'short', 
                  day: 'numeric',
                  year: 'numeric'
                });

                const isContinuous = isContinuousResource(alert.resource);
                const unit = getResourceUnit(alert.resource);
                const reqStr = formatResourceValue(alert.resource, alert.predicted_demand);
                const capStr = formatResourceValue(alert.resource, capacityVal);
                
                // Format gap for display without mutating stored alert numbers
                let gapDisplay = '—';
                const rawGap = alert.capacity_gap;
                if (rawGap !== null && rawGap !== undefined && !isNaN(rawGap)) {
                  if (isContinuous) {
                    const absVal = Math.abs(parseFloat(rawGap)).toFixed(2);
                    gapDisplay = rawGap < 0 ? `${absVal} Deficit` : `${absVal} Surplus`;
                  } else {
                    const absVal = Math.abs(Math.ceil(rawGap));
                    gapDisplay = rawGap < 0 ? `${absVal} Deficit` : `${absVal} Surplus`;
                  }
                }
                const isNegativeGap = rawGap !== null && rawGap !== undefined && rawGap < 0;
                
                return (
                  <tr key={alert.id}>
                    <td style={{ fontWeight: 600 }}>{dateStr}</td>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--primary-blue)' }}>{alert.resource}</span>
                      <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {isSimulated ? "Configured Parameter" : "Historical Actual"}
                      </span>
                    </td>
                    <td><strong>{reqStr}</strong> {unit}</td>
                    <td>{capStr} {unit}</td>
                    <td>
                      <span style={{ fontWeight: 700, color: isNegativeGap ? 'var(--danger-red)' : 'var(--success-green)' }}>
                        {gapDisplay}
                      </span>
                    </td>
                    <td>{getRiskBadge(alert.risk_level)}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{alert.reason}</span>
                        {onSelectResource && (
                          <button 
                            className="view-details-btn"
                            onClick={() => onSelectResource(mapResourceToTab(alert.resource))}
                            style={{ whiteSpace: 'nowrap' }}
                          >
                            <span>View Resource</span>
                            <ArrowRight size={13} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
