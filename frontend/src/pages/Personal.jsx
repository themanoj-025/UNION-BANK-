import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

function Personal() {
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
        className="subpage-hero bg-gray"
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
            style={{ fontSize: 'clamp(48px, 6vw, 64px)', fontWeight: '900', lineHeight: '1.1', marginBottom: '20px' }}
            variants={{
              hidden: { opacity: 0, y: 30 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.8, type: "spring", bounce: 0.4 } }
            }}
          >
            YOUR MONEY,<br/>WITHOUT BORDERS
          </motion.h1>
          <motion.p 
            style={{ fontSize: '20px', marginBottom: '30px', maxWidth: '500px', color: 'var(--gray-text)' }}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
          >
            Join millions of people who save when they send, spend, and manage their personal finances globally with Union Bank.
          </motion.p>
          <motion.button 
            className="btn-primary" 
            onClick={() => navigate('/signup')}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Open an account in minutes
          </motion.button>
        </div>
        <motion.div 
          className="subpage-hero-image"
          variants={{
            hidden: { opacity: 0, x: 50 },
            visible: { opacity: 1, x: 0, transition: { duration: 0.8, type: "spring", bounce: 0.2 } }
          }}
        >
          <img src="/images/personal_hero.png" alt="Personal banking" />
        </motion.div>
      </motion.section>

      <motion.section 
        className="info-section"
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
      >
        <h2 className="info-section-title">EVERYTHING YOU NEED<br/>IN ONE APP</h2>
        <div className="info-grid">
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">💸</div>
            <h3 className="info-card-title">Send money globally</h3>
            <p className="info-card-text">Send money to 160+ countries at the mid-market rate. No hidden fees, just fast, secure transfers.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">💳</div>
            <h3 className="info-card-title">Union Bank Travel Card</h3>
            <p className="info-card-text">Spend seamlessly abroad. We auto-convert your balance at the best rate with zero transaction fees.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">🛡️</div>
            <h3 className="info-card-title">Bank-level security</h3>
            <p className="info-card-text">Your money is safeguarded with leading banks and regulated globally, including by the RBI.</p>
          </motion.div>
        </div>
      </motion.section>
    </motion.div>
  );
}

export default Personal;
