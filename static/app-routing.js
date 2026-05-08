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

  function ensureNavAuthScript() {
    if (!document.querySelector('.site-nav')) {
      return;
    }

    const navAuthAlreadyPresent =
      document.querySelector('script[src*="nav-auth.js"]') || window.__NAV_AUTH_BOOTSTRAPPED;
    if (navAuthAlreadyPresent) {
      return;
    }

    const currentScript = document.currentScript;
    let navAuthSrc = '../static/nav-auth.js';

    if (currentScript && currentScript.getAttribute('src')) {
      navAuthSrc = currentScript.getAttribute('src').replace('app-routing.js', 'nav-auth.js');
    }

    const script = document.createElement('script');
    script.src = navAuthSrc;
    script.defer = true;
    window.__NAV_AUTH_BOOTSTRAPPED = true;
    document.head.appendChild(script);
  }

  function ensureTransitionVideo() {
    const overlay = document.querySelector('.page-transition-overlay');
    if (!overlay || overlay.dataset.videoReady === '1') {
      return;
    }

    overlay.innerHTML = '';

    const video = document.createElement('video');
    video.className = 'transition-logo-video';
    video.autoplay = true;
    video.loop = true;
    video.muted = true;
    video.playsInline = true;
    video.preload = 'auto';

    const source = document.createElement('source');
    source.src = appUrl('/static/my_logo_video.mp4');
    source.type = 'video/mp4';

    video.appendChild(source);
    overlay.appendChild(video);
    overlay.dataset.videoReady = '1';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ensureNavAuthScript);
    document.addEventListener('DOMContentLoaded', ensureTransitionVideo);
  } else {
    ensureNavAuthScript();
    ensureTransitionVideo();
  }

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
