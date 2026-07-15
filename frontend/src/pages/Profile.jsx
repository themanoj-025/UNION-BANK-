import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import Dropdown from '../components/Dropdown';
import { useAuth } from '../context/AuthContext';
import api from '../api';

function Profile() {
  const { user, checkAuth, logout } = useAuth();
  
  const [profileData, setProfileData] = useState({
    name: '',
    age: '',
    gender: '',
    mobile: '',
    email: ''
  });
  
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  const [message, setMessage] = useState({ text: '', type: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user && user.role === 'customer') {
      setProfileData({
        name: user.name || '',
        age: user.age || '',
        gender: user.gender || 'Male',
        mobile: user.mobile || '',
        email: user.email || ''
      });
    }
  }, [user]);

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({ ...prev, [name]: value }));
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
  };

  const updateProfile = async (e) => {
    e.preventDefault();
    setMessage({ text: '', type: '' });
    setLoading(true);

    try {
      await api.put('/api/account/profile', {
        ...profileData,
        age: parseInt(profileData.age)
      });
      setMessage({ text: 'Profile updated successfully', type: 'success' });
      checkAuth(); // Refresh user context
    } catch (err) {
      setMessage({ text: err.response?.data?.detail || 'Failed to update profile', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const updatePassword = async (e) => {
    e.preventDefault();
    setMessage({ text: '', type: '' });
    setLoading(true);

    try {
      await api.post('/api/account/change-password', passwordData);
      setMessage({ text: 'Password changed successfully', type: 'success' });
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err) {
      setMessage({ text: err.response?.data?.detail || 'Failed to change password', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="dashboard-container"
      style={{ padding: '40px', maxWidth: '800px', margin: '0 auto' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Link to="/dashboard" style={{ textDecoration: 'none', color: 'var(--gray-text)' }}>← Back</Link>
          <h2 style={{ margin: 0 }}>My Profile</h2>
        </div>
        <button onClick={logout} className="btn-secondary" style={{ padding: '8px 16px', color: 'red', borderColor: 'red' }}>
          Log Out
        </button>
      </div>

      {message.text && (
        <div style={{ 
          padding: '15px', 
          marginBottom: '20px', 
          borderRadius: '8px',
          backgroundColor: message.type === 'error' ? '#fdecea' : '#eafdf0',
          color: message.type === 'error' ? 'red' : 'green'
        }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', gap: '30px', flexDirection: 'column' }}>
        <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <h3>Personal Information</h3>
          <form onSubmit={updateProfile} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '20px' }}>
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Account Number</label>
              <input type="text" value={user?.account_number || ''} disabled style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', backgroundColor: '#f5f5f5' }} />
            </div>
            
            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Full Name</label>
              <input type="text" name="name" value={profileData.name} onChange={handleProfileChange} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Age</label>
              <input type="number" name="age" value={profileData.age} onChange={handleProfileChange} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Gender</label>
              <Dropdown options={['Male', 'Female', 'Other']} value={profileData.gender} onChange={(val) => setProfileData(p => ({...p, gender: val}))} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Mobile</label>
              <input type="tel" name="mobile" value={profileData.mobile} onChange={handleProfileChange} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Email</label>
              <input type="email" name="email" value={profileData.email} onChange={handleProfileChange} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd' }} />
            </div>

            <div style={{ gridColumn: '1 / -1', marginTop: '10px' }}>
              <button type="submit" className="btn-primary" disabled={loading} style={{ padding: '10px 20px' }}>
                Update Profile
              </button>
            </div>
          </form>
        </div>

        <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <h3>Change Password</h3>
          <form onSubmit={updatePassword} style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '20px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Current Password</label>
              <input type="password" name="current_password" value={passwordData.current_password} onChange={handlePasswordChange} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>New Password</label>
              <input type="password" name="new_password" value={passwordData.new_password} onChange={handlePasswordChange} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Confirm New Password</label>
              <input type="password" name="confirm_password" value={passwordData.confirm_password} onChange={handlePasswordChange} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd' }} />
            </div>

            <div style={{ marginTop: '10px' }}>
              <button type="submit" className="btn-secondary" disabled={loading} style={{ padding: '10px 20px' }}>
                Change Password
              </button>
            </div>
          </form>
        </div>
      </div>
    </motion.div>
  );
}

export default Profile;
