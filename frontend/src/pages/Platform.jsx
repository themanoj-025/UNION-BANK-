import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

function Platform() {
  const navigate = useNavigate();

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.2 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 50 } }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="page-container"
    >
      <motion.section 
        className="subpage-hero"
        style={{ backgroundColor: '#111111', color: '#ffffff' }}
        initial="hidden"
        animate="visible"
        variants={{
          visible: {
            transition: { staggerChildren: 0.2, delayChildren: 0.1 }
          }
        }}
      >
        <div className="subpage-hero-text">
          <motion.h1 
            style={{ fontSize: 'clamp(48px, 6vw, 64px)', fontWeight: '900', lineHeight: '1.1', marginBottom: '20px', color: '#ffffff' }}
            variants={{
              hidden: { opacity: 0, y: 30 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.8, type: "spring", bounce: 0.4 } }
            }}
          >
            POWERING GLOBAL<br/><span style={{color: 'var(--primary-green)'}}>FINANCE</span>
          </motion.h1>
          <motion.p 
            style={{ fontSize: '20px', marginBottom: '30px', maxWidth: '500px', color: '#cccccc' }}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
          >
            Integrate Union Bank's powerful API into your own platform. Offer your customers world-class international payments and borderless accounts.
          </motion.p>
          <motion.button 
            className="btn-primary" 
            style={{ backgroundColor: 'var(--primary-green)', color: '#000' }} 
            onClick={() => navigate('/signup')}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Read the API Docs
          </motion.button>
        </div>
        <motion.div 
          className="subpage-hero-image"
          variants={{
            hidden: { opacity: 0, x: 50 },
            visible: { opacity: 1, x: 0, transition: { duration: 0.8, type: "spring", bounce: 0.2 } }
          }}
        >
          <img src="/images/platform_hero.png" alt="Platform API" />
        </motion.div>
      </motion.section>

      <motion.section 
        className="info-section"
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
      >
        <h2 className="info-section-title">BUILD WITH UNION BANK</h2>
        <div className="info-grid">
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">🔌</div>
            <h3 className="info-card-title">Seamless Integration</h3>
            <p className="info-card-text">Our RESTful API is designed for developers, by developers. Go live in days, not months, with comprehensive SDKs and sandboxes.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">🏦</div>
            <h3 className="info-card-title">Bank-grade Infrastructure</h3>
            <p className="info-card-text">Leverage our global network of licenses, compliance engines, and local bank integrations without building it yourself.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">📈</div>
            <h3 className="info-card-title">Infinite Scalability</h3>
            <p className="info-card-text">Whether you're processing 100 or 100,000 transactions a minute, our platform scales instantly to meet your enterprise demands.</p>
          </motion.div>
        </div>
      </motion.section>
    </motion.div>
  );
}

export default Platform;
