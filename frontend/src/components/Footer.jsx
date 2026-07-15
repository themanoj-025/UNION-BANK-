import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const Facebook = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>
);
const Twitter = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z"/></svg>
);
const Instagram = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="20" x="2" y="2" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" x2="17.51" y1="6.5" y2="6.5"/></svg>
);
const Youtube = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2.5 17a24.12 24.12 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.56 49.56 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.12 24.12 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.55 49.55 0 0 1-16.2 0A2 2 0 0 1 2.5 17"/><path d="m10 15 5-3-5-3z"/></svg>
);
const Linkedin = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect width="4" height="12" x="2" y="9"/><circle cx="4" cy="4" r="2"/></svg>
);

function Footer() {
  return (
    <motion.footer 
      className="footer-section"
      initial={{ y: 100, opacity: 0 }}
      whileInView={{ y: 0, opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, type: "spring", stiffness: 100 }}
    >
      <div className="footer-content">
        <div className="footer-links-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <div className="footer-column">
            <h4>Union Bank</h4>
            <Link to="/personal">Personal</Link>
            <Link to="/business">Business</Link>
            <Link to="/travel-card">Travel card</Link>
            <Link to="/send-money">Send money</Link>
          </div>
          <div className="footer-column">
            <h4>Company</h4>
            <Link to="#">About us</Link>
            <Link to="/security">Security</Link>
            <Link to="/pricing">Pricing</Link>
            <Link to="#">Careers</Link>
          </div>
          <div className="footer-column">
            <h4>Support</h4>
            <Link to="/help">Help centre</Link>
            <Link to="#">Contact us</Link>
            <Link to="#">Service status</Link>
          </div>
        </div>

        <div className="footer-middle">
          <div className="footer-logo" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg width="40" height="40" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12.5 3L2 19h10.5l3.5-6h13.5L12.5 3z" fill="var(--primary-green)"/>
              <path d="M11 21l-3.5 8H20l3.5-8H11z" fill="var(--primary-green)"/>
            </svg>
            <span style={{fontSize: '36px', fontWeight: '900', letterSpacing: '-1px', color: 'var(--dark-green)'}}>Union Bank</span>
          </div>
          <div className="social-icons">
            <a href="#"><Facebook size={24} /></a>
            <a href="#"><Twitter size={24} /></a>
            <a href="#"><Instagram size={24} /></a>
            <a href="#"><Youtube size={24} /></a>
            <a href="#"><Linkedin size={24} /></a>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-legal-links" style={{display: 'flex', flexWrap: 'wrap', gap: '20px', margin: '30px 0 20px 0', borderTop: 'none', paddingTop: 0}}>
            <Link to="#">Legal</Link>
            <Link to="#">Privacy policy</Link>
            <Link to="#">Cookie policy</Link>
            <Link to="#">Accessibility</Link>
            <Link to="#">Complaints</Link>
          </div>

          <div className="footer-disclaimer" style={{fontSize: '12px', color: 'var(--gray-text)', borderTop: '1px solid var(--border-color)', paddingTop: '20px'}}>
            <p>© Union Bank Payments Limited 2026. Union Bank Payments Limited is authorised by the Financial Conduct Authority (FCA) under the Electronic Money Regulations 2011, Firm Reference 900507. Regulated by the Reserve Bank of India (RBI) for inward and outward remittance services.</p>
          </div>
        </div>
      </div>
    </motion.footer>
  );
}

export default Footer;
