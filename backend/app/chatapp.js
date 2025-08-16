// chatapp.js

document.addEventListener('DOMContentLoaded', () => {
  const welcomeScreen = document.getElementById('welcome-screen');
  const chatBox = document.getElementById('chat-box');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('user-input');
  const messages = document.getElementById('messages');

  // Display chat after short delay to simulate greeting
  setTimeout(() => {
    welcomeScreen.classList.add('hidden');
    chatBox.classList.remove('hidden');
  }, 2500);

  // Append message to chat box
  const appendMessage = (sender, text) => {
    const msg = document.createElement('div');
    msg.className = 'message';
    msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  };

  // Simulate Kai’s gentle response
  const getKaiResponse = (text) => {
    const replies = [
      "I'm here with you.",
      "That makes sense.",
      "You don’t have to carry that alone.",
      "Say more when you're ready.",
      "That matters — thank you for saying it."
    ];
    const randomReply = replies[Math.floor(Math.random() * replies.length)];
    return randomReply;
  };

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const userText = input.value.trim();
    if (!userText) return;

    appendMessage('You', userText);
    input.value = '';

    setTimeout(() => {
      const kaiReply = getKaiResponse(userText);
      appendMessage('Kai', kaiReply);
    }, 800);
  });
});
