window.AdminPage = {
  async render() {
    try {
      const [roles, me] = await Promise.all([api.getRoles(), api.getMe()]);
      return `
        <h2 style="margin-bottom:1.5rem">Admin Panel</h2>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Roles</div>
          </div>
          <div class="table-container">
            <table>
              <thead><tr><th>Name</th><th>Description</th><th>Created</th></tr></thead>
              <tbody>
                ${roles.map(r => `
                  <tr><td><span class="badge badge-${r.name}">${r.name}</span></td><td>${r.description || '-'}</td><td>${new Date(r.created_at).toLocaleDateString()}</td></tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Create Role</div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Name</label>
              <input class="form-input" id="role-name" placeholder="e.g. contributor">
            </div>
            <div class="form-group">
              <label>Description</label>
              <input class="form-input" id="role-desc" placeholder="Optional description">
            </div>
            <div class="form-group" style="padding-bottom:1px">
              <button class="btn btn-primary btn-sm" id="create-role-btn" style="margin-top:1.5rem">Create</button>
            </div>
          </div>
          <div id="role-msg" style="margin-top:0.5rem;font-size:0.85rem"></div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Current User</div>
          </div>
          <p><strong>Email:</strong> ${me.email}</p>
          <p><strong>Name:</strong> ${me.full_name}</p>
          <p><strong>Role:</strong> <span class="badge badge-${me.role || 'viewer'}">${me.role || 'Unknown'}</span></p>
        </div>
      `;
    } catch (e) {
      return `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
    }
  },

  async init() {
    const btn = document.getElementById('create-role-btn');
    if (!btn) return;
    const msg = document.getElementById('role-msg');
    btn.addEventListener('click', async () => {
      const name = document.getElementById('role-name').value.trim();
      if (!name) { msg.textContent = 'Name is required'; msg.style.color = 'var(--danger)'; return; }
      btn.disabled = true;
      try {
        await api.createRole(name, document.getElementById('role-desc').value.trim());
        msg.textContent = 'Role created! Refreshing...';
        msg.style.color = 'var(--success)';
        setTimeout(() => router.refresh(), 1000);
      } catch (e) {
        msg.textContent = e.message;
        msg.style.color = 'var(--danger)';
        btn.disabled = false;
      }
    });
  }
};
