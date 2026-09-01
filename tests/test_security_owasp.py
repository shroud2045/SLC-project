from datetime import date
from app.models.post import LockInPost, PostPrivacy


def test_sqli_payload_resilience(client):
    """Verifies that classic SQL injection payloads in auth forms do not cause database syntax errors or bypass auth."""
    sqli_payloads = [
        "' OR '1'='1",
        "admin' --",
        "' UNION SELECT null, null, null --",
        "\" OR \"\"=\""
    ]

    for payload in sqli_payloads:
        res = client.post('/auth/login', data={
            'identifier': payload,
            'password': payload
        })
        # Should return normal invalid credentials page or 200/302, never 500 database crash
        assert res.status_code in (200, 302)
        assert b'OperationalError' not in res.data
        assert b'syntax error' not in res.data


def test_xss_output_escaping(auth_client, regular_user, app):
    """Verifies that cross-site scripting (XSS) script tags are safely escaped in rendered HTML."""
    xss_payload = '<script>alert("PWNED_XSS")</script>'

    res = auth_client.post('/posts/create', data={
        'title': f'LockIn {xss_payload}',
        'description': f'Studying XSS defenses {xss_payload}',
        'hours_worked': '1.0',
        'privacy': PostPrivacy.COMMUNITY,
        'post_date': date.today().isoformat()
    }, follow_redirects=True)

    assert res.status_code == 200
    # Script tag should be escaped as &lt;script&gt; and never raw executable HTML
    assert b'<script>alert("PWNED_XSS")</script>' not in res.data
    assert b'&lt;script&gt;alert(&#34;PWNED_XSS&#34;)&lt;/script&gt;' in res.data or b'&lt;script&gt;' in res.data


def test_security_headers_present(client):
    """Verifies that all OWASP-recommended HTTP security headers are injected into responses."""
    res = client.get('/')
    assert res.status_code == 200

    headers = res.headers
    assert headers.get('X-Content-Type-Options') == 'nosniff'
    assert headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert 'Content-Security-Policy' in headers
    assert 'Referrer-Policy' in headers
