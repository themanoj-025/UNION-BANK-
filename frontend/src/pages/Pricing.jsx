import { motion } from 'framer-motion';

function Pricing() {
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
            100% TRANSPARENT <br/> ZERO HIDDEN FEES
          </motion.h1>
          <motion.p 
            style={{ fontSize: '20px', color: 'var(--gray-text)', margin: '0 auto' }}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
            }}
          >
            We don't hide fees in bad exchange rates. You get the real, mid-market rate, and pay a tiny, upfront fee.
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
            <h2 style={{ fontSize: '32px', marginBottom: '10px' }}>Sending Money</h2>
            <p style={{ fontSize: '48px', fontWeight: '900', margin: '20px 0' }}>from 0.43%</p>
            <p className="info-card-text" style={{ marginBottom: '30px' }}>Fixed fee varies by currency and payment method.</p>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              <li style={{ padding: '15px 0', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: '10px' }}><span>✅</span> <span>Real exchange rate</span></li>
              <li style={{ padding: '15px 0', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: '10px' }}><span>✅</span> <span>Guaranteed rate for up to 96h</span></li>
              <li style={{ padding: '15px 0', display: 'flex', gap: '10px' }}><span>✅</span> <span>Transparent tracking</span></li>
            </ul>
          </motion.div>
          
          <motion.div className="info-card" variants={itemVariants} style={{ border: '2px solid var(--primary-green)', position: 'relative' }}>
            <div style={{ position: 'absolute', top: '-15px', right: '40px', backgroundColor: 'var(--primary-green)', color: 'black', padding: '5px 15px', borderRadius: '20px', fontWeight: '600', fontSize: '14px' }}>
              Most Popular
            </div>
            <h2 style={{ fontSize: '32px', marginBottom: '10px' }}>Travel Card</h2>
            <p style={{ fontSize: '48px', fontWeight: '900', margin: '20px 0' }}>Free <span style={{ fontSize: '18px', fontWeight: '400', color: 'var(--gray-text)' }}>to get</span></p>
            <p className="info-card-text" style={{ marginBottom: '30px' }}>A one-time delivery fee may apply depending on your region.</p>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              <li style={{ padding: '15px 0', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: '10px' }}><span>✅</span> <span>Spend in 160+ countries</span></li>
              <li style={{ padding: '15px 0', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: '10px' }}><span>✅</span> <span>Auto-convert at lowest fee</span></li>
              <li style={{ padding: '15px 0', display: 'flex', gap: '10px' }}><span>✅</span> <span>2 free ATM withdrawals / month</span></li>
            </ul>
          </motion.div>
        </div>
      </motion.section>
    </motion.div>
  );
}

export default Pricing;
