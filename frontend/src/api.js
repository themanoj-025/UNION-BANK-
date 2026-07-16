import axios from 'axios';

const api = axios.create({
  // Use relative URL so Vite proxy forwards /api/* to the backend.
  // In production, set VITE_API_URL to the actual backend URL.
  baseURL: (import.meta.env.VITE_API_URL || '') + '/api/v2',
});

// Add a request interceptor to attach the JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Add a response interceptor to:
// 1. Unwrap the V2 ApiResponse envelope ({ success, data, error, meta })
// 2. Handle token expiration / unauthorized errors
api.interceptors.response.use((response) => {
  // Check if this is a V2 envelope response
  if (response.data && 'success' in response.data) {
    if (response.data.success === false) {
      // V2 error — reject with the error message
      return Promise.reject({
        response: {
          status: response.status,
          data: {
            detail: response.data.error || 'An error occurred',
          },
        },
      });
    }
    // V2 success — unwrap so response.data is the actual payload
    response.data = response.data.data || response.data;
  }
  // For non-envelope responses (CSV downloads, etc.), pass through
  return response;
}, (error) => {
  if (error.response && error.response.status === 401) {
    // Handle token expiration
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
  return Promise.reject(error);
});

export default api;
