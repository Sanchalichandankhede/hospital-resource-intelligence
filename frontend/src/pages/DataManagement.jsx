import React, { useState, useEffect } from 'react';
import { 
  Upload, 
  Plus, 
  ShieldAlert, 
  CheckCircle2, 
  History, 
  AlertTriangle, 
  Play, 
  Brain, 
  Check, 
  Info,
  FileSpreadsheet,
  FileText,
  Database,
  ArrowRight,
  Bed,
  Wind,
  Droplet,
  Users,
  Truck
} from 'lucide-react';
import { apiService } from '../services/api';

export default function DataManagement({ currentUser, onForecastGenerated }) {
  // Main Data Management Page Tabs: [ Manual Entry ] and [ Upload Dataset ]
  const [activeMainTab, setActiveMainTab] = useState('manual');

  // Resource category selection for manual entry selector
  const [selectedManualResource, setSelectedManualResource] = useState('Beds');

  // Import Upload States
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importNotice, setImportNotice] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  // Manual Resource Counts Forms
  const [manualDate, setManualDate] = useState(new Date().toISOString().split('T')[0]);
  const [manualBedsType, setManualBedsType] = useState('ICU Beds');
  const [availableBeds, setAvailableBeds] = useState('');
  const [occupiedBeds, setOccupiedBeds] = useState('');
  const [requiredBeds, setRequiredBeds] = useState('');

  const [oxyTotal, setOxyTotal] = useState('');
  const [oxyAvailable, setOxyAvailable] = useState('');
  const [oxyUsed, setOxyUsed] = useState('');
  const [oxyRefilled, setOxyRefilled] = useState('');
  const [oxyRequired, setOxyRequired] = useState('');
  const [oxyNotes, setOxyNotes] = useState('');

  const [bloodGroup, setBloodGroup] = useState('A+');
  const [bloodAvailable, setBloodAvailable] = useState('');
  const [bloodUsed, setBloodUsed] = useState('');
  const [bloodReceived, setBloodReceived] = useState('');
  const [bloodReserved, setBloodReserved] = useState('');
  const [bloodRequired, setBloodRequired] = useState('');

  const [staffCategory, setStaffCategory] = useState('Doctors');
  const [staffAvailable, setStaffAvailable] = useState('');
  const [staffAssigned, setStaffAssigned] = useState('');
  const [staffUsed, setStaffUsed] = useState('');
  const [staffRequired, setStaffRequired] = useState('');
  const [staffShift, setStaffShift] = useState('Day');
  const [staffNotes, setStaffNotes] = useState('');

  const [ambTotal, setAmbTotal] = useState('');
  const [ambAvailable, setAmbAvailable] = useState('');
  const [ambUsed, setAmbUsed] = useState('');
  const [ambMaintenance, setAmbMaintenance] = useState('');
  const [ambRequired, setAmbRequired] = useState('');
  const [ambNotes, setAmbNotes] = useState('');

  const [manualLoading, setManualLoading] = useState(false);
  const [manualNotice, setManualNotice] = useState(null);
  const [manualError, setManualError] = useState(null);

  // History logs states
  const [entries, setEntries] = useState([]);
  const [datasets, setDatasets] = useState([]);

  const fetchHistory = async () => {
    try {
      const [entriesData, datasetsData] = await Promise.all([
        apiService.getDataEntries().catch(() => []),
        apiService.getDatasets().catch(() => [])
      ]);
      setEntries(entriesData || []);
      setDatasets(datasetsData || []);
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleFileSelect = (file) => {
    if (file) {
      setSelectedFile(file);
      setUploadResult(null);
      setUploadError(null);
      setImportNotice(null);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleUploadAndValidate = async () => {
    if (!selectedFile) {
      setUploadError('Please choose a CSV or Excel file first.');
      return;
    }
    setUploadLoading(true);
    setUploadError(null);
    setImportNotice(null);

    try {
      const result = await apiService.uploadDataset(selectedFile);
      setUploadResult(result);
    } catch (err) {
      setUploadError(err.message || 'Validation failure.');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleImport = async () => {
    if (!uploadResult || !uploadResult.preview || uploadResult.preview.length === 0) return;
    setImportLoading(true);
    setUploadError(null);
    setImportNotice(null);

    try {
      const result = await apiService.importDataset(uploadResult.dataset_id);
      setImportNotice(`Dataset imported successfully! ${result.imported_rows || uploadResult.row_count} rows integrated into historical database.`);
      setUploadResult(null);
      setSelectedFile(null);
      fetchHistory();
      if (onForecastGenerated) {
        onForecastGenerated();
      }
    } catch (err) {
      setUploadError(err.message || 'Failed to import dataset.');
    } finally {
      setImportLoading(false);
    }
  };

  // Manual Resource Submit
  const handleManualSubmit = async (e) => {
    e.preventDefault();
    setManualError(null);
    setManualNotice(null);
    setManualLoading(true);

    try {
      if (selectedManualResource === 'Beds') {
        const av = parseFloat(availableBeds);
        const oc = parseFloat(occupiedBeds);
        const rq = parseFloat(requiredBeds);

        if (isNaN(av) || isNaN(oc) || isNaN(rq)) throw new Error("All bed counts must be numeric.");
        if (!Number.isInteger(av) || !Number.isInteger(oc) || !Number.isInteger(rq)) throw new Error("Bed counts must be whole integers.");
        if (av < 0 || oc < 0 || rq < 0) throw new Error("Negative bed counts are rejected.");

        await apiService.createResourceRecord('beds', {
          date: manualDate,
          bed_type: manualBedsType,
          available_count: parseInt(availableBeds),
          occupied_count: parseInt(occupiedBeds),
          required_count: parseInt(requiredBeds)
        });
        setManualNotice(`Successfully recorded ${manualBedsType} log.`);
        setAvailableBeds(''); setOccupiedBeds(''); setRequiredBeds('');

      } else if (selectedManualResource === 'Oxygen') {
        const tc = parseFloat(oxyTotal);
        const ac = parseFloat(oxyAvailable);
        const uc = parseFloat(oxyUsed);
        const fr = parseFloat(oxyRefilled);
        const rc = parseFloat(oxyRequired);

        if (isNaN(tc) || isNaN(ac) || isNaN(uc) || isNaN(fr) || isNaN(rc)) throw new Error("All cylinder counts must be numeric.");
        if (!Number.isInteger(tc) || !Number.isInteger(ac) || !Number.isInteger(uc) || !Number.isInteger(fr) || !Number.isInteger(rc)) throw new Error("Cylinder counts must be whole integers.");
        if (tc < 0 || ac < 0 || uc < 0 || fr < 0 || rc < 0) throw new Error("Negative values are rejected.");
        if (ac + uc > tc) throw new Error("Available + Used cylinders cannot exceed total pool.");

        await apiService.createResourceRecord('oxygen', {
          date: manualDate,
          total_cylinders: parseInt(oxyTotal),
          available_cylinders: parseInt(oxyAvailable),
          used_cylinders: parseInt(oxyUsed),
          filled_refilled: parseInt(oxyRefilled),
          required_cylinders: parseInt(oxyRequired),
          notes: oxyNotes
        });
        setManualNotice('Successfully recorded Oxygen cylinder log.');
        setOxyTotal(''); setOxyAvailable(''); setOxyUsed(''); setOxyRefilled(''); setOxyRequired(''); setOxyNotes('');

      } else if (selectedManualResource === 'Blood') {
        const av = parseFloat(bloodAvailable);
        const us = parseFloat(bloodUsed);
        const rc = parseFloat(bloodReceived);
        const rs = parseFloat(bloodReserved);
        const rq = parseFloat(bloodRequired);

        if (isNaN(av) || isNaN(us) || isNaN(rc) || isNaN(rs) || isNaN(rq)) throw new Error("All blood unit counts must be numeric.");
        if (!Number.isInteger(av) || !Number.isInteger(us) || !Number.isInteger(rc) || !Number.isInteger(rs) || !Number.isInteger(rq)) throw new Error("Blood units must be whole numbers.");
        if (av < 0 || us < 0 || rc < 0 || rs < 0 || rq < 0) throw new Error("Negative values are rejected.");

        await apiService.createResourceRecord('blood', {
          date: manualDate,
          blood_group: bloodGroup,
          available_units: parseInt(bloodAvailable),
          used_units: parseInt(bloodUsed),
          received_units: parseInt(bloodReceived),
          reserved_units: parseInt(bloodReserved),
          required_units: parseInt(bloodRequired)
        });
        setManualNotice(`Successfully recorded Blood ${bloodGroup} inventory.`);
        setBloodAvailable(''); setBloodUsed(''); setBloodReceived(''); setBloodReserved(''); setBloodRequired('');

      } else if (selectedManualResource === 'Staff') {
        const av = parseFloat(staffAvailable);
        const as = parseFloat(staffAssigned);
        const us = parseFloat(staffUsed);
        const rq = parseFloat(staffRequired);

        if (isNaN(av) || isNaN(as) || isNaN(us) || isNaN(rq)) throw new Error("All staff counts must be numeric.");
        if (!Number.isInteger(av) || !Number.isInteger(as) || !Number.isInteger(us) || !Number.isInteger(rq)) throw new Error("Staff counts must be whole integers.");
        if (av < 0 || as < 0 || us < 0 || rq < 0) throw new Error("Negative values are rejected.");

        await apiService.createResourceRecord('staff', {
          date: manualDate,
          staff_category: staffCategory,
          available_count: parseInt(staffAvailable),
          assigned_count: parseInt(staffAssigned),
          used_count: parseInt(staffUsed),
          required_count: parseInt(staffRequired),
          shift: staffShift,
          notes: staffNotes
        });
        setManualNotice(`Successfully recorded ${staffCategory} roster.`);
        setStaffAvailable(''); setStaffAssigned(''); setStaffUsed(''); setStaffRequired(''); setStaffNotes('');

      } else if (selectedManualResource === 'Ambulance') {
        const ta = parseFloat(ambTotal);
        const ac = parseFloat(ambAvailable);
        const uc = parseFloat(ambUsed);
        const um = parseFloat(ambMaintenance);
        const rc = parseFloat(ambRequired);

        if (isNaN(ta) || isNaN(ac) || isNaN(uc) || isNaN(um) || isNaN(rc)) throw new Error("All ambulance counts must be numeric.");
        if (!Number.isInteger(ta) || !Number.isInteger(ac) || !Number.isInteger(uc) || !Number.isInteger(um) || !Number.isInteger(rc)) throw new Error("Ambulance counts must be whole integers.");
        if (ta < 0 || ac < 0 || uc < 0 || um < 0 || rc < 0) throw new Error("Negative values are rejected.");
        if (ac + uc + um > ta) throw new Error("Available + Used + Maintenance ambulances cannot exceed total fleet.");

        await apiService.createResourceRecord('ambulance', {
          date: manualDate,
          total_ambulances: parseInt(ambTotal),
          available_count: parseInt(ambAvailable),
          used_count: parseInt(ambUsed),
          under_maintenance_count: parseInt(ambMaintenance),
          required_count: parseInt(ambRequired),
          notes: ambNotes
        });
        setManualNotice('Successfully recorded Ambulance fleet log.');
        setAmbTotal(''); setAmbAvailable(''); setAmbUsed(''); setAmbMaintenance(''); setAmbRequired(''); setAmbNotes('');
      }

      fetchHistory();
      if (onForecastGenerated) {
        onForecastGenerated();
      }
    } catch (err) {
      setManualError(err.message || 'Failed to submit manual record.');
    } finally {
      setManualLoading(false);
    }
  };

  const manualResourceTabs = [
    { id: 'Beds', label: 'Beds', icon: Bed },
    { id: 'Oxygen', label: 'Oxygen', icon: Wind },
    { id: 'Blood', label: 'Blood', icon: Droplet },
    { id: 'Staff', label: 'Staff', icon: Users },
    { id: 'Ambulance', label: 'Ambulance', icon: Truck }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Page Header */}
      <div className="page-header-bar">
        <div>
          <h2 className="page-title">
            <Database size={24} color="var(--primary-blue)" />
            DATA MANAGEMENT &amp; INGESTION
          </h2>
          <p className="page-subtitle">Input operational hospital observations, import bulk datasets, and validate schema integrity.</p>
        </div>
      </div>

      {/* Two Clear Tabs: [ Manual Entry ] and [ Upload Dataset ] */}
      <div className="tab-menu-bar">
        <button 
          className={`tab-btn-pill ${activeMainTab === 'manual' ? 'active' : ''}`}
          onClick={() => setActiveMainTab('manual')}
        >
          [ Manual Entry ]
        </button>
        <button 
          className={`tab-btn-pill ${activeMainTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveMainTab('upload')}
        >
          [ Upload Dataset ]
        </button>
      </div>

      {/* TAB 1: MANUAL ENTRY */}
      {activeMainTab === 'manual' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Sub-tabs for Resource Type */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {manualResourceTabs.map((res) => {
              const Icon = res.icon;
              return (
                <button
                  key={res.id}
                  onClick={() => { setSelectedManualResource(res.id); setManualError(null); setManualNotice(null); }}
                  className={`btn-secondary ${selectedManualResource === res.id ? 'btn-primary' : ''}`}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Icon size={16} />
                  <span>{res.label} Entry</span>
                </button>
              );
            })}
          </div>

          <div className="panel-card" style={{ maxWidth: '650px' }}>
            <h3 className="chart-title" style={{ marginBottom: '1rem' }}>
              Add {selectedManualResource} Record
            </h3>

            <form onSubmit={handleManualSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Observation Date</label>
                <input 
                  type="date" 
                  required
                  value={manualDate} 
                  onChange={(e) => setManualDate(e.target.value)} 
                  className="form-control"
                />
              </div>

              {/* BEDS FORM */}
              {selectedManualResource === 'Beds' && (
                <>
                  <div className="form-group">
                    <label className="form-label">Bed Type Category</label>
                    <select value={manualBedsType} onChange={(e) => setManualBedsType(e.target.value)} className="form-control">
                      <option value="ICU Beds">ICU Beds</option>
                      <option value="General Beds">General Beds</option>
                      <option value="Emergency Beds">Emergency Beds</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Available Beds (Total Capacity)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 50"
                        value={availableBeds} onChange={(e) => setAvailableBeds(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>beds</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Occupied Beds (Currently In Use)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 15"
                        value={occupiedBeds} onChange={(e) => setOccupiedBeds(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>beds</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Required Beds (Target Demand)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 20"
                        value={requiredBeds} onChange={(e) => setRequiredBeds(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>beds</span>
                    </div>
                  </div>
                </>
              )}

              {/* OXYGEN FORM */}
              {selectedManualResource === 'Oxygen' && (
                <>
                  <div className="form-group">
                    <label className="form-label">Total Cylinders (Stock Pool)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 80"
                        value={oxyTotal} onChange={(e) => setOxyTotal(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Available Cylinders (Filled)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 45"
                        value={oxyAvailable} onChange={(e) => setOxyAvailable(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Cylinders in Use (Active)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 32"
                        value={oxyUsed} onChange={(e) => setOxyUsed(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Refilled Today</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 10"
                        value={oxyRefilled} onChange={(e) => setOxyRefilled(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Required Cylinders (Daily Target)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 35"
                        value={oxyRequired} onChange={(e) => setOxyRequired(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>cylinders</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Notes</label>
                    <input 
                      type="text" placeholder="Additional logistics info..."
                      value={oxyNotes} onChange={(e) => setOxyNotes(e.target.value)}
                      className="form-control"
                    />
                  </div>
                </>
              )}

              {/* BLOOD FORM */}
              {selectedManualResource === 'Blood' && (
                <>
                  <div className="form-group">
                    <label className="form-label">Blood Group</label>
                    <select value={bloodGroup} onChange={(e) => setBloodGroup(e.target.value)} className="form-control">
                      {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map(bg => <option key={bg} value={bg}>{bg}</option>)}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Available Units</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 25"
                        value={bloodAvailable} onChange={(e) => setBloodAvailable(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Used Units Today</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 8"
                        value={bloodUsed} onChange={(e) => setBloodUsed(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Received Today</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 5"
                        value={bloodReceived} onChange={(e) => setBloodReceived(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Reserved Units</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 2"
                        value={bloodReserved} onChange={(e) => setBloodReserved(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Required Units Target</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 12"
                        value={bloodRequired} onChange={(e) => setBloodRequired(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>units</span>
                    </div>
                  </div>
                </>
              )}

              {/* STAFF FORM */}
              {selectedManualResource === 'Staff' && (
                <>
                  <div className="form-group">
                    <label className="form-label">Staff Category</label>
                    <select value={staffCategory} onChange={(e) => setStaffCategory(e.target.value)} className="form-control">
                      {["Doctors", "Nurses", "Support Staff", "Emergency Staff", "Technicians"].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Available Staff (Total Pool)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 25"
                        value={staffAvailable} onChange={(e) => setStaffAvailable(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>staff</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Assigned Staff</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 18"
                        value={staffAssigned} onChange={(e) => setStaffAssigned(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>staff</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">On Duty Active</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 18"
                        value={staffUsed} onChange={(e) => setStaffUsed(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>staff</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Required Staff Target</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 22"
                        value={staffRequired} onChange={(e) => setStaffRequired(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>staff</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Shift</label>
                    <select value={staffShift} onChange={(e) => setStaffShift(e.target.value)} className="form-control">
                      <option value="Day">Day Shift</option>
                      <option value="Night">Night Shift</option>
                    </select>
                  </div>
                </>
              )}

              {/* AMBULANCE FORM */}
              {selectedManualResource === 'Ambulance' && (
                <>
                  <div className="form-group">
                    <label className="form-label">Total Fleet Pool</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 15"
                        value={ambTotal} onChange={(e) => setAmbTotal(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Available (Ready)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 8"
                        value={ambAvailable} onChange={(e) => setAmbAvailable(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Active Dispatched</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 5"
                        value={ambUsed} onChange={(e) => setAmbUsed(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Under Maintenance</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 2"
                        value={ambMaintenance} onChange={(e) => setAmbMaintenance(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Required Dispatch Target</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" required min="0" step="1" placeholder="e.g. 6"
                        value={ambRequired} onChange={(e) => setAmbRequired(e.target.value)}
                        className="form-control" style={{ flex: 1 }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>vehicles</span>
                    </div>
                  </div>
                </>
              )}

              {manualError && <div className="error-alert">{manualError}</div>}
              {manualNotice && <div className="success-alert">{manualNotice}</div>}

              <button 
                type="submit" 
                className="btn-primary" 
                disabled={manualLoading}
                style={{ alignSelf: 'flex-start', marginTop: '0.5rem' }}
              >
                {manualLoading ? 'Saving Record...' : `Save ${selectedManualResource} Record`}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: UPLOAD DATASET */}
      {activeMainTab === 'upload' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="panel-card" style={{ maxWidth: '800px' }}>
            <h3 className="chart-title" style={{ marginBottom: '1rem' }}>
              Upload Operational Dataset (CSV / Excel .xlsx)
            </h3>

            {/* Drag & Drop Zone */}
            <div 
              className={`upload-dropzone ${dragActive ? 'drag-active' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById('file-upload-input').click()}
            >
              <input 
                id="file-upload-input"
                type="file" 
                accept=".csv, .xlsx, .xls"
                style={{ display: 'none' }}
                onChange={(e) => e.target.files && handleFileSelect(e.target.files[0])}
              />

              <Upload size={36} color="var(--primary-blue)" />
              <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                {selectedFile ? selectedFile.name : 'Drag & Drop Dataset Here'}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Supports standard CSV and Excel (.xlsx) formats. Max file size: 25MB.
              </p>

              <button type="button" className="btn-secondary" style={{ marginTop: '0.5rem' }}>
                Choose File from Computer
              </button>
            </div>

            {selectedFile && !uploadResult && (
              <div style={{ marginTop: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-card-alt)', padding: '0.85rem 1rem', borderRadius: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileSpreadsheet size={20} color="var(--primary-blue)" />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{selectedFile.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{(selectedFile.size / 1024).toFixed(1)} KB</div>
                  </div>
                </div>

                <button 
                  className="btn-primary" 
                  onClick={handleUploadAndValidate}
                  disabled={uploadLoading}
                >
                  {uploadLoading ? 'Validating Dataset...' : 'Validate & Preview'}
                </button>
              </div>
            )}

            {uploadError && <div className="error-alert" style={{ marginTop: '1rem' }}>{uploadError}</div>}
            {importNotice && <div className="success-alert" style={{ marginTop: '1rem' }}>{importNotice}</div>}

            {/* Validation & Preview Card */}
            {uploadResult && (
              <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
                  <div style={{ background: 'var(--bg-card-alt)', padding: '0.75rem', borderRadius: '4px' }}>
                    <span className="strip-item-label">File Name</span>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-main)' }}>{uploadResult.filename}</div>
                  </div>
                  <div style={{ background: 'var(--bg-card-alt)', padding: '0.75rem', borderRadius: '4px' }}>
                    <span className="strip-item-label">Number of Rows</span>
                    <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--primary-blue)' }}>{uploadResult.row_count} rows</div>
                  </div>
                  <div style={{ background: 'var(--bg-card-alt)', padding: '0.75rem', borderRadius: '4px' }}>
                    <span className="strip-item-label">Detected Resource</span>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-main)' }}>{uploadResult.detected_resource || 'ICU Beds / General'}</div>
                  </div>
                  <div style={{ background: 'var(--bg-card-alt)', padding: '0.75rem', borderRadius: '4px' }}>
                    <span className="strip-item-label">Validation Status</span>
                    <div>
                      <span className="badge badge-sufficient">
                        <CheckCircle2 size={12} /> Validated
                      </span>
                    </div>
                  </div>
                </div>

                {/* Preview Table */}
                <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Dataset Preview (First 5 Rows)</h4>
                <div className="table-responsive" style={{ maxHeight: '220px', marginBottom: '1.25rem' }}>
                  <table>
                    <thead>
                      <tr>
                        {uploadResult.columns && uploadResult.columns.map((col, idx) => (
                          <th key={idx}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {uploadResult.preview && uploadResult.preview.slice(0, 5).map((row, rIdx) => (
                        <tr key={rIdx}>
                          {uploadResult.columns.map((col, cIdx) => (
                            <td key={cIdx}>{row[col] !== undefined ? String(row[col]) : '—'}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button className="btn-secondary" onClick={() => { setSelectedFile(null); setUploadResult(null); }}>
                    Discard
                  </button>
                  <button 
                    className="btn-primary" 
                    onClick={handleImport}
                    disabled={importLoading}
                  >
                    {importLoading ? 'Importing Dataset...' : 'Import Dataset into Model'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audit History Log */}
      <div className="panel-card">
        <h3 className="chart-title" style={{ marginBottom: '0.85rem' }}>
          <History size={18} /> Ingested Datasets &amp; Manual History
        </h3>
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Batch / Dataset ID</th>
                <th>Source File</th>
                <th>Resource / Target</th>
                <th>Row Count</th>
                <th>Status</th>
                <th>Uploaded By</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {datasets.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                    No dataset uploads or manual entries recorded in database yet.
                  </td>
                </tr>
              ) : (
                datasets.map(d => {
                  const isManual = d.source_type === 'MANUAL_ENTRY';
                  const sourceName = isManual ? 'Manual Entry' : (d.filename || 'Uploaded Dataset');
                  const resourceName = d.resource_type || d.resource_category || 'Multi-Resource';
                  const rowLabel = `${d.row_count} ${d.row_count === 1 ? 'row' : 'rows'}`;
                  const statusLabel = isManual ? 'SAVED' : 'IMPORTED';
                  const uploader = d.uploaded_by_username || 'Admin';
                  const dateStr = (d.uploaded_at || d.created_at) ? new Date(d.uploaded_at || d.created_at).toLocaleDateString() : new Date().toLocaleDateString();

                  return (
                    <tr key={d.id}>
                      <td style={{ fontWeight: 600 }}>#{d.id}</td>
                      <td>{sourceName}</td>
                      <td>{resourceName}</td>
                      <td>{rowLabel}</td>
                      <td>
                        <span className="badge badge-sufficient">
                          {statusLabel}
                        </span>
                      </td>
                      <td>{uploader}</td>
                      <td>{dateStr}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
