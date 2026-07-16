import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import api from '../api';

const LOAN_TYPES = ['Personal', 'Home', 'Vehicle', 'Education', 'Business'];

function Loans() {
  const [loans, setLoans] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showApplyForm, setShowApplyForm] = useState(false);
  const [showEmiCalc, setShowEmiCalc] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [applyData, setApplyData] = useState({
    loan_type: 'Personal',
    principal_amount: '',
    interest_rate: '10',
    tenure_months: '12',
    purpose: '',
  });

  const [emiCalc, setEmiCalc] = useState({
    principal: 100000,
    annual_rate: 10,
    tenure_months: 12,
  });
  const [emiResult, setEmiResult] = useState(null);

  const [payEmiLoan, setPayEmiLoan] = useState(null);
  const [payEmiAmount, setPayEmiAmount] = useState('');

  const fetchLoans = async () => {
    try {
      const response = await api.get('/loans');
      const data = response.data;
      setLoans(data.loans || []);
      setSummary(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load loans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLoans();
  }, []);

  const handleApply = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const response = await api.post('/loans/apply', {
        loan_type: applyData.loan_type,
        principal_amount: parseFloat(applyData.principal_amount),
        interest_rate: parseFloat(applyData.interest_rate),
        tenure_months: parseInt(applyData.tenure_months),
        purpose: applyData.purpose,
      });
      setSuccess(response.data.message);
      setShowApplyForm(false);
      fetchLoans();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to apply for loan');
    }
  };

  const handleCalcEmi = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await api.post('/loans/calculate-emi', {
        principal: parseFloat(emiCalc.principal),
        annual_rate: parseFloat(emiCalc.annual_rate),
        tenure_months: parseInt(emiCalc.tenure_months),
      });
      setEmiResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to calculate EMI');
    }
  };

  const handlePayEmi = async (loanId) => {
    if (!payEmiAmount || parseFloat(payEmiAmount) <= 0) return;
    setError('');
    setSuccess('');
    try {
      const response = await api.post(`/loans/${loanId}/pay-emi`, {
        amount: parseFloat(payEmiAmount),
      });
      setSuccess(response.data.message);
      setPayEmiLoan(null);
      setPayEmiAmount('');
      fetchLoans();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to pay EMI');
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
      style={{ padding: '40px', maxWidth: '1000px', margin: '0 auto' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Link to="/dashboard" style={{ textDecoration: 'none', color: 'var(--gray-text)' }}>← Back</Link>
          <h2 style={{ margin: 0 }}>Loans</h2>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={() => setShowEmiCalc(!showEmiCalc)} className="btn-secondary" style={{ padding: '10px 20px' }}>
            {showEmiCalc ? 'Close Calculator' : 'Calculate EMI'}
          </button>
          <button onClick={() => setShowApplyForm(!showApplyForm)} className="btn-primary" style={{ padding: '10px 20px' }}>
            {showApplyForm ? 'Cancel' : '+ Apply for Loan'}
          </button>
        </div>
      </div>

      {error && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#fdecea', color: 'red' }}>{error}</div>}
      {success && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#eafdf0', color: 'green' }}>{success}</div>}

      <AnimatePresence>
        {showEmiCalc && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden', marginBottom: '20px' }}
          >
            <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
              <h3 style={{ marginBottom: '20px' }}>EMI Calculator</h3>
              <form onSubmit={handleCalcEmi} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Loan Amount ($)</label>
                    <input type="number" value={emiCalc.principal} onChange={(e) => setEmiCalc(p => ({...p, principal: e.target.value}))} style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                  </div>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Interest Rate (% p.a.)</label>
                    <input type="number" step="0.1" value={emiCalc.annual_rate} onChange={(e) => setEmiCalc(p => ({...p, annual_rate: e.target.value}))} style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                  </div>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Tenure (months)</label>
                    <input type="number" value={emiCalc.tenure_months} onChange={(e) => setEmiCalc(p => ({...p, tenure_months: e.target.value}))} style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                  </div>
                </div>
                <button type="submit" className="btn-secondary" style={{ padding: '12px', fontSize: '16px' }}>Calculate</button>
              </form>
              {emiResult && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: '20px', padding: '20px', backgroundColor: '#e5f8f5', borderRadius: '8px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '15px' }}>
                  <div><p style={{ fontSize: '12px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Monthly EMI</p><p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>${emiResult.emi.toFixed(2)}</p></div>
                  <div><p style={{ fontSize: '12px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Total Payable</p><p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>${emiResult.total_payable.toFixed(2)}</p></div>
                  <div><p style={{ fontSize: '12px', color: 'var(--gray-text)', margin: '0 0 5px 0' }}>Total Interest</p><p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>${emiResult.total_interest.toFixed(2)}</p></div>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showApplyForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden', marginBottom: '20px' }}
          >
            <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
              <h3 style={{ marginBottom: '20px' }}>Apply for a Loan</h3>
              <form onSubmit={handleApply} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Loan Type</label>
                    <select value={applyData.loan_type} onChange={(e) => setApplyData(p => ({...p, loan_type: e.target.value}))} style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px', background: 'white' }}>
                      {LOAN_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Amount ($)</label>
                    <input type="number" step="0.01" min="1000" value={applyData.principal_amount} onChange={(e) => setApplyData(p => ({...p, principal_amount: e.target.value}))} placeholder="10000" required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Interest Rate (% p.a.)</label>
                    <input type="number" step="0.1" value={applyData.interest_rate} onChange={(e) => setApplyData(p => ({...p, interest_rate: e.target.value}))} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                  </div>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Tenure (months)</label>
                    <input type="number" value={applyData.tenure_months} onChange={(e) => setApplyData(p => ({...p, tenure_months: e.target.value}))} required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                  </div>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Purpose (optional)</label>
                  <textarea value={applyData.purpose} onChange={(e) => setApplyData(p => ({...p, purpose: e.target.value}))} placeholder="Tell us why you need this loan" style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px', minHeight: '60px' }} />
                </div>
                <button type="submit" className="btn-primary" style={{ padding: '12px', fontSize: '16px' }}>Submit Application</button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {summary && !loading && (
        <div style={{ display: 'flex', gap: '20px', marginBottom: '30px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '150px', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <p style={{ color: 'var(--gray-text)', margin: '0 0 8px 0', fontSize: '14px' }}>Total Loans</p>
            <h3 style={{ margin: 0, fontSize: '28px' }}>{summary.total_loans}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '150px', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <p style={{ color: 'var(--gray-text)', margin: '0 0 8px 0', fontSize: '14px' }}>Active</p>
            <h3 style={{ margin: 0, fontSize: '28px', color: '#1565c0' }}>{summary.active_loans}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '150px', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <p style={{ color: 'var(--gray-text)', margin: '0 0 8px 0', fontSize: '14px' }}>Outstanding</p>
            <h3 style={{ margin: 0, fontSize: '28px', color: 'var(--dark-green)' }}>{summary.total_outstanding_formatted}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '150px', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <p style={{ color: 'var(--gray-text)', margin: '0 0 8px 0', fontSize: '14px' }}>Closed</p>
            <h3 style={{ margin: 0, fontSize: '28px', color: 'green' }}>{summary.closed_loans}</h3>
          </div>
        </div>
      )}

      {loading ? (
        <p>Loading loans...</p>
      ) : loans.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          {loans.map((loan) => (
            <motion.div
              key={loan.loan_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ backgroundColor: 'white', padding: '25px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px', flexWrap: 'wrap', gap: '10px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '5px' }}>
                    <h3 style={{ margin: 0, fontSize: '20px' }}>{loan.loan_type} Loan</h3>
                    <span style={{ padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 'bold', ...getStatusColor(loan.status) }}>{loan.status}</span>
                    {loan.is_overdue && <span style={{ padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 'bold', backgroundColor: '#ffebee', color: '#c62828' }}>OVERDUE</span>}
                  </div>
                  <p style={{ margin: 0, fontSize: '13px', color: 'var(--gray-text)' }}>
                    Applied: {new Date(loan.application_date).toLocaleDateString()}
                    {loan.approval_date && ` | Approved: ${new Date(loan.approval_date).toLocaleDateString()}`}
                  </p>
                  {loan.purpose && <p style={{ margin: '5px 0 0 0', fontSize: '13px', color: 'var(--gray-text)' }}>Purpose: {loan.purpose}</p>}
                </div>
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>${loan.principal_amount.toFixed(2)}</p>
                  <p style={{ fontSize: '12px', color: 'var(--gray-text)', margin: 0 }}>Principal</p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '15px', marginBottom: '15px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
                <div><p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 3px 0' }}>Interest Rate</p><p style={{ fontSize: '16px', fontWeight: 'bold', margin: 0 }}>{loan.interest_rate}%</p></div>
                <div><p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 3px 0' }}>Tenure</p><p style={{ fontSize: '16px', fontWeight: 'bold', margin: 0 }}>{loan.tenure_months} mo</p></div>
                <div><p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 3px 0' }}>EMI</p><p style={{ fontSize: '16px', fontWeight: 'bold', margin: 0 }}>${loan.emi_amount.toFixed(2)}</p></div>
                <div><p style={{ fontSize: '11px', color: 'var(--gray-text)', margin: '0 0 3px 0' }}>Remaining EMIs</p><p style={{ fontSize: '16px', fontWeight: 'bold', margin: 0 }}>{loan.remaining_emis}</p></div>
              </div>

              {['APPROVED', 'ACTIVE'].includes(loan.status) && (
                <>
                  <div style={{ marginBottom: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '14px' }}>
                      <span style={{ fontWeight: 'bold' }}>Paid: ${loan.amount_paid.toFixed(2)}</span>
                      <span style={{ color: 'var(--gray-text)' }}>Remaining: ${loan.remaining_amount.toFixed(2)}</span>
                    </div>
                    <div style={{ height: '8px', backgroundColor: '#f0f0f0', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', borderRadius: '4px', backgroundColor: loan.progress_pct >= 100 ? '#4caf50' : '#1565c0', width: `${Math.min(loan.progress_pct, 100)}%` }} />
                    </div>
                    <p style={{ textAlign: 'right', fontSize: '11px', color: 'var(--gray-text)', margin: '3px 0 0 0' }}>{loan.progress_pct}% paid</p>
                  </div>

                  {loan.next_emi_date && (
                    <p style={{ fontSize: '13px', margin: '0 0 10px 0' }}>
                      Next EMI due: <strong>{new Date(loan.next_emi_date).toLocaleDateString()}</strong>
                    </p>
                  )}

                  <div>
                    {payEmiLoan === loan.loan_id ? (
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
                        <div style={{ flex: 1 }}>
                          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', fontSize: '13px' }}>Amount to pay</label>
                          <input type="number" step="0.01" min="0.01" value={payEmiAmount} onChange={(e) => setPayEmiAmount(e.target.value)} placeholder={`EMI: $${loan.emi_amount.toFixed(2)}`} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '14px' }} />
                        </div>
                        <button onClick={() => handlePayEmi(loan.loan_id)} className="btn-primary" style={{ padding: '10px 20px', whiteSpace: 'nowrap' }}>Pay</button>
                        <button onClick={() => setPayEmiLoan(null)} style={{ padding: '10px 15px', background: 'none', border: '1px solid #ddd', borderRadius: '6px', cursor: 'pointer' }}>Cancel</button>
                      </div>
                    ) : (
                      <button onClick={() => { setPayEmiLoan(loan.loan_id); setPayEmiAmount(loan.emi_amount.toString()); }} className="btn-secondary" style={{ padding: '8px 16px', fontSize: '13px' }}>
                        Pay EMI
                      </button>
                    )}
                  </div>
                </>
              )}
            </motion.div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '60px 20px', backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <p style={{ fontSize: '48px', marginBottom: '20px' }}>🏦</p>
          <h3>No loans yet</h3>
          <p style={{ color: 'var(--gray-text)', marginBottom: '20px' }}>Apply for a loan to get started!</p>
          <button onClick={() => setShowApplyForm(true)} className="btn-primary" style={{ padding: '12px 24px' }}>Apply for a Loan</button>
        </div>
      )}
    </motion.div>
  );
}

export default Loans;
