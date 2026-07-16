import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';

function Dashboard() {
  const { user } = useAuth();
  const [balance, setBalance] = useState('0.00');
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [balRes, txRes] = await Promise.all([
          api.get('/account/balance'),
          api.get('/account/statements/mini')
        ]);
        setBalance(balRes.data.balance_formatted);
        setTransactions(txRes.data);
      } catch (err) {
        console.error('Failed to fetch dashboard data', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="dashboard-container"
      style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
        <h2>Welcome back, {user?.name || 'Customer'}</h2>
        <div style={{ display: 'flex', gap: '15px' }}>
          <Link to="/deposit" className="btn-primary" style={{ padding: '10px 20px', textDecoration: 'none' }}>Deposit</Link>
          <Link to="/withdraw" className="btn-secondary" style={{ padding: '10px 20px', textDecoration: 'none' }}>Withdraw</Link>
          <Link to="/transfer" className="btn-secondary" style={{ padding: '10px 20px', textDecoration: 'none' }}>Transfer</Link>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '15px', marginBottom: '30px', flexWrap: 'wrap' }}>
        <Link to="/savings" style={{ flex: 1, minWidth: '150px', textDecoration: 'none', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', textAlign: 'center', color: 'var(--black)', transition: 'transform 0.2s, box-shadow 0.2s' }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}>
          <span style={{ fontSize: '32px', display: 'block', marginBottom: '8px' }}>🎯</span>
          <strong>Savings Goals</strong>
        </Link>
        <Link to="/loans" style={{ flex: 1, minWidth: '150px', textDecoration: 'none', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', textAlign: 'center', color: 'var(--black)', transition: 'transform 0.2s, box-shadow 0.2s' }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}>
          <span style={{ fontSize: '32px', display: 'block', marginBottom: '8px' }}>🏦</span>
          <strong>Loans</strong>
        </Link>
        <Link to="/profile" style={{ flex: 1, minWidth: '150px', textDecoration: 'none', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', textAlign: 'center', color: 'var(--black)', transition: 'transform 0.2s, box-shadow 0.2s' }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}>
          <span style={{ fontSize: '32px', display: 'block', marginBottom: '8px' }}>👤</span>
          <strong>Profile</strong>
        </Link>
      </div>

      <div style={{ display: 'flex', gap: '30px' }}>
        <div style={{ flex: 1, backgroundColor: 'var(--primary-green)', color: 'white', padding: '30px', borderRadius: '12px' }}>
          <p style={{ margin: '0 0 10px 0', fontSize: '18px', opacity: 0.9 }}>Available Balance</p>
          <h1 style={{ margin: 0, fontSize: '48px', fontWeight: 'bold' }}>{loading ? '...' : balance}</h1>
          <p style={{ marginTop: '20px', opacity: 0.8 }}>Account: {user?.account_number}</p>
        </div>

        <div style={{ flex: 2, backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ margin: 0 }}>Recent Transactions</h3>
            <Link to="/statement" style={{ color: 'var(--primary-green)', textDecoration: 'none', fontWeight: 'bold' }}>View All</Link>
          </div>
          
          {loading ? (
            <p>Loading transactions...</p>
          ) : transactions.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #eee', textAlign: 'left', color: 'var(--gray-text)' }}>
                  <th style={{ padding: '10px 0' }}>Date</th>
                  <th>Description</th>
                  <th>Type</th>
                  <th style={{ textAlign: 'right' }}>Amount</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map(tx => (
                  <tr key={tx.txn_id} style={{ borderBottom: '1px solid #f5f5f5' }}>
                    <td style={{ padding: '15px 0', color: 'var(--gray-text)' }}>{new Date(tx.timestamp).toLocaleDateString()}</td>
                    <td>{tx.description}</td>
                    <td><span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', backgroundColor: '#f0f4f8', color: '#333' }}>{tx.type}</span></td>
                    <td style={{ textAlign: 'right', fontWeight: 'bold', color: tx.type.includes('DEPOSIT') || tx.type.includes('IN') ? 'green' : 'inherit' }}>
                      {tx.type.includes('DEPOSIT') || tx.type.includes('IN') ? '+' : '-'}${tx.amount.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p style={{ color: 'var(--gray-text)' }}>No recent transactions.</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default Dashboard;
