// components/JournalWindow.jsx
'use client';

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar } from 'recharts';

const EMOTION_COLORS = {
  happy: '#22c55e',
  sad: '#3b82f6', 
  mad: '#ef4444',
  anxious: '#f59e0b',
  calm: '#8b5cf6',
  neutral: '#6b7280'
};

export default function JournalWindow() {
  /* ---------- STATE ---------- */
  const [authToken, setAuthToken] = useState(null);
  const [userId, setUserId] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  
  // Journal-specific state
  const [journalEntry, setJournalEntry] = useState('');
  const [entryTitle, setEntryTitle] = useState('');
  const [emotionalAnalysis, setEmotionalAnalysis] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [topicData, setTopicData] = useState(null);
  const [journalHistory, setJournalHistory] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  
  // Auth state
  const [showLogin, setShowLogin] = useState(true);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [registerMode, setRegisterMode] = useState(false);

  /* ---------- LOGIN/REGISTER ---------- */
  async function handleAuth(e) {
  e.preventDefault();
  const { username, password } = loginForm;

  if (!username || !password) {
    alert('Please fill in all fields');
    return;
  }

  try {
    if (registerMode) {
      // /register expects JSON
      const resp = await fetch('http://127.0.0.1:8000/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const data = await resp.json();

      if (resp.ok) {
        alert('Registration successful! Please login.');
        setRegisterMode(false);
      } else {
        // FastAPI validation errors come as { detail: [...] }
        const msg = Array.isArray(data?.detail)
          ? data.detail.map(d => d.msg).join(', ')
          : (data?.detail || 'Registration failed');
        alert(`Registration error: ${msg}`);
      }
      return;
    }

    // LOGIN (/token) expects x-www-form-urlencoded
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);

    const resp = await fetch('http://127.0.0.1:8000/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString()
    });

    const data = await resp.json();

    if (!resp.ok) {
      const msg = data?.detail || 'Authentication failed';
      alert(`Login error: ${msg}`);
      return;
    }

    setAuthToken(data.access_token);
    setUserId(data.user_id);
    setIsAuthenticated(true);
    setShowLogin(false);
    localStorage.setItem('authToken', data.access_token);
    localStorage.setItem('userId', data.user_id);

    await loadDashboardData(data.access_token);
  } catch (err) {
    console.error('Auth failed:', err);
    alert('Network or server error. Please try again.');
  }
}



  /* ---------- JOURNAL FUNCTIONS ---------- */
  async function submitJournalEntry(e) {
    e.preventDefault();
    if (!journalEntry.trim() || isSubmitting) return;

    setIsSubmitting(true);
    
    try {
      const response = await fetch('http://127.0.0.1:8000/journal/entry', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          content: journalEntry.trim(),
          title: entryTitle.trim() || null
        })
      });

      const data = await response.json();
      
      if (response.ok) {
        setEmotionalAnalysis(data.analysis);
        setJournalEntry('');
        setEntryTitle('');
        
        // Refresh dashboard data
        await loadDashboardData(authToken);
        
        // Show success message
        alert('Journal entry saved and analyzed!');
      } else {
        alert(data.detail || 'Failed to save journal entry');
      }
    } catch (error) {
      console.error('Submit error:', error);
      alert('Failed to save journal entry. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function loadDashboardData(token = authToken) {
    if (!token) return;
    
    try {
      // Load overview data
      const overviewResponse = await fetch('http://127.0.0.1:8000/dashboard/overview', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (overviewResponse.ok) {
        const overviewData = await overviewResponse.json();
        setDashboardData(overviewData);
      }

      // Load topic data
      const topicResponse = await fetch('http://127.0.0.1:8000/dashboard/topics', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (topicResponse.ok) {
        const topicData = await topicResponse.json();
        setTopicData(topicData);
      }
    } catch (error) {
      console.error('Dashboard load error:', error);
    }
  }

  /* ---------- LOAD CACHED DATA ---------- */
  useEffect(() => {
    if (typeof window === "undefined") return;
    
    // Load theme preference
    const theme = localStorage.getItem("journalTheme");
    if (theme === "dark") setDarkMode(true);
    
    // Check for existing auth
    const storedToken = localStorage.getItem("authToken");
    const storedUserId = localStorage.getItem("userId");
    if (storedToken && storedUserId) {
      setAuthToken(storedToken);
      setUserId(storedUserId);
      setIsAuthenticated(true);
      setShowLogin(false);
      loadDashboardData(storedToken);
    }
  }, []);

  /* ---------- PERSIST THEME ---------- */
  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem("journalTheme", darkMode ? "dark" : "light");
  }, [darkMode]);

  /* ---------- THEME TOGGLE ---------- */
  function toggleTheme() {
    setDarkMode(prev => !prev);
  }

  /* ---------- LOGOUT ---------- */
  function logout() {
    setAuthToken(null);
    setUserId(null);
    setIsAuthenticated(false);
    setShowLogin(true);
    setDashboardData(null);
    setTopicData(null);
    setEmotionalAnalysis(null);
    localStorage.removeItem("authToken");
    localStorage.removeItem("userId");
  }

  /* ---------- RENDER CHARTS ---------- */
  function renderEmotionBreakdown() {
    if (!dashboardData?.emotion_breakdown) return null;
    
    const pieData = Object.entries(dashboardData.emotion_breakdown).map(([emotion, count]) => ({
      name: emotion,
      value: count,
      fill: EMOTION_COLORS[emotion] || '#6b7280'
    }));

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ color: darkMode ? '#fff' : '#000' }}>Emotion Breakdown</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {pieData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  function renderDailySummary() {
    if (!dashboardData?.daily_summaries) return null;

    const dailyData = Object.entries(dashboardData.daily_summaries)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-14) // Last 14 days
      .map(([date, summary]) => ({
        date: new Date(date).toLocaleDateString(),
        entries: summary.entries,
        intensity: summary.avg_intensity.toFixed(2)
      }));

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ color: darkMode ? '#fff' : '#000' }}>Daily Activity (Last 14 Days)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={dailyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="entries" fill="#4b9fe1" name="Journal Entries" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  function renderTopicAnalysis() {
    if (!topicData?.topic_emotional_patterns) return null;

    return (
      <div style={{ marginTop: '20px' }}>
        <h3 style={{ color: darkMode ? '#fff' : '#000' }}>Topic Emotional Patterns</h3>
        <div style={{ display: 'grid', gap: '15px', marginTop: '15px' }}>
          {Object.entries(topicData.topic_emotional_patterns).map(([topic, emotions]) => (
            <div key={topic} style={{
              padding: '15px',
              background: darkMode ? '#333' : '#f9f9f9',
              borderRadius: '8px',
              border: `1px solid ${darkMode ? '#555' : '#ddd'}`
            }}>
              <h4 style={{ 
                margin: '0 0 10px 0', 
                color: darkMode ? '#fff' : '#000',
                textTransform: 'capitalize'
              }}>
                {topic}
              </h4>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {Object.entries(emotions).map(([emotion, count]) => (
                  <span key={emotion} style={{
                    padding: '4px 8px',
                    background: EMOTION_COLORS[emotion] || '#6b7280',
                    color: 'white',
                    borderRadius: '12px',
                    fontSize: '0.8rem',
                    fontWeight: 'bold'
                  }}>
                    {emotion}: {count}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  /* ---------- LOGIN FORM ---------- */
  if (showLogin) {
    return (
      <div className={darkMode ? 'dark-mode' : ''} style={{ 
        minHeight: '100vh', 
        background: darkMode ? "#1a1a1a" : "#f9f9f9" 
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          padding: '20px'
        }}>
          <div style={{
            background: darkMode ? "#333" : "#fff",
            padding: '40px',
            borderRadius: '12px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
            width: '100%',
            maxWidth: '400px',
            color: darkMode ? "#fff" : "#000"
          }}>
            <h2 style={{ textAlign: 'center', marginBottom: '30px', color: "#4b9fe1" }}>
              {registerMode ? 'Register for Journal' : 'Login to Journal'}
            </h2>
            
            <form onSubmit={handleAuth}>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                  Username:
                </label>
                <input
                  type="text"
                  value={loginForm.username}
                  onChange={(e) => setLoginForm(prev => ({ ...prev, username: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
                    borderRadius: '6px',
                    background: darkMode ? "#444" : "#fff",
                    color: darkMode ? "#fff" : "#000",
                    fontSize: '16px'
                  }}
                  placeholder="Enter username"
                  required
                />
              </div>
              
              <div style={{ marginBottom: '30px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                  Password:
                </label>
                <input
                  type="password"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm(prev => ({ ...prev, password: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
                    borderRadius: '6px',
                    background: darkMode ? "#444" : "#fff",
                    color: darkMode ? "#fff" : "#000",
                    fontSize: '16px'
                  }}
                  placeholder="Enter password"
                  required
                />
              </div>
              
              <button
                type="submit"
                style={{
                  width: '100%',
                  padding: '12px',
                  background: '#4b9fe1',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  marginBottom: '15px'
                }}
              >
                {registerMode ? 'Register' : 'Login'}
              </button>
            </form>
            
            <div style={{ textAlign: 'center' }}>
              <button
                onClick={() => setRegisterMode(!registerMode)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#4b9fe1',
                  textDecoration: 'underline',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                {registerMode ? 'Already have an account? Login' : "Don't have an account? Register"}
              </button>
            </div>
            
            <div style={{ textAlign: 'center', marginTop: '20px' }}>
              <button 
                onClick={toggleTheme}
                style={{
                  background: 'rgba(75, 159, 225, 0.2)',
                  border: 'none',
                  color: darkMode ? '#fff' : '#4b9fe1',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                {darkMode ? '☀️ Light Mode' : '🌙  Dark Mode'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ---------- MAIN JOURNAL INTERFACE ---------- */
  return (
    <div className={darkMode ? 'dark-mode' : ''} style={{ 
      minHeight: '100vh',
      background: darkMode ? "#1a1a1a" : "#f9f9f9"
    }}>
      {/* Header */}
      <header style={{
        background: darkMode ? "#60a5fa" : "#4b9fe1",
        color: "white",
        padding: "15px 20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        <div>
          <h2 style={{ margin: 0 }}>Emotional Journal</h2>
          <div style={{ fontSize: '0.9rem', opacity: 0.9, marginTop: '4px' }}>
            Track your emotions and reflect on your thoughts
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button 
            onClick={() => setShowDashboard(!showDashboard)}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'white',
              padding: '8px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            📊 {showDashboard ? 'Write' : 'Dashboard'}
          </button>
          <button 
            onClick={toggleTheme}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'white',
              padding: '8px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            {darkMode ? '☀️ Light' : '🌙 Dark'}
          </button>
          <button 
            onClick={logout}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'white',
              padding: '8px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            🚪 Logout
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{
        maxWidth: '900px',
        margin: 'auto',
        padding: '30px 20px'
      }}>
        {!showDashboard ? (
          /* Journal Entry Form */
          <div>
            <form onSubmit={submitJournalEntry}>
              <div style={{ marginBottom: '20px' }}>
                <input
                  type="text"
                  placeholder="Entry title (optional)"
                  value={entryTitle}
                  onChange={(e) => setEntryTitle(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
                    borderRadius: '6px',
                    background: darkMode ? "#333" : "#fff",
                    color: darkMode ? "#fff" : "#000",
                    fontSize: '16px'
                  }}
                />
              </div>
              
              <div style={{ marginBottom: '20px' }}>
                <textarea
                  placeholder="How are you feeling today? Share your thoughts, experiences, and emotions..."
                  value={journalEntry}
                  onChange={(e) => setJournalEntry(e.target.value)}
                  rows={12}
                  style={{
                    width: '100%',
                    padding: '15px',
                    border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
                    borderRadius: '6px',
                    background: darkMode ? "#333" : "#fff",
                    color: darkMode ? "#fff" : "#000",
                    fontSize: '16px',
                    lineHeight: '1.5',
                    resize: 'vertical',
                    minHeight: '200px'
                  }}
                  required
                />
              </div>
              
              <button
                type="submit"
                disabled={isSubmitting || !journalEntry.trim()}
                style={{
                  padding: '12px 30px',
                  background: (isSubmitting || !journalEntry.trim()) ? '#ccc' : '#4b9fe1',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: (isSubmitting || !journalEntry.trim()) ? 'not-allowed' : 'pointer'
                }}
              >
                {isSubmitting ? 'Analyzing...' : 'Submit Entry'}
              </button>
            </form>

            {/* Emotional Analysis Results */}
            {emotionalAnalysis && (
              <div style={{
                marginTop: '30px',
                padding: '20px',
                background: darkMode ? '#333' : '#f9f9f9',
                border: `1px solid ${darkMode ? '#555' : '#ddd'}`,
                borderRadius: '8px'
              }}>
                <h3 style={{ color: darkMode ? '#fff' : '#000', marginTop: 0 }}>
                  Emotional Analysis Results
                </h3>
                <div style={{ 
                  display: 'grid', 
                  gap: '15px',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))'
                }}>
                  <div>
                    <strong style={{ color: darkMode ? '#fff' : '#000' }}>Primary Emotion:</strong>
                    <div style={{
                      padding: '8px 12px',
                      background: EMOTION_COLORS[emotionalAnalysis.primary_emotion] || '#6b7280',
                      color: 'white',
                      borderRadius: '6px',
                      marginTop: '5px',
                      fontWeight: 'bold',
                      textTransform: 'capitalize'
                    }}>
                      {emotionalAnalysis.primary_emotion}
                    </div>
                  </div>
                  <div>
                    <strong style={{ color: darkMode ? '#fff' : '#000' }}>Intensity:</strong>
                    <div style={{ color: darkMode ? '#ccc' : '#666', marginTop: '5px' }}>
                      {emotionalAnalysis.intensity}/1.0
                    </div>
                  </div>
                  <div>
                    <strong style={{ color: darkMode ? '#fff' : '#000' }}>Mood Category:</strong>
                    <div style={{ 
                      color: darkMode ? '#ccc' : '#666', 
                      marginTop: '5px',
                      textTransform: 'capitalize'
                    }}>
                      {emotionalAnalysis.mood_category.replace('_', ' ')}
                    </div>
                  </div>
                </div>
                <div style={{ 
                  marginTop: '15px', 
                  fontSize: '0.9rem', 
                  color: darkMode ? '#ccc' : '#666',
                  fontStyle: 'italic'
                }}>
                  Analysis completed on {new Date(emotionalAnalysis.analysis_timestamp).toLocaleString()}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Dashboard */
          <div>
            <h2 style={{ color: darkMode ? '#fff' : '#000', marginBottom: '20px' }}>
              Your Emotional Journey
            </h2>
            
            {dashboardData ? (
              <div>
                {/* Stats Overview */}
                <div style={{
                  display: 'grid',
                  gap: '20px',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  marginBottom: '30px'
                }}>
                  <div style={{
                    padding: '20px',
                    background: darkMode ? '#333' : '#fff',
                    border: `1px solid ${darkMode ? '#555' : '#ddd'}`,
                    borderRadius: '8px',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#4b9fe1' }}>
                      {dashboardData.total_entries}
                    </div>
                    <div style={{ color: darkMode ? '#ccc' : '#666' }}>Total Entries</div>
                  </div>
                  <div style={{
                    padding: '20px',
                    background: darkMode ? '#333' : '#fff',
                    border: `1px solid ${darkMode ? '#555' : '#ddd'}`,
                    borderRadius: '8px',
                    textAlign: 'center'
                  }}>
                    <div style={{ 
                      fontSize: '1.5rem', 
                      fontWeight: 'bold', 
                      color: EMOTION_COLORS[dashboardData.most_common_emotion] || '#6b7280',
                      textTransform: 'capitalize'
                    }}>
                      {dashboardData.most_common_emotion}
                    </div>
                    <div style={{ color: darkMode ? '#ccc' : '#666' }}>Most Common Emotion</div>
                  </div>
                </div>

                {/* Charts */}
                {renderEmotionBreakdown()}
                {renderDailySummary()}
                {renderTopicAnalysis()}
              </div>
            ) : (
              <div style={{
                textAlign: 'center',
                padding: '40px',
                color: darkMode ? '#ccc' : '#666',
                fontStyle: 'italic'
              }}>
                No journal entries yet. Start writing to see your emotional patterns!
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}