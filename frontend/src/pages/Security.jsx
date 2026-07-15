import { motion } from 'framer-motion';

function Security() {
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
        style={{ justifyContent: 'center', textAlign: 'center' }}
      >
        <div style={{ maxWidth: '800px' }}>
          <motion.h1 
            style={{ fontSize: 'clamp(48px, 6vw, 64px)', fontWeight: '900', lineHeight: '1.1', marginBottom: '20px' }}
            variants={{
              hidden: { opacity: 0, scale: 0.9, y: 30 },
              visible: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.8, type: "spring", bounce: 0.4 } }
            }}
          >
            HOW WE KEEP YOUR <br/> MONEY SAFE
          </motion.h1>
          <motion.p 
            style={{ fontSize: '20px', color: 'var(--gray-text)', margin: '0 auto' }}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
          >
            Trust is our top priority. Learn about the multiple layers of security we employ to protect your funds, data, and privacy at every step.
          </motion.p>
        </div>
      </motion.section>

      <motion.section 
        className="info-section"
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
      >
        <div className="info-grid">
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">🛡️</div>
            <h3 className="info-card-title">Bank-grade encryption</h3>
            <p className="info-card-text">We use industry-leading HTTPS encryption to protect your personal data and financial transactions from unauthorized access.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">🏛️</div>
            <h3 className="info-card-title">Strictly regulated</h3>
            <p className="info-card-text">We are authorized by the Financial Conduct Authority (FCA) and regulated by the Reserve Bank of India (RBI), ensuring we meet the highest standards.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">👥</div>
            <h3 className="info-card-title">Dedicated fraud team</h3>
            <p className="info-card-text">Our specialized anti-fraud teams work 24/7 alongside advanced AI algorithms to detect and prevent suspicious activities instantly.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">📱</div>
            <h3 className="info-card-title">Two-factor authentication</h3>
            <p className="info-card-text">Protect your account with 2FA, biometric logins, and instant app notifications for every transaction you make.</p>
          </motion.div>
        </div>
      </motion.section>
    </motion.div>
  );
}

export default Security;
