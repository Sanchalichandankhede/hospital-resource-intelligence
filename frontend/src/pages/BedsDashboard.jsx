import React, { useState, useEffect } from 'react';
import { Bed, Plus, Trash2, Calendar, ShieldCheck, AlertTriangle, ShieldAlert, Layers } from 'lucide-react';
import { apiService } from '../services/api';
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

export default function BedsDashboard({ currentUser, defaultTab = 'ICU Beds' }) {
  const [activeTab, setActiveTab] = useState(defaultTab);

  useEffect(() => {
    if (defaultTab) {
      setActiveTab(defaultTab);
    }
  }, [defaultTab]);

  const [records, setRecords] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [selectedModel, setSelectedModel] = useState('XGBoost');
  
  // Data Entry Form State
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    available_count: '',
    occupied_count: '',
    required_count: ''
  });
  
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  const fetchBedsData = async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const allRecords = await apiService.getResources('beds');
      setRecords(allRecords.filter(r => r.bed_type === activeTab));

      // Fetch forecast data
      if (activeTab === 'ICU Beds') {
        const icuForecast = await apiService.getForecast('ICU', selectedModel);
        if (icuForecast && icuForecast.predictions && icuForecast.predictions.length > 0) {
          setForecastData(icuForecast.predictions.map(p => ({
            date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
            'Actual Demand': p.actual_demand !== null ? Math.ceil(p.actual_demand) : null,
            'Forecasted Demand': Math.ceil(p.predicted_demand),
            'Available Capacity': 50
          })));
        } else {
          setForecastData([]);
        }
      } else if (activeTab === 'Emergency Beds') {
        const edForecast = await apiService.getForecast('ED', selectedModel);
        if (edForecast && edForecast.predictions && edForecast.predictions.length > 0) {
          setForecastData(edForecast.predictions.map(p => ({
            date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
            'Actual Demand': p.actual_demand !== null ? Math.ceil(p.actual_demand * 0.25) : null,
            'Forecasted Demand': Math.ceil(p.predicted_demand * 0.25),
            'Available Capacity': 25
          })));
        } else {
          setForecastData([]);
        }
      } else {
        // General Beds: dynamically consume multi-resource endpoint (18.0 baseline + 2.0 * ICU demand)
        const multiRes = await apiService.getMultiResourceForecast(selectedModel);
        const genBedsRes = multiRes?.resources?.["General Bed Demand"];
        if (genBedsRes && genBedsRes.predictions && genBedsRes.predictions.length > 0) {
          setForecastData(genBedsRes.predictions.map(p => ({
            date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
            'Actual Demand': p.actual_demand !== null ? Math.ceil(p.actual_demand) : null,
            'Forecasted Demand': Math.ceil(p.operational_requirement !== undefined ? p.operational_requirement : p.predicted_demand),
            'Available Capacity': Math.ceil(p.capacity || 25)
          })));
        } else {
          setForecastData([]);
        }
      }
    } catch (err) {
      console.error("Error fetching bed data:", err);
      setFetchError(err.message || 'Failed to load bed forecasting data.');
      setForecastData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBedsData();
  }, [activeTab, selectedModel]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const av = parseFloat(formData.available_count);
    const oc = parseFloat(formData.occupied_count);
    const rq = parseFloat(formData.required_count);

    if (isNaN(av) || isNaN(oc) || isNaN(rq)) {
      setErrorMsg('All bed counts must be numbers.');
      return;
    }

    if (!Number.isInteger(av) || !Number.isInteger(oc) || !Number.isInteger(rq)) {
      setErrorMsg('Bed quantities must be whole integers.');
      return;
    }

    if (av < 0 || oc < 0 || rq < 0) {
      setErrorMsg('Negative values are not accepted.');
      return;
    }

    try {
      await apiService.createResourceRecord('beds', {
        date: formData.date,
        bed_type: activeTab,
        available_count: parseInt(formData.available_count),
        occupied_count: parseInt(formData.occupied_count),
        required_count: parseInt(formData.required_count)
      });
      setSuccessMsg('Bed record saved successfully!');
      setFormData({
        date: new Date().toISOString().split('T')[0],
        available_count: '',
        occupied_count: '',
        required_count: ''
      });
      setShowForm(false);
      fetchBedsData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save bed record.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this bed record?")) return;
    try {
      await apiService.deleteResourceRecord('beds', id);
      fetchBedsData();
    } catch (err) {
      alert(err.message || 'Failed to delete record.');
    }
  };

  const latestRecord = records[0] || {
    available_count: activeTab === 'ICU Beds' ? 50 : activeTab === 'General Beds' ? 25 : 25,
    occupied_count: activeTab === 'ICU Beds' ? 12 : activeTab === 'General Beds' ? 18 : 8,
    required_count: activeTab === 'ICU Beds' ? 15 : activeTab === 'General Beds' ? 20 : 10,
    source_type: activeTab === 'General Beds' ? 'Configured Parameter (Simulated)' : 'Historical'
  };

  const availableCount = Math.ceil(latestRecord.available_count);
  const occupiedCount = Math.ceil(latestRecord.occupied_count);
  const requiredCount = Math.ceil(latestRecord.required_count);
  const predictedDemand = forecastData.length > 0 ? Math.ceil(forecastData[0]['Forecasted Demand'] || requiredCount) : requiredCount;
  const shortageSurplus = availableCount - requiredCount;
  const isShortage = shortageSurplus < 0;
  const utilization = Math.round((occupiedCount / availableCount) * 100) || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header */}
      <div className="page-header-bar">
        <div>
          <h2 className="page-title">
            <Bed size={24} color="var(--primary-blue)" />
            BEDS RESOURCE MANAGEMENT
          </h2>
          <p className="page-subtitle">Capacity planning, clinical allocation, and 7-day demand projections.</p>
        </div>

        {currentUser?.role !== 'VIEWER' && (
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={16} />
            <span>+ Add Bed Data</span>
          </button>
        )}
      </div>

      {/* Tabs: ICU, General, Emergency */}
      <div className="tab-menu-bar">
        {['ICU Beds', 'General Beds', 'Emergency Beds'].map(tab => (
          <button 
            key={tab}
            className={`tab-btn-pill ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      {/* General Beds Simulated Notice Banner */}
      {activeTab === 'General Beds' && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          background: '#FEF3C7',
          border: '1px solid #F59E0B',
          borderRadius: '6px',
          padding: '0.75rem 1rem',
          color: '#92400E',
          fontSize: '0.85rem'
        }}>
          <AlertTriangle size={20} color="#D97706" style={{ flexShrink: 0 }} />
          <div>
            <strong>Simulated Heuristic Baseline Notice:</strong> General Beds telemetry is formula-derived (Monthly baseline 18.0 + 2.0 &times; ICU) with a configured baseline capacity of 25 beds. The backend possesses no empirical ward-level General Beds sensor history; values represent a simulation prototype.
          </div>
        </div>
      )}

      {/* Summary Metrics Strip (Strictly Whole Numbers) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
        <div className="panel-card panel-card-accent-blue" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Available Beds</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-blue)', margin: '0.25rem 0' }}>
            {availableCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Bed Capacity</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Used / Occupied</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {occupiedCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Currently In Use</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Required Demand</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {requiredCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Operational Target</div>
        </div>

        <div className="panel-card panel-card-accent-gold" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Predicted Demand</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#B45309', margin: '0.25rem 0' }}>
            {predictedDemand}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>AI 7-Day Peak</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Shortage / Surplus</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: isShortage ? 'var(--danger-red)' : 'var(--success-green)', margin: '0.5rem 0' }}>
            {isShortage ? `${Math.abs(shortageSurplus)} Bed Shortage` : `${shortageSurplus} Bed Surplus`}
          </div>
          <span className={`badge ${isShortage ? 'badge-shortage' : 'badge-sufficient'}`}>
            {isShortage ? 'Shortage Warning' : 'Sufficient'}
          </span>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Capacity Utilization</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {utilization}%
          </div>
          <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px', marginTop: '6px', overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(100, utilization)}%`, height: '100%', backgroundColor: utilization > 85 ? 'var(--danger-red)' : 'var(--primary-blue)' }} />
          </div>
        </div>
      </div>

      {/* 7-Day Interactive Forecast Chart */}
      <div className="panel-card">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">
              {activeTab} — 7-Day Demand Forecast (Used vs Available vs Forecast)
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Primary Data: Royal Blue | Forecast Demand: Gold | Capacity Reference: Green
            </span>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>Forecasting Model:</label>
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              <option value="XGBoost">XGBoost (Operational)</option>
              <option value="Prophet">Facebook Prophet</option>
              <option value="LSTM">PyTorch LSTM</option>
            </select>
          </div>
        </div>

        <div style={{ height: '320px', width: '100%' }}>
          {loading ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Loading {activeTab} forecast data...
            </div>
          ) : fetchError ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.75rem' }}>
              <div className="error-alert" style={{ margin: 0 }}>{fetchError}</div>
              <button className="btn-secondary" onClick={fetchBedsData} style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}>
                Retry Loading
              </button>
            </div>
          ) : forecastData.length === 0 ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              No forecast observations available for {activeTab}.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecastData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" stroke="#64748B" style={{ fontSize: '0.75rem' }} />
                <YAxis stroke="#64748B" style={{ fontSize: '0.75rem' }} label={{ value: 'Beds', angle: -90, position: 'insideLeft', style: { fill: '#64748B', fontSize: '0.75rem' } }} />
                <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '6px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '10px' }} />
                
                {/* Royal Blue for primary actual data */}
                <Line type="monotone" dataKey="Actual Demand" stroke="#1455C0" strokeWidth={2.5} connectNulls name="Historical Occupancy" />
                
                {/* Yellow/Gold for forecast demand */}
                <Line type="monotone" dataKey="Forecasted Demand" stroke="#F4C430" strokeWidth={3} strokeDasharray="5 5" name="Forecasted Demand" />
                
                {/* Green for sufficient available capacity */}
                <Line type="monotone" dataKey="Available Capacity" stroke="#16A34A" strokeWidth={1.5} name="Total Bed Capacity" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Historical Entries Table */}
      <div className="panel-card">
        <h3 className="chart-title" style={{ marginBottom: '0.85rem' }}>Operational Bed Records ({activeTab})</h3>
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Available Capacity</th>
                <th>Occupied Count</th>
                <th>Required Target</th>
                <th>Status</th>
                <th>Provenance</th>
                <th>Created By</th>
                {currentUser?.role === 'ADMIN' && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No manual records found for {activeTab}. Click "+ Add Bed Data" to record operational counts.
                  </td>
                </tr>
              ) : (
                records.map(r => {
                  const diff = r.available_count - r.required_count;
                  return (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600 }}>{r.date}</td>
                      <td>{Math.ceil(r.available_count)} beds</td>
                      <td>{Math.ceil(r.occupied_count)} beds</td>
                      <td>{Math.ceil(r.required_count)} beds</td>
                      <td>
                        <span className={`badge ${diff < 0 ? 'badge-shortage' : 'badge-sufficient'}`}>
                          {diff < 0 ? 'Shortage' : 'Sufficient'}
                        </span>
                      </td>
                      <td>
                        <span className="badge badge-prov">
                          {r.source_type || 'Historical'}
                        </span>
                      </td>
                      <td>{r.created_by_username || 'System Seed'}</td>
                      {currentUser?.role === 'ADMIN' && (
                        <td>
                          <button 
                            style={{ background: 'transparent', border: 'none', color: 'var(--danger-red)', cursor: 'pointer' }}
                            onClick={() => handleDelete(r.id)}
                            title="Delete Record"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Bed Record Modal Form */}
      {showForm && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3 className="modal-title">Add {activeTab} Data</h3>
              <button className="modal-close-btn" onClick={() => setShowForm(false)}>&times;</button>
            </div>

            <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Record Date</label>
                <input 
                  type="date" 
                  name="date"
                  required
                  value={formData.date}
                  onChange={handleInputChange}
                  className="form-control"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Available Capacity (beds)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="available_count"
                    required
                    min="0"
                    step="1"
                    placeholder="e.g. 50"
                    value={formData.available_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>beds</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Occupied Beds (beds)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="occupied_count"
                    required
                    min="0"
                    step="1"
                    placeholder="e.g. 15"
                    value={formData.occupied_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>beds</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Required Target (beds)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="required_count"
                    required
                    min="0"
                    step="1"
                    placeholder="e.g. 20"
                    value={formData.required_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>beds</span>
                </div>
              </div>

              {errorMsg && <div className="error-alert">{errorMsg}</div>}
              {successMsg && <div className="success-alert">{successMsg}</div>}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '0.5rem' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Save Bed Data</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
