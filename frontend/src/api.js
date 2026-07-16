import axios from 'axios';

/**
 * Read a cookie value by name.
 * Used to read the CSRF token cookie for the double-submit pattern.
 */
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

const api = axios.create({
  // Use relative URL so Vite proxy forwards /api/* to the backend.
  // In production, set VITE_API_URL to the actual backend URL.
  baseURL: (import.meta.env.VITE_API_URL || '') + '/api/v2',
  // Send cookies with every request (httpOnly auth cookies)
  withCredentials: true,
});

// Add a request interceptor to attach the CSRF token header
// (double-submit cookie pattern: cookie value must match header value)
api.interceptors.request.use((config) => {
  // Only send CSRF token for state-changing methods
  const method = config.method?.toUpperCase();
  if (method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCookie('ub_csrf_token');
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
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
    // Token expired or invalid — cookies are cleared by the server.
    // Clear the readable role cookie and redirect to login.
    document.cookie = 'ub_user_role=; Path=/; Max-Age=0';
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
  return Promise.reject(error);
});

export default api;
