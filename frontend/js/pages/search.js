window.SearchPage = {
  render() {
    return `
      <h2 style="margin-bottom:1.5rem">Vector Search</h2>

      <div class="card">
        <div class="form-row">
          <div class="form-group" style="flex:2">
            <label>Search Query</label>
            <input class="form-input" id="vs-query" placeholder="Search across all documents...">
          </div>
          <div class="form-group" style="flex:1">
            <label>Top K Results</label>
            <input class="form-input" type="number" id="vs-topk" value="10" min="1" max="50">
          </div>
          <div class="form-group" style="padding-bottom:1px">
            <button class="btn btn-primary" id="vs-search-btn" style="margin-top:1.5rem">Search</button>
          </div>
        </div>
      </div>

      <div id="vs-results"></div>

      <div class="card" style="margin-top:1rem">
        <div class="card-header">
          <div class="card-title">Ingest Content</div>
        </div>
        <div class="form-group">
          <label>Document ID</label>
          <input class="form-input" id="ingest-doc-id" placeholder="UUID">
        </div>
        <div class="form-group">
          <label>Text</label>
          <textarea class="form-input" id="ingest-text" rows="4" placeholder="Content to ingest..."></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Strategy</label>
            <select class="form-input" id="ingest-strategy">
              <option value="recursive">Recursive</option>
              <option value="fixed">Fixed</option>
              <option value="sentence">Sentence</option>
              <option value="token_approx">Token Approx</option>
            </select>
          </div>
          <div class="form-group">
            <label>Chunk Size</label>
            <input class="form-input" type="number" id="ingest-size" value="500">
          </div>
          <div class="form-group">
            <label>Overlap</label>
            <input class="form-input" type="number" id="ingest-overlap" value="50">
          </div>
          <div class="form-group" style="padding-bottom:1px">
            <button class="btn btn-primary btn-sm" id="ingest-btn" style="margin-top:1.5rem">Ingest</button>
          </div>
        </div>
        <div id="ingest-msg" style="margin-top:0.5rem;font-size:0.85rem"></div>
      </div>
    `;
  },

  init() {
    // Search
    const searchBtn = document.getElementById('vs-search-btn');
    const results = document.getElementById('vs-results');
    searchBtn?.addEventListener('click', async () => {
      const query = document.getElementById('vs-query').value.trim();
      if (!query) { results.innerHTML = '<p style="color:var(--danger);margin-top:0.5rem">Query is required</p>'; return; }
      searchBtn.disabled = true;
      results.innerHTML = '<div class="spinner" style="margin:1rem auto"></div>';
      try {
        const data = await api.search(query, parseInt(document.getElementById('vs-topk').value));
        if (!data.count) {
          results.innerHTML = '<div class="empty-state"><h3>No results</h3><p>Try a different query.</p></div>';
        } else {
          results.innerHTML = `<p style="color:var(--text2);margin-bottom:0.75rem">${data.count} result(s)</p>
            ${data.hits.map(h => `
              <div class="card" style="padding:0.75rem">
                <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:0.25rem">
                  <span>Doc: ${h.document || 'N/A'}</span>
                  <span style="color:var(--text2)">Score: ${h.score?.toFixed(4) || 'N/A'}</span>
                </div>
                <div style="font-size:0.85rem;color:var(--text2)">${h.content || '(empty)'}</div>
              </div>
            `).join('')}
          `;
        }
      } catch (e) {
        results.innerHTML = `<p style="color:var(--danger);margin-top:0.5rem">${e.message}</p>`;
      } finally {
        searchBtn.disabled = false;
      }
    });

    // Ingest
    const ingestBtn = document.getElementById('ingest-btn');
    const ingestMsg = document.getElementById('ingest-msg');
    ingestBtn?.addEventListener('click', async () => {
      const text = document.getElementById('ingest-text').value.trim();
      const docId = document.getElementById('ingest-doc-id').value.trim();
      if (!text) { ingestMsg.textContent = 'Text is required'; ingestMsg.style.color = 'var(--danger)'; return; }
      ingestBtn.disabled = true;
      try {
        const data = await api.ingest(docId || undefined, text, {
          strategy: document.getElementById('ingest-strategy').value,
          chunk_size: parseInt(document.getElementById('ingest-size').value),
          chunk_overlap: parseInt(document.getElementById('ingest-overlap').value),
        });
        ingestMsg.innerHTML = `Ingested: ${data.chunk_count} chunks created.`;
        ingestMsg.style.color = 'var(--success)';
      } catch (e) {
        ingestMsg.textContent = e.message;
        ingestMsg.style.color = 'var(--danger)';
      } finally {
        ingestBtn.disabled = false;
      }
    });
  }
};
