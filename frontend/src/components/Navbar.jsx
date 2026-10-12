import React, { useState, useRef, useEffect } from 'react';
import { 
  Activity,
  LayoutDashboard, 
  Package, 
  TrendingUp, 
  ShieldAlert, 
  ClipboardList, 
  HelpCircle, 
  BarChart3, 
  Database,
  LogOut,
  ChevronDown,
  Bed,
  Wind,
  Droplet,
  Users,
  Truck
} from 'lucide-react';

export default function Navbar({ activeSection, setActiveSection, currentUser, onLogout }) {
  const [resourcesDropdownOpen, setResourcesDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const resourceSubmenu = [
    { id: 'icu_beds', label: 'ICU Beds', icon: Bed },
    { id: 'general_beds', label: 'General Beds', icon: Bed },
    { id: 'emergency_beds', label: 'Emergency Beds', icon: Bed },
    { id: 'oxygen', label: 'Oxygen', icon: Wind },
    { id: 'blood', label: 'Blood', icon: Droplet },
    { id: 'staff', label: 'Staff', icon: Users },
    { id: 'ambulance', label: 'Ambulance', icon: Truck },
  ];

  const isResourceActive = ['beds', 'icu_beds', 'general_beds', 'emergency_beds', 'oxygen', 'blood', 'staff', 'ambulance'].includes(activeSection);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setResourcesDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const canManageData = currentUser?.role === 'ADMIN' || currentUser?.role === 'PLANNER';

  const selectResource = (id) => {
    setActiveSection(id);
    setResourcesDropdownOpen(false);
  };

  const getActiveResourceLabel = () => {
    const item = resourceSubmenu.find(r => r.id === activeSection);
    if (item) return item.label;
    if (activeSection === 'beds') return 'Beds';
    return 'Resources';
  };

  return (
    <header className="top-header-container">
      {/* 1. Top Brand Banner Bar (Dark / Royal Navy Blue #0A2540) */}
      <div className="top-brand-bar">
        <div className="brand-left">
          <div className="brand-icon-wrapper">
            <Activity size={22} color="#F4C430" />
          </div>
          <div className="brand-title-group">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 className="brand-title-main">Hospital Resource Intelligence</h1>
              <span className="brand-divider">|</span>
              <span className="brand-section-label">Enterprise Platform</span>
            </div>
            <span className="brand-subtitle-tag">AI-Powered Demand Forecasting &amp; Capacity Planning</span>
          </div>
        </div>

        {/* Compact User Info & Sign Out */}
        <div className="user-profile-header">
          <div className="user-info-pill">
            <div className="user-avatar-circle">
              {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
            </div>
            <span className="user-name-text">{currentUser?.username || 'User'}</span>
            <span className={`user-role-badge badge-${currentUser?.role ? currentUser.role.toLowerCase() : 'viewer'}`}>
              {currentUser?.role || 'VIEWER'}
            </span>
          </div>

          <button 
            onClick={onLogout} 
            className="logout-top-btn"
            title="Sign Out of HRI"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* 2. Horizontal Navigation Bar */}
      <nav className="top-nav-bar">
        <ul className="nav-links-list">
          {/* Overview */}
          <li className="nav-link-item">
            <button 
              className={`top-nav-btn ${activeSection === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveSection('overview')}
            >
              <LayoutDashboard size={16} />
              <span>Overview</span>
            </button>
          </li>

          {/* Resources Dropdown (Exactly 7 options: ICU Beds, General Beds, Emergency Beds, Oxygen, Blood, Staff, Ambulance) */}
          <li className="nav-link-item" ref={dropdownRef}>
            <button 
              id="nav-btn-resources"
              className={`top-nav-btn ${isResourceActive ? 'active' : ''}`}
              onClick={() => setResourcesDropdownOpen(!resourcesDropdownOpen)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Package size={16} />
              <span>{isResourceActive ? getActiveResourceLabel() : 'Resources'}</span>
              <ChevronDown size={14} style={{ transform: resourcesDropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
            </button>

            {resourcesDropdownOpen && (
              <div className="dropdown-menu" id="resources-dropdown-menu">
                {resourceSubmenu.map((res) => {
                  const Icon = res.icon;
                  const isItemActive = activeSection === res.id || (activeSection === 'beds' && res.id === 'icu_beds');
                  return (
                    <button 
                      key={res.id}
                      id={`dropdown-item-${res.id}`}
                      className={`dropdown-item ${isItemActive ? 'active' : ''}`}
                      onClick={() => selectResource(res.id)}
                    >
                      <Icon size={16} style={{ color: isItemActive ? 'var(--primary-blue)' : 'var(--text-muted)' }} />
                      <span>{res.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </li>

          {/* Forecasts */}
          <li className="nav-link-item">
            <button 
              className={`top-nav-btn ${activeSection === 'forecasts' ? 'active' : ''}`}
              onClick={() => setActiveSection('forecasts')}
            >
              <TrendingUp size={16} />
              <span>Forecasts</span>
            </button>
          </li>

          {/* Risk Alerts */}
          <li className="nav-link-item">
            <button 
              className={`top-nav-btn ${activeSection === 'alerts' ? 'active' : ''}`}
              onClick={() => setActiveSection('alerts')}
            >
              <ShieldAlert size={16} />
              <span>Risk Alerts</span>
            </button>
          </li>

          {/* Recommendations */}
          <li className="nav-link-item">
            <button 
              className={`top-nav-btn ${activeSection === 'recommendations' ? 'active' : ''}`}
              onClick={() => setActiveSection('recommendations')}
            >
              <ClipboardList size={16} />
              <span>Recommendations</span>
            </button>
          </li>

          {/* Explainable AI */}
          <li className="nav-link-item">
            <button 
              className={`top-nav-btn ${activeSection === 'xai' ? 'active' : ''}`}
              onClick={() => setActiveSection('xai')}
            >
              <HelpCircle size={16} />
              <span>Explainable AI</span>
            </button>
          </li>

          {/* Model Performance */}
          <li className="nav-link-item">
            <button 
              className={`top-nav-btn ${activeSection === 'performance' ? 'active' : ''}`}
              onClick={() => setActiveSection('performance')}
            >
              <BarChart3 size={16} />
              <span>Model Performance</span>
            </button>
          </li>

          {/* Data Management (ADMIN & PLANNER only) */}
          {canManageData && (
            <li className="nav-link-item">
              <button 
                className={`top-nav-btn ${activeSection === 'dataManagement' ? 'active' : ''}`}
                onClick={() => setActiveSection('dataManagement')}
              >
                <Database size={16} />
                <span>Data Management</span>
              </button>
            </li>
          )}
        </ul>
      </nav>
    </header>
  );
}
