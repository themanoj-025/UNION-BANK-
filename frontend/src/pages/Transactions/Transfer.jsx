import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import Dropdown from '../../components/Dropdown';
import api from '../../api';

function Transfer() {
  const [targetAccount, setTargetAccount] = useState('');
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('General');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const categories = [
    "General", "Food & Dining", "Transport", "Shopping",
    "Bills & Utilities", "Entertainment", "Health", "Education",
    "Salary", "Savings", "Investment", "Rent", "Other"
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await api.post('/api/account/transfer', {
        target_account: targetAccount,
        amount: parseFloat(amount),
        category
      });
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred processing the transfer');
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="dashboard-container"
      style={{ padding: '40px', maxWidth: '600px', margin: '0 auto' }}
    >
      <div style={{ marginBottom: '30px', display: 'flex', alignItems: 'center', gap: '15px' }}>
        <Link to="/dashboard" style={{ textDecoration: 'none', color: 'var(--gray-text)' }}>← Back</Link>
        <h2 style={{ margin: 0 }}>Transfer Funds</h2>
      </div>

      <div style={{ backgroundColor: 'white', padding: '40px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
        {error && <div style={{ color: 'red', marginBottom: '20px' }}>{error}</div>}
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Recipient Account Number</label>
            <input 
              type="text" 
              value={targetAccount} 
              onChange={(e) => setTargetAccount(e.target.value)} 
              placeholder="10-digit account number" 
              required 
              style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Amount</label>
            <input 
              type="number" 
              step="0.01" 
              min="0.01" 
              value={amount} 
              onChange={(e) => setAmount(e.target.value)} 
              placeholder="0.00" 
              required 
              style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Category</label>
            <Dropdown 
              options={categories}
              value={category}
              onChange={setCategory}
            />
          </div>

          <button 
            type="submit" 
            className="btn-primary" 
            disabled={loading}
            style={{ padding: '15px', fontSize: '16px', marginTop: '10px' }}
          >
            {loading ? 'Processing...' : 'Confirm Transfer'}
          </button>
        </form>
      </div>
    </motion.div>
  );
}

export default Transfer;
