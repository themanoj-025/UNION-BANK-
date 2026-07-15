import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../api';

function Login() {
  const [accountNumber, setAccountNumber] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await api.post('/api/auth/login', {
        account_number: accountNumber,
        password: password
      });

      login(response.data.access_token, response.data.role);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred during login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.3 }}
      className="auth-container"
    >
      <div className="auth-split left">
        <div className="auth-form-container">
          <Link to="/" className="logo" style={{marginBottom: '40px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--dark-green)'}}>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12.5 3L2 19h10.5l3.5-6h13.5L12.5 3z" fill="var(--primary-green)"/>
              <path d="M11 21l-3.5 8H20l3.5-8H11z" fill="var(--primary-green)"/>
            </svg>
            <span style={{ fontWeight: '900', fontSize: '24px', letterSpacing: '-0.5px', color: 'var(--dark-green)' }}>Union Bank</span>
          </Link>
          
          <h2>Welcome back</h2>
          <p>Log in to your Union Bank account to continue.</p>

          {error && <div style={{ color: 'red', marginBottom: '15px' }}>{error}</div>}

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Account number</label>
              <input 
                type="text" 
                placeholder="Enter your 10-digit account number" 
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input 
                type="password" 
                placeholder="Enter your password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            
            <div className="form-options">
              <label className="checkbox-label">
                <input type="checkbox" />
                Remember me
              </label>
              <a href="#" className="forgot-password">Trouble logging in?</a>
            </div>

            <button type="submit" className="btn-primary auth-submit" disabled={loading}>
              {loading ? 'Logging in...' : 'Log in'}
            </button>
          </form>

          <p className="auth-switch">
            New to Union Bank? <Link to="/signup">Sign up</Link>
          </p>
        </div>
      </div>
      
      <div className="auth-split right" style={{position: 'relative'}}>
        <div style={{position: 'absolute', top: '40px', left: '40px', display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff'}}>
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12.5 3L2 19h10.5l3.5-6h13.5L12.5 3z" fill="#ffffff"/>
            <path d="M11 21l-3.5 8H20l3.5-8H11z" fill="#ffffff"/>
          </svg>
          <span style={{ fontWeight: '900', fontSize: '24px', letterSpacing: '-0.5px', color: 'var(--dark-green)' }}>Union Bank</span>
        </div>
        <div className="auth-info">
          <h2>Secure, fast, and transparent.</h2>
          <p>Join millions of Indians who trust Union Bank for their global money needs.</p>
          <img src="/images/transfer_woman.png" alt="Happy customer" className="auth-image" />
        </div>
      </div>
    </motion.div>
  );
}

export default Login;
