import React from 'react';
import { 
  Bed, 
  Wind, 
  Droplet, 
  Users, 
  Truck,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  ShieldAlert
} from 'lucide-react';

export default function SummaryCard({ 
  icuForecast, 
  edForecast, 
  alerts = [],
  latestBeds,
  latestOxygen,
  latestBlood = [],
  latestStaff = [],
  latestAmbulance,
  onSelectResource
}) {
  // Peak predictions helpers (Whole numbers)
  const getPeakIcu = () => {
    if (icuForecast?.predictions?.length > 0) {
      return Math.ceil(Math.max(...icuForecast.predictions.map(p => p.predicted_demand)));
    }
    return 15;
  };

  const getPeakEd = () => {
    if (edForecast?.predictions?.length > 0) {
      return Math.ceil(Math.max(...edForecast.predictions.map(p => p.predicted_demand)));
    }
    return 32;
  };

  const peakIcu = getPeakIcu();
  const peakEd = getPeakEd();

  // 1. Beds stats
  const bedsAvailable = Math.ceil(latestBeds?.available_count ?? 225);
  const bedsUsed = Math.ceil(latestBeds?.occupied_count ?? (Math.ceil(icuForecast?.predictions?.[0]?.actual_demand || 12) + 78 + Math.ceil((edForecast?.predictions?.[0]?.actual_demand || 32) * 0.25)));
  const bedsRequired = Math.ceil(latestBeds?.required_count ?? (Math.ceil(icuForecast?.predictions?.[0]?.actual_demand || 12) + 82 + Math.ceil((edForecast?.predictions?.[0]?.actual_demand || 32) * 0.25)));
  const bedsForecast = Math.ceil(peakIcu + 82 + Math.ceil(peakEd * 0.25));
  const bedsDiff = bedsAvailable - bedsRequired;
  const bedsStatus = bedsDiff < 0 ? "Shortage" : "Sufficient";
  const bedsProv = latestBeds?.source_type ?? "Historical";

  // 2. Oxygen stats (Cylinders strictly whole integers)
  const oxyAvailable = Math.ceil(latestOxygen?.available_cylinders ?? 45);
  const oxyUsed = Math.ceil(latestOxygen?.used_cylinders ?? 32);
  const oxyRequired = Math.ceil(latestOxygen?.required_cylinders ?? 35);
  const oxyForecast = Math.ceil(peakIcu * 1.5);
  const oxyDiff = oxyAvailable - oxyRequired;
  const oxyStatus = oxyDiff < 0 ? "Shortage" : "Sufficient";
  const oxyProv = latestOxygen?.source_type ?? "Configured Parameters";

  // 3. Blood stats (Units strictly whole integers)
  const bloodAvailable = Math.ceil(latestBlood?.length > 0 ? latestBlood.reduce((acc, b) => acc + b.available_units, 0) : 150);
  const bloodUsed = Math.ceil(latestBlood?.length > 0 ? latestBlood.reduce((acc, b) => acc + b.used_units, 0) : 40);
  const bloodRequired = Math.ceil(latestBlood?.length > 0 ? latestBlood.reduce((acc, b) => acc + b.required_units, 0) : 95);
  const bloodForecast = Math.ceil(peakEd * 0.20);
  const bloodDiff = bloodAvailable - bloodRequired;
  const bloodStatus = bloodDiff < 0 ? "Shortage" : "Sufficient";
  const bloodProv = latestBlood?.[0]?.source_type ?? "Configured Parameters";

  // 4. Staff stats (FTE strictly whole integer staff members)
  const staffAvailable = Math.ceil(latestStaff?.length > 0 ? latestStaff.reduce((acc, s) => acc + s.available_count, 0) : 110);
  const staffUsed = Math.ceil(latestStaff?.length > 0 ? latestStaff.reduce((acc, s) => acc + s.used_count, 0) : 80);
  const staffRequired = Math.ceil(latestStaff?.length > 0 ? latestStaff.reduce((acc, s) => acc + s.required_count, 0) : 93);
  const staffForecast = Math.ceil(peakIcu * 1.2 + peakEd * 0.4);
  const staffDiff = staffAvailable - staffRequired;
  const staffStatus = staffDiff < 0 ? "Shortage" : "Sufficient";
  const staffProv = latestStaff?.[0]?.source_type ?? "Configured Parameters";

  // 5. Ambulance stats (Fleet strictly whole integer vehicles)
  const ambAvailable = Math.ceil(latestAmbulance?.available_count ?? 5);
  const ambUsed = Math.ceil(latestAmbulance?.used_count ?? 5);
  const ambRequired = Math.ceil(latestAmbulance?.required_count ?? 6);
  const ambForecast = Math.ceil(peakEd / 6);
  const ambDiff = ambAvailable - ambRequired;
  const ambStatus = ambDiff < 0 ? "Shortage" : "Sufficient";
  const ambProv = latestAmbulance?.source_type ?? "Configured Parameters";

  const resourceTiles = [
    {
      id: 'beds',
      title: 'Beds',
      subtitle: 'Hospital Bed Allocation',
      icon: Bed,
      available: bedsAvailable,
      used: bedsUsed,
      required: bedsRequired,
      forecast: bedsForecast,
      diff: bedsDiff,
      status: bedsStatus,
      unit: 'beds',
      prov: bedsProv,
      breakdown: [
        { label: 'ICU', count: Math.ceil(latestBeds?.bed_type === 'ICU Beds' ? latestBeds.available_count : 50) },
        { label: 'General', count: Math.ceil(latestBeds?.bed_type === 'General Beds' ? latestBeds.available_count : 150) },
        { label: 'Emergency', count: Math.ceil(latestBeds?.bed_type === 'Emergency Beds' ? latestBeds.available_count : 25) }
      ]
    },
    {
      id: 'oxygen',
      title: 'Oxygen',
      subtitle: 'Cylinder Stock & Capacity',
      icon: Wind,
      available: oxyAvailable,
      used: oxyUsed,
      required: oxyRequired,
      forecast: oxyForecast,
      diff: oxyDiff,
      status: oxyStatus,
      unit: 'cylinders',
      prov: oxyProv,
      breakdown: [
        { label: 'Available', count: oxyAvailable },
        { label: 'In Use', count: oxyUsed },
        { label: 'Empty', count: Math.max(0, (latestOxygen?.total_cylinders || 80) - (oxyAvailable + oxyUsed)) }
      ]
    },
    {
      id: 'blood',
      title: 'Blood',
      subtitle: 'Blood Group Inventory',
      icon: Droplet,
      available: bloodAvailable,
      used: bloodUsed,
      required: bloodRequired,
      forecast: bloodForecast,
      diff: bloodDiff,
      status: bloodStatus,
      unit: 'units',
      prov: bloodProv,
      breakdown: [
        { label: 'O+ / O-', count: Math.ceil((latestBlood.find(b => b.blood_group === 'O+')?.available_units || 25) + (latestBlood.find(b => b.blood_group === 'O-')?.available_units || 10)) },
        { label: 'A+ / A-', count: Math.ceil((latestBlood.find(b => b.blood_group === 'A+')?.available_units || 25) + (latestBlood.find(b => b.blood_group === 'A-')?.available_units || 10)) },
        { label: 'B+ / AB+', count: Math.ceil((latestBlood.find(b => b.blood_group === 'B+')?.available_units || 25) + (latestBlood.find(b => b.blood_group === 'AB+')?.available_units || 25)) }
      ]
    },
    {
      id: 'staff',
      title: 'Staff',
      subtitle: 'Clinical & Support Roster',
      icon: Users,
      available: staffAvailable,
      used: staffUsed,
      required: staffRequired,
      forecast: staffForecast,
      diff: staffDiff,
      status: staffStatus,
      unit: 'staff',
      prov: staffProv,
      breakdown: [
        { label: 'Doctors', count: Math.ceil(latestStaff.find(s => s.staff_category === 'Doctors')?.available_count || 25) },
        { label: 'Nurses', count: Math.ceil(latestStaff.find(s => s.staff_category === 'Nurses')?.available_count || 50) },
        { label: 'Support', count: Math.ceil(latestStaff.find(s => s.staff_category === 'Support Staff')?.available_count || 20) }
      ]
    },
    {
      id: 'ambulance',
      title: 'Ambulance',
      subtitle: 'Emergency Fleet & Dispatch',
      icon: Truck,
      available: ambAvailable,
      used: ambUsed,
      required: ambRequired,
      forecast: ambForecast,
      diff: ambDiff,
      status: ambStatus,
      unit: 'ambulances',
      prov: ambProv,
      breakdown: [
        { label: 'Available', count: ambAvailable },
        { label: 'Dispatched', count: ambUsed },
        { label: 'Garage', count: Math.ceil(latestAmbulance?.under_maintenance_count || 2) }
      ]
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 className="chart-title" style={{ margin: 0 }}>Monitored Hospital Resources</h3>
        <span className="badge badge-prov">
          Provenance: Historical &amp; Configured Parameters
        </span>
      </div>

      <div className="resource-overview-grid">
        {resourceTiles.map((tile) => {
          const Icon = tile.icon;
          const isShortage = tile.diff < 0;
          const diffText = isShortage 
            ? `${Math.abs(tile.diff)} ${tile.unit} Shortage` 
            : `${tile.diff} ${tile.unit} Surplus`;

          return (
            <div key={tile.id} className="resource-tile-card">
              <div className="tile-header">
                <div className="tile-title-group">
                  <div className="tile-icon-box">
                    <Icon size={18} />
                  </div>
                  <div>
                    <h4 className="tile-title">{tile.title}</h4>
                    <span className="tile-category-tag">{tile.subtitle}</span>
                  </div>
                </div>

                <span className={`badge ${isShortage ? 'badge-shortage' : 'badge-sufficient'}`}>
                  {tile.status}
                </span>
              </div>

              {/* Sub-category Quick Summary */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.35rem', background: 'var(--bg-card-alt)', padding: '0.5rem', borderRadius: '4px', textAlign: 'center' }}>
                {tile.breakdown.map((b, idx) => (
                  <div key={idx}>
                    <div style={{ fontSize: '0.675rem', color: 'var(--text-muted)', fontWeight: 500 }}>{b.label}</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)' }}>{b.count}</div>
                  </div>
                ))}
              </div>

              {/* Operational Metrics */}
              <table className="tile-metrics-table">
                <tbody>
                  <tr>
                    <td>Available / Active:</td>
                    <td className="metric-val">{tile.available} / {tile.used}</td>
                  </tr>
                  <tr>
                    <td>Target Requirement:</td>
                    <td className="metric-val">{tile.required} {tile.unit}</td>
                  </tr>
                  <tr>
                    <td>7-Day Peak Forecast:</td>
                    <td className="metric-val" style={{ color: 'var(--primary-blue)' }}>
                      {tile.forecast} {tile.unit}
                    </td>
                  </tr>
                </tbody>
              </table>

              {/* Footer with Diff & Action */}
              <div className="tile-footer">
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: isShortage ? 'var(--danger-red)' : 'var(--success-green)' }}>
                  {diffText}
                </span>

                <button 
                  className="view-details-btn"
                  onClick={() => onSelectResource && onSelectResource(tile.id)}
                >
                  <span>View Details</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
