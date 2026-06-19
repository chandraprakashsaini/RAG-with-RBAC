window.ChatsPage = {
  async render() {
    const chats = await api.listChats();
    const currentChatId = window._currentChatId || null;

    let chatArea = '';
    if (currentChatId) {
      chatArea = `<div class="chat-container">
        <div class="chat-header">
          <button class="btn btn-ghost btn-sm" onclick="router.navigate('chats')">&larr; Back</button>
          <span id="chat-title" style="margin-left:0.75rem;font-weight:600"></span>
          <button class="btn btn-danger btn-sm" style="float:right" onclick="ChatsPage.deleteChat('${currentChatId}')">Delete</button>
        </div>
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input-area">
          <input class="form-input" id="chat-input" placeholder="Type a message..." autofocus>
          <button class="btn btn-primary" id="chat-send-btn">Send</button>
        </div>
        <div id="chunks-panel-container"></div>
      </div>`;
    } else {
      chatArea = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem">
          <h2>Chats</h2>
          <button class="btn btn-primary" onclick="ChatsPage.newChat()">+ New Chat</button>
        </div>
        ${chats.length === 0 ? '<div class="empty-state"><h3>No chats yet</h3><p>Create a new chat to get started.</p></div>' : ''}
        <div style="display:grid;gap:0.5rem">
          ${chats.map(c => `
            <div class="card" style="cursor:pointer;padding:1rem" onclick="router.navigate('chats', '${c.id}')">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-weight:500">${c.title}</span>
                <span style="font-size:0.8rem;color:var(--text2)">${new Date(c.updated_at).toLocaleDateString()}</span>
              </div>
            </div>
          `).join('')}
        </div>`;
    }

    return `
      <div id="chats-page">
        ${chatArea}
      </div>
    `;
  },

  async init() {
    const chatId = window._currentChatId;
    if (chatId) await this.loadChat(chatId);
    this.bindEvents(chatId);
  },

  bindEvents(chatId) {
    const input = document.getElementById('chat-input');
    const btn = document.getElementById('chat-send-btn');
    if (!input || !btn) return;

    const send = () => {
      const text = input.value.trim();
      if (!text || btn.disabled) return;
      input.value = '';
      this.sendMessage(chatId, text);
    };

    btn.addEventListener('click', send);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
  },

  async loadChat(chatId) {
    try {
      const data = await api.getChat(chatId);
      document.getElementById('chat-title').textContent = data.chat.title;

      const container = document.getElementById('chat-messages');
      container.innerHTML = data.messages.map(m => `
        <div class="msg ${m.sender_type}">
          ${m.content}
          <span class="msg-time">${new Date(m.created_at).toLocaleTimeString()}</span>
        </div>
      `).join('');
      container.scrollTop = container.scrollHeight;
    } catch (e) {
      this.showError(e.message);
    }
  },

  async sendMessage(chatId, text) {
    const container = document.getElementById('chat-messages');

    container.innerHTML += `<div class="msg user">${text}<span class="msg-time">Just now</span></div>`;
    container.scrollTop = container.scrollHeight;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'msg assistant streaming';
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;

    const btn = document.getElementById('chat-send-btn');
    const input = document.getElementById('chat-input');
    btn.disabled = true;

    let responseText = '';
    let lastChunks = null;
    let abortFn = null;

    abortFn = api.streamMessage(chatId, text,
      (chunks) => { lastChunks = chunks; },
      (token) => {
        responseText += token;
        msgDiv.textContent = responseText;
        container.scrollTop = container.scrollHeight;
      },
      () => {
        msgDiv.className = 'msg assistant';
        msgDiv.innerHTML += `<span class="msg-time">${new Date().toLocaleTimeString()}</span>`;

        if (lastChunks && lastChunks.length) {
          const panel = document.createElement('details');
          panel.className = 'chunks-panel';
          panel.innerHTML = `
            <summary>Context (${lastChunks.length} chunks retrieved)</summary>
            ${lastChunks.map((c, i) => `
              <div class="chunk-item">
                <div class="chunk-meta">#${i + 1} | Score: ${c.score?.toFixed(3) || 'N/A'} | Doc: ${c.metadata?.document_id || 'N/A'}</div>
                <div>${c.content?.slice(0, 200) || '(empty)'}${c.content?.length > 200 ? '...' : ''}</div>
              </div>
            `).join('')}
          `;
          document.getElementById('chunks-panel-container').appendChild(panel);
        }

        btn.disabled = false;
        input.focus();
      },
      (err) => {
        if (responseText) {
          msgDiv.className = 'msg assistant';
          msgDiv.innerHTML += `<span class="msg-time">${new Date().toLocaleTimeString()}</span>`;
        } else {
          msgDiv.remove();
          container.innerHTML += `<div class="msg assistant" style="background:rgba(239,68,68,0.15);color:var(--danger)">Error: ${err}</div>`;
        }
        btn.disabled = false;
        input.focus();
      }
    );
  },

  async newChat() {
    const title = prompt('Chat title:');
    if (!title || !title.trim()) return;
    try {
      const chat = await api.createChat(title.trim());
      window._currentChatId = chat.id;
      await router.refresh();
    } catch (e) {
      alert('Error: ' + e.message);
    }
  },

  async deleteChat(chatId) {
    if (!confirm('Delete this chat?')) return;
    try {
      await api.deleteChat(chatId);
      window._currentChatId = null;
      await router.refresh();
    } catch (e) {
      alert('Error: ' + e.message);
    }
  },

  showError(msg) {
    const container = document.getElementById('chat-messages');
    if (container) container.innerHTML = `<div class="msg assistant" style="background:rgba(239,68,68,0.15);color:var(--danger)">Error: ${msg}</div>`;
  }
};
