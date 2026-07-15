import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');
    const role = localStorage.getItem('user_role');
    if (token) {
      try {
        if (role === 'admin') {
          // Just setting basic role for admin since there isn't a specific admin profile endpoint in the standard API we saw,
          // but we can adjust if there is one.
          setUser({ role: 'admin' });
        } else {
          const res = await api.get('/api/account/profile');
          setUser({ ...res.data, role: 'customer' });
        }
      } catch (err) {
        console.error("Auth check failed", err);
        logout();
      }
    }
    setLoading(false);
  };

  const login = (token, role, profileData = null) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_role', role);
    if (profileData) {
      setUser({ ...profileData, role });
    } else {
      setUser({ role });
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, checkAuth }}>
      {!loading && children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
