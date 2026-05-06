(function () {
  function pathEquals(currentPath, targetPath) {
    if (!currentPath || !targetPath) {
      return false;
    }

    const normalizedCurrent = currentPath.replace(/\/$/, '') || '/';
    const normalizedTarget = targetPath.replace(/\/$/, '') || '/';
    return normalizedCurrent === normalizedTarget;
  }

  function ensureLink(nav, key, label, href) {
    if (!nav) {
      return;
    }

    var existing = nav.querySelector('a[data-nav-key="' + key + '"]');
    if (!existing) {
      existing = document.createElement('a');
      existing.setAttribute('data-nav-key', key);
      nav.appendChild(existing);
    }

    existing.textContent = label;
    existing.setAttribute('href', href);
  }

  function removeLink(nav, key) {
    if (!nav) {
      return;
    }

    var link = nav.querySelector('a[data-nav-key="' + key + '"]');
    if (link) {
      link.remove();
    }
  }

  function normalizeExistingLinks(nav) {
    if (!nav) {
      return;
    }

    function keyFromHref(href) {
      if (!href) {
        return null;
      }

      var cleaned = href;
      var hashIndex = cleaned.indexOf('#');
      if (hashIndex !== -1) {
        cleaned = cleaned.substring(0, hashIndex);
      }

      if (/^(https?:)?\/\//i.test(cleaned)) {
        try {
          cleaned = new URL(cleaned, window.location.origin).pathname;
        } catch (e) {
          return null;
        }
      }

      if (!cleaned.startsWith('/')) {
        return null;
      }

      if (cleaned === '/' || /\/templates\/storepage\.html$/i.test(cleaned)) return 'store';
      if (cleaned === '/about' || /\/templates\/about\.html$/i.test(cleaned)) return 'about';
      if (cleaned === '/inventory' || /\/templates\/inventory\.html$/i.test(cleaned)) return 'inventory';
      if (cleaned === '/seller' || /\/templates\/seller\.html$/i.test(cleaned)) return 'seller';
      if (cleaned === '/itemeditor' || /\/templates\/itemeditor\.html$/i.test(cleaned)) return 'itemeditor';
      if (cleaned === '/sign-in' || /\/templates\/sign-in\.html$/i.test(cleaned) || cleaned === '/login' || /\/templates\/login\.html$/i.test(cleaned)) return 'signin';
      if (cleaned === '/logout') return 'logout';
      if (cleaned === '/admin' || /\/templates\/admin\.html$/i.test(cleaned)) return 'admin';

      return null;
    }

    nav.querySelectorAll('a[href]').forEach(function (link) {
      var href = link.getAttribute('href') || '';
      var key = keyFromHref(href);
      if (key) {
        link.setAttribute('data-nav-key', key);
      }
    });

    var seen = {};
    nav.querySelectorAll('a[data-nav-key]').forEach(function (link) {
      var key = link.getAttribute('data-nav-key');
      if (!key) {
        return;
      }

      if (seen[key]) {
        link.remove();
        return;
      }

      seen[key] = true;
    });
  }

  function applyRoleAwareNav(sessionData) {
    var nav = document.querySelector('.site-nav');
    if (!nav) {
      return;
    }

    normalizeExistingLinks(nav);

    var role = sessionData && sessionData.role ? sessionData.role : null;
    var loggedIn = !!(sessionData && sessionData.logged_in);
    var isAdmin = role === 'admin';
    var isSeller = role === 'vendor';

    ensureLink(nav, 'store', 'Store Page', '/');
    ensureLink(nav, 'about', 'About Us', '/about');

    if (isAdmin) {
      ensureLink(nav, 'inventory', 'Inventory', '/inventory');
    } else {
      removeLink(nav, 'inventory');
    }

    if (isSeller) {
      ensureLink(nav, 'seller', 'Seller', '/seller');
      ensureLink(nav, 'itemeditor', 'Item editor', '/itemeditor');
    } else {
      removeLink(nav, 'seller');
      removeLink(nav, 'itemeditor');
    }

    if (isAdmin) {
      ensureLink(nav, 'admin', 'Admin', '/admin');
    } else {
      removeLink(nav, 'admin');
    }

    if (loggedIn) {
      ensureLink(nav, 'logout', 'Logout', '/logout');
      removeLink(nav, 'signin');
    } else {
      ensureLink(nav, 'signin', 'Sign In', '/sign-in');
      removeLink(nav, 'logout');
    }

    nav.querySelectorAll('a[href^="/"]').forEach(function (link) {
      link.setAttribute('href', appUrl(link.getAttribute('href')));
    });

    var pageTitle = document.querySelector('.section-title');
    var pageCopy = document.querySelector('.section-copy');
    var isStorePage = pathEquals(window.location.pathname, '/') || /storepage\.html$/i.test(window.location.pathname);

    if (isStorePage && pageTitle && pageCopy) {
      if (loggedIn) {
        var roleLabel = isAdmin ? 'Admin' : (isSeller ? 'Seller' : 'Customer');
        pageTitle.textContent = 'Welcome back, ' + (sessionData.username || 'User');
        pageCopy.textContent = 'Signed in as ' + roleLabel + '. Your navigation is tailored to your account permissions.';
      } else {
        pageTitle.textContent = 'Welcome to The Black Whale';
        pageCopy.textContent = 'Sign in to unlock role-based tools and personalized navigation.';
      }
    }
  }

  function applyGuestNav() {
    applyRoleAwareNav({ logged_in: false, role: null, username: null });
  }

  fetch(appUrl('/session-info'), {
    method: 'GET',
    credentials: 'same-origin'
  })
    .then(function (response) {
      if (!response.ok) {
        throw new Error('Session lookup failed');
      }
      return response.json();
    })
    .then(function (data) {
      applyRoleAwareNav(data || {});
    })
    .catch(function () {
      applyGuestNav();
    });
})();
