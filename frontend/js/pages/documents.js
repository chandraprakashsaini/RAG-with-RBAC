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
                  <td style="padding:0.5rem">${d.original_filename}</td>
                  <td style="padding:0.5rem;color:var(--text2)">${size}</td>
                  <td style="padding:0.5rem;color:var(--text2)">${d.mime_type}</td>
                  <td style="padding:0.5rem;text-align:center">${d.chunk_count}</td>
                  <td style="padding:0.5rem;color:var(--text2)">${created}</td>
                  <td style="padding:0.5rem;text-align:center">
                    <button class="btn btn-sm btn-primary view-chunks-action" data-id="${d.id}" title="View chunks">Chunks</button>
                    <a href="${api.downloadDocumentUrl(d.id)}" class="btn btn-sm btn-primary" download title="Download file">Download</a>
                    <button class="btn btn-sm btn-danger delete-doc-action" data-id="${d.id}" title="Delete document">Delete</button>
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
      container.innerHTML = `<p style="color:var(--danger)">Failed to load documents: ${e.message}</p>`;
    }
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
        uploadMsg.innerHTML = `Uploaded <strong>${data.original_filename}</strong> — ${data.chunk_count} chunks created.`;
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
        uploadMsg.innerHTML = `Text uploaded! ${data.chunk_count} chunks created. ID: <code>${data.id}</code>`;
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
          searchResults.innerHTML = `<p style="color:var(--text2);margin-bottom:0.75rem">${data.count} result(s)</p>
            ${data.hits.map(h => `
              <div class="search-result card" style="padding:0.75rem">
                <div style="display:flex;justify-content:space-between;font-size:0.8rem">
                  <span>Doc: ${h.document || 'N/A'}</span>
                  <span style="color:var(--text2)">Score: ${h.score?.toFixed(3) || 'N/A'}</span>
                </div>
                <div class="result-content">${h.content || '(no content)'}</div>
              </div>
            `).join('')}
          `;
        }
      } catch (e) {
        searchResults.innerHTML = `<p style="color:var(--danger)">${e.message}</p>`;
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
          chunksView.innerHTML = `<p style="color:var(--text2);margin-bottom:0.5rem">${data.total} chunk(s):</p>
            ${data.chunks.map((c, i) => `
              <div class="chunk-item">
                <div class="chunk-meta">#${i + 1} | ID: ${c.id}</div>
                <div>${c.content ? c.content.slice(0, 300) + (c.content.length > 300 ? '...' : '') : '(empty)'}</div>
              </div>
            `).join('')}
          `;
        }
      } catch (e) {
        chunksView.innerHTML = `<p style="color:var(--danger)">${e.message}</p>`;
      } finally {
        viewBtn.disabled = false;
      }
    });
  }
};
