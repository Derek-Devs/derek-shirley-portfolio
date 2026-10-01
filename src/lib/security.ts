const cloudfront = "https://d3fuhsnkvtfott.cloudfront.net";

export function contentSecurityPolicy(dev: boolean) {
  const connect = dev
    ? `'self' ${cloudfront} ws: wss:`
    : `'self' ${cloudfront}`;
  const script = dev ? `'self' 'unsafe-inline' 'unsafe-eval'` : `'self'`;
  const style = dev ? `'self' 'unsafe-inline'` : `'self'`;

  return [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    `script-src ${script}`,
    `style-src ${style}`,
    "style-src-attr 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src ${connect}`,
    "worker-src 'self'",
    "manifest-src 'self'",
    dev ? "" : "upgrade-insecure-requests",
  ]
    .filter(Boolean)
    .join("; ");
}

export function securityHeaders(dev: boolean) {
  const headers: Record<string, string> = {
    "Content-Security-Policy": contentSecurityPolicy(dev),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy":
      "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
  };

  if (!dev) {
    headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains";
  }

  return headers;
}
