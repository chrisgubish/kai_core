
const chat  = document.getElementById("chat");
const form  = document.getElementById("composer");
const input = document.getElementById("textInput");
const personaSelector = document.getElementById("personaSelector");

input.placeholder = "Speak your heart…";
input.focus();

let autoScrollEnabled = true;

chat.addEventListener('scroll', () => {
  autoScrollEnabled = (chat.scrollHeight - chat.scrollTop - chat.clientHeight < 50);
});

function scrollChatToBottom() {
  if (autoScrollEnabled) {
    chat.scrollTop = chat.scrollHeight;
  }
}

function addMessage(text, cls){
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.innerHTML = `<p>${text}</p>`;
  chat.appendChild(div);
  scrollChatToBottom();
}

function addTypingDots(persona){
  const dots = document.createElement("div");
  dots.className = `msg ${persona} dots`;
  dots.innerHTML = "<span></span><span></span><span></span>";
  chat.appendChild(dots);
  scrollChatToBottom();
  return dots;
}

function applyMoodTheme(mood) {
  if (!mood) return;
  document.documentElement.setAttribute('data-mood', mood.toLowerCase());
}

form.addEventListener("submit", async e => {
  e.preventDefault();
  const userText = input.value.trim();
  if (!userText || input.disabled) return;

  const persona = personaSelector.value || "eden";
  addMessage(userText, "user");
  input.value = "";
  input.disabled = true;

  const dots = addTypingDots(persona);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_input: userText,
        persona: persona
      })
    });

    const data = await res.json();
    chat.removeChild(dots);
    addMessage(data.response ?? "…something went wrong", persona);
    applyMoodTheme(data.mood);
  } catch (err) {
    chat.removeChild(dots);
    addMessage("Network error, please try again.", persona);
    console.error(err);
  } finally {
    input.disabled = false;
  }
});

// 🌙 Dreamlog Viewer Logic
async function loadDreamlog() {
  const logList = document.getElementById("dreamlog-list");
  logList.innerHTML = "Loading Eden’s reflections...";

  try {
    const res = await fetch("/dreamlog?n=5");
    const data = await res.json();

    if (data.logs && data.logs.length) {
      logList.innerHTML = data.logs
        .map(entry => {
          const ts = new Date(entry.timestamp).toLocaleString();
          return `<div style="margin-bottom: 1em;"><strong>${ts}</strong><br>${entry.monologue}</div>`;
        })
        .join("");
    } else {
      logList.innerHTML = "Eden hasn’t shared any reflections yet.";
    }
  } catch (err) {
    logList.innerHTML = "Error fetching dreamlogs.";
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", loadDreamlog);
