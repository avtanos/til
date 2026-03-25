/**
 * API base URL for TIL backend.
 * - Empty string: same origin (when running with backend locally)
 * - Set via meta tag: <meta name="til-api" content="https://your-api.example.com">
 * - Or window.TIL_API_BASE before scripts load
 */
window.TIL_API_BASE = (function () {
  const meta = document.querySelector('meta[name="til-api"]');
  if (meta && meta.content) return meta.content.replace(/\/$/, '');
  if (typeof window.TIL_API_BASE === 'string') return window.TIL_API_BASE;

  // Local dev helper:
  // When frontend is served on a different port (e.g. 5173) than backend (8000),
  // calls to "/api/..." would go to the wrong origin unless til-api is set.
  const host = window.location && window.location.hostname ? window.location.hostname : '';
  const isLocalHost =
    host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0';
  return isLocalHost ? 'http://127.0.0.1:8000' : '';
})();
