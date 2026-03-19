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
  return '';
})();
