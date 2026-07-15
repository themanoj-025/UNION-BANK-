import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useRef, useState } from 'react';
import CurrencyDropdown from '../components/CurrencyDropdown';

function Home() {
  const navigate = useNavigate();
  const scrollRef = useRef(null);
  const [inputAmount, setInputAmount] = useState(80000);
  const [inputMode, setInputMode] = useState('send');
  const [sendCurrency, setSendCurrency] = useState('INR');
  const [receiveCurrency, setReceiveCurrency] = useState('USD');
  const [widgetTab, setWidgetTab] = useState('send');
  
  const [activeTab, setActiveTab] = useState('send');

  const rates = { INR: 0.012, USD: 1, EUR: 1.08, GBP: 1.25 };
  const getFlag = (cur) => ({ INR: '🇮🇳', USD: '🇺🇸', EUR: '🇪🇺', GBP: '🇬🇧' }[cur]);
  
  const exchangeRate = rates[sendCurrency] / rates[receiveCurrency];
  const feeRate = 0.02158325;
  
  let computedSend = 0;
  let computedReceive = 0;
  let fee = 0;

  if (inputMode === 'send') {
    computedSend = inputAmount;
    fee = computedSend * feeRate;
    const afterFee = computedSend - fee;
    computedReceive = afterFee > 0 ? afterFee * exchangeRate : 0;
  } else {
    computedReceive = inputAmount;
    const afterFee = computedReceive / exchangeRate;
    computedSend = afterFee / (1 - feeRate);
    fee = computedSend * feeRate;
  }

  const scroll = (direction) => {
    if (scrollRef.current) {
      if (direction === 'left') {
        scrollRef.current.scrollBy({ left: -350, behavior: 'smooth' });
      } else {
        scrollRef.current.scrollBy({ left: 350, behavior: 'smooth' });
      }
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="app-container"
    >
      {/* Hero Section */}
      <motion.section 
        className="hero"
        initial="hidden"
        animate="visible"
        variants={{
          visible: {
            transition: { staggerChildren: 0.2, delayChildren: 0.1 }
          }
        }}
      >
        <motion.div 
          style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginBottom: '40px', flexWrap: 'wrap' }}
          variants={{
            hidden: { opacity: 0, y: -20 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } }
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'rgba(0,0,0,0.05)', padding: '8px 20px', borderRadius: '30px', fontSize: '15px', fontWeight: '700' }}>
            <span style={{color: '#00a300', fontSize: '20px'}}>★</span>
            <span>4.8 on App Store</span>
            <span style={{ fontWeight: '500', opacity: 0.7 }}>• 152K reviews</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'rgba(0,0,0,0.05)', padding: '8px 20px', borderRadius: '30px', fontSize: '15px', fontWeight: '700' }}>
            <span style={{color: '#00a300', fontSize: '20px'}}>★</span>
            <span>4.8 on Google Play</span>
            <span style={{ fontWeight: '500', opacity: 0.7 }}>• 1.3M reviews</span>
          </div>
        </motion.div>

        <motion.h1
          variants={{
            hidden: { opacity: 0, scale: 0.9, y: 30 },
            visible: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.8, type: "spring", bounce: 0.4 } }
          }}
        >
          SEND AND SPEND<br/>MONEY WORLDWIDE
        </motion.h1>

        <motion.p
          variants={{
            hidden: { opacity: 0, y: 20 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
          }}
        >
          Save on hidden conversion fees when you use your Union Bank Travel card, or send money abroad.
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
          Sign up in minutes
        </motion.button>

        <motion.div 
          className="hero-image-container"
          variants={{
            hidden: { opacity: 0, y: 100 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.8, delay: 0.4, type: "spring", bounce: 0.2 } }
          }}
        >
          <img src="/images/hero.png" alt="Hand holding Union Bank card and phone" />
        </motion.div>
      </motion.section>

      {/* Features Section */}
      <motion.section 
        className="features-section"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        variants={{
          visible: {
            transition: {
              staggerChildren: 0.2
            }
          }
        }}
        style={{ padding: '80px 5%' }}
      >
        <motion.h2 
          className="section-title"
          variants={{
            hidden: { opacity: 0, y: 30 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
          }}
          style={{ textAlign: 'center', marginBottom: '50px' }}
        >
          TAKE CONTROL<br/>OF YOUR MONEY
        </motion.h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '30px', maxWidth: '1200px', margin: '0 auto' }}>
          
          <motion.div 
            variants={{
              hidden: { opacity: 0, y: 50 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
            }}
            whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0,0,0,0.08)' }}
            style={{ backgroundColor: '#fff', padding: '40px', borderRadius: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', boxShadow: '0 4px 20px rgba(0,0,0,0.04)', transition: 'box-shadow 0.3s' }}
          >
            <div style={{ width: '80px', height: '80px', borderRadius: '50%', backgroundColor: '#e5f8f5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '32px', marginBottom: '24px' }}>⭐</div>
            <h3 style={{ fontSize: '20px', fontWeight: '800', marginBottom: '12px' }}>Award Winning</h3>
            <p style={{ color: 'var(--gray-text)', lineHeight: '1.6', margin: 0 }}>Winner of <a href="#" style={{ color: 'var(--dark-green)', fontWeight: '600' }}>Best Cross-Border Fintech 2025</a></p>
          </motion.div>

          <motion.div 
            variants={{
              hidden: { opacity: 0, y: 50 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
            }}
            whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0,0,0,0.08)' }}
            style={{ backgroundColor: '#fff', padding: '40px', borderRadius: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', boxShadow: '0 4px 20px rgba(0,0,0,0.04)', transition: 'box-shadow 0.3s' }}
          >
            <div style={{ width: '80px', height: '80px', borderRadius: '50%', backgroundColor: '#e5f8f5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '32px', marginBottom: '24px' }}>🏛️</div>
            <h3 style={{ fontSize: '20px', fontWeight: '800', marginBottom: '12px' }}>Fully Regulated</h3>
            <p style={{ color: 'var(--gray-text)', lineHeight: '1.6', margin: 0 }}>Regulated by the <a href="#" style={{ color: 'var(--dark-green)', fontWeight: '600' }}>Reserve Bank of India</a></p>
          </motion.div>

          <motion.div 
            variants={{
              hidden: { opacity: 0, y: 50 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
            }}
            whileHover={{ y: -10, boxShadow: '0 20px 40px rgba(0,0,0,0.08)' }}
            style={{ backgroundColor: '#fff', padding: '40px', borderRadius: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', boxShadow: '0 4px 20px rgba(0,0,0,0.04)', transition: 'box-shadow 0.3s' }}
          >
            <div style={{ width: '80px', height: '80px', borderRadius: '50%', backgroundColor: '#e5f8f5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '32px', marginBottom: '24px' }}>🎧</div>
            <h3 style={{ fontSize: '20px', fontWeight: '800', marginBottom: '12px' }}>Always Here</h3>
            <p style={{ color: 'var(--gray-text)', lineHeight: '1.6', margin: 0 }}>We provide round-the-clock 24/7 customer support.</p>
          </motion.div>

        </div>
      </motion.section>

      {/* Travel Card Split Section */}
      <motion.section 
        className="split-section"
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6 }}
      >
        <div className="split-content">
          <h2>SAVE ON YOUR<br/>TRAVELS ABROAD</h2>
          <p>Make spending around the world simple when you pack your Union Bank Travel card.</p>
          
          <div className="list-item">
            <div className="list-icon">📈</div>
            <div className="list-text">
              <h4>Get the mid-market exchange rate every time</h4>
              <p>Pay at the rate you can usually check on Google, with no hidden fees.</p>
            </div>
          </div>
          <div className="list-item">
            <div className="list-icon">💳</div>
            <div className="list-text">
              <h4>40+ currencies, 160+ countries</h4>
              <p>One card for pounds, pesos, ringgit, dollars and more. Our smart conversions work worldwide.</p>
            </div>
          </div>
          <button className="btn-secondary learn-more-btn" onClick={() => navigate('/travel-card')}>Learn about the Union Bank Travel card</button>
        </div>
        <div className="split-image">
          <img src="/images/travel_card.png" alt="Travel card with money and sunglasses" />
        </div>
      </motion.section>

      {/* Transfer Count Split Section */}
      <motion.section 
        className="split-section reverse"
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6 }}
      >
        <div className="split-content">
          <h2>MAKE YOUR<br/>TRANSFER COUNT</h2>
          <p>Save up to 45% when you send money globally. Lightning-fast. Completely transparent.</p>
          
          <div className="list-item">
            <div className="list-icon">🎓</div>
            <div className="list-text">
              <h4>Pay international education costs</h4>
              <p>Open doors for your loved ones' future</p>
            </div>
          </div>
          <div className="list-item">
            <div className="list-icon">✈️</div>
            <div className="list-text">
              <h4>Make travelling simple</h4>
              <p>Sort vacation and travel expenses</p>
            </div>
          </div>
          <div className="list-item">
            <div className="list-icon">❤️</div>
            <div className="list-text">
              <h4>Support with medical bills</h4>
              <p>Give a helping hand when it's needed</p>
            </div>
          </div>
          <button className="btn-secondary learn-more-btn" onClick={() => navigate('/send-money')}>Learn about sending money</button>
        </div>
        <div className="split-image">
          <img src="/images/transfer_woman.png" alt="Smiling young woman with phone" />
        </div>
      </motion.section>

      {/* 100% Transparent Section */}
      <motion.section 
        className="transparent-section"
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6 }}
      >
        <div className="transparent-content">
          <div className="transparent-text">
            <h2>100% transparent</h2>
            <p>Use our calculator to see how much more you'd get when you send money with Union Bank from India.</p>
            <button className="btn-primary" onClick={() => navigate('/pricing')}>See our pricing</button>
          </div>
          <div>
            <div style={{ display: 'flex', gap: '5px', marginBottom: '15px', backgroundColor: '#f6f7f6', padding: '5px', borderRadius: '30px', width: 'fit-content' }}>
              <button 
                onClick={() => setWidgetTab('send')}
                style={{ padding: '8px 16px', border: 'none', borderRadius: '20px', fontWeight: 'bold', cursor: 'pointer', backgroundColor: widgetTab === 'send' ? 'var(--primary-green)' : 'transparent', color: 'var(--black)' }}
              >Send money</button>
              <button 
                onClick={() => setWidgetTab('hold')}
                style={{ padding: '8px 16px', border: 'none', borderRadius: '20px', fontWeight: 'bold', cursor: 'pointer', backgroundColor: widgetTab === 'hold' ? 'var(--primary-green)' : 'transparent', color: 'var(--black)' }}
              >Hold and convert money</button>
            </div>
            <div className="calculator-widget">
              <div className="calc-row">
                <div className="calc-input">
                  <label>You send exactly</label>
                  <div className="currency-select" style={{padding: '5px 10px', background: '#f6f7f6', borderRadius: '20px', display: 'flex', alignItems: 'center', gap: '5px', width: 'fit-content'}}>
                    <span>{getFlag(sendCurrency)}</span>
                    <CurrencyDropdown 
                      value={sendCurrency} 
                      onChange={setSendCurrency}
                      options={['INR', 'USD', 'EUR', 'GBP']}
                      getFlag={getFlag}
                    />
                  </div>
                </div>
                <input 
                  type="number" 
                  className="amount" 
                  value={inputMode === 'send' ? inputAmount : computedSend.toFixed(2)}
                  onChange={(e) => {
                    setInputMode('send');
                    setInputAmount(Number(e.target.value));
                  }}
                  style={{textAlign: 'right', border: 'none', fontSize: '32px', fontWeight: '900', outline: 'none', background: 'transparent', width: '200px', color: 'var(--black)', padding: 0}}
                />
              </div>
              <div className="calc-details" style={{backgroundColor: '#e5f8f5', padding: '10px', borderRadius: '8px', marginBottom: '20px', fontSize: '12px', fontWeight: '600'}}>
                <span style={{display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--dark-green)'}}>
                  <span>⚡</span> Sending over 80,000 {sendCurrency}? <a href="#" style={{textDecoration: 'underline'}}>We'll discount our fee</a>
                </span>
              </div>
              <div className="calc-details" style={{marginTop: '20px'}}>
                <span style={{color: 'var(--gray-text)'}}>Recipient gets</span>
                <span style={{color: 'var(--black)'}}></span>
              </div>
              <div className="calc-row" style={{borderBottom: 'none'}}>
                <div className="calc-input">
                  <div className="currency-select" style={{padding: '5px 10px', background: '#f6f7f6', borderRadius: '20px', display: 'flex', alignItems: 'center', gap: '5px', width: 'fit-content'}}>
                    <span>{getFlag(receiveCurrency)}</span>
                    <CurrencyDropdown 
                      value={receiveCurrency} 
                      onChange={setReceiveCurrency}
                      options={['INR', 'USD', 'EUR', 'GBP']}
                      getFlag={getFlag}
                    />
                  </div>
                </div>
                <input 
                  type="number" 
                  className="amount" 
                  value={inputMode === 'receive' ? inputAmount : computedReceive.toFixed(2)}
                  onChange={(e) => {
                    setInputMode('receive');
                    setInputAmount(Number(e.target.value));
                  }}
                  style={{textAlign: 'right', border: 'none', fontSize: '32px', fontWeight: '900', outline: 'none', background: 'transparent', width: '200px', color: 'var(--black)', padding: 0}}
                />
              </div>
              <div className="calc-details" style={{borderTop: '1px solid var(--border-color)', paddingTop: '20px', marginTop: '10px'}}>
                <span style={{display: 'flex', alignItems: 'center', gap: '8px'}}><span style={{fontSize: '16px'}}>🕒</span> <div>Arrives<br/><strong style={{color: 'var(--black)'}}>by Monday</strong></div></span>
              </div>
              <div className="calc-details" style={{marginTop: '20px'}}>
                <span style={{display: 'flex', alignItems: 'center', gap: '8px'}}><span style={{fontSize: '16px'}}>🧾</span> <div>Total fees<br/><strong style={{color: 'var(--black)'}}>Included in {sendCurrency} amount</strong></div></span>
                <a href="#" style={{textDecoration: 'underline', color: 'var(--black)', fontWeight: '600', alignSelf: 'flex-end'}}>{fee.toFixed(2)} {sendCurrency} &gt;</a>
              </div>
              <button className="calc-btn" onClick={() => navigate('/signup')}>{widgetTab === 'send' ? 'Send money' : 'Hold money'}</button>
              
              <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '20px', marginTop: '20px'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: 'var(--gray-text)', fontWeight: '600'}}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                  256-bit secure
                </div>
                <div style={{display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: 'var(--gray-text)', fontWeight: '600'}}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                  RBI Regulated
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* Safe at Every Step Section */}
      <motion.section 
        className="split-section"
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6 }}
      >
        <div className="split-content">
          <h2>SAFE AT EVERY STEP</h2>
          <p>100,000 new customers join Union Bank every month in India. Here's how we keep their rupees secure.</p>
          
          <div className="list-item">
            <div className="list-icon">👥</div>
            <div className="list-text">
              <h4>With our <a href="#" style={{textDecoration: 'underline'}}>dedicated team in India</a></h4>
              <p>Your money is protected from your doorstep.</p>
            </div>
          </div>
          <div className="list-item">
            <div className="list-icon">🛡️</div>
            <div className="list-text">
              <h4>Anti-fraud and security teams</h4>
              <p>Our specialist teams partner with cutting-edge tech to beat thieves.</p>
            </div>
          </div>
          <div className="list-item">
            <div className="list-icon">🏛️</div>
            <div className="list-text">
              <h4>Regulated nationwide</h4>
              <p>Regulated by the RBI, with 70 licences worldwide to keep your money moving safely.</p>
            </div>
          </div>
          <button className="btn-secondary learn-more-btn" style={{backgroundColor: 'var(--primary-green)'}} onClick={() => navigate('/security')}>How we keep your money safe</button>
        </div>
        <div className="split-image" style={{backgroundColor: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <img src="/images/padlock.png" alt="Watercolor Padlock" style={{width: '80%', height: '80%', objectFit: 'contain'}} />
        </div>
      </motion.section>

      {/* Excellent Everywhere Section */}
      <motion.section 
        className="reviews-section"
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6 }}
      >
        <div className="reviews-header" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end'}}>
          <div>
            <p style={{fontWeight: '600', marginBottom: '10px'}}>▶️ 4.8 ★ on Google Play 1.3M reviews</p>
            <h2 style={{fontSize: '80px', fontWeight: '900', lineHeight: '0.9', margin: '0 0 20px 0'}}>EXCELLENT<br/>EVERYWHERE</h2>
            <p style={{fontSize: '18px', maxWidth: '400px'}}>See the stories of people across India choosing Union Bank.</p>
          </div>
          <div style={{display: 'flex', gap: '10px'}}>
            <button onClick={() => scroll('left')} style={{width: '50px', height: '50px', borderRadius: '50%', border: 'none', backgroundColor: '#e5e5e5', fontSize: '20px', cursor: 'pointer'}}>←</button>
            <button onClick={() => scroll('right')} style={{width: '50px', height: '50px', borderRadius: '50%', border: 'none', backgroundColor: 'var(--primary-green)', fontSize: '20px', cursor: 'pointer'}}>→</button>
          </div>
        </div>
        <div className="reviews-scroll" ref={scrollRef}>
          <div className="review-card">
            <div className="feature-icon" style={{backgroundColor: 'white'}}>▶️</div>
            <p className="review-quote">"Union Bank is awesome — truly fast, reliable, and refreshingly transparent. There are no hidden fees, no extra charges."</p>
            <div style={{display: 'flex', alignItems: 'center', gap: '15px', marginTop: 'auto'}}>
              <img src="/images/avatar_rahul.png" alt="Rahul" style={{width: '50px', height: '50px', borderRadius: '50%', objectFit: 'cover'}} />
              <p className="review-author" style={{margin: 0}}>Rahul Sharma, Mumbai</p>
            </div>
          </div>
          <div className="review-card dark">
            <div className="feature-icon" style={{backgroundColor: 'white', color: 'black', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', width: '40px', height: '40px'}}>▶️</div>
            <p className="review-quote">"Union Bank is a popular money transfer app known for being *cheap*, *easy*, and *fast* for sending money abroad to India."</p>
            <div style={{display: 'flex', alignItems: 'center', gap: '15px', marginTop: 'auto'}}>
              <img src="/images/avatar_priyanka.png" alt="Priyanka" style={{width: '50px', height: '50px', borderRadius: '50%', objectFit: 'cover'}} />
              <p className="review-author" style={{margin: 0}}>Priyanka Dey, Bengaluru</p>
            </div>
          </div>
          <div className="review-card" style={{backgroundColor: '#e5f6df'}}>
            <div className="feature-icon" style={{backgroundColor: 'white'}}>▶️</div>
            <p className="review-quote">"The best way to send rupees to my family. Extremely fast and the exchange rates are unbeatable. I've used it for years."</p>
            <div style={{display: 'flex', alignItems: 'center', gap: '15px', marginTop: 'auto'}}>
              <img src="/images/avatar_amit.png" alt="Amit" style={{width: '50px', height: '50px', borderRadius: '50%', objectFit: 'cover'}} />
              <p className="review-author" style={{margin: 0}}>Amit Patel, Gujarat</p>
            </div>
          </div>
          <div className="review-card" style={{backgroundColor: '#f6f7f6'}}>
            <div className="feature-icon" style={{backgroundColor: 'white'}}>▶️</div>
            <p className="review-quote">"I was skeptical at first, but transferring funds for my brother's education in the US was incredibly smooth and secure."</p>
            <div style={{display: 'flex', alignItems: 'center', gap: '15px', marginTop: 'auto'}}>
              <img src="/images/avatar_neha.png" alt="Neha" style={{width: '50px', height: '50px', borderRadius: '50%', objectFit: 'cover'}} />
              <p className="review-author" style={{margin: 0}}>Neha Gupta, Delhi</p>
            </div>
          </div>
          <div className="review-card dark">
            <div className="feature-icon" style={{backgroundColor: 'white', color: 'black', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', width: '40px', height: '40px'}}>▶️</div>
            <p className="review-quote">"As a freelancer working with global clients, Union Bank has saved me thousands in unfair bank fees."</p>
            <p className="review-author">Vikram Singh, Pune</p>
          </div>
          <div className="review-card" style={{backgroundColor: '#e5f6df'}}>
            <div className="feature-icon" style={{backgroundColor: 'white'}}>▶️</div>
            <p className="review-quote">"Customer support was very helpful when I made a mistake with account details. Very trustworthy service."</p>
            <p className="review-author">Anjali Desai, Ahmedabad</p>
          </div>
          <div className="review-card">
            <div className="feature-icon" style={{backgroundColor: 'white'}}>▶️</div>
            <p className="review-quote">"Quick, painless setup and money arrives almost instantly in most cases. Fantastic app experience."</p>
            <p className="review-author">Ravi Kumar, Hyderabad</p>
          </div>
          <div className="review-card" style={{backgroundColor: '#f6f7f6'}}>
            <div className="feature-icon" style={{backgroundColor: 'white'}}>▶️</div>
            <p className="review-quote">"I use the Union Bank card on all my international trips. The auto-conversion is magical and hassle-free."</p>
            <p className="review-author">Sneha Reddy, Chennai</p>
          </div>
        </div>
      </motion.section>

      {/* Countries Section */}
      <motion.section 
        className="countries-section"
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6 }}
      >
        <h2>Union Bank works nearly everywhere</h2>
        <div className="country-tabs">
          <button className={activeTab === 'send' ? "tab-active" : "tab-inactive"} onClick={() => setActiveTab('send')}>Send money</button>
          <button className={activeTab === 'hold' ? "tab-active" : "tab-inactive"} onClick={() => setActiveTab('hold')}>Hold and convert money</button>
        </div>
        {activeTab === 'send' ? (
          <div className="countries-grid">
            <div className="country-item"><span className="country-flag fi fi-gh fis"></span><a href="#">Send money to Ghana</a></div>
            <div className="country-item"><span className="country-flag fi fi-gi fis"></span><a href="#">Send money to Gibraltar</a></div>
            <div className="country-item"><span className="country-flag fi fi-gr fis"></span><a href="#">Send money to Greece</a></div>
            <div className="country-item"><span className="country-flag fi fi-gp fis"></span><a href="#">Send money to Guadeloupe</a></div>
            <div className="country-item"><span className="country-flag fi fi-gg fis"></span><a href="#">Send money to Guernsey</a></div>
            
            <div className="country-item"><span className="country-flag fi fi-hk fis"></span><a href="#">Send money to Hong Kong</a></div>
            <div className="country-item"><span className="country-flag fi fi-hu fis"></span><a href="#">Send money to Hungary</a></div>
            <div className="country-item"><span className="country-flag fi fi-in fis"></span><a href="#">Send money to India</a></div>
            <div className="country-item"><span className="country-flag fi fi-id fis"></span><a href="#">Send money to Indonesia</a></div>
            <div className="country-item"><span className="country-flag fi fi-ie fis"></span><a href="#">Send money to Ireland</a></div>
            
            <div className="country-item"><span className="country-flag fi fi-im fis"></span><a href="#">Send money to Isle of Man</a></div>
            <div className="country-item"><span className="country-flag fi fi-il fis"></span><a href="#">Send money to Israel</a></div>
            <div className="country-item"><span className="country-flag fi fi-it fis"></span><a href="#">Send money to Italy</a></div>
            <div className="country-item"><span className="country-flag fi fi-jp fis"></span><a href="#">Send money to Japan</a></div>
            <div className="country-item"><span className="country-flag fi fi-je fis"></span><a href="#">Send money to Jersey</a></div>
  
            <div className="country-item"><span className="country-flag fi fi-ke fis"></span><a href="#">Send money to Kenya</a></div>
            <div className="country-item"><span className="country-flag fi fi-lv fis"></span><a href="#">Send money to Latvia</a></div>
            <div className="country-item"><span className="country-flag fi fi-li fis"></span><a href="#">Send money to Liechtenstein</a></div>
            <div className="country-item"><span className="country-flag fi fi-lt fis"></span><a href="#">Send money to Lithuania</a></div>
            <div className="country-item"><span className="country-flag fi fi-lu fis"></span><a href="#">Send money to Luxembourg</a></div>
            
            <div className="country-item"><span className="country-flag fi fi-my fis"></span><a href="#">Send money to Malaysia</a></div>
            <div className="country-item"><span className="country-flag fi fi-mt fis"></span><a href="#">Send money to Malta</a></div>
            <div className="country-item"><span className="country-flag fi fi-mh fis"></span><a href="#">Send money to Marshall Islands</a></div>
            <div className="country-item"><span className="country-flag fi fi-mq fis"></span><a href="#">Send money to Martinique</a></div>
            <div className="country-item"><span className="country-flag fi fi-yt fis"></span><a href="#">Send money to Mayotte</a></div>
  
            <div className="country-item"><span className="country-flag fi fi-mx fis"></span><a href="#">Send money to Mexico</a></div>
            <div className="country-item"><span className="country-flag fi fi-fm fis"></span><a href="#">Send money to Micronesia</a></div>
            <div className="country-item"><span className="country-flag fi fi-mc fis"></span><a href="#">Send money to Monaco</a></div>
            <div className="country-item"><span className="country-flag fi fi-me fis"></span><a href="#">Send money to Montenegro</a></div>
            <div className="country-item"><span className="country-flag fi fi-ma fis"></span><a href="#">Send money to Morocco</a></div>
            
            <div className="country-item"><span className="country-flag fi fi-bl fis"></span><a href="#">Send money to Saint Barthélemy</a></div>
            <div className="country-item"><span className="country-flag fi fi-mf fis"></span><a href="#">Send money to Saint Martin</a></div>
            <div className="country-item"><span className="country-flag fi fi-pm fis"></span><a href="#">Send money to Saint Pierre</a></div>
            <div className="country-item"><span className="country-flag fi fi-sm fis"></span><a href="#">Send money to San Marino</a></div>
            <div className="country-item"><span className="country-flag fi fi-sg fis"></span><a href="#">Send money to Singapore</a></div>
          </div>
        ) : (
          <div className="countries-grid">
            <div className="country-item"><span className="country-flag fi fi-us fis"></span><a href="#">Hold US Dollars</a></div>
            <div className="country-item"><span className="country-flag fi fi-gb fis"></span><a href="#">Hold British Pounds</a></div>
            <div className="country-item"><span className="country-flag fi fi-eu fis"></span><a href="#">Hold Euros</a></div>
            <div className="country-item"><span className="country-flag fi fi-ca fis"></span><a href="#">Hold Canadian Dollars</a></div>
            <div className="country-item"><span className="country-flag fi fi-au fis"></span><a href="#">Hold Australian Dollars</a></div>
            
            <div className="country-item"><span className="country-flag fi fi-jp fis"></span><a href="#">Hold Japanese Yen</a></div>
            <div className="country-item"><span className="country-flag fi fi-sg fis"></span><a href="#">Hold Singapore Dollars</a></div>
            <div className="country-item"><span className="country-flag fi fi-ch fis"></span><a href="#">Hold Swiss Francs</a></div>
            <div className="country-item"><span className="country-flag fi fi-nz fis"></span><a href="#">Hold New Zealand Dollars</a></div>
            <div className="country-item"><span className="country-flag fi fi-in fis"></span><a href="#">Hold Indian Rupees</a></div>
          </div>
        )}
      </motion.section>

      {/* Take Everywhere Section */}
      <motion.section 
        className="split-section reverse" style={{alignItems: 'center'}}
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6 }}
      >
        <div className="split-content">
          <h2 style={{fontSize: '72px', marginBottom: '30px', fontWeight: '900', lineHeight: '0.9'}}>TAKE UNION BLANK<br/>EVERYWHERE<br/>YOU GO</h2>
          <div className="qr-box">
            <div className="qr-code" style={{backgroundColor: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4px'}}>
               <img src="https://api.qrserver.com/v1/create-qr-code/?size=60x60&data=https://unionbankofindia.co.in" alt="QR Code" style={{width: '100%', height: '100%'}}/>
            </div>
            <p style={{margin: '0', fontSize: '12px'}}>Scan to<br/>get the<br/>Union Bank app</p>
          </div>
        </div>
        <div className="split-image" style={{backgroundColor: '#fff', borderRadius: '40px'}}>
          <img src="/images/app_download.png" alt="Hand holding phone with Union Bank App" style={{objectFit: 'contain'}} />
        </div>
      </motion.section>
    </motion.div>
  );
}

export default Home;
