const Router = {
  currentRoute: null,

  navigate(route, param) {
    if (route === 'login' || route === 'register') {
      window._currentChatId = null;
      window.location.hash = route;
    } else if (route === 'chats') {
      window._currentChatId = param || null;
      window.location.hash = param ? `chats/${param}` : 'chats';
    } else {
      window._currentChatId = null;
      window.location.hash = route;
    }
  },

  async refresh() {
    this.render();
  },

  async render() {
    const app = document.getElementById('app');
    const hash = window.location.hash.slice(1) || 'login';

    if (!api.isAuthenticated() && !['login', 'register'].includes(hash.split('/')[0])) {
      window.location.hash = 'login';
      return;
    }

    if (api.isAuthenticated() && ['login', 'register'].includes(hash.split('/')[0])) {
      window.location.hash = 'chats';
      return;
    }

    this.currentRoute = hash;

    if (hash === 'login' || hash === 'register') {
      const page = hash === 'login' ? LoginPage : RegisterPage;
      app.innerHTML = page.render();
      page.init();
      return;
    }

    // Parse route
    let page, content;
    if (hash.startsWith('chats')) {
      const parts = hash.split('/');
      if (parts[1]) {
        window._currentChatId = parts[1];
      } else {
        window._currentChatId = null;
      }
      page = ChatsPage;
    } else if (hash === 'admin') {
      page = AdminPage;
    } else if (hash === 'documents') {
      page = DocumentsPage;
    } else if (hash === 'search') {
      page = SearchPage;
    } else {
      window.location.hash = 'chats';
      return;
    }

    // Render layout with sidebar
    const navItems = [
      { route: 'chats', label: 'Chats', icon: '\uD83D\uDCAC' },
      { route: 'documents', label: 'Documents', icon: '\uD83D\uDCC4' },
      { route: 'search', label: 'Search', icon: '\uD83D\uDD0D' },
      { route: 'admin', label: 'Admin', icon: '\u2699\uFE0F' },
    ];

    const currentBase = hash.split('/')[0];

    app.innerHTML = `
      <div class="app-layout">
        <aside class="sidebar">
          <div class="sidebar-brand">RAG Admin</div>
          <nav class="sidebar-nav">
            ${navItems.map(n => `
              <button class="nav-item ${currentBase === n.route ? 'active' : ''}" onclick="router.navigate('${n.route}')">
                <span>${n.icon}</span>
                <span>${n.label}</span>
              </button>
            `).join('')}
            <button class="nav-item logout" onclick="Router.logout()">
              <span>\uD83D\uDEAA</span>
              <span>Logout</span>
            </button>
          </nav>
        </aside>
        <main class="main-content" id="main-content"></main>
      </div>
    `;

    const mainContent = document.getElementById('main-content');
    mainContent.innerHTML = '<div class="spinner" style="margin:3rem auto"></div>';

    try {
      const html = await page.render();
      mainContent.innerHTML = html;
      page.init();
    } catch (e) {
      mainContent.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
    }
  },

  logout() {
    api.setToken(null);
    window._currentChatId = null;
    window.location.hash = 'login';
  }
};

window.router = Router;

// Handle hash changes
window.addEventListener('hashchange', () => router.render());
window.addEventListener('DOMContentLoaded', () => {
  // Check auth on load
  if (api.isAuthenticated()) {
    // Verify token is still valid
    api.getMe().then(() => {
      router.render();
    }).catch(() => {
      api.setToken(null);
      router.render();
    });
  } else {
    router.render();
  }
});
