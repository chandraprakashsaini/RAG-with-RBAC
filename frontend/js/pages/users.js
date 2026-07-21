window.UsersPage = {
  _users: [],

  async render() {
    try {
      const [users, roles] = await Promise.all([api.listUsers(), api.getRoles()]);
      this._users = users;
      return `
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem">
          <h2>Users</h2>
          <button class="btn btn-primary" id="show-create-user-btn">+ New User</button>
        </div>

        <div class="card" id="create-user-card" style="display:none">
          <div class="card-header">
            <div class="card-title">Create User</div>
            <button class="btn btn-ghost btn-sm" id="cancel-create-btn">Cancel</button>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Full Name</label>
              <input class="form-input" id="new-user-name" placeholder="Jane Doe">
            </div>
            <div class="form-group">
              <label>Email</label>
              <input class="form-input" type="email" id="new-user-email" placeholder="jane@example.com">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Password</label>
              <input class="form-input" type="password" id="new-user-password" placeholder="Min 8 chars">
            </div>
            <div class="form-group">
              <label>Role</label>
              <select class="form-input" id="new-user-role">
                ${roles.map(r => `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name)}</option>`).join('')}
              </select>
            </div>
            <div class="form-group" style="padding-bottom:1px">
              <button class="btn btn-primary btn-sm" id="create-user-btn" style="margin-top:1.5rem">Create</button>
            </div>
          </div>
          <div id="create-user-msg" style="font-size:0.85rem;margin-top:0.5rem"></div>
        </div>

        <div class="card">
          <div class="table-container">
            <table>
              <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
              <tbody>
                ${users.map(u => `
                  <tr id="user-row-${escapeHtml(u.id)}">
                    <td>${escapeHtml(u.full_name)}</td>
                    <td>${escapeHtml(u.email)}</td>
                    <td><span class="badge badge-${escapeHtml(u.role_name)}">${escapeHtml(u.role_name)}</span></td>
                    <td>
                      <label class="toggle-switch">
                        <input type="checkbox" ${u.is_active ? 'checked' : ''} onchange="UsersPage.toggleActive('${escapeHtml(u.id)}', this.checked)">
                        <span class="toggle-slider"></span>
                      </label>
                      <span style="margin-left:6px;font-size:0.8rem;color:${u.is_active ? 'var(--success)' : 'var(--danger)'}">${u.is_active ? 'Active' : 'Inactive'}</span>
                    </td>
                    <td>${new Date(u.created_at).toLocaleDateString()}</td>
                    <td>
                      <button class="btn btn-ghost btn-sm" onclick="UsersPage.showEdit('${escapeHtml(u.id)}')">Edit</button>
                      <button class="btn btn-danger btn-sm" onclick="UsersPage.confirmDelete('${escapeHtml(u.id)}')">Delete</button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Edit modal backdrop -->
        <div id="edit-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:100;align-items:center;justify-content:center">
          <div class="card" style="width:100%;max-width:440px">
            <div class="card-header">
              <div class="card-title">Edit User</div>
              <button class="btn btn-ghost btn-sm" onclick="UsersPage.closeEdit()">Close</button>
            </div>
            <input type="hidden" id="edit-user-id">
            <div class="form-group">
              <label>Full Name</label>
              <input class="form-input" id="edit-user-name">
            </div>
            <div class="form-group">
              <label>Role</label>
              <select class="form-input" id="edit-user-role">
                ${roles.map(r => `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name)}</option>`).join('')}
              </select>
            </div>
            <div class="form-group">
              <label>New Password (leave blank to keep)</label>
              <input class="form-input" type="password" id="edit-user-password" placeholder="New password">
            </div>
            <div class="form-group">
              <label>
                <input type="checkbox" id="edit-user-active"> Active
              </label>
            </div>
            <div style="display:flex;gap:0.5rem">
              <button class="btn btn-primary" id="save-edit-btn">Save</button>
              <button class="btn btn-ghost" onclick="UsersPage.closeEdit()">Cancel</button>
            </div>
            <div id="edit-msg" style="font-size:0.85rem;margin-top:0.5rem"></div>
          </div>
        </div>
      `;
    } catch (e) {
      return `<div class="empty-state"><h3>Error</h3><p>${escapeHtml(e.message)}</p></div>`;
    }
  },

  init() {
    const showBtn = document.getElementById('show-create-user-btn');
    const cancelBtn = document.getElementById('cancel-create-btn');
    const createCard = document.getElementById('create-user-card');
    const createBtn = document.getElementById('create-user-btn');
    const createMsg = document.getElementById('create-user-msg');
    const saveEditBtn = document.getElementById('save-edit-btn');

    if (showBtn) {
      showBtn.addEventListener('click', () => {
        createCard.style.display = 'block';
        showBtn.style.display = 'none';
      });
    }
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        createCard.style.display = 'none';
        document.getElementById('show-create-user-btn').style.display = '';
        createMsg.textContent = '';
      });
    }
    if (createBtn) {
      createBtn.addEventListener('click', async () => {
        const name = document.getElementById('new-user-name').value.trim();
        const email = document.getElementById('new-user-email').value.trim();
        const password = document.getElementById('new-user-password').value;
        const roleId = document.getElementById('new-user-role').value;

        if (!name || !email || !password) {
          createMsg.textContent = 'All fields are required';
          createMsg.style.color = 'var(--danger)';
          return;
        }
        if (password.length < 8) {
          createMsg.textContent = 'Password must be at least 8 characters';
          createMsg.style.color = 'var(--danger)';
          return;
        }

        createBtn.disabled = true;
        try {
          await api.register(email, name, password, roleId);
          createMsg.textContent = 'User created! Refreshing...';
          createMsg.style.color = 'var(--success)';
          setTimeout(() => router.refresh(), 800);
        } catch (e) {
          createMsg.textContent = e.message;
          createMsg.style.color = 'var(--danger)';
          createBtn.disabled = false;
        }
      });
    }
    if (saveEditBtn) {
      saveEditBtn.addEventListener('click', async () => {
        const id = document.getElementById('edit-user-id').value;
        const name = document.getElementById('edit-user-name').value.trim();
        const roleId = document.getElementById('edit-user-role').value;
        const password = document.getElementById('edit-user-password').value;
        const isActive = document.getElementById('edit-user-active').checked;
        const msg = document.getElementById('edit-msg');

        if (!name) {
          msg.textContent = 'Name is required';
          msg.style.color = 'var(--danger)';
          return;
        }

        const payload = { full_name: name, role_id: roleId, is_active: isActive };
        if (password) payload.password = password;

        saveEditBtn.disabled = true;
        try {
          await api.updateUser(id, payload);
          msg.textContent = 'Saved! Refreshing...';
          msg.style.color = 'var(--success)';
          setTimeout(() => router.refresh(), 800);
        } catch (e) {
          msg.textContent = e.message;
          msg.style.color = 'var(--danger)';
          saveEditBtn.disabled = false;
        }
      });
    }
  },

  showEdit(id) {
    const u = this._users.find(x => x.id === id);
    if (!u) return;
    const modal = document.getElementById('edit-modal');
    document.getElementById('edit-user-id').value = u.id;
    document.getElementById('edit-user-name').value = u.full_name;
    document.getElementById('edit-user-role').value = u.role_id;
    document.getElementById('edit-user-password').value = '';
    document.getElementById('edit-user-active').checked = u.is_active;
    document.getElementById('edit-msg').textContent = '';
    document.getElementById('save-edit-btn').disabled = false;
    modal.style.display = 'flex';
  },

  closeEdit() {
    document.getElementById('edit-modal').style.display = 'none';
  },

  async toggleActive(id, checked) {
    try {
      await api.updateUser(id, { is_active: checked });
    } catch {
      router.refresh();
    }
  },

  confirmDelete(id) {
    const u = this._users.find(x => x.id === id);
    const name = u ? u.full_name : id;
    if (confirm(`Delete user "${name}"? This cannot be undone.`)) {
      this.deleteUser(id);
    }
  },

  async deleteUser(id) {
    try {
      await api.deleteUser(id);
      router.refresh();
    } catch (e) {
      alert(e.message);
    }
  }
};
