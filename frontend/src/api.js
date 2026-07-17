import axios from 'axios';

/**
 * @file API Client for Union Bank V2 API
 *
 * All endpoints use the V2 ApiResponse envelope:
 *   { "success": boolean, "data": T | null, "error": string | null, "meta": object | null }
 *
 * The response interceptor unwraps this envelope so components receive `response.data`
 * directly as the typed payload.
 *
 * Pagination and rate-limit headers are exposed on the response for admin UIs.
 */

// ──────────────────────────────────────────────────────────────────────────────
//  JSDoc Type Definitions (used for editor autocompletion)
// ──────────────────────────────────────────────────────────────────────────────

/**
 * @typedef {Object} TokenData
 * @property {string} access_token - JWT access token
 * @property {string} refresh_token - JWT refresh token
 * @property {string} role - "customer" or "admin"
 * @property {number} expires_in - Token expiry in seconds
 */

/**
 * @typedef {Object} ProfileData
 * @property {string} account_number
 * @property {string} name
 * @property {number} age
 * @property {string} gender
 * @property {string} mobile
 * @property {string} email
 * @property {number} balance
 * @property {string} balance_formatted
 * @property {string} status - "active", "frozen", or "closed"
 * @property {string} created_at
 */

/**
 * @typedef {Object} BalanceData
 * @property {string} account_number
 * @property {string} name
 * @property {number} balance
 * @property {string} balance_formatted
 */

/**
 * @typedef {Object} TransactionOut
 * @property {string} txn_id
 * @property {string} timestamp
 * @property {string} type
 * @property {number} amount
 * @property {number} balance
 * @property {string} description
 * @property {string} category
 * @property {string|null} target_account
 */

/**
 * @typedef {Object} LoanSummaryData
 * @property {number} total_loans
 * @property {number} active_loans
 * @property {number} closed_loans
 * @property {number} total_disbursed
 * @property {string} total_disbursed_formatted
 * @property {number} total_outstanding
 * @property {string} total_outstanding_formatted
 * @property {LoanOut[]} loans
 */

/**
 * @typedef {Object} LoanOut
 * @property {string} loan_id
 * @property {string} account_number
 * @property {string} loan_type
 * @property {number} principal_amount
 * @property {number} interest_rate
 * @property {number} tenure_months
 * @property {number} emi_amount
 * @property {number} amount_paid
 * @property {number} remaining_amount
 * @property {string} status
 * @property {string} application_date
 * @property {string|null} approval_date
 * @property {string|null} next_emi_date
 * @property {string|null} purpose
 * @property {string|null} admin_notes
 * @property {number} progress_pct
 * @property {number} remaining_emis
 * @property {boolean} is_overdue
 */

/**
 * @typedef {Object} EMIPreviewData
 * @property {number} emi
 * @property {number} total_payable
 * @property {number} total_interest
 */

/**
 * @typedef {Object} SavingsGoalsSummary
 * @property {number} total_goals
 * @property {number} completed
 * @property {number} total_saved
 * @property {string} total_saved_formatted
 * @property {number} total_target
 * @property {string} total_target_formatted
 * @property {SavingsGoalOut[]} goals
 */

/**
 * @typedef {Object} SavingsGoalOut
 * @property {string} goal_id
 * @property {string} name
 * @property {number} target_amount
 * @property {number} current_amount
 * @property {string|null} target_date
 * @property {string} created_at
 * @property {boolean} is_completed
 * @property {number} progress_pct
 */

/**
 * @typedef {Object} AccountListItem
 * @property {string} account_number
 * @property {string} name
 * @property {number} balance
 * @property {string} balance_formatted
 * @property {string} status
 * @property {string} mobile
 * @property {string} email
 * @property {number} age
 * @property {string} gender
 * @property {string} created_at
 */

/**
 * @typedef {Object} StatisticsData
 * @property {number} total_customers
 * @property {number} active_accounts
 * @property {number} frozen_accounts
 * @property {number} closed_accounts
 * @property {number} total_balance
 * @property {string} total_balance_formatted
 * @property {number} total_deposits
 * @property {number} total_withdrawals
 * @property {number} total_transfers
 * @property {number} total_transactions
 */

/**
 * @typedef {Object} MessageData
 * @property {string} message
 */

/**
 * @typedef {Object} LoanAdminStats
 * @property {number} total_pending
 * @property {number} total_approved
 * @property {number} total_active
 * @property {number} total_closed
 * @property {number} total_rejected
 * @property {number} total_disbursed
 * @property {string} total_disbursed_formatted
 * @property {number} total_outstanding
 * @property {string} total_outstanding_formatted
 */

/**
 * @typedef {Object} HealthData
 * @property {string} status - "ok" or "degraded"
 * @property {string} database - "connected" or "disconnected"
 * @property {string} cache - "connected" or "disconnected"
 * @property {string} timestamp
 */

/**
 * @typedef {Object} ApiResponseMeta
 * @property {number} [page] - Current page (pagination)
 * @property {number} [per_page] - Items per page (pagination)
 * @property {number} [total] - Total items (pagination)
 * @property {string} [cursor] - Next cursor for keyset pagination
 * @property {boolean} [has_more] - Whether more results exist
 */

/**
 * @template T
 * @typedef {Object} ApiResponse
 * @property {boolean} success
 * @property {T|null} data
 * @property {string|null} error
 * @property {ApiResponseMeta|null} meta
 */

// ──────────────────────────────────────────────────────────────────────────────
//  Cookie Reader
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Read a cookie value by name.
 * Used to read the CSRF token cookie for the double-submit pattern.
 *
 * @param {string} name - Cookie name to read
 * @returns {string|null} Cookie value or null if not found
 */
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

// ──────────────────────────────────────────────────────────────────────────────
//  Axios Instance
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Pre-configured Axios instance pointing to the V2 API.
 *
 * Features:
 * - Base URL from VITE_API_URL env var or relative proxy
 * - httpOnly cookie auth with `withCredentials: true`
 * - Automatic CSRF token injection on state-changing methods
 * - Automatic ApiResponse envelope unwrapping
 * - Exposes X-Total-Count and X-RateLimit-Remaining headers on response.meta
 */
const api = axios.create({
  baseURL: (import.meta.env.VITE_API_URL || '') + '/api/v2',
  withCredentials: true,
});

// ──────────────────────────────────────────────────────────────────────────────
//  Request Interceptor — CSRF Token Injection
// ──────────────────────────────────────────────────────────────────────────────

api.interceptors.request.use((config) => {
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

// ──────────────────────────────────────────────────────────────────────────────
//  Response Interceptor — Envelope Unwrapping + Header Exposure
// ──────────────────────────────────────────────────────────────────────────────

/**
 * @param {import('axios').AxiosResponse} response
 */
api.interceptors.response.use((response) => {
  // Expose pagination/rate-limit headers on response.config for admin UIs
  const totalCount = response.headers['x-total-count'];
  const rateLimitRemaining = response.headers['x-ratelimit-remaining'];
  const retryAfter = response.headers['retry-after'];

  if (totalCount || rateLimitRemaining || retryAfter) {
    response.config.__headers = {
      totalCount,
      rateLimitRemaining,
      retryAfter,
    };
  }

  // Check if this is a V2 envelope response
  if (response.data && 'success' in response.data) {
    if (response.data.success === false) {
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
    // Preserve meta on response.config for pagination-aware components
    if (response.data.meta) {
      response.config.__meta = response.data.meta;
    }
    response.data = response.data.data || response.data;
  }
  return response;
}, (error) => {
  if (error.response && error.response.status === 401) {
    document.cookie = 'ub_user_role=; Path=/; Max-Age=0';
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
  return Promise.reject(error);
});

export default api;
