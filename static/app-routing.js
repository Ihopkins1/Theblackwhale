(function () {
  const isFileProtocol = window.location.protocol === 'file:';
  const isGitHubPages = window.location.hostname.endsWith('github.io');
  const isLocalPreviewHost =
    (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') &&
    window.location.port === '3000';
  const isPreviewContext = isFileProtocol || isLocalPreviewHost;
  const shouldRewriteRootRelative = isPreviewContext || isGitHubPages;
  const githubPagesPathPrefix = (function () {
    if (!isGitHubPages) {
      return '';
    }

    const segments = window.location.pathname.split('/').filter(Boolean);
    if (segments.length > 0 && !segments[0].includes('.')) {
      return '/' + segments[0];
    }

    return '';
  })();
  const defaultBackendBase = 'http://127.0.0.1:5000';
  var configuredBackendBase = window.APP_BACKEND_BASE;
  try { configuredBackendBase = configuredBackendBase || localStorage.getItem('APP_BACKEND_BASE'); } catch(e) {}
  const appBase = isPreviewContext ? (configuredBackendBase || defaultBackendBase) : '';
  const githubPagesRouteMap = {
    '/': '/templates/storepage.html',
    '/about': '/templates/about.html',
    '/inventory': '/templates/inventory.html',
    '/seller': '/templates/seller.html',
    '/admin': '/templates/admin.html',
    '/itemeditor': '/templates/itemeditor.html',
    '/sign-in': '/templates/sign-in.html',
    '/register': '/templates/CreateAccount.html',
    '/login': '/templates/login.html',
    '/logout': '/templates/storepage.html'
  };

  function appUrl(path) {
    if (!path) {
      return path;
    }

    if (/^(https?:)?\/\//i.test(path) || path.startsWith('#') || path.startsWith('mailto:') || path.startsWith('tel:')) {
      return path;
    }

    if (isGitHubPages && path.startsWith('/')) {
      const mappedPath = githubPagesRouteMap[path] || path;
      return githubPagesPathPrefix + mappedPath;
    }

    if (path.startsWith('/')) {
      return appBase + path;
    }

    return path;
  }

  window.appUrl = appUrl;

  if (!shouldRewriteRootRelative) {
    return;
  }

  function rewriteRootRelativeAttributes() {
    const selectors = [
      'a[href^="/"]',
      'link[href^="/"]',
      'script[src^="/"]',
      'img[src^="/"]',
      'source[src^="/"]',
      'video[poster^="/"]',
      'form[action^="/"]'
    ];

    document.querySelectorAll(selectors.join(',')).forEach((element) => {
      if (element.hasAttribute('href')) {
        element.setAttribute('href', appUrl(element.getAttribute('href')));
      }

      if (element.hasAttribute('src')) {
        element.setAttribute('src', appUrl(element.getAttribute('src')));
      }

      if (element.hasAttribute('poster')) {
        element.setAttribute('poster', appUrl(element.getAttribute('poster')));
      }

      if (element.hasAttribute('action')) {
        element.setAttribute('action', appUrl(element.getAttribute('action')));
      }
    });
  }

  rewriteRootRelativeAttributes();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', rewriteRootRelativeAttributes);
  }
})();
