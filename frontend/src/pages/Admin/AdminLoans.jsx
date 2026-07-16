import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import api from '../../api';

function AdminLoans() {
  const [pendingLoans, setPendingLoans] = useState([]);
  const [allLoans, setAllLoans] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('pending');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [rejectReason, setRejectReason] = useState({});

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [pendingRes, allRes, statsRes] = await Promise.all([
        api.get('/admin/loans/pending'),
        api.get('/admin/loans/all'),
        api.get('/admin/loans'),
      ]);
      setPendingLoans(pendingRes.data || []);
      setAllLoans(allRes.data || []);
      setStats(statsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load loans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleApprove = async (loanId) => {
    if (!window.confirm('Approve this loan? The funds will be disbursed to the customer account.')) return;
    setError('');
    setSuccess('');
    try {
      const response = await api.post(`/admin/loans/${loanId}/approve`);
      setSuccess(response.data.message);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to approve loan');
    }
  };

  const handleReject = async (loanId) => {
    const reason = rejectReason[loanId] || '';
    if (!window.confirm(`Reject this loan?${reason ? ` Reason: ${reason}` : ''}`)) return;
    setError('');
    setSuccess('');
    try {
      const response = await api.post(`/admin/loans/${loanId}/reject`, { reason });
      setSuccess(response.data.message);
      setRejectReason(prev => ({ ...prev, [loanId]: '' }));
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reject loan');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'PENDING': return { bg: '#fff3e0', color: '#e65100' };
      case 'APPROVED':
      case 'ACTIVE': return { bg: '#e3f2fd', color: '#1565c0' };
      case 'CLOSED': return { bg: '#e8f5e9', color: '#2e7d32' };
      case 'REJECTED': return { bg: '#ffebee', color: '#c62828' };
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
      <div style={{ marginBottom: '30px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '10px' }}>
          <Link to="/admin/dashboard" style={{ textDecoration: 'none', color: 'var(--gray-text)' }}>← Back</Link>
          <h2 style={{ margin: 0 }}>Loan Management</h2>
        </div>
      </div>

      {error && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#fdecea', color: 'red' }}>{error}</div>}
      {success && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#eafdf0', color: 'green' }}>{success}</div>}

      {stats && !loading && (
        <div style={{ display: 'flex', gap: '15px', marginBottom: '30px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '120px', backgroundColor: 'white', padding: '15px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', textAlign: 'center' }}>
            <p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Pending</p>
            <h3 style={{ margin: 0, fontSize: '24px', color: '#e65100' }}>{stats.total_pending}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '120px', backgroundColor: 'white', padding: '15px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', textAlign: 'center' }}>
            <p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Approved</p>
            <h3 style={{ margin: 0, fontSize: '24px', color: '#1565c0' }}>{stats.total_approved}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '120px', backgroundColor: 'white', padding: '15px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', textAlign: 'center' }}>
            <p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Active</p>
            <h3 style={{ margin: 0, fontSize: '24px', color: '#1565c0' }}>{stats.total_active}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '120px', backgroundColor: 'white', padding: '15px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', textAlign: 'center' }}>
            <p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Closed</p>
            <h3 style={{ margin: 0, fontSize: '24px', color: '#2e7d32' }}>{stats.total_closed}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '120px', backgroundColor: 'white', padding: '15px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', textAlign: 'center' }}>
            <p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Disbursed</p>
            <h3 style={{ margin: 0, fontSize: '24px', color: 'var(--dark-green)' }}>{stats.total_disbursed_formatted}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '120px', backgroundColor: 'white', padding: '15px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', textAlign: 'center' }}>
            <p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Outstanding</p>
            <h3 style={{ margin: 0, fontSize: '24px', color: '#e65100' }}>{stats.total_outstanding_formatted}</h3>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button onClick={() => setTab('pending')} className={tab === 'pending' ? 'btn-primary' : 'btn-secondary'} style={{ padding: '10px 20px' }}>
          Pending ({stats?.total_pending || 0})
        </button>
        <button onClick={() => setTab('all')} className={tab === 'all' ? 'btn-primary' : 'btn-secondary'} style={{ padding: '10px 20px' }}>
          All Loans
        </button>
      </div>

      {loading ? (
        <p>Loading loans...</p>
      ) : (
        <div style={{ backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #eee', textAlign: 'left' }}>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Loan ID</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Account</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Type</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Amount</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Interest</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Tenure</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Status</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9' }}>Applied</th>
                <th style={{ padding: '15px', backgroundColor: '#f9f9f9', minWidth: '200px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(tab === 'pending' ? pendingLoans : allLoans).map((loan) => (
                <tr key={loan.loan_id} style={{ borderBottom: '1px solid #f0f0f0' }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#fafafa'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <td style={{ padding: '15px', fontFamily: 'monospace', fontSize: '12px', color: '#888' }}>{loan.loan_id}</td>
                  <td style={{ padding: '15px', fontFamily: 'monospace', fontWeight: 'bold' }}>{loan.account_number}</td>
                  <td style={{ padding: '15px' }}>{loan.loan_type}</td>
                  <td style={{ padding: '15px', fontWeight: 'bold' }}>${loan.principal_amount.toFixed(2)}</td>
                  <td style={{ padding: '15px' }}>{loan.interest_rate}%</td>
                  <td style={{ padding: '15px' }}>{loan.tenure_months} mo</td>
                  <td style={{ padding: '15px' }}>
                    <span style={{ padding: '3px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: 'bold', ...getStatusColor(loan.status) }}>
                      {loan.status}
                    </span>
                  </td>
                  <td style={{ padding: '15px', fontSize: '12px', color: 'var(--gray-text)' }}>{new Date(loan.application_date).toLocaleDateString()}</td>
                  <td style={{ padding: '15px' }}>
                    {loan.status === 'PENDING' ? (
                      <div style={{ display: 'flex', gap: '6px', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button onClick={() => handleApprove(loan.loan_id)} className="btn-primary" style={{ padding: '5px 12px', fontSize: '12px', backgroundColor: '#2e7d32' }}>Approve</button>
                          <button onClick={() => handleReject(loan.loan_id)} style={{ padding: '5px 12px', fontSize: '12px', color: '#c62828', border: '1px solid #c62828', background: 'transparent', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>Reject</button>
                        </div>
                        <input
                          type="text"
                          value={rejectReason[loan.loan_id] || ''}
                          onChange={(e) => setRejectReason(prev => ({ ...prev, [loan.loan_id]: e.target.value }))}
                          placeholder="Rejection reason (optional)"
                          style={{ padding: '5px 8px', fontSize: '11px', border: '1px solid #ddd', borderRadius: '4px', width: '180px' }}
                        />
                      </div>
                    ) : (
                      <span style={{ fontSize: '12px', color: 'var(--gray-text)' }}>
                        {loan.status === 'REJECTED' && loan.admin_notes ? `Rejected: ${loan.admin_notes}` : loan.status}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {(tab === 'pending' ? pendingLoans : allLoans).length === 0 && (
                <tr>
                  <td colSpan={9} style={{ padding: '40px', textAlign: 'center', color: 'var(--gray-text)' }}>
                    {tab === 'pending' ? 'No pending loans.' : 'No loans found.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
}

export default AdminLoans;
