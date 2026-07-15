import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { AuthProvider, useAuth } from './context/AuthContext';
import PrivateRoute from './components/Auth/PrivateRoute';
import './App.css';

// Components
import { Link as RouterLink } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import ErrorBoundary from './components/ErrorBoundary';

// Pages
import Home from './pages/Home';
import Personal from './pages/Personal';
import Business from './pages/Business';
import Platform from './pages/Platform';
import Help from './pages/Help';
import Login from './pages/Auth/Login';
import SignUp from './pages/Auth/SignUp';
import Security from './pages/Security';
import SendingMoney from './pages/SendingMoney';
import TravelCard from './pages/TravelCard';
import Pricing from './pages/Pricing';

// Authenticated Pages
import Dashboard from './pages/Dashboard';
import Deposit from './pages/Transactions/Deposit';
import Withdraw from './pages/Transactions/Withdraw';
import Transfer from './pages/Transactions/Transfer';
import Statement from './pages/Statement';
import Profile from './pages/Profile';
import SavingsGoals from './pages/SavingsGoals';
import Loans from './pages/Loans';

// Admin Pages
import AdminLogin from './pages/Admin/AdminLogin';
import AdminDashboard from './pages/Admin/AdminDashboard';
import AdminAccounts from './pages/Admin/AdminAccounts';
import AdminTransactions from './pages/Admin/AdminTransactions';
import AdminLoans from './pages/Admin/AdminLoans';

// Import flag-icons CSS
import 'flag-icons/css/flag-icons.min.css';

function AppLayout() {
  const location = useLocation();
  const { user } = useAuth();
  
  // Hide footer for auth pages or when logged in (to give a more app-like feel for dashboard, etc.)
  const hideFooter = [
    '/login', '/signup', '/admin', '/personal', '/business', '/platform', '/help'
  ].includes(location.pathname) || !!user;
  
  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="*" element={
              <div style={{ textAlign: 'center', padding: '80px 20px' }}>
                <span style={{ fontSize: '64px', display: 'block', marginBottom: '20px' }}>🔍</span>
                <h2>Page Not Found</h2>
                <p style={{ color: 'var(--gray-text)', marginBottom: '20px' }}>The page you're looking for doesn't exist.</p>
                <RouterLink to="/" className="btn-primary" style={{ textDecoration: 'none', padding: '12px 24px', display: 'inline-block' }}>Go Home</RouterLink>
              </div>
            } />
            {/* Public Routes */}
            <Route path="/" element={<Home />} />
            <Route path="/personal" element={<Personal />} />
            <Route path="/business" element={<Business />} />
            <Route path="/platform" element={<Platform />} />
            <Route path="/help" element={<Help />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<SignUp />} />
            <Route path="/security" element={<Security />} />
            <Route path="/send-money" element={<SendingMoney />} />
            <Route path="/travel-card" element={<TravelCard />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/admin" element={<AdminLogin />} />

            {/* Customer Protected Routes */}
            <Route path="/dashboard" element={<PrivateRoute roleRequired="customer"><Dashboard /></PrivateRoute>} />
            <Route path="/deposit" element={<PrivateRoute roleRequired="customer"><Deposit /></PrivateRoute>} />
            <Route path="/withdraw" element={<PrivateRoute roleRequired="customer"><Withdraw /></PrivateRoute>} />
            <Route path="/transfer" element={<PrivateRoute roleRequired="customer"><Transfer /></PrivateRoute>} />
            <Route path="/statement" element={<PrivateRoute roleRequired="customer"><Statement /></PrivateRoute>} />
            <Route path="/profile" element={<PrivateRoute roleRequired="customer"><Profile /></PrivateRoute>} />

            {/* Customer Protected Routes */}
            <Route path="/savings" element={<PrivateRoute roleRequired="customer"><SavingsGoals /></PrivateRoute>} />
            <Route path="/loans" element={<PrivateRoute roleRequired="customer"><Loans /></PrivateRoute>} />

            {/* Admin Protected Routes */}
            <Route path="/admin/dashboard" element={<PrivateRoute roleRequired="admin"><AdminDashboard /></PrivateRoute>} />
            <Route path="/admin/accounts" element={<PrivateRoute roleRequired="admin"><AdminAccounts /></PrivateRoute>} />
            <Route path="/admin/transactions" element={<PrivateRoute roleRequired="admin"><AdminTransactions /></PrivateRoute>} />
            <Route path="/admin/loans" element={<PrivateRoute roleRequired="admin"><AdminLoans /></PrivateRoute>} />
          </Routes>
        </AnimatePresence>
      </main>
      {!hideFooter && <Footer />}
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <ErrorBoundary>
          <AppLayout />
        </ErrorBoundary>
      </AuthProvider>
    </Router>
  );
}

export default App;
