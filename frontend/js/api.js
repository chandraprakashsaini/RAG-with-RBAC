const API_BASE = '';

function escapeHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
window.escapeHtml = escapeHtml;

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('token');
  }

  setToken(token) {
    this.token = token;
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
  }

  isAuthenticated() { return !!this.token; }

  headers(extra) {
    const h = { 'Content-Type': 'application/json', ...extra };
    if (this.token) h['Authorization'] = `Bearer ${this.token}`;
    return h;
  }

  async request(method, path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) {
      const msg = data?.detail || data?.error?.message || data?.message || res.statusText;
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  }

  get(path) { return this.request('GET', path); }
  post(path, body) { return this.request('POST', path, body); }
  del(path) { return this.request('DELETE', path); }

  // Auth
  login(email, password) {
    return this.post('/auth/login', { email, password });
  }
  register(email, fullName, password, roleId) {
    return this.post('/auth/register', { email, full_name: fullName, password, role_id: roleId });
  }
  getMe() { return this.get('/auth/me'); }
  getRoles() { return this.get('/auth/roles'); }
  createRole(name, description) {
    return this.post('/auth/roles', { name, description });
  }

  // Documents
  createDocument(text, chunking) {
    return this.post('/api/v1/documents', { text, chunking });
  }
  listDocuments() { return this.get('/api/v1/documents'); }
  getDocument(id) { return this.get(`/api/v1/documents/${id}`); }
  deleteDocument(id) { return this.del(`/api/v1/documents/${id}`); }
  getDocumentChunks(id, limit = 50, offset = 0) {
    return this.get(`/api/v1/documents/${id}/chunks?limit=${limit}&offset=${offset}`);
  }
  downloadDocumentUrl(id) { return `${API_BASE}/api/v1/documents/${id}/download`; }

  // Authenticated download: Bearer tokens aren't attached by plain <a> navigation,
  // so fetch with the Authorization header and return a Blob URL the browser can open.
  async downloadDocument(id) {
    const res = await fetch(this.downloadDocumentUrl(id), {
      headers: this.headers(),
    });
    if (!res.ok) {
      let msg = res.statusText;
      try { const data = await res.json(); msg = data?.detail || data?.error?.message || msg; } catch {}
      throw new Error(msg);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const match = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') || '');
    return { url, filename: match ? match[1] : id };
  }
  getDocumentPermissions(docId) { return this.get(`/api/v1/documents/${docId}/permissions`); }
  grantDocumentPermission(docId, data) { return this.post(`/api/v1/documents/${docId}/permissions`, data); }
  updateDocumentPermission(docId, permId, data) {
    return this.request('PUT', `/api/v1/documents/${docId}/permissions/${permId}`, data);
  }
  revokeDocumentPermission(docId, permId) {
    return this.del(`/api/v1/documents/${docId}/permissions/${permId}`);
  }

  uploadDocument(file, documentName) {
    const formData = new FormData();
    formData.append('file', file);
    if (documentName) formData.append('document_name', documentName);
    return fetch(`${API_BASE}/api/v1/documents/upload`, {
      method: 'POST',
      headers: this.token ? { 'Authorization': `Bearer ${this.token}` } : {},
      body: formData,
    }).then(async res => {
      const data = await res.json();
      if (!res.ok) {
        const msg = data?.detail || data?.error?.message || data?.message || res.statusText;
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      }
      return data;
    });
  }

  // Ingest / Search
  ingest(documentId, text, chunking) {
    return this.post('/api/v1/ingest', { document_id: documentId, text, chunking });
  }
  search(query, topK = 5, documentId) {
    const body = { query, top_k: topK };
    if (documentId) body.document_id = documentId;
    return this.post('/api/v1/search', body);
  }

  // Users
  listUsers() { return this.get('/users'); }
  getUser(id) { return this.get(`/users/${id}`); }
  updateUser(id, data) { return this.request('PATCH', `/users/${id}`, data); }
  deleteUser(id) { return this.del(`/users/${id}`); }

  // Chats
  createChat(title) { return this.post('/api/v1/chats', { title }); }
  listChats() { return this.get('/api/v1/chats'); }
  getChat(id) { return this.get(`/api/v1/chats/${id}`); }
  deleteChat(id) { return this.del(`/api/v1/chats/${id}`); }
  sendMessage(chatId, content) {
    return this.post(`/api/v1/chats/${chatId}/messages`, { content });
  }

  // SSE Chat stream
  streamMessage(chatId, content, onChunks, onToken, onDone, onError) {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/api/v1/chats/${chatId}/messages/stream`);
    xhr.setRequestHeader('Content-Type', 'application/json');
    if (this.token) xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
    xhr.responseType = 'text';

    let lastIndex = 0;
    let currentEvent = '';

    xhr.onprogress = () => {
      const newData = xhr.responseText.slice(lastIndex);
      lastIndex = xhr.responseText.length;

      const lines = newData.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) { currentEvent = ''; continue; }

        if (trimmed.startsWith('event: ')) {
          currentEvent = trimmed.slice(7).trim();
          if (currentEvent === 'done') { onDone(); return; }
          if (currentEvent === 'error') { onError('Stream error'); return; }
          continue;
        }

        if (trimmed.startsWith('data: ')) {
          const payload = trimmed.slice(6);
          if (currentEvent === 'chunks') {
            try { onChunks(JSON.parse(payload)); } catch (e) {}
            currentEvent = '';
            continue;
          }
          try {
            const parsed = JSON.parse(payload);
            if (parsed.token) onToken(parsed.token);
          } catch {}
        }
      }
    };

    xhr.onerror = () => onError('Connection failed');
    xhr.onloadend = () => {
      if (xhr.status !== 200) onError(`HTTP ${xhr.status}`);
    };

    xhr.send(JSON.stringify({ content }));
    return () => xhr.abort();
  }
}

window.api = new ApiClient();
