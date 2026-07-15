import { motion } from 'framer-motion';
import { useState } from 'react';

function Help() {
  const [search, setSearch] = useState('');

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.2 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -30 },
    show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 50 } }
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
        style={{ justifyContent: 'center', textAlign: 'center', flexDirection: 'column' }}
      >
        <motion.h1 
          style={{ fontSize: 'clamp(48px, 6vw, 64px)', fontWeight: '900', lineHeight: '1.1', marginBottom: '20px' }}
          variants={{
            hidden: { opacity: 0, scale: 0.9, y: 30 },
            visible: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.8, type: "spring", bounce: 0.4 } }
          }}
        >
          HOW CAN WE HELP?
        </motion.h1>
        <motion.p 
          style={{ fontSize: '20px', marginBottom: '40px', maxWidth: '600px', color: 'var(--gray-text)' }}
          variants={{
            hidden: { opacity: 0, y: 20 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
          }}
        >
          Search our knowledge base or get in touch with our friendly support team.
        </motion.p>
        
        <motion.div 
          style={{ width: '100%', maxWidth: '600px', position: 'relative' }}
          variants={{
            hidden: { opacity: 0, y: 30 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.7, type: "spring", bounce: 0.3 } }
          }}
        >
          <input 
            type="text" 
            placeholder="E.g. How do I order a travel card?" 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="help-search"
          />
          <span style={{ position: 'absolute', left: '20px', top: '50%', transform: 'translateY(-50%)', fontSize: '20px' }}>🔍</span>
        </motion.div>
      </motion.section>

      <motion.section 
        className="info-section"
        variants={containerVariants}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '40px', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ flex: '1 1 400px' }}>
            <h2 style={{ fontSize: '36px', fontWeight: '900', marginBottom: '30px' }}>Popular topics</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <motion.a href="#" className="help-link" variants={itemVariants}>
                How do I verify my identity? <span>→</span>
              </motion.a>
              <motion.a href="#" className="help-link" variants={itemVariants}>
                Where is my money? <span>→</span>
              </motion.a>
              <motion.a href="#" className="help-link" variants={itemVariants}>
                What are the fees for sending money to India? <span>→</span>
              </motion.a>
              <motion.a href="#" className="help-link" variants={itemVariants}>
                How do I activate my travel card? <span>→</span>
              </motion.a>
            </div>
          </div>
          <div style={{ flex: '1 1 400px' }}>
            <img src="/images/help_hero.png" alt="Customer support" style={{ width: '100%', borderRadius: '20px', boxShadow: '0 20px 40px rgba(0,0,0,0.1)' }} />
          </div>
        </div>
      </motion.section>
      
      <section style={{ padding: '0 5% 80px 5%', textAlign: 'center' }}>
        <h3 style={{ fontSize: '24px', fontWeight: '800', marginBottom: '20px' }}>Still need help?</h3>
        <p style={{ marginBottom: '30px', color: 'var(--gray-text)' }}>Our 24/7 support team is always ready to assist you.</p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', flexWrap: 'wrap' }}>
          <button className="btn-primary" style={{ backgroundColor: 'var(--primary-green)', color: '#000' }}>Chat with us</button>
          <button className="btn-secondary">Send an email</button>
        </div>
      </section>
    </motion.div>
  );
}

export default Help;
