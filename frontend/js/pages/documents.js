window.DocumentsPage = {
  async render() {
    return `
      <h2 style="margin-bottom:1.5rem">Documents</h2>

      <div class="card">
        <div class="card-header">
          <div class="card-title">Upload Document</div>
        </div>
        <div class="form-group">
          <label>Text Content</label>
          <textarea class="form-input" id="doc-text" rows="6" placeholder="Paste or type document content here..."></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Chunk Strategy</label>
            <select class="form-input" id="doc-strategy">
              <option value="recursive">Recursive</option>
              <option value="fixed">Fixed</option>
              <option value="sentence">Sentence</option>
              <option value="token_approx">Token Approx</option>
            </select>
          </div>
          <div class="form-group">
            <label>Chunk Size</label>
            <input class="form-input" type="number" id="doc-size" value="500" min="50" max="4000">
          </div>
          <div class="form-group">
            <label>Chunk Overlap</label>
            <input class="form-input" type="number" id="doc-overlap" value="50" min="0" max="500">
          </div>
          <div class="form-group" style="padding-bottom:1px">
            <button class="btn btn-primary" id="upload-doc-btn" style="margin-top:1.5rem">Upload</button>
          </div>
        </div>
        <div id="doc-msg" style="margin-top:0.75rem;font-size:0.85rem"></div>
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
          <div class="form-group" style="padding-bottom:1px">
            <button class="btn btn-danger btn-sm" id="delete-doc-btn" style="margin-top:1.5rem">Delete</button>
          </div>
        </div>
        <div id="chunks-view" style="margin-top:0.75rem"></div>
      </div>
    `;
  },

  init() {
    // Upload
    const uploadBtn = document.getElementById('upload-doc-btn');
    const docMsg = document.getElementById('doc-msg');
    uploadBtn?.addEventListener('click', async () => {
      const text = document.getElementById('doc-text').value.trim();
      if (!text) { docMsg.textContent = 'Text content is required'; docMsg.style.color = 'var(--danger)'; return; }
      uploadBtn.disabled = true;
      uploadBtn.textContent = 'Uploading...';
      try {
        const data = await api.createDocument(text, {
          strategy: document.getElementById('doc-strategy').value,
          chunk_size: parseInt(document.getElementById('doc-size').value),
          chunk_overlap: parseInt(document.getElementById('doc-overlap').value),
        });
        docMsg.innerHTML = `Uploaded! Document ID: <code>${data.id}</code> - ${data.chunk_count} chunks created.`;
        docMsg.style.color = 'var(--success)';
      } catch (e) {
        docMsg.textContent = e.message;
        docMsg.style.color = 'var(--danger)';
      } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload';
      }
    });

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

    // Delete document
    const delBtn = document.getElementById('delete-doc-btn');
    delBtn?.addEventListener('click', async () => {
      const docId = document.getElementById('doc-id').value.trim();
      if (!docId) return;
      if (!confirm('Delete this document and all its chunks?')) return;
      delBtn.disabled = true;
      try {
        await api.deleteDocument(docId);
        document.getElementById('chunks-view').innerHTML = '<p style="color:var(--success)">Document deleted.</p>';
      } catch (e) {
        document.getElementById('chunks-view').innerHTML = `<p style="color:var(--danger)">${e.message}</p>`;
      } finally {
        delBtn.disabled = false;
      }
    });
  }
};
