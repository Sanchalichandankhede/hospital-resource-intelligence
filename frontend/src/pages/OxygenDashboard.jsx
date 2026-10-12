import React, { useState, useEffect } from 'react';
import { Wind, Plus, Trash2, Calendar, AlertTriangle } from 'lucide-react';
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

export default function OxygenDashboard({ currentUser }) {
  const [records, setRecords] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [selectedModel, setSelectedModel] = useState('XGBoost');
  
  // Data Entry Form State
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    total_cylinders: '',
    available_cylinders: '',
    used_cylinders: '',
    filled_refilled: '',
    required_cylinders: '',
    notes: ''
  });
  
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  const fetchOxygenData = async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const allRecords = await apiService.getResources('oxygen');
      setRecords(allRecords);

      // Fetch 7-Day Oxygen forecast from canonical multi-resource endpoint (Liters; 100.0 L capacity)
      const multiRes = await apiService.getMultiResourceForecast(selectedModel);
      const oxygenRes = multiRes?.resources?.["Oxygen Demand"];
      if (oxygenRes && oxygenRes.predictions && oxygenRes.predictions.length > 0) {
        setForecastData(oxygenRes.predictions.map(p => ({
          date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
          'Oxygen Usage': p.actual_demand !== null ? parseFloat(p.actual_demand.toFixed(2)) : null,
          'Oxygen Requirement Forecast': parseFloat((p.operational_requirement !== undefined ? p.operational_requirement : p.predicted_demand).toFixed(2)),
          'Available Oxygen Capacity': parseFloat((p.capacity || 100.0).toFixed(2))
        })));
      } else {
        setForecastData([]);
      }
    } catch (err) {
      console.error("Error fetching oxygen data:", err);
      setFetchError(err.message || 'Failed to load oxygen forecasting data.');
      setForecastData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOxygenData();
  }, [selectedModel]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const tc = parseFloat(formData.total_cylinders);
    const ac = parseFloat(formData.available_cylinders);
    const uc = parseFloat(formData.used_cylinders);
    const fr = parseFloat(formData.filled_refilled);
    const rc = parseFloat(formData.required_cylinders);

    if (isNaN(tc) || isNaN(ac) || isNaN(uc) || isNaN(fr) || isNaN(rc)) {
      setErrorMsg('All cylinder counts must be numeric.');
      return;
    }

    if (!Number.isInteger(tc) || !Number.isInteger(ac) || !Number.isInteger(uc) || !Number.isInteger(fr) || !Number.isInteger(rc)) {
      setErrorMsg('Cylinder counts must be whole integers.');
      return;
    }

    if (tc < 0 || ac < 0 || uc < 0 || fr < 0 || rc < 0) {
      setErrorMsg('Negative counts are not allowed.');
      return;
    }

    if (ac + uc > tc) {
      setErrorMsg('Sum of available and used cylinders cannot exceed total pool.');
      return;
    }

    try {
      await apiService.createResourceRecord('oxygen', {
        date: formData.date,
        total_cylinders: parseInt(formData.total_cylinders),
        available_cylinders: parseInt(formData.available_cylinders),
        used_cylinders: parseInt(formData.used_cylinders),
        filled_refilled: parseInt(formData.filled_refilled),
        required_cylinders: parseInt(formData.required_cylinders),
        notes: formData.notes
      });
      setSuccessMsg('Oxygen log saved successfully!');
      setFormData({
        date: new Date().toISOString().split('T')[0],
        total_cylinders: '',
        available_cylinders: '',
        used_cylinders: '',
        filled_refilled: '',
        required_cylinders: '',
        notes: ''
      });
      setShowForm(false);
      fetchOxygenData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save oxygen log.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this oxygen log?")) return;
    try {
      await apiService.deleteResourceRecord('oxygen', id);
      fetchOxygenData();
    } catch (err) {
      alert(err.message || 'Failed to delete oxygen log.');
    }
  };

  const latestRecord = records[0] || {
    total_cylinders: 80,
    available_cylinders: 45,
    used_cylinders: 32,
    filled_refilled: 12,
    required_cylinders: 35,
    notes: 'Default baseline logistics'
  };

  const totalCylinders = Math.ceil(latestRecord.total_cylinders);
  const availableCylinders = Math.ceil(latestRecord.available_cylinders);
  const usedCylinders = Math.ceil(latestRecord.used_cylinders);
  const emptyCylinders = Math.max(0, totalCylinders - (availableCylinders + usedCylinders));
  const requiredCylinders = Math.ceil(latestRecord.required_cylinders);
  const forecastedOxygenLiters = forecastData.length > 0 && forecastData[0]['Oxygen Requirement Forecast'] !== undefined 
    ? parseFloat(forecastData[0]['Oxygen Requirement Forecast']).toFixed(1) 
    : '—';
  const shortageSurplus = availableCylinders - requiredCylinders;
  const isShortage = shortageSurplus < 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header */}
      <div className="page-header-bar">
        <div>
          <h2 className="page-title">
            <Wind size={24} color="var(--primary-blue)" />
            OXYGEN RESOURCE MANAGEMENT
          </h2>
          <p className="page-subtitle">Medical oxygen cylinders, consumption monitoring, refills, and forecasting.</p>
        </div>

        {currentUser?.role !== 'VIEWER' && (
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={16} />
            <span>+ Add Oxygen Data</span>
          </button>
        )}
      </div>

      {/* Simulated Heuristic Forecast Notice Banner */}
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
          <strong>Simulated Heuristic Forecast Notice:</strong> 7-Day Oxygen Demand is mathematically simulated from ICU bed occupancy (15.0 L/day per bed) and Emergency Department admissions (5.0 L/day per bed), with a canonical capacity of 100.0 Liters. Physical on-site cylinder counts reflect discrete ward inventory logs.
        </div>
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '1rem' }}>
        <div className="panel-card panel-card-accent-blue" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Available Cylinders</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-blue)', margin: '0.25rem 0' }}>
            {availableCylinders}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Filled &amp; Ready</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Cylinders In Use</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {usedCylinders}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Active Consumption</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Cylinders Remaining</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {emptyCylinders}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Empty / Awaiting Refill</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Daily Oxygen Requirement</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {requiredCylinders}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target Cylinders / Day</div>
        </div>

        <div className="panel-card panel-card-accent-gold" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Forecasted Demand (L)</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#B45309', margin: '0.25rem 0' }}>
            {forecastedOxygenLiters} L
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>7-Day Model (100.0 L Cap)</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Status</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: isShortage ? 'var(--danger-red)' : 'var(--success-green)', margin: '0.5rem 0' }}>
            {isShortage ? `${Math.abs(shortageSurplus)} Cyl. Shortage` : `${shortageSurplus} Cyl. Surplus`}
          </div>
          <span className={`badge ${isShortage ? 'badge-shortage' : 'badge-sufficient'}`}>
            {isShortage ? 'Refill Required' : 'Sufficient Stock'}
          </span>
        </div>
      </div>

      {/* OXYGEN CYLINDER STATUS Breakdown Box */}
      <div className="panel-card">
        <h3 className="chart-title" style={{ marginBottom: '0.75rem' }}>OXYGEN CYLINDER STATUS</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', background: 'var(--bg-card-alt)', padding: '1rem', borderRadius: '6px' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>AVAILABLE</span>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--success-green)' }}>{availableCylinders} cylinders</div>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>IN USE</span>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary-blue)' }}>{usedCylinders} cylinders</div>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>UNDER MAINTENANCE / EMPTY</span>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--warning-amber)' }}>{emptyCylinders} cylinders</div>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL STOCK POOL</span>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>{totalCylinders} cylinders</div>
          </div>
        </div>
      </div>

      {/* 7-Day Oxygen Graph */}
      <div className="panel-card">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">Oxygen Demand 7-Day Graph (Liters)</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Usage (Royal Blue) vs Requirement Forecast (Gold, Liters) vs Available Capacity (Green, 100.0 L)
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
          {loading ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Loading oxygen forecast data...
            </div>
          ) : fetchError ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.75rem' }}>
              <div className="error-alert" style={{ margin: 0 }}>{fetchError}</div>
              <button className="btn-secondary" onClick={fetchOxygenData} style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}>
                Retry Loading
              </button>
            </div>
          ) : forecastData.length === 0 ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              No oxygen forecast observations available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecastData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" stroke="#64748B" style={{ fontSize: '0.75rem' }} />
                <YAxis stroke="#64748B" style={{ fontSize: '0.75rem' }} label={{ value: 'Liters (L)', angle: -90, position: 'insideLeft', style: { fill: '#64748B', fontSize: '0.75rem' } }} />
                <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '6px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '10px' }} />
                <Line type="monotone" dataKey="Oxygen Usage" stroke="#1455C0" strokeWidth={2.5} connectNulls name="Oxygen Usage (L)" />
                <Line type="monotone" dataKey="Oxygen Requirement Forecast" stroke="#F4C430" strokeWidth={3} strokeDasharray="5 5" name="Oxygen Requirement Forecast (L)" />
                <Line type="monotone" dataKey="Available Oxygen Capacity" stroke="#16A34A" strokeWidth={1.5} name="Available Oxygen Capacity (100.0 L)" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Historical Oxygen Entries Table */}
      <div className="panel-card">
        <h3 className="chart-title" style={{ marginBottom: '0.85rem' }}>Historical Oxygen Logs</h3>
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Total Pool</th>
                <th>Available</th>
                <th>In Use</th>
                <th>Refilled Today</th>
                <th>Required</th>
                <th>Provenance</th>
                <th>Notes</th>
                {currentUser?.role === 'ADMIN' && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No oxygen logs recorded yet. Click "+ Add Oxygen Data" to log inventory.
                  </td>
                </tr>
              ) : (
                records.map(r => (
                  <tr key={r.id}>
                    <td style={{ fontWeight: 600 }}>{r.date}</td>
                    <td>{Math.ceil(r.total_cylinders)} cyl</td>
                    <td>{Math.ceil(r.available_cylinders)} cyl</td>
                    <td>{Math.ceil(r.used_cylinders)} cyl</td>
                    <td>{Math.ceil(r.filled_refilled)} cyl</td>
                    <td>{Math.ceil(r.required_cylinders)} cyl</td>
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
                ))
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
              <h3 className="modal-title">Add Oxygen Data</h3>
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
                <label className="form-label">Total Cylinders (Stock Pool)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="total_cylinders"
                    required
                    min="0"
                    step="1"
                    placeholder="e.g. 80"
                    value={formData.total_cylinders}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Available Cylinders (Filled)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="available_cylinders"
                    required
                    min="0"
                    step="1"
                    placeholder="e.g. 45"
                    value={formData.available_cylinders}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Cylinders in Use (Active)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="used_cylinders"
                    required
                    min="0"
                    step="1"
                    placeholder="e.g. 32"
                    value={formData.used_cylinders}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Cylinders Refilled Today</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="filled_refilled"
                    required
                    min="0"
                    step="1"
                    placeholder="e.g. 10"
                    value={formData.filled_refilled}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Daily Required Cylinders</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="required_cylinders"
                    required
                    min="0"
                    step="1"
                    placeholder="e.g. 35"
                    value={formData.required_cylinders}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Notes</label>
                <input 
                  type="text" 
                  name="notes"
                  placeholder="e.g. Ward 4 refilled in morning batch"
                  value={formData.notes}
                  onChange={handleInputChange}
                  className="form-control"
                />
              </div>

              {errorMsg && <div className="error-alert">{errorMsg}</div>}
              {successMsg && <div className="success-alert">{successMsg}</div>}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '0.5rem' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Save Oxygen Data</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
