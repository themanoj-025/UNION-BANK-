import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../api';

function AdminDashboard() {
  const { logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get('/admin/statistics');
        setStats(response.data);
      } catch (err) {
        console.error('Failed to fetch admin statistics', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="dashboard-container"
      style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
        <h2>Admin Dashboard</h2>
        <button onClick={logout} className="btn-secondary" style={{ padding: '10px 20px', borderColor: 'red', color: 'red' }}>Log Out</button>
      </div>

      {/* Admin Navigation Cards */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '30px', flexWrap: 'wrap' }}>
        <Link to="/admin/accounts" style={{ flex: 1, minWidth: '150px', textDecoration: 'none', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', textAlign: 'center', color: 'var(--black)', transition: 'transform 0.2s, box-shadow 0.2s' }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}>
          <span style={{ fontSize: '32px', display: 'block', marginBottom: '8px' }}>👥</span>
          <strong>Accounts</strong>
        </Link>
        <Link to="/admin/transactions" style={{ flex: 1, minWidth: '150px', textDecoration: 'none', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', textAlign: 'center', color: 'var(--black)', transition: 'transform 0.2s, box-shadow 0.2s' }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}>
          <span style={{ fontSize: '32px', display: 'block', marginBottom: '8px' }}>📋</span>
          <strong>Transactions</strong>
        </Link>
        <Link to="/admin/loans" style={{ flex: 1, minWidth: '150px', textDecoration: 'none', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', textAlign: 'center', color: 'var(--black)', transition: 'transform 0.2s, box-shadow 0.2s' }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}>
          <span style={{ fontSize: '32px', display: 'block', marginBottom: '8px' }}>🏦</span>
          <strong>Loans</strong>
        </Link>
      </div>

      {loading ? (
        <p>Loading statistics...</p>
      ) : stats ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <h4 style={{ color: 'var(--gray-text)', margin: '0 0 10px 0' }}>Total Customers</h4>
            <h2 style={{ margin: 0, fontSize: '32px' }}>{stats.total_customers}</h2>
          </div>
          
          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <h4 style={{ color: 'var(--gray-text)', margin: '0 0 10px 0' }}>Active Accounts</h4>
            <h2 style={{ margin: 0, fontSize: '32px', color: 'green' }}>{stats.active_accounts}</h2>
          </div>

          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <h4 style={{ color: 'var(--gray-text)', margin: '0 0 10px 0' }}>Frozen Accounts</h4>
            <h2 style={{ margin: 0, fontSize: '32px', color: 'orange' }}>{stats.frozen_accounts}</h2>
          </div>

          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <h4 style={{ color: 'var(--gray-text)', margin: '0 0 10px 0' }}>Total Balance in Bank</h4>
            <h2 style={{ margin: 0, fontSize: '32px', color: 'var(--primary-green)' }}>{stats.total_balance_formatted}</h2>
          </div>

          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <h4 style={{ color: 'var(--gray-text)', margin: '0 0 10px 0' }}>Total Deposits</h4>
            <h2 style={{ margin: 0, fontSize: '24px' }}>${stats.total_deposits.toFixed(2)}</h2>
          </div>
          
          <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <h4 style={{ color: 'var(--gray-text)', margin: '0 0 10px 0' }}>Total Withdrawals</h4>
            <h2 style={{ margin: 0, fontSize: '24px' }}>${stats.total_withdrawals.toFixed(2)}</h2>
          </div>
        </div>
      ) : (
        <p style={{ color: 'red' }}>Failed to load statistics.</p>
      )}
    </motion.div>
  );
}

export default AdminDashboard;
