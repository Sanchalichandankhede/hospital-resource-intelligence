const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

let token = localStorage.getItem('hri_token') || null;

export const setAuthToken = (newToken) => {
  token = newToken;
  if (newToken) {
    localStorage.setItem('hri_token', newToken);
  } else {
    localStorage.removeItem('hri_token');
  }
};

export const getAuthToken = () => token;

async function requestApi(endpoint, options = {}) {
  const { method = 'GET', params = {}, body = null, isMultipart = false } = options;
  
  const url = new URL(`${BASE_URL}${endpoint}`);
  
  if (method === 'GET') {
    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
        url.searchParams.append(key, params[key]);
      }
    });
  }

  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const fetchOptions = {
    method,
    headers
  };

  if (body) {
    if (isMultipart) {
      // Browser sets appropriate multipart boundary automatically
      fetchOptions.body = body;
    } else {
      headers['Content-Type'] = 'application/json';
      fetchOptions.body = JSON.stringify(body);
    }
  }

  try {
    const response = await fetch(url.toString(), fetchOptions);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || `HTTP Error ${response.status}`;
      throw new Error(errorMessage);
    }

    if (response.status === 204) {
      return null;
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Unable to connect to forecasting backend.');
    }
    throw error;
  }
}

export const apiService = {
  checkHealth: () => requestApi('/health'),
  
  // Auth endpoints
  login: async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const data = await requestApi('/api/auth/login', {
      method: 'POST',
      body: formData,
      isMultipart: true
    });
    setAuthToken(data.access_token);
    return data.user;
  },
  
  logout: async () => {
    try {
      await requestApi('/api/auth/logout', { method: 'POST' });
    } catch (err) {
      console.warn("Logout endpoint error:", err);
    }
    setAuthToken(null);
  },
  
  getMe: () => requestApi('/api/auth/me'),
  
  register: (username, email, password, role) => {
    return requestApi('/api/auth/register', {
      method: 'POST',
      body: { username, email, password, role }
    });
  },

  // Forecast endpoints
  getForecast: (resourceType, model = 'XGBoost', startDate = null, endDate = null) => {
    const endpoint = resourceType.toLowerCase().includes('icu') ? '/api/forecast/icu' : '/api/forecast/ed';
    return requestApi(endpoint, { params: { model, start_date: startDate, end_date: endDate } });
  },
  
  getAlerts: (resource = null, riskLevel = null, startDate = null, endDate = null) => {
    return requestApi('/api/alerts', { params: { resource, risk_level: riskLevel, start_date: startDate, end_date: endDate } });
  },
  
  getRecommendations: (resource = null, riskLevel = null) => {
    return requestApi('/api/recommendations', { params: { resource, risk_level: riskLevel } });
  },
  
  getExplanations: (resourceType, date = null, method = 'SHAP') => {
    const endpoint = resourceType.toLowerCase().includes('icu') ? '/api/explanations/icu' : '/api/explanations/ed';
    return requestApi(endpoint, { params: { date, method } });
  },
  
  getModelPerformance: () => requestApi('/api/model-performance'),
  
  getMultiResourceForecast: (model = 'XGBoost') => {
    return requestApi('/api/forecast/multi', { params: { model } });
  },

  // Data management endpoints
  uploadDataset: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return requestApi('/api/data/upload', {
      method: 'POST',
      body: formData,
      isMultipart: true
    });
  },

  importDataset: (filename, entries) => {
    return requestApi('/api/data/import', {
      method: 'POST',
      body: { filename, entries }
    });
  },

  createManualEntry: (manualData) => {
    return requestApi('/api/data/manual', {
      method: 'POST',
      body: manualData
    });
  },

  getDataEntries: () => requestApi('/api/data/entries'),

  getDatasets: () => requestApi('/api/data/datasets'),

  generateForecast: (datasetId, model, retrain = false) => {
    return requestApi('/api/data/forecast/generate', {
      method: 'POST',
      body: { dataset_id: datasetId, model, retrain }
    });
  },

  // Resource Categories Endpoints
  getResources: (category) => requestApi(`/api/resources/${category}`),
  createResourceRecord: (category, data) => requestApi(`/api/resources/${category}`, { method: 'POST', body: data }),
  deleteResourceRecord: (category, id) => requestApi(`/api/resources/${category}/${id}`, { method: 'DELETE' })
};
