window.DocumentsPage = {
  async render() {
    return `
      <h2 style="margin-bottom:1.5rem">Documents</h2>

      <div class="card">
        <div class="card-header">
          <div class="card-title">Upload Document</div>
        </div>
        <div class="form-group">
          <label>Upload a file (.txt, .md, .csv, .json, .pdf, .docx)</label>
          <input class="form-input" type="file" id="doc-file" accept=".txt,.md,.csv,.json,.pdf,.docx,.xml,.yml,.yaml,.html,.htm">
        </div>
        <div class="form-group">
          <label>Document Name (optional, defaults to filename)</label>
          <input class="form-input" id="doc-name" placeholder="e.g. Q4 Financial Report">
        </div>
        <button class="btn btn-primary" id="upload-file-btn">Upload File</button>
        <div class="form-group" style="margin-top:0.75rem">
          <details>
            <summary style="cursor:pointer;font-size:0.85rem;color:var(--text2)">Or paste text directly</summary>
            <textarea class="form-input" id="doc-text" rows="4" placeholder="Paste document content..." style="margin-top:0.5rem"></textarea>
            <div class="form-row" style="margin-top:0.5rem">
              <div class="form-group">
                <label>Strategy</label>
                <select class="form-input" id="doc-strategy">
                  <option value="recursive">Recursive</option>
                  <option value="fixed">Fixed</option>
                  <option value="sentence">Sentence</option>
                  <option value="token_approx">Token Approx</option>
                </select>
              </div>
              <div class="form-group">
                <label>Size</label>
                <input class="form-input" type="number" id="doc-size" value="800" min="50" max="4000">
              </div>
              <div class="form-group">
                <label>Overlap</label>
                <input class="form-input" type="number" id="doc-overlap" value="120" min="0" max="500">
              </div>
              <div class="form-group" style="padding-bottom:1px">
                <button class="btn btn-primary btn-sm" id="upload-text-btn" style="margin-top:1.5rem">Upload Text</button>
              </div>
            </div>
          </details>
        </div>
        <div id="upload-msg" style="margin-top:0.75rem;font-size:0.85rem"></div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-title">My Documents</div>
          <button class="btn btn-sm btn-primary" id="refresh-docs-btn" style="margin-left:auto">Refresh</button>
        </div>
        <div id="doc-list"><div class="spinner" style="margin:1rem auto"></div></div>
      </div>

      <!-- Share modal -->
      <div id="share-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:100;align-items:center;justify-content:center">
        <div class="card" style="width:100%;max-width:520px;max-height:80vh;overflow-y:auto">
          <div class="card-header">
            <div class="card-title">Share Document</div>
            <button class="btn btn-ghost btn-sm" onclick="DocumentsPage.closeShare()">Close</button>
          </div>
          <p style="color:var(--text2);font-size:0.85rem;margin-bottom:1rem" id="share-doc-filename"></p>

          <div class="card-header">
            <div class="card-title" style="font-size:0.95rem">Current Permissions</div>
          </div>
          <div id="share-perms-list"><div class="spinner" style="margin:1rem auto"></div></div>

          <div style="margin-top:1.5rem;border-top:1px solid var(--border);padding-top:1rem">
            <div class="card-header">
              <div class="card-title" style="font-size:0.95rem">Grant Role Access</div>
            </div>
            <div class="form-row">
              <div class="form-group" style="flex:1">
                <label>Role</label>
                <select class="form-input" id="share-role-select"></select>
              </div>
            </div>
            <div style="display:flex;gap:1.5rem;margin:0.5rem 0 1rem">
              <label><input type="checkbox" id="share-can-read" checked> Read</label>
              <label><input type="checkbox" id="share-can-write"> Write</label>
              <label><input type="checkbox" id="share-can-delete"> Delete</label>
            </div>
            <button class="btn btn-primary btn-sm" id="share-grant-btn">Grant Access</button>
            <span id="share-msg" style="font-size:0.85rem;margin-left:0.75rem"></span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-title">Search Documents</div>
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:2">
            <label>Query</label>
            <input class="form-input" id="search-query" placeholder="Search document contents...">
          </div>
          <div class="form-group" style="flex:1">
            <label>Top K</label>
            <input class="form-input" type="number" id="search-topk" value="5" min="1" max="20">
          </div>
          <div class="form-group" style="padding-bottom:1px">
            <button class="btn btn-primary" id="search-btn" style="margin-top:1.5rem">Search</button>
          </div>
        </div>
        <div id="search-results" style="margin-top:0.75rem"></div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-title">View Document Chunks</div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Document ID</label>
            <input class="form-input" id="doc-id" placeholder="UUID of document">
          </div>
          <div class="form-group" style="padding-bottom:1px">
            <button class="btn btn-primary btn-sm" id="view-chunks-btn" style="margin-top:1.5rem">View</button>
          </div>
        </div>
        <div id="chunks-view" style="margin-top:0.75rem"></div>
      </div>
    `;
  },

  async loadDocs() {
    const container = document.getElementById('doc-list');
    if (!container) return;
    try {
      const data = await api.listDocuments();
      const docs = data.documents || [];
      if (!docs.length) {
        container.innerHTML = '<div class="empty-state">No documents uploaded yet. Use the form above to upload.</div>';
        return;
      }
      container.innerHTML = `
        <table style="width:100%;border-collapse:collapse;font-size:0.85rem">
          <thead>
            <tr style="border-bottom:1px solid var(--border)">
              <th style="padding:0.5rem;text-align:left">Filename</th>
              <th style="padding:0.5rem;text-align:left">Owner</th>
              <th style="padding:0.5rem;text-align:left">Size</th>
              <th style="padding:0.5rem;text-align:left">Type</th>
              <th style="padding:0.5rem;text-align:center">Chunks</th>
              <th style="padding:0.5rem;text-align:left">Created</th>
              <th style="padding:0.5rem;text-align:center">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${docs.map(d => {
              const size = d.file_size > 1024 * 1024
                ? (d.file_size / 1024 / 1024).toFixed(1) + ' MB'
                : d.file_size > 1024
                  ? (d.file_size / 1024).toFixed(0) + ' KB'
                  : d.file_size + ' B';
              const created = new Date(d.created_at).toLocaleDateString();
              return `
                <tr style="border-bottom:1px solid var(--border)">
                  <td style="padding:0.5rem">${escapeHtml(d.original_filename)}</td>
                  <td style="padding:0.5rem;color:var(--text2)">${escapeHtml(d.owner_name) || '-'}</td>
                  <td style="padding:0.5rem;color:var(--text2)">${escapeHtml(size)}</td>
                  <td style="padding:0.5rem;color:var(--text2)">${escapeHtml(d.mime_type)}</td>
                  <td style="padding:0.5rem;text-align:center">${escapeHtml(d.chunk_count)}</td>
                  <td style="padding:0.5rem;color:var(--text2)">${escapeHtml(created)}</td>
                  <td style="padding:0.5rem;text-align:center">
                    <button class="btn btn-sm btn-primary view-chunks-action" data-id="${escapeHtml(d.id)}" title="View chunks">Chunks</button>
                    <button class="btn btn-sm btn-primary download-doc-action" data-id="${escapeHtml(d.id)}" title="Download file">DL</button>
                    <button class="btn btn-sm btn-primary share-doc-action" data-id="${escapeHtml(d.id)}" data-name="${escapeHtml(d.original_filename)}" title="Share">Share</button>
                    <button class="btn btn-sm btn-danger delete-doc-action" data-id="${escapeHtml(d.id)}" title="Delete document">Delete</button>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      `;
      container.querySelectorAll('.view-chunks-action').forEach(btn => {
        btn.addEventListener('click', () => {
          document.getElementById('doc-id').value = btn.dataset.id;
          document.getElementById('view-chunks-btn').click();
        });
      });
      container.querySelectorAll('.download-doc-action').forEach(btn => {
        btn.addEventListener('click', async () => {
          try {
            const { url, filename } = await api.downloadDocument(btn.dataset.id);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
          } catch (e) {
            alert(e.message);
          }
        });
      });
      container.querySelectorAll('.share-doc-action').forEach(btn => {
        btn.addEventListener('click', () => this.openShare(btn.dataset.id, btn.dataset.name));
      });
      container.querySelectorAll('.delete-doc-action').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.dataset.id;
          if (!confirm('Delete this document and all its chunks?')) return;
          btn.disabled = true;
          try {
            await api.deleteDocument(id);
            this.loadDocs();
          } catch (e) {
            alert(e.message);
            btn.disabled = false;
          }
        });
      });
    } catch (e) {
      container.innerHTML = `<p style="color:var(--danger)">Failed to load documents: ${escapeHtml(e.message)}</p>`;
    }
  },

  async openShare(docId, docName) {
    const modal = document.getElementById('share-modal');
    document.getElementById('share-doc-filename').textContent = docName;
    document.getElementById('share-msg').textContent = '';
    modal.style.display = 'flex';
    modal.dataset.docId = docId;

    try {
      const [perms, roles] = await Promise.all([
        api.getDocumentPermissions(docId),
        api.getRoles()
      ]);

      const roleSelect = document.getElementById('share-role-select');
      roleSelect.innerHTML = roles.map(r => `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name)}</option>`).join('');

      const permsList = document.getElementById('share-perms-list');
      if (!perms.length) {
        permsList.innerHTML = '<p style="color:var(--text2);font-size:0.85rem">No role permissions set. Only the document owner can access.</p>';
      } else {
        permsList.innerHTML = perms.map(p => `
          <div style="display:flex;align-items:center;justify-content:space-between;padding:0.5rem 0;border-bottom:1px solid var(--border)">
            <div>
              <span class="badge badge-${escapeHtml(p.role_name)}">${escapeHtml(p.role_name)}</span>
              <span style="font-size:0.8rem;color:var(--text2);margin-left:0.5rem">
                ${p.can_read ? 'Read' : ''}${p.can_write ? ' Write' : ''}${p.can_delete ? ' Delete' : ''}
              </span>
              <span style="font-size:0.75rem;color:var(--text2);margin-left:0.5rem">by ${escapeHtml(p.granted_by_name)}</span>
            </div>
            <div>
              <input type="checkbox" class="perm-toggle" data-perm-id="${escapeHtml(p.id)}" data-field="can_read" ${p.can_read ? 'checked' : ''} title="Read">
              <input type="checkbox" class="perm-toggle" data-perm-id="${escapeHtml(p.id)}" data-field="can_write" ${p.can_write ? 'checked' : ''} title="Write">
              <input type="checkbox" class="perm-toggle" data-perm-id="${escapeHtml(p.id)}" data-field="can_delete" ${p.can_delete ? 'checked' : ''} title="Delete">
              <button class="btn btn-danger btn-sm" data-perm-id="${escapeHtml(p.id)}" title="Revoke" style="margin-left:0.5rem">X</button>
            </div>
          </div>
        `).join('');
      }

      this._bindPermEvents(docId);
    } catch (e) {
      document.getElementById('share-perms-list').innerHTML = `<p style="color:var(--danger)">${escapeHtml(e.message)}</p>`;
    }

    document.getElementById('share-grant-btn').onclick = async () => {
      const roleId = document.getElementById('share-role-select').value;
      const canRead = document.getElementById('share-can-read').checked;
      const canWrite = document.getElementById('share-can-write').checked;
      const canDelete = document.getElementById('share-can-delete').checked;
      const msg = document.getElementById('share-msg');
      msg.style.color = 'var(--text2)';
      msg.textContent = 'Granting...';

      try {
        await api.grantDocumentPermission(docId, {
          role_id: roleId,
          can_read: canRead,
          can_write: canWrite,
          can_delete: canDelete,
        });
        msg.textContent = 'Access granted!';
        msg.style.color = 'var(--success)';
        this.openShare(docId, docName);
      } catch (e) {
        msg.textContent = e.message;
        msg.style.color = 'var(--danger)';
      }
    };
  },

  _bindPermEvents(docId) {
    document.querySelectorAll('.perm-toggle').forEach(cb => {
      cb.addEventListener('change', async () => {
        const permId = cb.dataset.permId;
        const field = cb.dataset.field;
        const update = { can_read: null, can_write: null, can_delete: null };
        update[field] = cb.checked;
        try {
          await api.updateDocumentPermission(docId, permId, update);
        } catch (e) {
          alert(e.message);
          cb.checked = !cb.checked;
        }
      });
    });

    document.querySelectorAll('.btn-danger.btn-sm[data-perm-id]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Revoke this role\'s access?')) return;
        try {
          await api.revokeDocumentPermission(docId, btn.dataset.permId);
          const docName = document.getElementById('share-doc-filename').textContent;
          this.openShare(docId, docName);
        } catch (e) {
          alert(e.message);
        }
      });
    });
  },

  closeShare() {
    document.getElementById('share-modal').style.display = 'none';
  },

  init() {
    this.loadDocs();

    // File upload
    const uploadFileBtn = document.getElementById('upload-file-btn');
    const uploadMsg = document.getElementById('upload-msg');
    uploadFileBtn?.addEventListener('click', async () => {
      const fileInput = document.getElementById('doc-file');
      const file = fileInput.files[0];
      if (!file) { uploadMsg.textContent = 'Please select a file'; uploadMsg.style.color = 'var(--danger)'; return; }
      const docName = document.getElementById('doc-name').value.trim() || null;
      uploadFileBtn.disabled = true;
      uploadFileBtn.textContent = 'Uploading...';
      try {
        const data = await api.uploadDocument(file, docName);
        uploadMsg.innerHTML = `Uploaded <strong>${escapeHtml(data.original_filename)}</strong> — ${escapeHtml(data.chunk_count)} chunks created.`;
        uploadMsg.style.color = 'var(--success)';
        fileInput.value = '';
        document.getElementById('doc-name').value = '';
        this.loadDocs();
      } catch (e) {
        uploadMsg.textContent = e.message;
        uploadMsg.style.color = 'var(--danger)';
      } finally {
        uploadFileBtn.disabled = false;
        uploadFileBtn.textContent = 'Upload File';
      }
    });

    // Text upload
    const uploadTextBtn = document.getElementById('upload-text-btn');
    uploadTextBtn?.addEventListener('click', async () => {
      const text = document.getElementById('doc-text').value.trim();
      if (!text) { uploadMsg.textContent = 'Text content is required'; uploadMsg.style.color = 'var(--danger)'; return; }
      const docName = document.getElementById('doc-name').value.trim() || null;
      uploadTextBtn.disabled = true;
      uploadTextBtn.textContent = 'Uploading...';
      try {
        const data = await api.createDocument(text, {
          strategy: document.getElementById('doc-strategy').value,
          chunk_size: parseInt(document.getElementById('doc-size').value),
          chunk_overlap: parseInt(document.getElementById('doc-overlap').value),
        });
        uploadMsg.innerHTML = `Text uploaded! ${escapeHtml(data.chunk_count)} chunks created. ID: <code>${escapeHtml(data.id)}</code>`;
        uploadMsg.style.color = 'var(--success)';
        document.getElementById('doc-text').value = '';
        this.loadDocs();
      } catch (e) {
        uploadMsg.textContent = e.message;
        uploadMsg.style.color = 'var(--danger)';
      } finally {
        uploadTextBtn.disabled = false;
        uploadTextBtn.textContent = 'Upload Text';
      }
    });

    // Refresh document list
    document.getElementById('refresh-docs-btn')?.addEventListener('click', () => this.loadDocs());

    // Search
    const searchBtn = document.getElementById('search-btn');
    const searchResults = document.getElementById('search-results');
    searchBtn?.addEventListener('click', async () => {
      const query = document.getElementById('search-query').value.trim();
      if (!query) { searchResults.innerHTML = '<p style="color:var(--danger)">Query is required</p>'; return; }
      searchBtn.disabled = true;
      searchResults.innerHTML = '<div class="spinner" style="margin:1rem auto"></div>';
      try {
        const data = await api.search(query, parseInt(document.getElementById('search-topk').value));
        if (!data.count) {
          searchResults.innerHTML = '<p style="color:var(--text2)">No results found.</p>';
        } else {
          searchResults.innerHTML = `<p style="color:var(--text2);margin-bottom:0.75rem">${escapeHtml(data.count)} result(s)</p>
            ${data.hits.map(h => `
              <div class="search-result card" style="padding:0.75rem">
                <div style="display:flex;justify-content:space-between;font-size:0.8rem">
                  <span>Doc: ${escapeHtml(h.document) || 'N/A'}</span>
                  <span style="color:var(--text2)">Score: ${h.score != null ? h.score.toFixed(3) : 'N/A'}</span>
                </div>
                <div class="result-content">${escapeHtml(h.content) || '(no content)'}</div>
              </div>
            `).join('')}
          `;
        }
      } catch (e) {
        searchResults.innerHTML = `<p style="color:var(--danger)">${escapeHtml(e.message)}</p>`;
      } finally {
        searchBtn.disabled = false;
      }
    });

    // View chunks
    const viewBtn = document.getElementById('view-chunks-btn');
    const chunksView = document.getElementById('chunks-view');
    viewBtn?.addEventListener('click', async () => {
      const docId = document.getElementById('doc-id').value.trim();
      if (!docId) { chunksView.innerHTML = '<p style="color:var(--danger)">Document ID is required</p>'; return; }
      viewBtn.disabled = true;
      chunksView.innerHTML = '<div class="spinner" style="margin:1rem auto"></div>';
      try {
        const data = await api.getDocumentChunks(docId);
        if (!data.chunks?.length) {
          chunksView.innerHTML = '<p style="color:var(--text2)">No chunks found for this document.</p>';
        } else {
          chunksView.innerHTML = `<p style="color:var(--text2);margin-bottom:0.5rem">${escapeHtml(data.total)} chunk(s):</p>
            ${data.chunks.map((c, i) => `
              <div class="chunk-item">
                <div class="chunk-meta">#${i + 1} | ID: ${escapeHtml(c.id)}</div>
                <div>${escapeHtml(c.content ? c.content.slice(0, 300) + (c.content.length > 300 ? '...' : '') : '(empty)')}</div>
              </div>
            `).join('')}
          `;
        }
      } catch (e) {
        chunksView.innerHTML = `<p style="color:var(--danger)">${escapeHtml(e.message)}</p>`;
      } finally {
        viewBtn.disabled = false;
      }
    });
  }
};
