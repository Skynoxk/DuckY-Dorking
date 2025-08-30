from urllib.parse import urlunparse, urlparse, parse_qsl, urlencode

def normalize_url(url: str) -> str:
    """
    Canonicalize URL for better de-duplication:
    - lowercase scheme/host
    - strip default ports
    - remove fragment
    - remove trailing slash on non-root paths
    - sort query parameters
    """
    p = urlparse(url)
    scheme = (p.scheme or 'http').lower()
    host = (p.hostname or '').lower()

    # Handle default ports
    port = p.port
    if port and not ((scheme == 'http' and port == 80) or (scheme == 'https' and port == 443)):
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = p.path or '/'
    if len(path) > 1 and path.endswith('/'):
        path = path.rstrip('/')

    query = p.query
    if query:
        qsl = sorted(parse_qsl(query, keep_blank_values=True))
        query = urlencode(qsl, doseq=True)

    return urlunparse((scheme, netloc, path, '', query, ''))