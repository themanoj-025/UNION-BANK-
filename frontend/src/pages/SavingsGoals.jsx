import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import api from '../api';

function SavingsGoals() {
  const [goals, setGoals] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [contributingGoal, setContributingGoal] = useState(null);
  const [contributeAmount, setContributeAmount] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    target_amount: '',
    target_date: '',
  });

  const fetchGoals = async () => {
    try {
      const response = await api.get('/savings');
      const data = response.data;
      setGoals(data.goals || []);
      setSummary(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load savings goals');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGoals();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await api.post('/savings', {
        name: formData.name,
        target_amount: parseFloat(formData.target_amount),
        target_date: formData.target_date || null,
      });
      setSuccess(`Goal "${formData.name}" created!`);
      setFormData({ name: '', target_amount: '', target_date: '' });
      setShowForm(false);
      fetchGoals();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create goal');
    }
  };

  const handleContribute = async (goalId) => {
    if (!contributeAmount || parseFloat(contributeAmount) <= 0) return;
    setError('');
    setSuccess('');
    try {
      await api.post(`/savings/${goalId}/contribute`, {
        amount: parseFloat(contributeAmount),
      });
      setSuccess('Contribution made successfully!');
      setContributingGoal(null);
      setContributeAmount('');
      fetchGoals();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to contribute');
    }
  };

  const handleDelete = async (goalId, goalName) => {
    if (!window.confirm(`Delete goal "${goalName}"? The amount will be refunded to your balance.`)) return;
    setError('');
    setSuccess('');
    try {
      await api.delete(`/savings/${goalId}`);
      setSuccess(`Goal "${goalName}" deleted and refunded.`);
      fetchGoals();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete goal');
    }
  };

  const getProgressColor = (pct) => {
    if (pct >= 100) return '#4caf50';
    if (pct >= 50) return '#8bc34a';
    if (pct >= 25) return '#ff9800';
    return '#f44336';
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
          <h2 style={{ margin: 0 }}>Savings Goals</h2>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary" style={{ padding: '10px 20px' }}>
          {showForm ? 'Cancel' : '+ New Goal'}
        </button>
      </div>

      {error && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#fdecea', color: 'red' }}>{error}</div>}
      {success && <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '8px', backgroundColor: '#eafdf0', color: 'green' }}>{success}</div>}

      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden', marginBottom: '20px' }}
          >
            <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
              <h3 style={{ marginBottom: '20px' }}>Create New Savings Goal</h3>
              <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Goal Name</label>
                  <input type="text" value={formData.name} onChange={(e) => setFormData(p => ({...p, name: e.target.value}))} placeholder="e.g., New Laptop" required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                </div>
                <div style={{ display: 'flex', gap: '15px' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Target Amount ($)</label>
                    <input type="number" step="0.01" min="0.01" value={formData.target_amount} onChange={(e) => setFormData(p => ({...p, target_amount: e.target.value}))} placeholder="1000.00" required style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Target Date (optional)</label>
                    <input type="date" value={formData.target_date} onChange={(e) => setFormData(p => ({...p, target_date: e.target.value}))} style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '16px' }} />
                  </div>
                </div>
                <button type="submit" className="btn-primary" style={{ padding: '12px', fontSize: '16px', marginTop: '10px' }}>Create Goal</button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {summary && !loading && (
        <div style={{ display: 'flex', gap: '20px', marginBottom: '30px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '200px', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <p style={{ color: 'var(--gray-text)', margin: '0 0 8px 0', fontSize: '14px' }}>Total Goals</p>
            <h3 style={{ margin: 0, fontSize: '28px' }}>{summary.total_goals}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '200px', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <p style={{ color: 'var(--gray-text)', margin: '0 0 8px 0', fontSize: '14px' }}>Completed</p>
            <h3 style={{ margin: 0, fontSize: '28px', color: 'green' }}>{summary.completed}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '200px', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <p style={{ color: 'var(--gray-text)', margin: '0 0 8px 0', fontSize: '14px' }}>Total Saved</p>
            <h3 style={{ margin: 0, fontSize: '28px', color: 'var(--dark-green)' }}>{summary.total_saved_formatted}</h3>
          </div>
          <div style={{ flex: 1, minWidth: '200px', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <p style={{ color: 'var(--gray-text)', margin: '0 0 8px 0', fontSize: '14px' }}>Total Target</p>
            <h3 style={{ margin: 0, fontSize: '28px' }}>{summary.total_target_formatted}</h3>
          </div>
        </div>
      )}

      {loading ? (
        <p>Loading savings goals...</p>
      ) : goals.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          {goals.map((goal) => (
            <motion.div
              key={goal.goal_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ backgroundColor: 'white', padding: '25px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px' }}>
                <div>
                  <h3 style={{ margin: '0 0 5px 0', fontSize: '20px' }}>{goal.name}</h3>
                  {goal.target_date && <p style={{ margin: 0, fontSize: '13px', color: 'var(--gray-text)' }}>Target: {goal.target_date}</p>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {goal.is_completed ? (
                    <span style={{ padding: '4px 12px', borderRadius: '12px', backgroundColor: '#e8f5e9', color: 'green', fontSize: '12px', fontWeight: 'bold' }}>✓ Completed</span>
                  ) : (
                    <button onClick={() => setContributingGoal(contributingGoal === goal.goal_id ? null : goal.goal_id)} className="btn-secondary" style={{ padding: '6px 14px', fontSize: '13px' }}>
                      Contribute
                    </button>
                  )}
                  <button onClick={() => handleDelete(goal.goal_id, goal.name)} style={{ background: 'none', border: 'none', color: '#f44336', cursor: 'pointer', fontSize: '18px' }} title="Delete goal">✕</button>
                </div>
              </div>

              <div style={{ marginBottom: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', fontSize: '14px' }}>
                  <span style={{ fontWeight: 'bold' }}>${goal.current_amount.toFixed(2)}</span>
                  <span style={{ color: 'var(--gray-text)' }}>${goal.target_amount.toFixed(2)}</span>
                </div>
                <div style={{ height: '10px', backgroundColor: '#f0f0f0', borderRadius: '5px', overflow: 'hidden' }}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(goal.progress_pct, 100)}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    style={{ height: '100%', borderRadius: '5px', backgroundColor: getProgressColor(goal.progress_pct) }}
                  />
                </div>
                <p style={{ textAlign: 'right', fontSize: '12px', color: 'var(--gray-text)', margin: '5px 0 0 0' }}>{goal.progress_pct}%</p>
              </div>

              <AnimatePresence>
                {contributingGoal === goal.goal_id && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    style={{ overflow: 'hidden', marginTop: '10px', borderTop: '1px solid #eee', paddingTop: '15px' }}
                  >
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', fontSize: '14px' }}>Amount to contribute</label>
                        <input type="number" step="0.01" min="0.01" value={contributeAmount} onChange={(e) => setContributeAmount(e.target.value)} placeholder="0.00" style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '14px' }} />
                      </div>
                      <button onClick={() => handleContribute(goal.goal_id)} className="btn-primary" style={{ padding: '10px 20px', whiteSpace: 'nowrap' }}>Submit</button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '60px 20px', backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <p style={{ fontSize: '48px', marginBottom: '20px' }}>🎯</p>
          <h3>No savings goals yet</h3>
          <p style={{ color: 'var(--gray-text)', marginBottom: '20px' }}>Create your first savings goal and start building your future!</p>
          <button onClick={() => setShowForm(true)} className="btn-primary" style={{ padding: '12px 24px' }}>Create a Goal</button>
        </div>
      )}
    </motion.div>
  );
}

export default SavingsGoals;
