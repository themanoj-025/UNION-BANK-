import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

function TravelCard() {
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
            THE ONLY CARD <br/> YOU NEED TO PACK
          </motion.h1>
          <motion.p 
            style={{ fontSize: '20px', color: 'var(--gray-text)', maxWidth: '800px', marginBottom: '40px' }}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
          >
            Spend abroad with the real exchange rate. No sneaky transaction fees. Always know exactly what you're paying in your local currency.
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
              Order your card now
            </motion.button>
          </Link>
        </div>
        <motion.div 
          className="subpage-hero-image" style={{ display: 'flex', justifyContent: 'center' }}
          variants={{
            hidden: { opacity: 0, x: 50 },
            visible: { opacity: 1, x: 0, transition: { duration: 0.8, type: "spring", bounce: 0.2 } }
          }}
        >
          <img src="/images/travel_card.png" alt="Travel Card" style={{ maxWidth: '80%' }} />
        </motion.div>
      </motion.section>

      <motion.section 
        className="info-section"
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
      >
        <h2 className="info-section-title">Spend like a local</h2>
        <div className="info-grid">
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">🏧</div>
            <h3 className="info-card-title">Free ATM withdrawals</h3>
            <p className="info-card-text">Up to 2 free withdrawals per month (under £200 equivalent).</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">📱</div>
            <h3 className="info-card-title">Apple & Google Pay</h3>
            <p className="info-card-text">Add your card to your digital wallet immediately and start spending before the physical card arrives.</p>
          </motion.div>
          <motion.div className="info-card" variants={itemVariants}>
            <div className="info-card-icon">🛡️</div>
            <h3 className="info-card-title">Instant Freeze</h3>
            <p className="info-card-text">Lost your card? Freeze and unfreeze it instantly from the app with a single tap.</p>
          </motion.div>
        </div>
      </motion.section>
    </motion.div>
  );
}

export default TravelCard;
