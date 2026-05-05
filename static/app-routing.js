(function () {
  const isFileProtocol = window.location.protocol === 'file:';
  const isLocalPreviewHost =
    (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') &&
    window.location.port === '3000';
  const isPreviewContext = isFileProtocol || isLocalPreviewHost;
  const defaultBackendBase = 'http://127.0.0.1:5000';
  const configuredBackendBase = window.APP_BACKEND_BASE || localStorage.getItem('APP_BACKEND_BASE');
  const appBase = isPreviewContext ? (configuredBackendBase || defaultBackendBase) : '';

  function appUrl(path) {
    if (!path) {
      return path;
    }

    if (/^(https?:)?\/\//i.test(path) || path.startsWith('#') || path.startsWith('mailto:') || path.startsWith('tel:')) {
      return path;
    }

    if (path.startsWith('/')) {
      return appBase + path;
    }

    return path;
  }

  window.appUrl = appUrl;

  if (!isPreviewContext) {
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
