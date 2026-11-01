import ipaddress
import socket
from urllib.parse import urlparse


class URLValidationError(Exception):
    """Raised when a submitted URL fails security validation."""
    pass


# IP ranges that should never be scanned.
# These are internal/private networks that a public-facing
# testing tool should not be able to reach.
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

ALLOWED_SCHEMES = {"http", "https"}


def validate_url(url: str) -> str:
    """
    Validate that a URL is safe to scan.

    Checks:
    1. Scheme is http or https
    2. Hostname exists and is not empty
    3. Hostname does not resolve to a private/internal IP

    Returns the validated URL string.
    Raises URLValidationError if the URL is unsafe.
    """

    # ── 1. Parse and check scheme ──
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise URLValidationError(
            f"URL scheme '{parsed.scheme}' is not allowed. "
            f"Only http and https are supported."
        )

    # ── 2. Check hostname exists ──
    hostname = parsed.hostname

    if not hostname:
        raise URLValidationError(
            "URL must include a valid hostname."
        )

    # ── 3. Resolve hostname and check IP ──
    try:
        resolved_ip = socket.getaddrinfo(
            hostname, None, socket.AF_UNSPEC
        )[0][4][0]
    except socket.gaierror:
        raise URLValidationError(
            f"Could not resolve hostname: {hostname}"
        )

    ip = ipaddress.ip_address(resolved_ip)

    for network in BLOCKED_NETWORKS:
        if ip in network:
            raise URLValidationError(
                "URL resolves to a blocked internal address. "
                "Scanning private networks is not allowed."
            )

    return url

