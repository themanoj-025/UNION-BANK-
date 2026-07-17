import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import api from '../../api';

function AdminTransactions() {
  const [accountFilter, setAccountFilter] = useState('');
  const [transactions, setTransactions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fetched, setFetched] = useState(false);

  const fetchTransactions = async () => {
    setLoading(true);
    setError('');
    setFetched(true);
    try {
      const endpoint = accountFilter
        ? `/admin/transactions?account=${encodeURIComponent(accountFilter)}`
        : '/admin/transactions';
      const response = await api.get(endpoint);
      // V2 returns a flat list; group by account number for the grouped UI
      const data = response.data;
      if (Array.isArray(data)) {
        const grouped = {};
        for (const tx of data) {
          const acc = tx.target_account || 'Unknown';
          if (!grouped[acc]) grouped[acc] = [];
          grouped[acc].push(tx);
        }
        setTransactions(grouped);
      } else {
        setTransactions(data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="dashboard-container"
      style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Link to="/admin/dashboard" style={{ textDecoration: 'none', color: 'var(--gray-text)' }}>← Back</Link>
          <h2 style={{ margin: 0 }}>All Transactions</h2>
        </div>
      </div>

      {error && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#fdecea', color: 'red' }}>{error}</div>}

      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px' }}>
        <input
          type="text"
          value={accountFilter}
          onChange={(e) => setAccountFilter(e.target.value)}
          placeholder="Filter by account number (optional)"
          style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', border: '1px solid #ddd', fontSize: '16px' }}
        />
        <button onClick={fetchTransactions} className="btn-primary" style={{ padding: '12px 24px' }} disabled={loading}>
          {loading ? 'Loading...' : 'Fetch Transactions'}
        </button>
      </div>

      {loading && <p>Loading transactions...</p>}

      {fetched && !loading && transactions && Object.keys(transactions).length > 0 && (
        <div>
          {Object.entries(transactions).map(([accNo, txns]) => (
            <div key={accNo} style={{ marginBottom: '30px', backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
              <div style={{ padding: '15px 20px', backgroundColor: '#f9f9f9', borderBottom: '1px solid #eee' }}>
                <h3 style={{ margin: 0, fontSize: '16px', fontFamily: 'monospace' }}>Account: {accNo}</h3>
                <p style={{ margin: '5px 0 0 0', fontSize: '12px', color: 'var(--gray-text)' }}>{txns.length} transaction(s)</p>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #eee', textAlign: 'left', fontSize: '12px' }}>
                      <th style={{ padding: '12px 15px' }}>Date</th>
                      <th style={{ padding: '12px 15px' }}>Txn ID</th>
                      <th style={{ padding: '12px 15px' }}>Type</th>
                      <th style={{ padding: '12px 15px' }}>Amount</th>
                      <th style={{ padding: '12px 15px' }}>Balance</th>
                      <th style={{ padding: '12px 15px' }}>Description</th>
                      <th style={{ padding: '12px 15px' }}>Category</th>
                      <th style={{ padding: '12px 15px' }}>Target</th>
                    </tr>
                  </thead>
                  <tbody>
                    {txns.map((tx) => (
                      <tr key={tx.txn_id} style={{ borderBottom: '1px solid #f5f5f5' }}
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fafafa'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                      >
                        <td style={{ padding: '10px 15px', color: 'var(--gray-text)', fontSize: '12px' }}>{new Date(tx.timestamp).toLocaleString()}</td>
                        <td style={{ padding: '10px 15px', fontFamily: 'monospace', fontSize: '11px', color: '#888' }}>{tx.txn_id}</td>
                        <td style={{ padding: '10px 15px' }}>
                          <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', backgroundColor: tx.type.includes('DEPOSIT') || tx.type.includes('IN') ? '#e8f5e9' : tx.type.includes('WITHDRAW') || tx.type.includes('OUT') ? '#ffebee' : '#f5f5f5', color: tx.type.includes('DEPOSIT') || tx.type.includes('IN') ? '#2e7d32' : tx.type.includes('WITHDRAW') || tx.type.includes('OUT') ? '#c62828' : '#333' }}>
                            {tx.type}
                          </span>
                        </td>
                        <td style={{ padding: '10px 15px', fontWeight: 'bold' }}>${tx.amount.toFixed(2)}</td>
                        <td style={{ padding: '10px 15px', color: 'var(--gray-text)' }}>${tx.balance.toFixed(2)}</td>
                        <td style={{ padding: '10px 15px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tx.description}</td>
                        <td style={{ padding: '10px 15px', fontSize: '12px' }}>{tx.category}</td>
                        <td style={{ padding: '10px 15px', fontFamily: 'monospace', fontSize: '11px' }}>{tx.target_account || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}

      {fetched && !loading && transactions && Object.keys(transactions).length === 0 && (
        <div style={{ textAlign: 'center', padding: '60px', backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <p style={{ fontSize: '40px', marginBottom: '15px' }}>📋</p>
          <p>No transactions found.</p>
        </div>
      )}
    </motion.div>
  );
}

export default AdminTransactions;
