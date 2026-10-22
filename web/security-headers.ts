/**
 * The response headers the web app should be served with in production (the API sends its own, see api/main.py).
 *
 * `style-src 'unsafe-inline'` is needed because the charts and a few components set inline `style` attributes; scripts, fonts, images and
 * connections are limited to this site. The API is reached through the same origin (a reverse proxy sends /api to it), so `connect-src 'self'` is enough.
 * `vite preview` serves these headers too, and e2e/csp.spec.ts proves no page of the app breaks under them.
 */
export const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

export const SECURITY_HEADERS: Record<string, string> = {
  "Content-Security-Policy": CSP,
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "no-referrer",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
};
