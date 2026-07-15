import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

function SendingMoney() {
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
            SEND MONEY <br/> BORDERS WITHOUT BARRIERS
          </motion.h1>
          <motion.p 
            style={{ fontSize: '20px', color: 'var(--gray-text)', marginBottom: '40px' }}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
          >
            Whether it's supporting family back home or paying for international tuition, sending money should be fast, transparent, and cheap.
          </motion.p>
          <Link to="/signup">
            <motion.button 
              className="btn-primary"
              variants={{
                hidden: { opacity: 0, y: 20 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
              }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Get started today
            </motion.button>
          </Link>
        </div>
        <motion.div 
          className="subpage-hero-image"
          variants={{
            hidden: { opacity: 0, x: 50 },
            visible: { opacity: 1, x: 0, transition: { duration: 0.8, type: "spring", bounce: 0.2 } }
          }}
        >
          <img src="/images/transfer_woman.png" alt="Send money" />
        </motion.div>
      </motion.section>

      <motion.section 
        className="info-section"
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
      >
        <h2 className="info-section-title">Why send with Union Bank?</h2>
        <div className="info-grid">
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">⚡</div>
            <h3 className="info-card-title">Lightning Fast</h3>
            <p className="info-card-text">Over 50% of our transfers arrive instantly. The rest typically arrive within hours, not days.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">💸</div>
            <h3 className="info-card-title">Real Exchange Rate</h3>
            <p className="info-card-text">We use the mid-market exchange rate. You only pay a small, upfront fee—no hidden markups.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">🌍</div>
            <h3 className="info-card-title">Global Reach</h3>
            <p className="info-card-text">Send money to over 160 countries in 40+ currencies directly from your phone.</p>
          </motion.div>
        </div>
      </motion.section>
    </motion.div>
  );
}

export default SendingMoney;
