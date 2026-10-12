import React, { useState, useEffect } from 'react';
import { Truck, Plus, Trash2, Calendar } from 'lucide-react';
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

export default function AmbulanceDashboard({ currentUser }) {
  const [records, setRecords] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [selectedModel, setSelectedModel] = useState('XGBoost');
  
  // Form State
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    total_ambulances: '',
    available_count: '',
    used_count: '',
    under_maintenance_count: '',
    required_count: '',
    notes: ''
  });

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchAmbulanceData = async () => {
    setLoading(true);
    try {
      const allRecords = await apiService.getResources('ambulance');
      setRecords(allRecords);

      // Derive Ambulance Demand Forecast based on ED Arrivals Forecast (1 per 6 arrivals, ceiling rounded)
      const edForecast = await apiService.getForecast('ED', selectedModel);
      if (edForecast && edForecast.predictions) {
        setForecastData(edForecast.predictions.map(p => ({
          date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
          'Ambulance Usage': p.actual_demand !== null ? Math.ceil(p.actual_demand / 6) : null,
          'Required Ambulances Forecast': Math.ceil(p.predicted_demand / 6),
          'Available Fleet': 10
        })));
      }
    } catch (err) {
      console.error("Error fetching ambulance data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAmbulanceData();
  }, [selectedModel]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const ta = parseFloat(formData.total_ambulances);
    const ac = parseFloat(formData.available_count);
    const uc = parseFloat(formData.used_count);
    const um = parseFloat(formData.under_maintenance_count);
    const rc = parseFloat(formData.required_count);

    if (isNaN(ta) || isNaN(ac) || isNaN(uc) || isNaN(um) || isNaN(rc)) {
      setErrorMsg('All ambulance counts must be numbers.');
      return;
    }

    if (!Number.isInteger(ta) || !Number.isInteger(ac) || !Number.isInteger(uc) || !Number.isInteger(um) || !Number.isInteger(rc)) {
      setErrorMsg('Ambulance counts must be whole integers.');
      return;
    }

    if (ta < 0 || ac < 0 || uc < 0 || um < 0 || rc < 0) {
      setErrorMsg('Negative counts are not allowed.');
      return;
    }

    if (ac + uc + um > ta) {
      setErrorMsg('Active, available and maintenance ambulances cannot exceed total fleet.');
      return;
    }

    try {
      await apiService.createResourceRecord('ambulance', {
        date: formData.date,
        total_ambulances: parseInt(formData.total_ambulances),
        available_count: parseInt(formData.available_count),
        used_count: parseInt(formData.used_count),
        under_maintenance_count: parseInt(formData.under_maintenance_count),
        required_count: parseInt(formData.required_count),
        notes: formData.notes
      });
      setSuccessMsg('Ambulance record saved!');
      setFormData({
        date: new Date().toISOString().split('T')[0],
        total_ambulances: '',
        available_count: '',
        used_count: '',
        under_maintenance_count: '',
        required_count: '',
        notes: ''
      });
      setShowForm(false);
      fetchAmbulanceData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save ambulance record.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this ambulance record?")) return;
    try {
      await apiService.deleteResourceRecord('ambulance', id);
      fetchAmbulanceData();
    } catch (err) {
      alert(err.message || 'Failed to delete ambulance record.');
    }
  };

  const latestRecord = records[0] || {
    total_ambulances: 12,
    available_count: 5,
    used_count: 5,
    under_maintenance_count: 2,
    required_count: 6,
    notes: 'Standard operational fleet counts'
  };

  const totalAmbulances = Math.ceil(latestRecord.total_ambulances);
  const availableFleet = Math.ceil(latestRecord.available_count);
  const inService = Math.ceil(latestRecord.used_count);
  const underMaintenance = Math.ceil(latestRecord.under_maintenance_count);
  const requiredDispatch = Math.ceil(latestRecord.required_count);
  const forecastedRequirement = forecastData.length > 0 ? Math.ceil(forecastData[0]['Required Ambulances Forecast'] || requiredDispatch) : requiredDispatch;
  const shortageSurplus = availableFleet - requiredDispatch;
  const isShortage = shortageSurplus < 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header */}
      <div className="page-header-bar">
        <div>
          <h2 className="page-title">
            <Truck size={24} color="var(--primary-blue)" />
            AMBULANCE RESOURCE MANAGEMENT
          </h2>
          <p className="page-subtitle">Emergency fleet dispatch, turnaround metrics, garage maintenance, and demand forecasting.</p>
        </div>

        {currentUser?.role !== 'VIEWER' && (
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={16} />
            <span>+ Add Ambulance Data</span>
          </button>
        )}
      </div>

      {/* Overview Cards (Whole Numbers) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
        <div className="panel-card panel-card-accent-blue" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Total Fleet</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-blue)', margin: '0.25rem 0' }}>
            {totalAmbulances}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Registered Vehicles</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Available Fleet</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--success-green)', margin: '0.25rem 0' }}>
            {availableFleet}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Standby / Ready</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">In Service (Active)</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {inService}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Currently Dispatched</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Under Maintenance</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--warning-amber)', margin: '0.25rem 0' }}>
            {underMaintenance}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Service Garage</div>
        </div>

        <div className="panel-card panel-card-accent-gold" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Required Dispatch</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#B45309', margin: '0.25rem 0' }}>
            {requiredDispatch}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target Fleet Demand</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Forecasted Requirement</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-blue)', margin: '0.25rem 0' }}>
            {forecastedRequirement}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>AI 7-Day Peak Demand</div>
        </div>
      </div>

      {/* 7-Day Fleet Usage & Demand Chart */}
      <div className="panel-card">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">Ambulance Demand 7-Day Forecast</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Ambulance Usage (Royal Blue) vs Required Ambulances Forecast (Gold) vs Available Fleet (Green)
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>Baseline Model:</label>
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              <option value="XGBoost">XGBoost (Operational)</option>
              <option value="Prophet">Facebook Prophet</option>
              <option value="LSTM">PyTorch LSTM</option>
            </select>
          </div>
        </div>

        <div style={{ height: '320px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={forecastData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" stroke="#64748B" style={{ fontSize: '0.75rem' }} />
              <YAxis stroke="#64748B" style={{ fontSize: '0.75rem' }} label={{ value: 'Ambulances', angle: -90, position: 'insideLeft', style: { fill: '#64748B', fontSize: '0.75rem' } }} />
              <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '6px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
              <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '10px' }} />
              <Line type="monotone" dataKey="Ambulance Usage" stroke="#1455C0" strokeWidth={2.5} connectNulls name="Dispatched Ambulances" />
              <Line type="monotone" dataKey="Required Ambulances Forecast" stroke="#F4C430" strokeWidth={3} strokeDasharray="5 5" name="Required Ambulances Forecast" />
              <Line type="monotone" dataKey="Available Fleet" stroke="#16A34A" strokeWidth={1.5} name="Total Fleet Capacity" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Historical Entries Table */}
      <div className="panel-card">
        <h3 className="chart-title" style={{ marginBottom: '0.85rem' }}>Historical Fleet Logs</h3>
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Total Fleet</th>
                <th>Available</th>
                <th>In Service</th>
                <th>Maintenance</th>
                <th>Required</th>
                <th>Status</th>
                <th>Provenance</th>
                <th>Notes</th>
                {currentUser?.role === 'ADMIN' && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr>
                  <td colSpan="10" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No fleet records found. Click "+ Add Ambulance Data" to log vehicle dispatches.
                  </td>
                </tr>
              ) : (
                records.map(r => {
                  const diff = r.available_count - r.required_count;
                  return (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600 }}>{r.date}</td>
                      <td>{Math.ceil(r.total_ambulances)}</td>
                      <td><strong>{Math.ceil(r.available_count)}</strong></td>
                      <td>{Math.ceil(r.used_count)}</td>
                      <td>{Math.ceil(r.under_maintenance_count)}</td>
                      <td>{Math.ceil(r.required_count)}</td>
                      <td>
                        <span className={`badge ${diff < 0 ? 'badge-shortage' : 'badge-sufficient'}`}>
                          {diff < 0 ? 'Shortage' : 'Sufficient'}
                        </span>
                      </td>
                      <td>
                        <span className="badge badge-prov">{r.source_type || 'Configured Parameters'}</span>
                      </td>
                      <td>{r.notes || '—'}</td>
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

      {/* Modal Form */}
      {showForm && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3 className="modal-title">Add Ambulance Data</h3>
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
                <label className="form-label">Total Fleet Pool</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="total_ambulances"
                    required min="0" step="1" placeholder="e.g. 15"
                    value={formData.total_ambulances}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Available (Standby / Ready)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="available_count"
                    required min="0" step="1" placeholder="e.g. 8"
                    value={formData.available_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Active Dispatched</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="used_count"
                    required min="0" step="1" placeholder="e.g. 5"
                    value={formData.used_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Under Maintenance / Garage</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="under_maintenance_count"
                    required min="0" step="1" placeholder="e.g. 2"
                    value={formData.under_maintenance_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Required Dispatch Target</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="required_count"
                    required min="0" step="1" placeholder="e.g. 6"
                    value={formData.required_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Notes</label>
                <input 
                  type="text" 
                  name="notes"
                  placeholder="e.g. 2 ambulances scheduled for engine overhaul"
                  value={formData.notes}
                  onChange={handleInputChange}
                  className="form-control"
                />
              </div>

              {errorMsg && <div className="error-alert">{errorMsg}</div>}
              {successMsg && <div className="success-alert">{successMsg}</div>}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '0.5rem' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Save Ambulance Data</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
