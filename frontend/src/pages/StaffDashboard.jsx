import React, { useState, useEffect } from 'react';
import { Users, Plus, Trash2, Calendar } from 'lucide-react';
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

export default function StaffDashboard({ currentUser }) {
  const [records, setRecords] = useState([]);
  const [forecastData, setForecastData] = useState([]);
  const [activeCategory, setActiveCategory] = useState('All');
  const [selectedModel, setSelectedModel] = useState('XGBoost');
  
  // Form State
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    staff_category: 'Doctors',
    available_count: '',
    assigned_count: '',
    used_count: '',
    required_count: '',
    shift: 'Day',
    notes: ''
  });

  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const staffCategories = ["Doctors", "Nurses", "Support Staff", "Emergency Staff", "Technicians"];

  const fetchStaffData = async () => {
    setLoading(true);
    try {
      const allRecords = await apiService.getResources('staff');
      setRecords(allRecords);

      // Derive staff requirements forecast (ICU * 1.2 + ED * 0.4, ceiling rounded)
      const icuForecast = await apiService.getForecast('ICU', selectedModel);
      const edForecast = await apiService.getForecast('ED', selectedModel);
      
      if (icuForecast && icuForecast.predictions && edForecast && edForecast.predictions) {
        const staffForecast = icuForecast.predictions.map((p, idx) => {
          const edPred = edForecast.predictions[idx] ? edForecast.predictions[idx].predicted_demand : 0;
          const edAct = edForecast.predictions[idx] ? edForecast.predictions[idx].actual_demand : null;
          return {
            date: new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
            'Actual Staff Active': p.actual_demand !== null && edAct !== null ? Math.ceil(p.actual_demand * 1.2 + edAct * 0.4) : null,
            'Forecasted Requirement': Math.ceil(p.predicted_demand * 1.2 + edPred * 0.4),
            'Total Staff Pool': 110
          };
        });
        setForecastData(staffForecast);
      }
    } catch (err) {
      console.error("Error fetching staff data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStaffData();
  }, [selectedModel]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const av = parseFloat(formData.available_count);
    const as = parseFloat(formData.assigned_count);
    const us = parseFloat(formData.used_count);
    const rq = parseFloat(formData.required_count);

    if (isNaN(av) || isNaN(as) || isNaN(us) || isNaN(rq)) {
      setErrorMsg('All staff counts must be numeric.');
      return;
    }

    if (!Number.isInteger(av) || !Number.isInteger(as) || !Number.isInteger(us) || !Number.isInteger(rq)) {
      setErrorMsg('Staff counts must be whole integers.');
      return;
    }

    if (av < 0 || as < 0 || us < 0 || rq < 0) {
      setErrorMsg('Negative counts are not allowed.');
      return;
    }

    try {
      await apiService.createResourceRecord('staff', {
        date: formData.date,
        staff_category: formData.staff_category,
        available_count: parseInt(formData.available_count),
        assigned_count: parseInt(formData.assigned_count),
        used_count: parseInt(formData.used_count),
        required_count: parseInt(formData.required_count),
        shift: formData.shift,
        notes: formData.notes
      });
      setSuccessMsg('Staff roster record saved!');
      setFormData({
        date: new Date().toISOString().split('T')[0],
        staff_category: 'Doctors',
        available_count: '',
        assigned_count: '',
        used_count: '',
        required_count: '',
        shift: 'Day',
        notes: ''
      });
      setShowForm(false);
      fetchStaffData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save staff record.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this staff roster log?")) return;
    try {
      await apiService.deleteResourceRecord('staff', id);
      fetchStaffData();
    } catch (err) {
      alert(err.message || 'Failed to delete staff record.');
    }
  };

  const latestSummary = staffCategories.map(cat => {
    const catRecords = records.filter(r => r.staff_category === cat);
    return catRecords[0] || {
      staff_category: cat,
      available_count: cat === 'Doctors' ? 25 : cat === 'Nurses' ? 50 : cat === 'Emergency Staff' ? 15 : cat === 'Support Staff' ? 20 : 10,
      assigned_count: cat === 'Doctors' ? 18 : cat === 'Nurses' ? 38 : cat === 'Emergency Staff' ? 10 : cat === 'Support Staff' ? 14 : 8,
      used_count: cat === 'Doctors' ? 18 : cat === 'Nurses' ? 38 : cat === 'Emergency Staff' ? 10 : cat === 'Support Staff' ? 14 : 8,
      required_count: cat === 'Doctors' ? 22 : cat === 'Nurses' ? 44 : cat === 'Emergency Staff' ? 12 : cat === 'Support Staff' ? 16 : 9,
      source_type: 'Configured Parameters'
    };
  });

  const totalAvailable = Math.ceil(latestSummary.reduce((acc, s) => acc + s.available_count, 0));
  const totalOnDuty = Math.ceil(latestSummary.reduce((acc, s) => acc + s.used_count, 0));
  const totalRequired = Math.ceil(latestSummary.reduce((acc, s) => acc + s.required_count, 0));
  const shortageSurplus = totalAvailable - totalRequired;
  const isShortage = shortageSurplus < 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header */}
      <div className="page-header-bar">
        <div>
          <h2 className="page-title">
            <Users size={24} color="var(--primary-blue)" />
            STAFF RESOURCE MANAGEMENT
          </h2>
          <p className="page-subtitle">Clinical staff allocation, duty shift rosters, and patient-to-staff demand forecasting.</p>
        </div>

        {currentUser?.role !== 'VIEWER' && (
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={16} />
            <span>+ Add Staff Data</span>
          </button>
        )}
      </div>

      {/* Overview Cards (Whole Numbers) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div className="panel-card panel-card-accent-blue" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Available Staff</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary-blue)', margin: '0.25rem 0' }}>
            {totalAvailable}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Hospital Staff Pool</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">On Duty (Active)</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', margin: '0.25rem 0' }}>
            {totalOnDuty}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Assigned to Active Shifts</div>
        </div>

        <div className="panel-card panel-card-accent-gold" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Required Staff</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#B45309', margin: '0.25rem 0' }}>
            {totalRequired}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Staffing Target Demand</div>
        </div>

        <div className="panel-card" style={{ textAlign: 'center' }}>
          <div className="strip-item-label">Shortage / Surplus</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: isShortage ? 'var(--danger-red)' : 'var(--success-green)', margin: '0.5rem 0' }}>
            {isShortage ? `${Math.abs(shortageSurplus)} Staff Shortage` : `${shortageSurplus} Staff Surplus`}
          </div>
          <span className={`badge ${isShortage ? 'badge-shortage' : 'badge-sufficient'}`}>
            {isShortage ? 'Staffing Alert' : 'Adequate Roster'}
          </span>
        </div>
      </div>

      {/* Staff Sections Table */}
      <div className="panel-card">
        <h3 className="chart-title" style={{ marginBottom: '0.85rem' }}>Staff Roster Breakdown by Category</h3>
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Available Staff</th>
                <th>Assigned Shifts</th>
                <th>On Duty Active</th>
                <th>Required Target</th>
                <th>Shortage / Surplus</th>
                <th>Provenance</th>
              </tr>
            </thead>
            <tbody>
              {latestSummary.map(row => {
                const diff = row.available_count - row.required_count;
                const isShort = diff < 0;
                return (
                  <tr key={row.staff_category}>
                    <td style={{ fontWeight: 700, color: 'var(--primary-blue)' }}>{row.staff_category}</td>
                    <td><strong>{Math.ceil(row.available_count)}</strong> staff</td>
                    <td>{Math.ceil(row.assigned_count)} staff</td>
                    <td>{Math.ceil(row.used_count)} staff</td>
                    <td>{Math.ceil(row.required_count)} staff</td>
                    <td>
                      <span className={`badge ${isShort ? 'badge-shortage' : 'badge-sufficient'}`}>
                        {isShort ? `${Math.abs(diff)} Shortage` : `${diff} Surplus`}
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

      {/* 7-Day Staff Demand Forecast Chart */}
      <div className="panel-card">
        <div className="chart-header">
          <div>
            <h3 className="chart-title">7-Day Staff Requirement Forecast</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Active Staff (Royal Blue) vs Requirement Forecast (Gold) vs Total Pool (Green)
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
              <YAxis stroke="#64748B" style={{ fontSize: '0.75rem' }} label={{ value: 'Staff', angle: -90, position: 'insideLeft', style: { fill: '#64748B', fontSize: '0.75rem' } }} />
              <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '6px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} />
              <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '10px' }} />
              <Line type="monotone" dataKey="Actual Staff Active" stroke="#1455C0" strokeWidth={2.5} connectNulls name="Active Staff on Duty" />
              <Line type="monotone" dataKey="Forecasted Requirement" stroke="#F4C430" strokeWidth={3} strokeDasharray="5 5" name="Forecasted Requirement" />
              <Line type="monotone" dataKey="Total Staff Pool" stroke="#16A34A" strokeWidth={1.5} name="Total Available Staff" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Modal Form */}
      {showForm && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3 className="modal-title">Add Staff Data</h3>
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
                <label className="form-label">Staff Category</label>
                <select name="staff_category" value={formData.staff_category} onChange={handleInputChange} className="form-control">
                  {staffCategories.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Available Staff (Whole count)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="available_count"
                    required min="0" step="1" placeholder="e.g. 25"
                    value={formData.available_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>staff</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Assigned Staff</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="assigned_count"
                    required min="0" step="1" placeholder="e.g. 18"
                    value={formData.assigned_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>staff</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">On Duty Active</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="used_count"
                    required min="0" step="1" placeholder="e.g. 18"
                    value={formData.used_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>staff</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Required Staff Target</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input 
                    type="number" 
                    name="required_count"
                    required min="0" step="1" placeholder="e.g. 22"
                    value={formData.required_count}
                    onChange={handleInputChange}
                    className="form-control"
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>staff</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Shift</label>
                <select name="shift" value={formData.shift} onChange={handleInputChange} className="form-control">
                  <option value="Day">Day Shift</option>
                  <option value="Night">Night Shift</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Notes</label>
                <input 
                  type="text" 
                  name="notes"
                  placeholder="e.g. On-call coverage verified"
                  value={formData.notes}
                  onChange={handleInputChange}
                  className="form-control"
                />
              </div>

              {errorMsg && <div className="error-alert">{errorMsg}</div>}
              {successMsg && <div className="success-alert">{successMsg}</div>}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '0.5rem' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Save Staff Data</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
