import React, { useState } from 'react';
import { Activity, ShieldAlert, Eye, EyeOff, Lock, User as UserIcon } from 'lucide-react';
import { apiService } from '../services/api';

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const user = await apiService.login(username, password);
      onLoginSuccess(user);
    } catch (err) {
      setError(err.message || 'Invalid credentials or server connection error.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        <div className="login-header">
          <div style={{ display: 'inline-flex', padding: '10px', background: 'var(--primary-blue-light)', borderRadius: '12px', marginBottom: '0.75rem' }}>
            <Activity size={36} color="var(--primary-blue)" />
          </div>
          <h1 className="login-brand-title">Hospital Resource Intelligence</h1>
          <p className="login-subtitle">AI-Powered Demand Forecasting &amp; Capacity Planning Platform</p>
        </div>

        {error && (
          <div className="error-alert" style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldAlert size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label" htmlFor="username">Username or Email</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <input
                id="username"
                type="text"
                className="form-control"
                placeholder="e.g. admin or planner"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                style={{ width: '100%', paddingLeft: '2.25rem' }}
              />
              <UserIcon size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '10px' }} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <div className="password-input-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                className="form-control"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                style={{ width: '100%', paddingLeft: '2.25rem', paddingRight: '2.5rem' }}
              />
              <Lock size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '10px' }} />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                disabled={loading}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn-primary login-submit-btn"
            disabled={loading}
            style={{ width: '100%', justifyContent: 'center', padding: '0.75rem', fontSize: '0.95rem' }}
          >
            {loading ? 'Authenticating Session...' : 'Sign In to Dashboard'}
          </button>
        </form>

        <div className="clinical-disclaimer-text">
          <p>
            <strong>Enterprise Notice:</strong> Authorized healthcare personnel only. Access sessions and resource modifications are cryptographically logged.
          </p>
        </div>
      </div>
    </div>
  );
}
