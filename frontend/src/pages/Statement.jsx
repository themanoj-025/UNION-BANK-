import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import api from '../api';

function Statement() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchStatement = async () => {
      try {
        const response = await api.get('/account/statements');
        setTransactions(response.data);
      } catch (err) {
        console.error('Failed to fetch statement', err);
        setError(err.response?.data?.detail || 'Failed to load statement');
      } finally {
        setLoading(false);
      }
    };
    fetchStatement();
  }, []);

  const handleDownload = async () => {
    try {
      const response = await api.get('/account/export-csv', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'statement.csv');
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error('Failed to download CSV', err);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="dashboard-container"
      style={{ padding: '40px', maxWidth: '1000px', margin: '0 auto' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Link to="/dashboard" style={{ textDecoration: 'none', color: 'var(--gray-text)' }}>← Back</Link>
          <h2 style={{ margin: 0 }}>Account Statement</h2>
        </div>
        <button onClick={handleDownload} className="btn-secondary" style={{ padding: '8px 16px' }}>
          Download CSV
        </button>
      </div>

      {error && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#fdecea', color: 'red' }}>{error}</div>}

      <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
        {loading ? (
          <p>Loading transactions...</p>
        ) : transactions.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #eee', textAlign: 'left', color: 'var(--gray-text)' }}>
                <th style={{ padding: '15px 0' }}>Date</th>
                <th>Transaction ID</th>
                <th>Description</th>
                <th>Type</th>
                <th>Category</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th style={{ textAlign: 'right' }}>Balance</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map(tx => (
                <tr key={tx.txn_id} style={{ borderBottom: '1px solid #f5f5f5' }}>
                  <td style={{ padding: '15px 0', color: 'var(--gray-text)' }}>{new Date(tx.timestamp).toLocaleString()}</td>
                  <td style={{ fontSize: '12px', color: '#888' }}>{tx.txn_id}</td>
                  <td>{tx.description}</td>
                  <td><span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', backgroundColor: '#f0f4f8', color: '#333' }}>{tx.type}</span></td>
                  <td>{tx.category}</td>
                  <td style={{ textAlign: 'right', fontWeight: 'bold', color: tx.type.includes('DEPOSIT') || tx.type.includes('IN') ? 'green' : 'inherit' }}>
                    {tx.type.includes('DEPOSIT') || tx.type.includes('IN') ? '+' : '-'}${tx.amount.toFixed(2)}
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--gray-text)' }}>${tx.balance.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: 'var(--gray-text)' }}>No transactions found.</p>
        )}
      </div>
    </motion.div>
  );
}

export default Statement;
