import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  RefreshCw, 
  Activity, 
  Calendar, 
  CheckCircle2, 
  AlertTriangle,
  Info,
  Clock
} from 'lucide-react';

import { apiService } from '../services/api';
import Navbar from '../components/Navbar';
import SummaryCard from '../components/SummaryCard';
import ForecastChart from '../components/ForecastChart';
import AlertTable from '../components/AlertTable';
import RecommendationCard from '../components/RecommendationCard';
import ExplanationChart from '../components/ExplanationChart';
import ModelComparison from '../components/ModelComparison';
import DataManagement from './DataManagement';

// Dedicated Resource Dashboards
import BedsDashboard from './BedsDashboard';
import OxygenDashboard from './OxygenDashboard';
import BloodDashboard from './BloodDashboard';
import StaffDashboard from './StaffDashboard';
import AmbulanceDashboard from './AmbulanceDashboard';

export default function Dashboard({ currentUser, onLogout }) {
  const [activeSection, setActiveSection] = useState('overview');

  const handleLogout = async () => {
    await apiService.logout();
    onLogout();
  };
  
  // Data States
  const [icuForecast, setIcuForecast] = useState(null);
  const [edForecast, setEdForecast] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [explanations, setExplanations] = useState([]);
  const [performance, setPerformance] = useState([]);
  const [explanationDate, setExplanationDate] = useState('2137-10-17');
  const [lastUpdated, setLastUpdated] = useState(new Date().toLocaleString());

  // Resource Real-time States
  const [latestBeds, setLatestBeds] = useState(null);
  const [latestOxygen, setLatestOxygen] = useState(null);
  const [latestBlood, setLatestBlood] = useState([]);
  const [latestStaff, setLatestStaff] = useState([]);
  const [latestAmbulance, setLatestAmbulance] = useState(null);

  // Interactive Parameter States
  const [icuModel, setIcuModel] = useState('XGBoost');
  const [edModel, setEdModel] = useState('XGBoost');
  
  const [filterResource, setFilterResource] = useState(null);
  const [filterRisk, setFilterRisk] = useState(null);
  const [filterStartDate, setFilterStartDate] = useState(null);
  const [filterEndDate, setFilterEndDate] = useState(null);
  
  const [xaiResource, setXaiResource] = useState('ICU Beds');
  const [xaiMethod, setXaiMethod] = useState('SHAP');

  // Loading & Error States
  const [loading, setLoading] = useState(true);
  const [loadingIcu, setLoadingIcu] = useState(false);
  const [loadingEd, setLoadingEd] = useState(false);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  const [loadingXai, setLoadingXai] = useState(false);
  const [connectionError, setConnectionError] = useState(false);

  // Main Loader
  const loadDashboardData = async () => {
    setLoading(true);
    setConnectionError(false);
    try {
      await apiService.checkHealth();

      const [icuRes, edRes, alertsRes, recsRes, performanceRes, bedsRes, oxygenRes, bloodRes, staffRes, ambulanceRes] = await Promise.all([
        apiService.getForecast('ICU Beds', icuModel),
        apiService.getForecast('ED Arrivals', edModel),
        apiService.getAlerts(filterResource, filterRisk, filterStartDate, filterEndDate),
        apiService.getRecommendations(),
        apiService.getModelPerformance(),
        apiService.getResources('beds').catch(() => []),
        apiService.getResources('oxygen').catch(() => []),
        apiService.getResources('blood').catch(() => []),
        apiService.getResources('staff').catch(() => []),
        apiService.getResources('ambulance').catch(() => [])
      ]);

      setIcuForecast(icuRes);
      setEdForecast(edRes);
      setAlerts(alertsRes.alerts || []);
      setRecommendations(recsRes.recommendations || []);
      setPerformance(performanceRes.metrics || []);

      // Map latest resource state records
      setLatestBeds(bedsRes[0] || null);
      setLatestOxygen(oxygenRes[0] || null);
      setLatestBlood(bloodRes || []);
      setLatestStaff(staffRes || []);
      setLatestAmbulance(ambulanceRes[0] || null);

      setLastUpdated(new Date().toLocaleString());

      // Load initial XAI
      const xaiRes = await apiService.getExplanations(xaiResource, null, xaiMethod);
      setExplanations(xaiRes.explanations || []);
      setExplanationDate(xaiRes.date || '2137-10-17');

    } catch (err) {
      console.error(err);
      setConnectionError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  // Reload ICU forecast when model changes
  useEffect(() => {
    if (loading) return;
    const fetchIcu = async () => {
      setLoadingIcu(true);
      try {
        const res = await apiService.getForecast('ICU Beds', icuModel);
        setIcuForecast(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingIcu(false);
      }
    };
    fetchIcu();
  }, [icuModel]);

  // Reload ED forecast when model changes
  useEffect(() => {
    if (loading) return;
    const fetchEd = async () => {
      setLoadingEd(true);
      try {
        const res = await apiService.getForecast('ED Arrivals', edModel);
        setEdForecast(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingEd(false);
      }
    };
    fetchEd();
  }, [edModel]);

  // Reload Alerts when filters change
  useEffect(() => {
    if (loading) return;
    const fetchAlerts = async () => {
      setLoadingAlerts(true);
      try {
        const res = await apiService.getAlerts(filterResource, filterRisk, filterStartDate, filterEndDate);
        setAlerts(res.alerts || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingAlerts(false);
      }
    };
    fetchAlerts();
  }, [filterResource, filterRisk, filterStartDate, filterEndDate]);

  // Reload XAI when selection changes
  useEffect(() => {
    if (loading) return;
    const fetchXai = async () => {
      setLoadingXai(true);
      try {
        const res = await apiService.getExplanations(xaiResource, null, xaiMethod);
        setExplanations(res.explanations || []);
        setExplanationDate(res.date || '2137-10-17');
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingXai(false);
      }
    };
    fetchXai();
  }, [xaiResource, xaiMethod]);

  // Compute Overall Status
  const criticalCount = alerts.filter(a => a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL').length;
  const warningCount = alerts.filter(a => a.risk_level === 'MEDIUM').length;
  const overallStatus = criticalCount > 0 ? 'Critical' : warningCount > 0 ? 'Warning' : 'Healthy';

  if (connectionError) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', padding: '2rem' }}>
        <div className="panel-card" style={{ maxWidth: '480px', width: '100%', textAlign: 'center', padding: '2.5rem 2rem' }}>
          <ShieldAlert size={48} style={{ color: 'var(--danger-red)', margin: '0 auto 1rem' }} />
          <h2 style={{ fontSize: '1.25rem', color: 'var(--text-main)', marginBottom: '0.5rem' }}>Backend Connection Error</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
            Unable to connect to the hospital forecasting backend. Please confirm the FastAPI server is running on port 8000.
          </p>
          <button className="btn-primary" onClick={loadDashboardData} style={{ margin: '0 auto' }}>
            <RefreshCw size={16} /> Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <div className="loader-wrapper">
          <div className="spinner"></div>
          <span style={{ fontWeight: 600, color: 'var(--primary-blue)' }}>Loading Hospital Intelligence Platform...</span>
        </div>
      </div>
    );
  }

  const renderActiveSection = () => {
    switch (activeSection) {
      case 'overview':
        return (
          <>
            {/* Header Banner */}
            <div className="header-banner">
              <div className="banner-title-group">
                <h2 className="banner-title">Hospital Resource Intelligence</h2>
                <p className="banner-subtitle">
                  AI-Powered Demand Forecasting &amp; Capacity Planning
                </p>
              </div>

              <div className="provenance-notice-compact">
                <Info size={16} style={{ flexShrink: 0 }} />
                <span>Forecasts are generated from available historical data and configured planning parameters.</span>
              </div>
            </div>

            {/* Summary Status Strip */}
            <div className="overview-summary-strip">
              <div className="summary-strip-item">
                <span className="strip-item-label">Total Resources</span>
                <span className="strip-item-value">7 Monitored Resources</span>
              </div>

              <div className="summary-strip-item">
                <span className="strip-item-label">Forecast Horizon</span>
                <span className="strip-item-value">
                  <Calendar size={15} color="var(--primary-blue)" /> Next 7 Days
                </span>
              </div>

              <div className="summary-strip-item">
                <span className="strip-item-label">Current Status</span>
                <span className="strip-item-value">
                  {overallStatus === 'Healthy' && (
                    <span className="badge badge-healthy" style={{ fontSize: '0.8rem', padding: '0.25rem 0.6rem' }}>
                      <CheckCircle2 size={13} /> Healthy
                    </span>
                  )}
                  {overallStatus === 'Warning' && (
                    <span className="badge badge-warning" style={{ fontSize: '0.8rem', padding: '0.25rem 0.6rem' }}>
                      <AlertTriangle size={13} /> Warning ({warningCount})
                    </span>
                  )}
                  {overallStatus === 'Critical' && (
                    <span className="badge badge-critical" style={{ fontSize: '0.8rem', padding: '0.25rem 0.6rem' }}>
                      <ShieldAlert size={13} /> Critical ({criticalCount})
                    </span>
                  )}
                </span>
              </div>

              <div className="summary-strip-item">
                <span className="strip-item-label">Data Status</span>
                <span className="strip-item-value" style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  <Clock size={14} /> Last Updated: {lastUpdated}
                </span>
              </div>
            </div>

            {/* Resource Centric Grid (5 Tiles) */}
            <SummaryCard 
              icuForecast={icuForecast} 
              edForecast={edForecast} 
              alerts={alerts} 
              latestBeds={latestBeds}
              latestOxygen={latestOxygen}
              latestBlood={latestBlood}
              latestStaff={latestStaff}
              latestAmbulance={latestAmbulance}
              onSelectResource={(resId) => setActiveSection(resId)}
            />
            
            {/* 7-Day ICU & ED Forecast Overview */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '1.25rem' }}>
              {loadingIcu ? (
                <div className="panel-card loader-wrapper"><div className="spinner"></div><span>Loading ICU Forecast...</span></div>
              ) : (
                <ForecastChart 
                  forecastData={icuForecast} 
                  selectedModel={icuModel} 
                  setSelectedModel={setIcuModel}
                  title="ICU Occupancy — 7 Day Operational Demand"
                  yAxisLabel="Beds"
                />
              )}
              {loadingEd ? (
                <div className="panel-card loader-wrapper"><div className="spinner"></div><span>Loading ED Forecast...</span></div>
              ) : (
                <ForecastChart 
                  forecastData={edForecast} 
                  selectedModel={edModel} 
                  setSelectedModel={setEdModel}
                  title="ED Arrivals — 7 Day Patient Inflow"
                  yAxisLabel="Patients"
                />
              )}
            </div>
            
            {/* Risk Alerts Table */}
            {loadingAlerts ? (
              <div className="panel-card loader-wrapper"><div className="spinner"></div><span>Loading Alerts...</span></div>
            ) : (
              <AlertTable 
                alerts={alerts}
                filterResource={filterResource}
                setFilterResource={setFilterResource}
                filterRisk={filterRisk}
                setFilterRisk={setFilterRisk}
                filterStartDate={filterStartDate}
                setFilterStartDate={setFilterStartDate}
                filterEndDate={filterEndDate}
                setFilterEndDate={setFilterEndDate}
                onSelectResource={(resId) => setActiveSection(resId)}
              />
            )}
          </>
        );

      case 'forecasts':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="page-header-bar">
              <div>
                <h2 className="page-title">7-Day Resource Forecast Center</h2>
                <p className="page-subtitle">Multi-model projected operational requirements with confidence benchmarks.</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '1.25rem' }}>
              <ForecastChart 
                forecastData={icuForecast} 
                selectedModel={icuModel} 
                setSelectedModel={setIcuModel}
                title="ICU Bed Demand — 7-Day Forecast"
                yAxisLabel="Beds"
              />
              <ForecastChart 
                forecastData={edForecast} 
                selectedModel={edModel} 
                setSelectedModel={setEdModel}
                title="ED Patient Inflow — 7-Day Forecast"
                yAxisLabel="Patients"
              />
            </div>
          </div>
        );
      
      // Dedicated Resource Sub-Dashboards
      case 'beds':
      case 'icu_beds':
        return <BedsDashboard currentUser={currentUser} defaultTab="ICU Beds" />;
      case 'general_beds':
        return <BedsDashboard currentUser={currentUser} defaultTab="General Beds" />;
      case 'emergency_beds':
        return <BedsDashboard currentUser={currentUser} defaultTab="Emergency Beds" />;
      case 'oxygen':
        return <OxygenDashboard currentUser={currentUser} />;
      case 'blood':
        return <BloodDashboard currentUser={currentUser} />;
      case 'staff':
        return <StaffDashboard currentUser={currentUser} />;
      case 'ambulance':
        return <AmbulanceDashboard currentUser={currentUser} />;

      case 'alerts':
        return (
          <AlertTable 
            alerts={alerts}
            filterResource={filterResource}
            setFilterResource={setFilterResource}
            filterRisk={filterRisk}
            setFilterRisk={setFilterRisk}
            filterStartDate={filterStartDate}
            setFilterStartDate={setFilterStartDate}
            filterEndDate={filterEndDate}
            setFilterEndDate={setFilterEndDate}
            onSelectResource={(resId) => setActiveSection(resId)}
          />
        );
      case 'recommendations':
        return (
          <RecommendationCard 
            recommendations={recommendations} 
            onSelectResource={(resId) => setActiveSection(resId)}
          />
        );
      case 'xai':
        return (
          loadingXai ? (
            <div className="panel-card loader-wrapper"><div className="spinner"></div><span>Loading Explainability Chart...</span></div>
          ) : (
            <ExplanationChart 
              explanations={explanations}
              selectedResource={xaiResource}
              setSelectedResource={setXaiResource}
              selectedMethod={xaiMethod}
              setSelectedMethod={setXaiMethod}
              explanationDate={explanationDate}
            />
          )
        );
      case 'performance':
        return (
          <ModelComparison 
            performanceMetrics={performance} 
          />
        );
      case 'dataManagement':
        return (
          <DataManagement 
            currentUser={currentUser} 
            onForecastGenerated={loadDashboardData} 
          />
        );
      default:
        return <div>Section not found.</div>;
    }
  };

  return (
    <div className="app-container">
      <Navbar 
        activeSection={activeSection} 
        setActiveSection={setActiveSection} 
        currentUser={currentUser} 
        onLogout={handleLogout} 
      />
      
      <main className="dashboard-content">
        {renderActiveSection()}
      </main>
    </div>
  );
}
