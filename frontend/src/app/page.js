"use client";
import JournalWindow from "../components/JournalWindow.jsx";

export default function Page() {
  return <JournalWindow />;
}

// "use client";
// import { useState, useEffect } from "react";
// import ReactMarkdown from "react-markdown";
// import ChatWindow from '../components/ChatWindow.jsx';




// // Avatar mapping by persona
// // const [selectedAvatar, setSelectedAvatar] = useState('penguin');

// // const AVATAR_MAP = {
// //   samoyed: "/samoyed_avatar.png",
// //   penguin: "/penguin_avatar.png",
// //   capybara: "/capybara_avatar.png",
// //   axolotl: "/axolotle_avatar.png",
// //   bat: "/bat_avatar.png",
// //   // Add more as needed
// // };

// // export default function Home() {
// //   const [darkMode, setDarkMode] = useState(false);
// //   const [input, setInput] = useState("");
// //   const [messages, setMessages] = useState([]);
// //   const [persona, setPersona] = useState("kai");
// //   const [sessionId, setSessionId] = useState("");
// //   const [memory, setMemory] = useState([]);
  
// export default function Page() {
//   return <ChatWindow />;
// }

// //   // Hydrate cache from localStorage
// //   useEffect(() => {
// //     if (typeof window === "undefined") return;
// //     const cache = JSON.parse(localStorage.getItem("kaiChatCache") || "[]");
// //     setMessages(cache);
// //     const theme = localStorage.getItem("kaiTheme");
// //     if (theme === "dark") setDarkMode(true);
// //   }, []);

// //   // Persist cache
// //   useEffect(() => {
// //     if (typeof window === "undefined") return;
// //     localStorage.setItem("kaiChatCache", JSON.stringify(messages.slice(-200)));
// //   }, [messages]);

// //   // Theme toggler
// //   function toggleTheme() {
// //     setDarkMode((v) => {
// //       const newMode = !v;
// //       if (typeof window !== "undefined") {
// //         localStorage.setItem("kaiTheme", newMode ? "dark" : "light");
// //       }
// //       return newMode;
// //     });
// //   }

// //   // Send message to backend
// //   async function sendMessage(e) {
// //     e.preventDefault();
// //     if (!input.trim()) return;
// //     const msg = { speaker: "user", message: input };
// //     setMessages((prev) => [...prev, msg]);
// //     setInput("");
// //     // POST to backend
// //     const resp = await fetch("http://127.0.0.1:8000/chat", {
// //       method: "POST",
// //       headers: { "Content-Type": "application/json" },
// //       body: JSON.stringify({
// //         user_input: input,
// //         session_id: sessionId || "default",
// //         persona,
// //       }),
// //     });
// //     const data = await resp.json();
// //     const reply = {
// //       speaker: persona,
// //       message: data.response,
// //       tags: data.emotions
// //         ? Object.entries(data.emotions).map(([k, v]) => `emotion:${k}:${v}`)
// //         : [],
// //     };
// //     setMessages((prev) => [...prev, reply]);
// //     updateMemory(sessionId || "default");
// //   }

// //   // Update memory from backend
// //   async function updateMemory(session) {
// //     const resp = await fetch(
// //       `http://127.0.0.1:8000/memory?session=${session || "default"}`
// //     );
// //     const data = await resp.json();
// //     setMemory(data);
// //   }

// //   return (
// //     <div className={darkMode ? "dark-mode" : ""} style={{ minHeight: "100vh" }}>
// //       <header
// //         style={{
// //           background: darkMode ? "#60a5fa" : "#4b9fe1",
// //           color: "white",
// //           padding: "10px 20px",
// //           display: "flex",
// //           justifyContent: "space-between",
// //           alignItems: "center",
// //         }}
// //         id="header"
// //       >
// //         <h2>Chat with Kai or Eden</h2>
// //         <button onClick={toggleTheme}>Toggle Dark Mode</button>
// //       </header>

// //       <div
// //         id="chat"
// //         style={{
// //           flex: 1,
// //           padding: 15,
// //           maxWidth: 800,
// //           margin: "auto",
// //           overflowY: "auto",
// //         }}
// //       >
// //         {messages.map((msg, idx) => {
// //           const personaKey = msg.speaker?.toLowerCase();
// //           const isKai = personaKey === "kai";
// //           const isEden = personaKey === "eden";
// //           const isUser = personaKey === "user";
// //           const avatarSrc = isKai
// //             ? AVATAR_MAP.kai
// //             : isEden
// //             ? AVATAR_MAP.eden
// //             : null;

// //           // Large centered avatar + chat bubble for Kai/Eden
// //           if ((isKai || isEden) && avatarSrc) {
// //             return (
// //               <div
// //                 key={idx}
// //                 style={{
// //                   display: "flex",
// //                   flexDirection: "column",
// //                   alignItems: "center",
// //                   margin: "36px 0",
// //                 }}
// //               >
// //                 <img
// //                   src={avatarSrc}
// //                   alt={msg.speaker}
// //                   style={{
// //                     width: 180,
// //                     height: 180,
// //                     borderRadius: "50%",
// //                     boxShadow: "0 4px 32px rgba(0,0,0,0.08)",
// //                     objectFit: "contain",
// //                     zIndex: 1,
// //                     marginBottom: -32, // overlap the bubble
// //                   }}
// //                 />
// //                 <div
// //                   style={{
// //                     background: "#fff",
// //                     color: "#222",
// //                     minWidth: 200,
// //                     maxWidth: 420,
// //                     marginTop: 0,
// //                     borderRadius: 30,
// //                     boxShadow: "0 2px 16px rgba(0,0,0,0.11)",
// //                     fontSize: "1.08rem",
// //                     padding: "26px 30px 26px 36px",
// //                     position: "relative",
// //                     zIndex: 2,
// //                     textAlign: "left",
// //                   }}
// //                 >
// //                   <strong style={{ color: "#4b9fe1" }}>
// //                     {msg.speaker || "AI"}:
// //                   </strong>{" "}
// //                   <ReactMarkdown>{msg.message || ""}</ReactMarkdown>
// //                   {/* Bubble pointer */}
// //                   <div
// //                     style={{
// //                       position: "absolute",
// //                       top: -18,
// //                       left: 70,
// //                       width: 40,
// //                       height: 28,
// //                       background: "transparent",
// //                       zIndex: 1,
// //                       overflow: "visible",
// //                     }}
// //                   >
// //                     <svg width="38" height="28" viewBox="0 0 38 28">
// //                       <path
// //                         d="M0,28 Q19,0 38,28"
// //                         fill="#fff"
// //                         stroke="#fff"
// //                         strokeWidth="1"
// //                       />
// //                     </svg>
// //                   </div>
// //                 </div>
// //               </div>
// //             );
// //           }

// //           // USER messages (small right-aligned bubble)
// //           if (isUser) {
// //             return (
// //               <div
// //                 key={idx}
// //                 style={{
// //                   display: "flex",
// //                   flexDirection: "row-reverse",
// //                   alignItems: "flex-end",
// //                   marginBottom: 16,
// //                 }}
// //               >
// //                 <div
// //                   style={{
// //                     background: "#4b9fe1",
// //                     color: "#fff",
// //                     padding: "16px 22px",
// //                     borderRadius: 20,
// //                     minWidth: 60,
// //                     maxWidth: 360,
// //                     fontSize: "1.02rem",
// //                     margin: "0 4px",
// //                     wordBreak: "break-word",
// //                     textAlign: "right",
// //                   }}
// //                 >
// //                   <strong>{msg.speaker || "You"}:</strong>{" "}
// //                   <ReactMarkdown>{msg.message || ""}</ReactMarkdown>
// //                 </div>
// //               </div>
// //             );
// //           }

// //           // fallback (ignore others)
// //           return null;
// //         })}
// //       </div>

// //       <form
// //         id="controls"
// //         style={{
// //           display: "flex",
// //           flexWrap: "wrap",
// //           justifyContent: "center",
// //           padding: 10,
// //           // background is now handled by CSS dark mode overrides
// //         }}
// //         onSubmit={sendMessage}
// //       >
// //         <input
// //           type="text"
// //           id="userInput"
// //           placeholder="Type your message..."
// //           style={{ flex: 1, minWidth: 250, margin: 5, padding: 8, fontSize: "1rem" }}
// //           value={input}
// //           onChange={(e) => setInput(e.target.value)}
// //         />
// //         <select
// //           id="persona"
// //           value={persona}
// //           onChange={(e) => setPersona(e.target.value)}
// //           style={{ margin: 5, padding: 8, fontSize: "1rem" }}
// //         >
// //           <option value="kai">Kai</option>
// //           <option value="eden">Eden</option>
// //         </select>
// //         <input
// //           type="text"
// //           id="sessionId"
// //           placeholder="Session ID (default)"
// //           style={{ minWidth: 160, margin: 5, padding: 8, fontSize: "1rem" }}
// //           value={sessionId}
// //           onChange={(e) => setSessionId(e.target.value)}
// //         />
// //         <button type="submit" style={{ margin: 5, padding: "8px 16px" }}>
// //           Send
// //         </button>
// //       </form>

// //       <h3 style={{ paddingLeft: 15 }}>Memory Log</h3>
// //       <div
// //         id="memory"
// //         style={{
// //           // Color and background handled by global CSS
// //           padding: 10,
// //           marginTop: 20,
// //           border: "1px solid #ccc",
// //           overflowX: "auto",
// //         }}
// //       >
// //         {memory.map((m, idx) => (
// //           <div key={idx}>
// //             <b>{m.speaker}</b>: {m.message} <i>({m.emotion})</i>
// //           </div>
// //         ))}
// //       </div>
// //     </div>
// //   );
// // }
