import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect } from 'react';

function Header() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const location = useLocation();

  useEffect(() => {
    // Close mobile menu on route change
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const toggleTheme = () => {
    const newTheme = !isDarkMode;
    setIsDarkMode(newTheme);
    if (newTheme) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  };

  return (
    <>
      <motion.header 
        className="header"
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, type: "spring", stiffness: 100 }}
      >
        <div className="header-left">
          <Link to="/" className="logo">
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12.5 3L2 19h10.5l3.5-6h13.5L12.5 3z" fill="var(--black)"/>
              <path d="M11 21l-3.5 8H20l3.5-8H11z" fill="var(--black)"/>
            </svg>
            <span style={{ fontWeight: '900', fontSize: '20px', letterSpacing: '-0.5px' }}>Union Bank</span>
          </Link>
          <nav className="nav-links">
            <Link to="/personal">Personal</Link>
            <Link to="/business">Business</Link>
            <Link to="/platform">Platform</Link>
          </nav>
        </div>

        <div className="header-right">
          <button onClick={toggleTheme} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>
            {isDarkMode ? '☀️' : '🌙'}
          </button>
          <div className="auth-links">
            <Link to="/help">Help</Link>
            <Link to="/login">Log in</Link>
          </div>
          <Link to="/signup" className="btn-primary" style={{textDecoration: 'none', display: 'inline-flex', alignItems: 'center'}}>Sign up</Link>
        </div>

        <button 
          className="hamburger-menu" 
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        >
          {isMobileMenuOpen ? '✕' : '☰'}
        </button>
      </motion.header>

      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              position: 'absolute',
              top: '73px',
              left: 0,
              right: 0,
              background: 'var(--background-color)',
              borderBottom: '1px solid var(--border-color)',
              zIndex: 999,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              padding: '20px',
              gap: '20px',
              boxShadow: '0 10px 20px rgba(0,0,0,0.1)'
            }}
          >
            <Link to="/personal" style={{ fontSize: '18px', fontWeight: '600' }}>Personal</Link>
            <Link to="/business" style={{ fontSize: '18px', fontWeight: '600' }}>Business</Link>
            <Link to="/platform" style={{ fontSize: '18px', fontWeight: '600' }}>Platform</Link>
            <div style={{ height: '1px', background: 'var(--border-color)', width: '100%' }}></div>
            <Link to="/help" style={{ fontSize: '18px', fontWeight: '600' }}>Help</Link>
            <Link to="/login" style={{ fontSize: '18px', fontWeight: '600' }}>Log in</Link>
            <Link to="/signup" className="btn-primary" style={{ textAlign: 'center' }}>Sign up</Link>
            <button 
              onClick={toggleTheme} 
              style={{ background: 'var(--primary-green)', padding: '12px', borderRadius: '12px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            >
              {isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default Header;
