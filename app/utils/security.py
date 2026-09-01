from flask import Response, current_app


def apply_security_headers(response: Response) -> Response:
    """
    Applies security headers to every HTTP response following OWASP recommendations:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: SAMEORIGIN (prevents clickjacking)
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy (CSP)
    - Strict-Transport-Security (HSTS) in production
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

    # Content Security Policy
    # Allows scripts/styles from self and trusted CDNs (like Google Fonts, Feather/FontAwesome icons)
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:",
        "img-src 'self' data: blob:",
        "connect-src 'self'",
        "frame-ancestors 'self'",
        "base-uri 'self'",
        "form-action 'self'"
    ]
    response.headers['Content-Security-Policy'] = "; ".join(csp_directives)

    # Enable HSTS only if configured for HTTPS / production
    if current_app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    return response
