import React, { useState, useEffect } from 'react';
import { Droplet, Plus, Trash2, Calendar, FileText, AlertTriangle } from 'lucide-react';
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

export default function BloodDashboard({ currentUser }) {
  const [records, setRecords] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState('All');
  const [selectedModel, setSelectedModel] = useState('XGBoost');
  
  // Data Entry state
  const [showForm, setShowForm] = useState(false);
  const [bulkMode, setBulkMode] = useState(false);
  
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    blood_group: 'A+',
    available_units: '',
    used_units: '',
    received_units: '',
    reserved_units: '',
    required_units: ''
  });

  const [bulkDate, setBulkDate] = useState(new Date().toISOString().split('T')[0]);
  const [bulkGroups, setBulkGroups] = useState({
    'A+': { available: '', used: '', received: '', reserved: '', required: '' },
    'A-': { available: '', used: '', received: '', reserved: '', required: '' },
    'B+': { available: '', used: '', received: '', reserved: '', required: '' },
    'B-': { available: '', used: '', received: '', reserved: '', required: '' },
    'AB+': { available: '', used: '', received: '', reserved: '', required: '' },
    'AB-': { available: '', used: '', received: '', reserved: '', required: '' },
    'O+': { available: '', used: '', received: '', reserved: '', required: '' },
    'O-': { available: '', used: '', received: '', reserved: '', required: '' }
  });

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  const bloodGroups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

  const fetchBloodData = async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const allRecords = await apiService.getResources('blood');
      setRecords(allRecords);

      // Fetch 7-Day Blood forecast from canonical multi-resource endpoint (derived from ED arrivals: 0.20 units/patient)
      const multiRes = await apiService.getMultiResourceForecast(selectedModel);
      const bloodRes = multiRes?.resources?.["Blood Demand"];
      if (bloodRes && bloodRes.predictions && bloodRes.predictions.length > 0) {
        setForecastData(bloodRes.predictions.map(p => ({
          date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
          'Blood Usage': p.actual_demand !== null ? Math.ceil(p.actual_demand) : null,
          '7-Day Blood Demand Forecast': Math.ceil(p.operational_requirement !== undefined ? p.operational_requirement : p.predicted_demand),
          'Available Blood Capacity': Math.ceil(p.capacity || 10.0)
        })));
      } else {
        setForecastData([]);
      }
    } catch (err) {
      console.error("Error fetching blood data:", err);
      setFetchError(err.message || 'Failed to load blood forecasting data.');
      setForecastData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBloodData();
  }, [selectedModel]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleBulkGroupChange = (group, field, value) => {
    setBulkGroups(prev => ({
      ...prev,
      [group]: {
        ...prev[group],
        [field]: value
      }
    }));
  };

  const handleIndividualSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const av = parseFloat(formData.available_units);
    const us = parseFloat(formData.used_units);
    const rc = parseFloat(formData.received_units);
    const rs = parseFloat(formData.reserved_units);
    const rq = parseFloat(formData.required_units);

    if (isNaN(av) || isNaN(us) || isNaN(rc) || isNaN(rs) || isNaN(rq)) {
      setErrorMsg('All blood unit counts must be numeric.');
      return;
    }

    if (!Number.isInteger(av) || !Number.isInteger(us) || !Number.isInteger(rc) || !Number.isInteger(rs) || !Number.isInteger(rq)) {
      setErrorMsg('Blood units must be whole numbers.');
      return;
    }

    if (av < 0 || us < 0 || rc < 0 || rs < 0 || rq < 0) {
      setErrorMsg('Negative counts are not allowed.');
      return;
    }

    try {
      await apiService.createResourceRecord('blood', {
        date: formData.date,
        blood_group: formData.blood_group,
        available_units: parseInt(formData.available_units),
        used_units: parseInt(formData.used_units),
        received_units: parseInt(formData.received_units),
        reserved_units: parseInt(formData.reserved_units),
        required_units: parseInt(formData.required_units)
      });
      setSuccessMsg('Blood inventory record saved!');
      setShowForm(false);
      fetchBloodData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save blood record.');
    }
  };

  const handleBulkSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const groupsToSave = [];
    for (const [group, vals] of Object.entries(bulkGroups)) {
      const av = parseFloat(vals.available);
      const us = parseFloat(vals.used);
      const rc = parseFloat(vals.received);
      const rs = parseFloat(vals.reserved);
      const rq = parseFloat(vals.required);

      if (isNaN(av) || isNaN(us) || isNaN(rc) || isNaN(rs) || isNaN(rq)) {
        setErrorMsg(`Missing or non-numeric counts in group ${group}.`);
        return;
      }
      if (!Number.isInteger(av) || !Number.isInteger(us) || !Number.isInteger(rc) || !Number.isInteger(rs) || !Number.isInteger(rq)) {
        setErrorMsg(`Decimals rejected. Group ${group} requires whole integers.`);
        return;
      }
      if (av < 0 || us < 0 || rc < 0 || rs < 0 || rq < 0) {
        setErrorMsg(`Negative values rejected in group ${group}.`);
        return;
      }

      groupsToSave.push({
        date: bulkDate,
        blood_group: group,
        available_units: parseInt(vals.available),
        used_units: parseInt(vals.used),
        received_units: parseInt(vals.received),
        reserved_units: parseInt(vals.reserved),
        required_units: parseInt(vals.required)
      });
    }

    try {
      for (const item of groupsToSave) {
        await apiService.createResourceRecord('blood', item);
      }
      setSuccessMsg('Bulk inventory for all 8 blood groups saved!');
      setShowForm(false);
      fetchBloodData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save bulk blood inventory.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this blood record?")) return;
    try {
      await apiService.deleteResourceRecord('blood', id);
      fetchBloodData();
    } catch (err) {
      alert(err.message || 'Failed to delete blood record.');
    }
  };

  // Group summary calculations (Strict Whole Numbers)
  const latestSummary = bloodGroups.map(group => {
    const groupRecords = records.filter(r => r.blood_group === group);
    return groupRecords[0] || {
      blood_group: group,
      available_units: group.includes('+') ? 25 : 10,
      used_units: group.includes('+') ? 8 : 3,
      required_units: group.includes('+') ? 12 : 5,
      received_units: 0,
      reserved_units: 0,
      source_type: 'Configured Parameters'
    };
  });

  const filteredSummary = selectedGroup === 'All' 
    ? latestSummary 
    : latestSummary.filter(s => s.blood_group === selectedGroup);

  const totalAvailable = Math.ceil(latestSummary.reduce((acc, s) => acc + s.available_units, 0));
  const totalUsed = Math.ceil(latestSummary.reduce((acc, s) => acc + s.used_units, 0));
  const totalRequired = Math.ceil(latestSummary.reduce((acc, s) => acc + s.required_units, 0));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header */}
      <div className="page-header-bar">
        <div>
          <h2 className="page-title">
            <Droplet size={24} color="var(--primary-blue)" />
            BLOOD RESOURCE MANAGEMENT
          </h2>
          <p className="page-subtitle">Group-wise blood bank inventory, transfusion demand, and supply reserves.</p>
        </div>

        {currentUser?.role !== 'VIEWER' && (
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={16} />
            <span>+ Add Blood Inventory</span>
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
          <strong>Simulated Heuristic Forecast Notice:</strong> 7-Day Blood Demand forecast is mathematically derived from Emergency Department patient arrival projections (0.20 units per arrival; emergency reserve capacity: 10.0 Units). Group-wise blood bank inventories below reflect logged physical ward reserves.
        </div>
      </div>

      {/* Aggregate Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div className="panel-card panel-card-accent-blue" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Total Blood Inventory</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-blue)', margin: '0.25rem 0' }}>
            {totalAvailable}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Combined Units Available</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Total Blood Usage Today</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {totalUsed}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Transfused Units</div>
        </div>

        <div className="panel-card panel-card-accent-gold" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Total Required Target</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#B45309', margin: '0.25rem 0' }}>
            {totalRequired}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Daily Reserve Target</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Inventory Status</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: totalAvailable >= totalRequired ? 'var(--success-green)' : 'var(--danger-red)', margin: '0.5rem 0' }}>
            {totalAvailable >= totalRequired ? `${totalAvailable - totalRequired} Units Surplus` : `${totalRequired - totalAvailable} Units Shortage`}
          </div>
          <span className={`badge ${totalAvailable >= totalRequired ? 'badge-sufficient' : 'badge-shortage'}`}>
            {totalAvailable >= totalRequired ? 'Sufficient Reserves' : 'Replenishment Needed'}
          </span>
        </div>
      </div>

      {/* Individual Blood Group Inventory Grid / Table */}
      <div className="panel-card">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">Blood Group-Wise Inventory (All 8 Groups)</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Individual status monitoring for A+, A-, B+, B-, AB+, AB-, O+, O-
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>Filter Group:</label>
            <select value={selectedGroup} onChange={(e) => setSelectedGroup(e.target.value)}>
              <option value="All">All Groups</option>
              {bloodGroups.map(bg => <option key={bg} value={bg}>{bg}</option>)}
            </select>
          </div>
        </div>

        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Blood Group</th>
                <th>Available Units</th>
                <th>Used Today</th>
                <th>Required Units</th>
                <th>Forecast Demand</th>
                <th>Status</th>
                <th>Provenance</th>
              </tr>
            </thead>
            <tbody>
              {filteredSummary.map(row => {
                const diff = row.available_units - row.required_units;
                const isShort = diff < 0;
                const forecastGroupDemand = Math.ceil(row.required_units * 1.1);

                return (
                  <tr key={row.blood_group}>
                    <td style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--primary-blue)' }}>
                      {row.blood_group}
                    </td>
                    <td><strong>{Math.ceil(row.available_units)}</strong> units</td>
                    <td>{Math.ceil(row.used_units)} units</td>
                    <td>{Math.ceil(row.required_units)} units</td>
                    <td style={{ color: 'var(--primary-blue)', fontWeight: 600 }}>{forecastGroupDemand} units</td>
                    <td>
                      <span className={`badge ${isShort ? 'badge-shortage' : 'badge-sufficient'}`}>
                        {isShort ? 'Shortage' : 'Sufficient'}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-prov">{row.source_type || 'Configured Parameters'}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 7-Day Blood Demand Forecast Chart */}
      <div className="panel-card">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">7-Day Blood Demand Forecast</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Blood Usage (Royal Blue) vs 7-Day Forecast (Gold, Units) vs Canonical Emergency Capacity (Green, 10.0 Units)
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
              Loading blood forecast data...
            </div>
          ) : fetchError ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.75rem' }}>
              <div className="error-alert" style={{ margin: 0 }}>{fetchError}</div>
              <button className="btn-secondary" onClick={fetchBloodData} style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}>
                Retry Loading
              </button>
            </div>
          ) : forecastData.length === 0 ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              No blood forecast observations available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecastData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" stroke="#64748B" style={{ fontSize: '0.75rem' }} />
                <YAxis stroke="#64748B" style={{ fontSize: '0.75rem' }} label={{ value: 'Units', angle: -90, position: 'insideLeft', style: { fill: '#64748B', fontSize: '0.75rem' } }} />
                <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '6px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '10px' }} />
                <Line type="monotone" dataKey="Blood Usage" stroke="#1455C0" strokeWidth={2.5} connectNulls name="Blood Usage" />
                <Line type="monotone" dataKey="7-Day Blood Demand Forecast" stroke="#F4C430" strokeWidth={3} strokeDasharray="5 5" name="7-Day Blood Demand Forecast" />
                <Line type="monotone" dataKey="Available Blood Capacity" stroke="#16A34A" strokeWidth={1.5} name="Available Blood Capacity (10.0 Units)" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Modal Form */}
      {showForm && (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ maxWidth: bulkMode ? '720px' : '480px' }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h3 className="modal-title">Add Blood Inventory</h3>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button 
                    type="button" 
                    className={`tab-btn-pill ${!bulkMode ? 'active' : ''}`}
                    onClick={() => setBulkMode(false)}
                    style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}
                  >
                    Single Group
                  </button>
                  <button 
                    type="button" 
                    className={`tab-btn-pill ${bulkMode ? 'active' : ''}`}
                    onClick={() => setBulkMode(true)}
                    style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}
                  >
                    All 8 Groups
                  </button>
                </div>
              </div>
              <button className="modal-close-btn" onClick={() => setShowForm(false)}>&times;</button>
            </div>

            {bulkMode ? (
              <form onSubmit={handleBulkSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="form-group" style={{ width: '200px' }}>
                  <label className="form-label">Record Date</label>
                  <input 
                    type="date" 
                    value={bulkDate}
                    required
                    onChange={(e) => setBulkDate(e.target.value)}
                    className="form-control"
                  />
                </div>

                <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                  <table style={{ width: '100%', fontSize: '0.8rem' }}>
                    <thead>
                      <tr>
                        <th>Group</th>
                        <th>Available</th>
                        <th>Used</th>
                        <th>Received</th>
                        <th>Reserved</th>
                        <th>Required</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bloodGroups.map(bg => (
                        <tr key={bg}>
                          <td style={{ fontWeight: 700, color: 'var(--primary-blue)' }}>{bg}</td>
                          <td>
                            <input 
                              type="number" 
                              required min="0" step="1" placeholder="0"
                              style={{ width: '65px', padding: '0.25rem' }}
                              value={bulkGroups[bg].available}
                              onChange={(e) => handleBulkGroupChange(bg, 'available', e.target.value)}
                            />
                          </td>
                          <td>
                            <input 
                              type="number" 
                              required min="0" step="1" placeholder="0"
                              style={{ width: '65px', padding: '0.25rem' }}
                              value={bulkGroups[bg].used}
                              onChange={(e) => handleBulkGroupChange(bg, 'used', e.target.value)}
                            />
                          </td>
                          <td>
                            <input 
                              type="number" 
                              required min="0" step="1" placeholder="0"
                              style={{ width: '65px', padding: '0.25rem' }}
                              value={bulkGroups[bg].received}
                              onChange={(e) => handleBulkGroupChange(bg, 'received', e.target.value)}
                            />
                          </td>
                          <td>
                            <input 
                              type="number" 
                              required min="0" step="1" placeholder="0"
                              style={{ width: '65px', padding: '0.25rem' }}
                              value={bulkGroups[bg].reserved}
                              onChange={(e) => handleBulkGroupChange(bg, 'reserved', e.target.value)}
                            />
                          </td>
                          <td>
                            <input 
                              type="number" 
                              required min="0" step="1" placeholder="0"
                              style={{ width: '65px', padding: '0.25rem' }}
                              value={bulkGroups[bg].required}
                              onChange={(e) => handleBulkGroupChange(bg, 'required', e.target.value)}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {errorMsg && <div className="error-alert">{errorMsg}</div>}
                {successMsg && <div className="success-alert">{successMsg}</div>}

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '0.5rem' }}>
                  <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                  <button type="submit" className="btn-primary">Save All 8 Groups</button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleIndividualSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
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
                  <label className="form-label">Blood Group</label>
                  <select name="blood_group" value={formData.blood_group} onChange={handleInputChange} className="form-control">
                    {bloodGroups.map(bg => <option key={bg} value={bg}>{bg}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Available Units (units)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input 
                      type="number" 
                      name="available_units"
                      required min="0" step="1" placeholder="e.g. 25"
                      value={formData.available_units}
                      onChange={handleInputChange}
                      className="form-control"
                      style={{ flex: 1 }}
                    />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Used Units Today (units)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input 
                      type="number" 
                      name="used_units"
                      required min="0" step="1" placeholder="e.g. 8"
                      value={formData.used_units}
                      onChange={handleInputChange}
                      className="form-control"
                      style={{ flex: 1 }}
                    />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Received Today (units)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input 
                      type="number" 
                      name="received_units"
                      required min="0" step="1" placeholder="e.g. 5"
                      value={formData.received_units}
                      onChange={handleInputChange}
                      className="form-control"
                      style={{ flex: 1 }}
                    />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Reserved Units (units)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input 
                      type="number" 
                      name="reserved_units"
                      required min="0" step="1" placeholder="e.g. 2"
                      value={formData.reserved_units}
                      onChange={handleInputChange}
                      className="form-control"
                      style={{ flex: 1 }}
                    />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Required Units Target (units)</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input 
                      type="number" 
                      name="required_units"
                      required min="0" step="1" placeholder="e.g. 15"
                      value={formData.required_units}
                      onChange={handleInputChange}
                      className="form-control"
                      style={{ flex: 1 }}
                    />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                  </div>
                </div>

                {errorMsg && <div className="error-alert">{errorMsg}</div>}
                {successMsg && <div className="success-alert">{successMsg}</div>}

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '0.5rem' }}>
                  <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                  <button type="submit" className="btn-primary">Save Blood Data</button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
