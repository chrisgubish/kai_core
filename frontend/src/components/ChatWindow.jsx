'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

// Updated AVATAR_MAP with correct paths
const AVATAR_MAP = {
  samoyed: "/samoyed_avatar.png",
  penguin: "/penguin_avatar.png",
  capybara: "/capybara_avatar.png",
  axolotl: "/axolotl_avatar.png",  // Fixed typo: was "axolotle"
  bat: "/bat_avatar.png"
};

export default function ChatWindow() {
  /* ---------- STATE ---------- */
  const [darkMode, setDarkMode] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [persona, setPersona] = useState('kai');
  const [sessionId, setSessionId] = useState('default');
  const [memory, setMemory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [selectedAvatar, setSelectedAvatar] = useState('penguin'); // MOVED INSIDE COMPONENT

  /* ---------- LOAD CACHED DATA ---------- */
  useEffect(() => {
    if (typeof window === "undefined") return;
    
    // Load theme preference
    const theme = localStorage.getItem("kaiTheme");
    if (theme === "dark") setDarkMode(true);
    
    // Load last used persona and session
    const lastPersona = localStorage.getItem("lastPersona");
    if (lastPersona) setPersona(lastPersona);
    
    const lastSession = localStorage.getItem("lastSessionId");
    if (lastSession) setSessionId(lastSession);
    
    // Load selected avatar
    const savedAvatar = localStorage.getItem("selectedAvatar");
    if (savedAvatar && AVATAR_MAP[savedAvatar]) {
      setSelectedAvatar(savedAvatar);
    }
    
    // Load cached messages ONLY if backend memory exists
    loadMemory().then(() => {
      const cache = JSON.parse(localStorage.getItem("kaiChatCache") || "[]");
      if (cache.length > 0 && memory.length > 0) {
        setMessages(cache);
      }
    });
  }, []);

  /* ---------- PERSIST CACHE ---------- */
  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem("kaiChatCache", JSON.stringify(messages.slice(-200)));
  }, [messages]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem("lastPersona", persona);
  }, [persona]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem("lastSessionId", sessionId);
  }, [sessionId]);

  // Save selected avatar to localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem("selectedAvatar", selectedAvatar);
  }, [selectedAvatar]);

  /* ---------- LOAD MEMORY ---------- */
  useEffect(() => {
    loadMemory();
  }, [sessionId]);

  async function loadMemory() {
    try {
      setConnectionStatus('connecting');
      const res = await fetch(
        `http://127.0.0.1:8000/memory?session=${sessionId}`
      );
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      setMemory(data);
      setConnectionStatus('connected');
    } catch (err) { 
      console.error('loadMemory error:', err);
      setConnectionStatus('error');
    }
  }

  /* ---------- THEME TOGGLE ---------- */
  function toggleTheme() {
    setDarkMode(prev => {
      const newMode = !prev;
      if (typeof window !== "undefined") {
        localStorage.setItem("kaiTheme", newMode ? "dark" : "light");
      }
      return newMode;
    });
  }

  /* ---------- SEND MESSAGE ---------- */
  async function sendMessage(e) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    
    const userMsg = { speaker: 'user', message: userMessage };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setConnectionStatus('sending');

    try {
      const res = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: userMessage,
          session_id: sessionId,
          persona: persona
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      }

      const aiMsg = {
        speaker: persona,
        message: data.response,
        emotions: data.emotions || {}
      };
      setMessages(prev => [...prev, aiMsg]);
      setConnectionStatus('connected');

      setTimeout(() => loadMemory(), 500);

    } catch (err) {
      console.error('sendMessage error:', err);
      setConnectionStatus('error');
      
      const errorMsg = {
        speaker: 'system',
        message: `Error: ${err.message}. Check if backend is running on port 8000.`,
        isError: true
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }

  /* ---------- CLEAR MEMORY ---------- */
  async function clearMemory() {
    try {
      const res = await fetch(`http://127.0.0.1:8000/memory/reset?session=${sessionId}`);
      if (!res.ok) throw new Error(res.statusText);
      
      setMessages([]);
      setMemory([]);
      
      if (typeof window !== "undefined") {
        localStorage.removeItem("kaiChatCache");
        localStorage.removeItem("lastPersona");
        localStorage.removeItem("lastSessionId");
      }
      
      await loadMemory();
      
    } catch (err) {
      console.error('clearMemory error:', err);
      setMessages([]);
      setMemory([]);
      if (typeof window !== "undefined") {
        localStorage.removeItem("kaiChatCache");
      }
    }
  }

  /* ---------- CONNECTION INDICATOR ---------- */
  function getConnectionColor() {
    switch(connectionStatus) {
      case 'connected': return '#22c55e';
      case 'connecting': case 'sending': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  }

  function getConnectionText() {
    switch(connectionStatus) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      case 'sending': return 'Sending...';
      case 'error': return 'Connection Error';
      default: return 'Disconnected';
    }
  }

  /* ---------- RENDER ---------- */
  return (
    <div className={darkMode ? 'dark-mode' : ''} style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header
        style={{
          background: darkMode ? "#60a5fa" : "#4b9fe1",
          color: "white",
          padding: "10px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h2>Chat with {persona === 'kai' ? 'Kai' : 'Eden'}</h2>
          <div style={{ 
            fontSize: '0.8rem', 
            opacity: 0.9,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: getConnectionColor()
            }}></div>
            {getConnectionText()} • Session: {sessionId}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button 
            onClick={clearMemory}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'white',
              padding: '5px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            🗑️ Clear
          </button>
          <button 
            onClick={() => {
              const newSessionId = `session_${Date.now()}`;
              setSessionId(newSessionId);
              setMessages([]);
              setMemory([]);
              if (typeof window !== "undefined") {
                localStorage.removeItem("kaiChatCache");
                localStorage.setItem("lastSessionId", newSessionId);
              }
            }}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'white',
              padding: '5px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            ✨ New Chat
          </button>
          <button 
            onClick={toggleTheme}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: 'white',
              padding: '5px 10px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            {darkMode ? '☀️ Light' : '🌙 Dark'}
          </button>
        </div>
      </header>

      {/* Chat Messages */}
      <main
        style={{
          flex: 1,
          padding: 15,
          maxWidth: 800,
          margin: "auto",
          overflowY: "auto",
          minHeight: "calc(100vh - 200px)",
          background: darkMode ? "#1a1a1a" : "#f9f9f9"
        }}
      >
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center',
            margin: '40px 0',
            color: darkMode ? '#ccc' : '#666',
            fontStyle: 'italic'
          }}>
            Start chatting with {persona === 'kai' ? 'Kai' : 'Eden'}! 
            {persona === 'kai' ? ' He\'s your supportive friend who actually listens.' : ' She\'s your caring guide who\'s always there for you.'}
          </div>
        )}

        {messages.map((msg, idx) => {
          const personaKey = msg.speaker?.toLowerCase();
          const isKai = personaKey === 'kai';
          const isEden = personaKey === 'eden';
          const isUser = personaKey === 'user';
          const isSystem = personaKey === 'system';
          const avatarSrc = (isKai || isEden) ? AVATAR_MAP[selectedAvatar] : null;

          // System/Error messages
          if (isSystem || msg.isError) {
            return (
              <div
                key={idx}
                style={{
                  textAlign: 'center',
                  margin: '20px 0',
                  padding: '12px',
                  background: msg.isError ? '#ffebee' : '#e3f2fd',
                  color: msg.isError ? '#c62828' : '#1565c0',
                  borderRadius: '8px',
                  fontSize: '0.9rem',
                  border: `1px solid ${msg.isError ? '#ffcdd2' : '#bbdefb'}`
                }}
              >
                {msg.message}
              </div>
            );
          }

          // AI messages with large centered avatar
          if ((isKai || isEden) && avatarSrc) {
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  margin: "36px 0",
                }}
              >
                <img
                  src={avatarSrc}
                  alt={msg.speaker}
                  onError={(e) => {
                    console.log(`Failed to load avatar: ${avatarSrc}`);
                    e.target.src = "/penguin_avatar.png"; // Fallback to penguin
                  }}
                  style={{
                    width: 180,
                    height: 180,
                    borderRadius: "50%",
                    boxShadow: "0 4px 32px rgba(0,0,0,0.08)",
                    objectFit: "contain",
                    zIndex: 1,
                    marginBottom: -32,
                  }}
                />
                <div
                  style={{
                    background: darkMode ? "#333" : "#fff",
                    color: darkMode ? "#fff" : "#222",
                    minWidth: 200,
                    maxWidth: 420,
                    marginTop: 0,
                    borderRadius: 30,
                    boxShadow: "0 2px 16px rgba(0,0,0,0.11)",
                    fontSize: "1.08rem",
                    padding: "26px 30px 26px 36px",
                    position: "relative",
                    zIndex: 2,
                    textAlign: "left",
                  }}
                >
                  <strong style={{ color: "#4b9fe1" }}>
                    {msg.speaker?.charAt(0).toUpperCase() + msg.speaker?.slice(1) || "AI"}:
                  </strong>{" "}
                  <ReactMarkdown>{msg.message || ""}</ReactMarkdown>
                  
                  {/* Show emotions if present */}
                  {msg.emotions && Object.keys(msg.emotions).length > 0 && (
                    <div style={{ 
                      marginTop: '10px', 
                      fontSize: '0.8rem', 
                      opacity: 0.7,
                      fontStyle: 'italic'
                    }}>
                      Emotions detected: {Object.entries(msg.emotions).map(([emotion, score]) => 
                        `${emotion} (${score})`).join(', ')}
                    </div>
                  )}
                  
                  {/* Bubble pointer */}
                  <div
                    style={{
                      position: "absolute",
                      top: -18,
                      left: 70,
                      width: 40,
                      height: 28,
                      background: "transparent",
                      zIndex: 1,
                      overflow: "visible",
                    }}
                  >
                    <svg width="38" height="28" viewBox="0 0 38 28">
                      <path
                        d="M0,28 Q19,0 38,28"
                        fill={darkMode ? "#333" : "#fff"}
                        stroke={darkMode ? "#333" : "#fff"}
                        strokeWidth="1"
                      />
                    </svg>
                  </div>
                </div>
              </div>
            );
          }

          // User messages
          if (isUser) {
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  flexDirection: "row-reverse",
                  alignItems: "flex-end",
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    background: "#4b9fe1",
                    color: "#fff",
                    padding: "16px 22px",
                    borderRadius: 20,
                    minWidth: 60,
                    maxWidth: 360,
                    fontSize: "1.02rem",
                    margin: "0 4px",
                    wordBreak: "break-word",
                    textAlign: "right",
                  }}
                >
                  <strong>You:</strong>{" "}
                  <ReactMarkdown>{msg.message || ""}</ReactMarkdown>
                </div>
              </div>
            );
          }

          return null;
        })}

        {/* Loading indicator */}
        {isLoading && (
          <div
            style={{
              textAlign: 'center',
              margin: '20px 0',
              color: darkMode ? '#ccc' : '#666'
            }}
          >
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '12px 20px',
              background: darkMode ? '#333' : '#f0f0f0',
              borderRadius: '20px'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#4b9fe1',
                animation: 'pulse 1.5s ease-in-out infinite'
              }}></div>
              <em>{persona === 'kai' ? 'Kai' : 'Eden'} is typing...</em>
            </div>
          </div>
        )}
      </main>

      {/* Input Form */}
      <form
        onSubmit={sendMessage}
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          padding: 10,
          background: darkMode ? "#2a2a2a" : "#fff",
          borderTop: `1px solid ${darkMode ? "#444" : "#ddd"}`,
          gap: '8px'
        }}
      >
        <select
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          style={{ 
            margin: 5, 
            padding: 8, 
            fontSize: "1rem",
            background: darkMode ? "#333" : "#fff",
            color: darkMode ? "#fff" : "#000",
            border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
            borderRadius: "4px",
            minWidth: '100px'
          }}
          disabled={isLoading}
        >
          <option value="kai"> Kai</option>
          <option value="eden"> Eden</option>
        </select>
        
        <select
          value={selectedAvatar}
          onChange={(e) => setSelectedAvatar(e.target.value)}
          style={{
            margin: 5, 
            padding: 8, 
            fontSize: "1rem",
            background: darkMode ? "#333" : "#fff",
            color: darkMode ? "#fff" : "#000",
            border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
            borderRadius: "4px",
            minWidth: '140px'
          }}
          disabled={isLoading}
        >
          <option value="samoyed">🐕 Samoyed</option>
          <option value="penguin">🐧 Penguin</option>
          <option value="capybara">🐹 Capybara</option>
          <option value="axolotl">🦎 Axolotl</option>
          <option value="bat">🦇 Bat</option>
        </select>

        <input
          type="text"
          placeholder="Session ID"
          style={{ 
            minWidth: 120, 
            margin: 5, 
            padding: 8, 
            fontSize: "1rem",
            background: darkMode ? "#333" : "#fff",
            color: darkMode ? "#fff" : "#000",
            border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
            borderRadius: "4px"
          }}
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
          disabled={isLoading}
        />
        
        <input
          type="text"
          placeholder="Type your message..."
          style={{ 
            flex: 1, 
            minWidth: 250, 
            margin: 5, 
            padding: 8, 
            fontSize: "1rem",
            background: darkMode ? "#333" : "#fff",
            color: darkMode ? "#fff" : "#000",
            border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
            borderRadius: "4px"
          }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        
        <button 
          type="submit" 
          style={{ 
            margin: 5, 
            padding: "8px 16px",
            background: isLoading ? "#ccc" : "#4b9fe1",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: isLoading ? "not-allowed" : "pointer",
            minWidth: '80px'
          }}
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? "..." : "Send"}
        </button>
      </form>

      {/* Memory Log */}
      <details 
        style={{ 
          padding: "10px 20px", 
          borderTop: `1px solid ${darkMode ? "#444" : "#ddd"}`,
          background: darkMode ? "#2a2a2a" : "#f9f9f9"
        }}
      >
        <summary 
          style={{ 
            cursor: "pointer", 
            fontWeight: "bold",
            color: darkMode ? "#fff" : "#000",
            marginBottom: '10px'
          }}
        >
          Memory Log ({memory.length} entries)
        </summary>
        <div
          style={{
            marginTop: 10,
            padding: 10,
            background: darkMode ? "#333" : "#fff",
            border: `1px solid ${darkMode ? "#555" : "#ddd"}`,
            borderRadius: "4px",
            maxHeight: 300,
            overflowY: "auto",
            fontSize: "0.9rem"
          }}
        >
          {memory.length === 0 ? (
            <p style={{ color: darkMode ? "#ccc" : "#666", fontStyle: "italic" }}>
              No memory entries yet
            </p>
          ) : (
            memory.map((m, idx) => (
              <div 
                key={idx} 
                style={{ 
                  marginBottom: 8,
                  paddingBottom: 8,
                  borderBottom: idx < memory.length - 1 ? `1px solid ${darkMode ? "#444" : "#eee"}` : 'none',
                  color: darkMode ? "#fff" : "#000"
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                  <strong style={{ color: "#4b9fe1" }}>{m.speaker}:</strong>
                  <span style={{ fontSize: '0.8rem', color: darkMode ? "#ccc" : "#666" }}>
                    {m.emotion && `${m.emotion}`}
                    {m.tags && m.tags.length > 0 && ` • ${m.tags.slice(0, 2).join(', ')}`}
                  </span>
                </div>
                <div>{m.message}</div>
              </div>
            ))
          )}
        </div>
      </details>

      {/* CSS for animations */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.3;
          }
        }
      `}</style>
    </div>
  );
}