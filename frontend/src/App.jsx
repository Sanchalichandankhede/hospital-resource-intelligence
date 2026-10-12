import React, { useState, useEffect } from 'react';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import { apiService, getAuthToken } from './services/api';

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifySession = async () => {
      const token = getAuthToken();
      if (!token) {
        setLoading(false);
        return;
      }
      
      try {
        const user = await apiService.getMe();
        setCurrentUser(user);
      } catch (err) {
        console.warn("Session validation failed:", err);
        // Clear invalid token
        localStorage.removeItem('hri_token');
      } finally {
        setLoading(false);
      }
    };
    verifySession();
  }, []);

  if (loading) {
    return (
      <div className="login-page-container">
        <div className="panel-card loader-wrapper">
          <div className="spinner"></div>
          <span>Verifying secure session...</span>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <Login onLoginSuccess={(user) => setCurrentUser(user)} />
    );
  }

  return (
    <Dashboard currentUser={currentUser} onLogout={() => setCurrentUser(null)} />
  );
}

export default App;
