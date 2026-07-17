import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import api from '../../api';

function AdminAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchAccounts = async (query) => {
    setLoading(true);
    setError('');
    try {
      const endpoint = query
        ? `/admin/accounts/search?q=${encodeURIComponent(query)}`
        : '/admin/accounts';
      const response = await api.get(endpoint);
      const data = response.data;
      setAccounts(Array.isArray(data) ? data : data.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load accounts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchAccounts(search);
  };

  const handleFreeze = async (accNo, name) => {
    if (!window.confirm(`Freeze account ${accNo} (${name})?`)) return;
    setError('');
    setSuccess('');
    try {
      const response = await api.post(`/admin/accounts/${accNo}/freeze`);
      setSuccess(response.data.message);
      fetchAccounts(search);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to freeze account');
    }
  };

  const handleUnfreeze = async (accNo, name) => {
    if (!window.confirm(`Unfreeze account ${accNo} (${name})?`)) return;
    setError('');
    setSuccess('');
    try {
      const response = await api.post(`/admin/accounts/${accNo}/unfreeze`);
      setSuccess(response.data.message);
      fetchAccounts(search);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to unfreeze account');
    }
  };

  const handleDelete = async (accNo, name) => {
    if (!window.confirm(`PERMANENTLY DELETE account ${accNo} (${name})? This cannot be undone!`)) return;
    setError('');
    setSuccess('');
    try {
      const response = await api.delete(`/admin/accounts/${accNo}`);
      setSuccess(response.data.message);
      fetchAccounts(search);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete account');
    }
  };

  const getStatusStyle = (status) => {
    switch (status) {
      case 'active': return { bg: '#e8f5e9', color: '#2e7d32' };
      case 'frozen': return { bg: '#fff3e0', color: '#e65100' };
      case 'closed': return { bg: '#ffebee', color: '#c62828' };
      default: return { bg: '#f5f5f5', color: '#616161' };
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="dashboard-container"
      style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Link to="/admin/dashboard" style={{ textDecoration: 'none', color: 'var(--gray-text)' }}>← Back</Link>
          <h2 style={{ margin: 0 }}>Account Management</h2>
        </div>
      </div>

      {error && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#fdecea', color: 'red' }}>{error}</div>}
      {success && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#eafdf0', color: 'green' }}>{success}</div>}

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by account number or name..."
          style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '16px' }}
        />
        <button type="submit" className="btn-secondary" style={{ padding: '12px 24px' }}>Search</button>
        {search && <button type="button" onClick={() => { setSearch(''); fetchAccounts(); }} className="btn-secondary" style={{ padding: '12px 24px', backgroundColor: '#f0f0f0' }}>Clear</button>}
      </form>

      {loading ? (
        <p>Loading accounts...</p>
      ) : accounts.length > 0 ? (
        <div style={{ backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #eee', textAlign: 'left' }}>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Account #</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Name</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Balance</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Status</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Mobile</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Email</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((acc) => (
                <tr key={acc.account_number} style={{ borderBottom: '1px solid #f0f0f0', transition: 'background 0.2s' }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fafafa'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <td style={{ padding: '15px', fontWeight: 'bold', fontFamily: 'monospace' }}>{acc.account_number}</td>
                  <td style={{ padding: '15px' }}>{acc.name}</td>
                  <td style={{ padding: '15px', fontWeight: 'bold' }}>{acc.balance_formatted}</td>
                  <td style={{ padding: '15px' }}>
                    <span style={{ padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase', ...getStatusStyle(acc.status) }}>
                      {acc.status}
                    </span>
                  </td>
                  <td style={{ padding: '15px', color: 'var(--gray-text)' }}>{acc.mobile}</td>
                  <td style={{ padding: '15px', color: 'var(--gray-text)', fontSize: '12px' }}>{acc.email}</td>
                  <td style={{ padding: '15px' }}>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {acc.status === 'active' && (
                        <button onClick={() => handleFreeze(acc.account_number, acc.name)} className="btn-secondary" style={{ padding: '5px 10px', fontSize: '11px', color: '#e65100', border: '1px solid #e65100', background: 'transparent' }}>
                          Freeze
                        </button>
                      )}
                      {acc.status === 'frozen' && (
                        <button onClick={() => handleUnfreeze(acc.account_number, acc.name)} className="btn-secondary" style={{ padding: '5px 10px', fontSize: '11px', color: '#2e7d32', border: '1px solid #2e7d32', background: 'transparent' }}>
                          Unfreeze
                        </button>
                      )}
                      {acc.status !== 'closed' && (
                        <button onClick={() => handleDelete(acc.account_number, acc.name)} style={{ padding: '5px 10px', fontSize: '11px', color: '#c62828', border: '1px solid #c62828', background: 'transparent', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '60px', backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <p style={{ fontSize: '40px', marginBottom: '15px' }}>🔍</p>
          <p>No accounts found.</p>
        </div>
      )}
    </motion.div>
  );
}

export default AdminAccounts;
