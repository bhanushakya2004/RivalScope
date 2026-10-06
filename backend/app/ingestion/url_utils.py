"""URL canonicalization utilities (Stage 1 pre-fetch normalization)."""

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "ref",
    "ref_src",
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "mc_eid",
    "_hsenc",
    "_hsmi",
    "ysclid",
    "igshid",
    "s",
    "t",
}


def canonicalize_url(url: str) -> str:
    """
    Standardize a URL before fetching:
    - Strips query tracking parameters
    - Normalizes scheme to lowercase (enforces https if http)
    - Lowercases hostname and removes trailing default ports (:80, :443)
    - Strips fragments (#...)
    - Sorts query parameters deterministically
    - Strips trailing slash on non-root paths
    """
    if not url:
        return ""

    url_str = url.strip()
    # Normalize scheme
    if url_str.startswith("//"):
        url_str = "https:" + url_str
    elif not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str

    parsed = urlparse(url_str)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Normalize path
    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Filter out tracking query params and sort remainder
    query_tuples = parse_qsl(parsed.query, keep_blank_values=False)
    filtered_query = [
        (k, v)
        for k, v in query_tuples
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    filtered_query.sort(key=lambda x: (x[0], x[1]))
    clean_query = urlencode(filtered_query)

    # Reconstruct without fragment
    return urlunparse((scheme, netloc, path, "", clean_query, ""))
