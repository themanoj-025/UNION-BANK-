import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import Dropdown from '../../components/Dropdown';
import api from '../../api';

function SignUp() {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    gender: 'Male',
    mobile: '',
    email: '',
    password: '',
    confirm_password: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleGenderChange = (val) => {
    setFormData(prev => ({ ...prev, gender: val }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const response = await api.post('/auth/register', {
        name: formData.name,
        age: parseInt(formData.age),
        gender: formData.gender,
        mobile: formData.mobile,
        email: formData.email,
        password: formData.password,
        confirm_password: formData.confirm_password
      });

      setSuccess(response.data.message);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred during sign up');
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
        <div className="auth-form-container" style={{ maxHeight: '90vh', overflowY: 'auto', paddingRight: '15px', scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
          <style>{`
            .auth-form-container::-webkit-scrollbar {
              display: none;
            }
          `}</style>
          <Link to="/" className="logo" style={{marginBottom: '30px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--dark-green)'}}>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12.5 3L2 19h10.5l3.5-6h13.5L12.5 3z" fill="var(--primary-green)"/>
              <path d="M11 21l-3.5 8H20l3.5-8H11z" fill="var(--primary-green)"/>
            </svg>
            <span style={{ fontWeight: '900', fontSize: '24px', letterSpacing: '-0.5px', color: 'var(--dark-green)' }}>Union Bank</span>
          </Link>
          
          <h2>Create your account</h2>
          <p>Join Union Bank to send, spend, and manage your money globally.</p>

          {error && <div style={{ color: 'red', marginBottom: '15px' }}>{error}</div>}
          {success && <div style={{ color: 'green', marginBottom: '15px' }}>{success} Redirecting to login...</div>}

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="signup-name">Full Name</label>
              <input id="signup-name" type="text" name="name" placeholder="John Doe" value={formData.name} onChange={handleChange} autoComplete="name" aria-label="Full name" required />
            </div>
            
            <div style={{ display: 'flex', gap: '15px' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label htmlFor="signup-age">Age</label>
                <input id="signup-age" type="number" name="age" placeholder="18" value={formData.age} onChange={handleChange} autoComplete="bday" aria-label="Age" required />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label htmlFor="signup-gender">Gender</label>
                <div id="signup-gender" aria-label="Gender">
                <Dropdown 
                  options={['Male', 'Female', 'Other']} 
                  value={formData.gender} 
                  onChange={handleGenderChange} 
                />
                </div>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="signup-mobile">Mobile Number</label>
              <input id="signup-mobile" type="tel" name="mobile" placeholder="10-digit number" value={formData.mobile} onChange={handleChange} autoComplete="tel" aria-label="Mobile number" required />
            </div>

            <div className="form-group">
              <label htmlFor="signup-email">Email address</label>
              <input id="signup-email" type="email" name="email" placeholder="Enter your email" value={formData.email} onChange={handleChange} autoComplete="email" aria-label="Email address" required />
            </div>
            
            <div className="form-group">
              <label htmlFor="signup-password">Password</label>
              <input id="signup-password" type="password" name="password" placeholder="Create a password" value={formData.password} onChange={handleChange} autoComplete="new-password" aria-label="Password" required />
            </div>

            <div className="form-group">
              <label htmlFor="signup-confirm-password">Confirm Password</label>
              <input id="signup-confirm-password" type="password" name="confirm_password" placeholder="Confirm your password" value={formData.confirm_password} onChange={handleChange} autoComplete="new-password" aria-label="Confirm password" required />
            </div>
            
            <p style={{fontSize: '12px', color: 'var(--gray-text)', margin: '15px 0'}}>
              By registering, you confirm that you accept our Terms of Use and Privacy Policy.
            </p>

            <button type="submit" className="btn-primary auth-submit" disabled={loading}>
              {loading ? 'Signing up...' : 'Sign up'}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Log in</Link>
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
          <h2>Your money, without borders.</h2>
          <p>Get the mid-market exchange rate every time, with no hidden fees.</p>
          <img src="/images/travel_card.png" alt="Travel card" className="auth-image" />
        </div>
      </div>
    </motion.div>
  );
}

export default SignUp;
