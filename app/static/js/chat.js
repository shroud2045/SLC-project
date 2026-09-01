/**
 * Shroud's Lockin Crib (SLC) - Community Chatroom Engine
 */
class CommunityChat {
  constructor() {
    this.messagesContainer = document.getElementById('chatMessages');
    this.chatForm = document.getElementById('chatForm');
    this.chatInput = document.getElementById('chatInput');
    this.btnSend = document.getElementById('btnChatSend');
    this.lastMessageId = 0;
    this.pollInterval = null;

    this.init();
  }

  init() {
    if (!this.messagesContainer) return;

    // Find initial lastMessageId
    const messageElements = this.messagesContainer.querySelectorAll('[data-message-id]');
    if (messageElements.length > 0) {
      const lastEl = messageElements[messageElements.length - 1];
      this.lastMessageId = parseInt(lastEl.dataset.messageId, 10) || 0;
    }

    this.scrollToBottom();

    // Setup Form submit
    if (this.chatForm) {
      this.chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.sendMessage();
      });
    }

    // Start polling every 2.5 seconds
    this.pollInterval = setInterval(() => this.pollNewMessages(), 2500);
  }

  scrollToBottom() {
    if (this.messagesContainer) {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
  }

  async pollNewMessages() {
    try {
      const res = await fetch(`/chat/api/messages?after_id=${this.lastMessageId}`);
      if (!res.ok) return;
      const data = await res.json();

      if (data.success && data.messages.length > 0) {
        data.messages.forEach(msg => {
          this.appendMessage(msg);
          if (msg.id > this.lastMessageId) {
            this.lastMessageId = msg.id;
          }
        });
        this.scrollToBottom();
      }
    } catch (e) {
      // Polling network drop
    }
  }

  async sendMessage() {
    const content = this.chatInput.value.trim();
    if (!content) return;

    this.chatInput.disabled = true;
    if (this.btnSend) this.btnSend.disabled = true;

    try {
      const res = await fetch('/chat/api/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.csrfToken
        },
        body: JSON.stringify({ content: content })
      });

      const data = await res.json();
      if (data.success) {
        this.chatInput.value = '';
        this.appendMessage(data.message);
        if (data.message.id > this.lastMessageId) {
          this.lastMessageId = data.message.id;
        }
        this.scrollToBottom();
      } else {
        alert(data.error || 'Failed to send message.');
      }
    } catch (err) {
      alert('Network error sending message.');
    } finally {
      this.chatInput.disabled = false;
      if (this.btnSend) this.btnSend.disabled = false;
      this.chatInput.focus();
    }
  }

  appendMessage(msg) {
    // Avoid duplicates
    if (document.getElementById(`chat-msg-${msg.id}`)) return;

    const currentUserId = window.currentUserId || 0;
    const isMine = msg.user_id === currentUserId;

    const bubble = document.createElement('div');
    bubble.id = `chat-msg-${msg.id}`;
    bubble.className = `chat-bubble ${isMine ? 'mine' : ''}`;
    bubble.dataset.messageId = msg.id;

    const avatarHtml = msg.avatar_filename 
      ? `<img src="/uploads/${msg.avatar_filename}" class="chat-avatar" alt="${msg.username}">`
      : `<div class="chat-avatar" style="background:#1e293b; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#00e5ff;">${msg.username[0].toUpperCase()}</div>`;

    const roleBadge = msg.role === 'ADMIN' ? '<span class="badge-pill badge-mythic" style="font-size:0.65rem;">ADMIN</span>' : (msg.role === 'MODERATOR' ? '<span class="badge-pill badge-rare" style="font-size:0.65rem;">MOD</span>' : '');

    bubble.innerHTML = `
      ${avatarHtml}
      <div class="chat-content-wrap">
        <div class="chat-meta">
          <span class="chat-username">${msg.username}</span>
          ${roleBadge}
          <span class="chat-time">${msg.created_at}</span>
        </div>
        <div class="chat-text">${this.escapeHtml(msg.content)}</div>
      </div>
    `;

    this.messagesContainer.appendChild(bubble);
  }

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('chatMessages')) {
    window.slcChat = new CommunityChat();
  }
});
