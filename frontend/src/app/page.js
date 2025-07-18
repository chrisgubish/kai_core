"use client";
import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";

export default function Home() {
  const [darkMode, setDarkMode] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [persona, setPersona] = useState("kai");
  const [sessionId, setSessionId] = useState("");
  const [memory, setMemory] = useState([]);

  // Hydrate cache from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    const cache = JSON.parse(localStorage.getItem("kaiChatCache") || "[]");
    setMessages(cache);
    const theme = localStorage.getItem("kaiTheme");
    if (theme === "dark") setDarkMode(true);
  }, []);

  // Persist cache
  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem("kaiChatCache", JSON.stringify(messages.slice(-200)));
  }, [messages]);

  // Theme toggler
  function toggleTheme() {
    setDarkMode((v) => {
      const newMode = !v;
      if (typeof window !== "undefined") {
        localStorage.setItem("kaiTheme", newMode ? "dark" : "light");
      }
      return newMode;
    });
  }

  // Send message to backend
  async function sendMessage(e) {
    e.preventDefault();
    if (!input.trim()) return;
    const msg = { speaker: "user", message: input };
    setMessages((prev) => [...prev, msg]);
    setInput("");
    // POST to backend
    const resp = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_input: input,
        session_id: sessionId || "default",
        persona,
      }),
    });
    const data = await resp.json();
    const reply = {
      speaker: persona,
      message: data.response,
      tags: data.emotions
        ? Object.entries(data.emotions).map(([k, v]) => `emotion:${k}:${v}`)
        : [],
    };
    setMessages((prev) => [...prev, reply]);
    updateMemory(sessionId || "default");
  }

  // Update memory from backend
  async function updateMemory(session) {
    const resp = await fetch(
      `http://127.0.0.1:8000/memory?session=${session || "default"}`
    );
    const data = await resp.json();
    setMemory(data);
  }

  return (
    <div className={darkMode ? "dark-mode" : ""} style={{ minHeight: "100vh" }}>
      <header
        style={{
          background: darkMode ? "#60a5fa" : "#4b9fe1",
          color: "white",
          padding: "10px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
        id="header"
      >
        <h2>Chat with Kai or Eden</h2>
        <button onClick={toggleTheme}>Toggle Dark Mode</button>
      </header>

      <div
        id="chat"
        style={{
          flex: 1,
          padding: 15,
          maxWidth: 800,
          margin: "auto",
          overflowY: "auto",
        }}
      >
        {messages.map((msg, idx) => (
          <div
            className={`message ${msg.speaker?.toLowerCase()}`}
            key={idx}
            style={{
              marginBottom: 12,
              color:
                msg.speaker?.toLowerCase() === "kai"
                  ? "#4b9fe1"
                  : msg.speaker?.toLowerCase() === "eden"
                  ? "#5c6ac4"
                  : undefined,
              fontWeight: msg.speaker === "user" ? "bold" : undefined,
            }}
          >
            <strong>{msg.speaker || "AI"}</strong>:{" "}
            <ReactMarkdown>{msg.message || ""}</ReactMarkdown>
          </div>
        ))}
      </div>

      <form
        id="controls"
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          padding: 10,
          background: darkMode ? "#1f2937" : "#d1e8ff",
        }}
        onSubmit={sendMessage}
      >
        <input
          type="text"
          id="userInput"
          placeholder="Type your message..."
          style={{ flex: 1, minWidth: 250, margin: 5, padding: 8, fontSize: "1rem" }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <select
          id="persona"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          style={{ margin: 5, padding: 8, fontSize: "1rem" }}
        >
          <option value="kai">Kai</option>
          <option value="eden">Eden</option>
        </select>
        <input
          type="text"
          id="sessionId"
          placeholder="Session ID (default)"
          style={{ minWidth: 160, margin: 5, padding: 8, fontSize: "1rem" }}
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
        />
        <button type="submit" style={{ margin: 5, padding: "8px 16px" }}>
          Send
        </button>
      </form>

      <h3 style={{ paddingLeft: 15 }}>Memory Log</h3>
      <div
        id="memory"
        style={{
          background: darkMode ? "#1f2937" : "rgba(255,255,255,0.8)",
          color: darkMode ? "#e5e7eb" : "#0a2540",
          padding: 10,
          marginTop: 20,
          border: "1px solid #ccc",
          overflowX: "auto",
        }}
      >
        {memory.map((m, idx) => (
          <div key={idx}>
            <b>{m.speaker}</b>: {m.message} <i>({m.emotion})</i>
          </div>
        ))}
      </div>
    </div>
  );
}
