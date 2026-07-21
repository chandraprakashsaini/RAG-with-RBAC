window.LoginPage = {
  render() {
    return `
      <div class="auth-page">
        <div class="auth-card">
          <h1>RAG Admin</h1>
          <p>Sign in to your account</p>
          <div id="login-form">
            <div class="form-group">
              <label>Email</label>
              <input class="form-input" type="email" id="login-email" placeholder="you@example.com">
            </div>
            <div class="form-group">
              <label>Password</label>
              <input class="form-input" type="password" id="login-password" placeholder="Your password">
            </div>
            <button class="btn btn-primary btn-block" id="login-btn">Sign In</button>
            <p style="text-align:center;margin-top:1rem;font-size:0.85rem;color:var(--text2)">
              Don't have an account? <a href="#" onclick="router.navigate('register')">Register</a>
            </p>
          </div>
          <div id="login-error" style="color:var(--danger);margin-top:0.75rem;font-size:0.85rem;display:none"></div>
        </div>
      </div>
    `;
  },

  init() {
    const btn = document.getElementById('login-btn');
    const err = document.getElementById('login-error');
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.textContent = 'Signing in...';
      err.style.display = 'none';
      try {
        const data = await api.login(
          document.getElementById('login-email').value,
          document.getElementById('login-password').value
        );
        api.setToken(data.access_token);
        router.navigate('chats');
      } catch (e) {
        err.textContent = e.message;
        err.style.display = 'block';
      } finally {
        btn.disabled = false;
        btn.textContent = 'Sign In';
      }
    });
  }
};

window.RegisterPage = {
  render() {
    return `
      <div class="auth-page">
        <div class="auth-card">
          <h1>Create Account</h1>
          <p>Register a new user</p>
          <div id="register-form">
            <div class="form-group">
              <label>Full Name</label>
              <input class="form-input" type="text" id="reg-name">
            </div>
            <div class="form-group">
              <label>Email</label>
              <input class="form-input" type="email" id="reg-email">
            </div>
            <div class="form-group">
              <label>Password</label>
              <input class="form-input" type="password" id="reg-password">
            </div>
            <div class="form-group">
              <label>Role</label>
              <select class="form-input" id="reg-role">
                <option value="">Loading...</option>
              </select>
            </div>
            <button class="btn btn-primary btn-block" id="register-btn">Create Account</button>
            <p style="text-align:center;margin-top:1rem;font-size:0.85rem;color:var(--text2)">
              Already have an account? <a href="#" onclick="router.navigate('login')">Sign In</a>
            </p>
          </div>
          <div id="register-error" style="color:var(--danger);margin-top:0.75rem;font-size:0.85rem;display:none"></div>
        </div>
      </div>
    `;
  },

  async init() {
    try {
      const roles = await api.getRoles();
      const sel = document.getElementById('reg-role');
      sel.innerHTML = roles.map(r => `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name)}</option>`).join('');
    } catch {}

    const btn = document.getElementById('register-btn');
    const err = document.getElementById('register-error');
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.textContent = 'Creating...';
      err.style.display = 'none';
      try {
        await api.register(
          document.getElementById('reg-email').value,
          document.getElementById('reg-name').value,
          document.getElementById('reg-password').value,
          document.getElementById('reg-role').value
        );
        router.navigate('login');
      } catch (e) {
        err.textContent = e.message;
        err.style.display = 'block';
      } finally {
        btn.disabled = false;
        btn.textContent = 'Create Account';
      }
    });
  }
};
