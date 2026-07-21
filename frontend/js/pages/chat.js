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
          <button class="btn btn-danger btn-sm" style="float:right" onclick="ChatsPage.deleteChat('${escapeHtml(currentChatId)}')">Delete</button>
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
            <div class="card" style="cursor:pointer;padding:1rem" onclick="router.navigate('chats', '${escapeHtml(c.id)}')">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-weight:500">${escapeHtml(c.title)}</span>
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
      container.innerHTML = '';
      for (const m of data.messages) {
        const div = document.createElement('div');
        div.className = `msg ${m.sender_type}`;
        const contentNode = document.createElement('span');
        contentNode.textContent = m.content;
        const timeSpan = document.createElement('span');
        timeSpan.className = 'msg-time';
        timeSpan.textContent = new Date(m.created_at).toLocaleTimeString();
        div.appendChild(contentNode);
        div.appendChild(timeSpan);
        container.appendChild(div);
      }
      container.scrollTop = container.scrollHeight;
    } catch (e) {
      this.showError(e.message);
    }
  },

  async sendMessage(chatId, text) {
    const container = document.getElementById('chat-messages');

    const userDiv = document.createElement('div');
    userDiv.className = 'msg user';
    const userContent = document.createElement('span');
    userContent.textContent = text;
    const userTime = document.createElement('span');
    userTime.className = 'msg-time';
    userTime.textContent = 'Just now';
    userDiv.appendChild(userContent);
    userDiv.appendChild(userTime);
    container.appendChild(userDiv);
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
        const timeSpan = document.createElement('span');
        timeSpan.className = 'msg-time';
        timeSpan.textContent = new Date().toLocaleTimeString();
        msgDiv.appendChild(timeSpan);

        if (lastChunks && lastChunks.length) {
          const panel = document.createElement('details');
          panel.className = 'chunks-panel';
          const summary = document.createElement('summary');
          summary.textContent = `Context (${lastChunks.length} chunks retrieved)`;
          panel.appendChild(summary);
          lastChunks.forEach((c, i) => {
            const item = document.createElement('div');
            item.className = 'chunk-item';
            const meta = document.createElement('div');
            meta.className = 'chunk-meta';
            meta.textContent = `#${i + 1} | Score: ${c.score != null ? c.score.toFixed(3) : 'N/A'} | Doc: ${c.metadata?.document_id || 'N/A'}`;
            const body = document.createElement('div');
            const slice = (c.content || '(empty)').slice(0, 200);
            body.textContent = slice + (c.content && c.content.length > 200 ? '...' : '');
            item.appendChild(meta);
            item.appendChild(body);
            panel.appendChild(item);
          });
          document.getElementById('chunks-panel-container').appendChild(panel);
        }

        btn.disabled = false;
        input.focus();
      },
      (err) => {
        if (responseText) {
          msgDiv.className = 'msg assistant';
          const timeSpan = document.createElement('span');
          timeSpan.className = 'msg-time';
          timeSpan.textContent = new Date().toLocaleTimeString();
          msgDiv.appendChild(timeSpan);
        } else {
          msgDiv.remove();
          const errDiv = document.createElement('div');
          errDiv.className = 'msg assistant';
          errDiv.style.background = 'rgba(239,68,68,0.15)';
          errDiv.style.color = 'var(--danger)';
          errDiv.textContent = `Error: ${err}`;
          container.appendChild(errDiv);
        }
        btn.disabled = false;
        input.focus();
      }
    );
  },

  async newChat() {
    if (document.getElementById('new-chat-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'new-chat-modal';
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal">
        <h3>New Chat</h3>
        <input class="form-input" id="new-chat-title" placeholder="Chat title">
        <div id="new-chat-error" class="modal-error" style="display:none"></div>
        <div class="modal-actions">
          <button class="btn btn-ghost" id="new-chat-cancel">Cancel</button>
          <button class="btn btn-primary" id="new-chat-create">Create</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const input = document.getElementById('new-chat-title');
    const errBox = document.getElementById('new-chat-error');
    const cancelBtn = document.getElementById('new-chat-cancel');
    const createBtn = document.getElementById('new-chat-create');

    const close = () => modal.remove();
    const showErr = (msg) => {
      errBox.textContent = msg;
      errBox.style.display = 'block';
    };

    const submit = async () => {
      const title = input.value.trim();
      if (!title) { showErr('Title is required'); return; }
      createBtn.disabled = true;
      try {
        const chat = await api.createChat(title);
        close();
        router.navigate('chats', chat.id);
      } catch (e) {
        createBtn.disabled = false;
        showErr(e.message || 'Failed to create chat');
      }
    };

    cancelBtn.addEventListener('click', close);
    createBtn.addEventListener('click', submit);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); submit(); }
      else if (e.key === 'Escape') { close(); }
    });
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });
    input.focus();
  },

  async deleteChat(chatId) {
    if (document.getElementById('delete-chat-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'delete-chat-modal';
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal">
        <h3>Delete chat?</h3>
        <p style="color:var(--text2);margin:0 0 0.5rem">This action cannot be undone.</p>
        <div id="delete-chat-error" class="modal-error" style="display:none"></div>
        <div class="modal-actions">
          <button class="btn btn-ghost" id="delete-chat-cancel">Cancel</button>
          <button class="btn btn-danger" id="delete-chat-confirm">Delete</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const errBox = document.getElementById('delete-chat-error');
    const cancelBtn = document.getElementById('delete-chat-cancel');
    const confirmBtn = document.getElementById('delete-chat-confirm');

    const close = () => modal.remove();
    const showErr = (msg) => {
      errBox.textContent = msg;
      errBox.style.display = 'block';
    };

    const doDelete = async () => {
      confirmBtn.disabled = true;
      try {
        await api.deleteChat(chatId);
        close();
        window._currentChatId = null;
        await router.refresh();
      } catch (e) {
        confirmBtn.disabled = false;
        showErr(e.message || 'Failed to delete chat');
      }
    };

    cancelBtn.addEventListener('click', close);
    confirmBtn.addEventListener('click', doDelete);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });
    confirmBtn.focus();
  },

  showError(msg) {
    const container = document.getElementById('chat-messages');
    if (container) {
      container.innerHTML = '';
      const errDiv = document.createElement('div');
      errDiv.className = 'msg assistant';
      errDiv.style.background = 'rgba(239,68,68,0.15)';
      errDiv.style.color = 'var(--danger)';
      errDiv.textContent = `Error: ${msg}`;
      container.appendChild(errDiv);
    }
  }
};
