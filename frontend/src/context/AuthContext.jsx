import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const AuthContext = createContext();

/**
 * Read a cookie value by name (for non-httpOnly cookies like role).
 * httpOnly cookies (access_token, refresh_token) cannot be read by JS.
 */
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    // Token is now in httpOnly cookie — we can't read it directly,
    // but we can try to call an authenticated endpoint to check.
    // The role cookie IS readable (not httpOnly) for UI routing.
    const role = getCookie('ub_user_role');

    try {
      if (role === 'admin') {
        setUser({ role: 'admin' });
      } else if (role === 'customer') {
        const res = await api.get('/account/profile');
        setUser({ ...res.data, role: 'customer' });
      } else {
        // No role cookie — not logged in
        setUser(null);
      }
    } catch (err) {
      console.error("Auth check failed", err);
      logout();
    }
    setLoading(false);
  };

  const login = (token, role, profileData = null) => {
    // Tokens are now set as httpOnly cookies by the backend response.
    // We just need to update the React state for UI rendering.
    // The backend sets ub_user_role cookie (readable) for UI routing.
    if (profileData) {
      setUser({ ...profileData, role });
    } else {
      setUser({ role });
    }
  };

  const logout = () => {
    // Backend clears cookies on logout. We just clear React state.
    // Also clear the readable role cookie.
    document.cookie = 'ub_user_role=; Path=/; Max-Age=0';
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, checkAuth }}>
      {!loading && children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
