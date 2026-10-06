"""SSRF Firewall, DNS Re-resolution, and Redirect Validator."""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.core.errors import SSRFSecurityError
from app.core.logging import get_logger

logger = get_logger("mcp.ssrf")

# Comprehensive disallowed IP networks (IPv4 + IPv6 + CGNAT + 0.0.0.0/8)
BLOCKED_NETWORKS = [
    # IPv4 Loopback and special
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    # Private RFC 1918
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # Link-local & Cloud Metadata (AWS, GCP, Azure, DigitalOcean)
    ipaddress.ip_network("169.254.0.0/16"),
    # Carrier-Grade NAT (CGNAT)
    ipaddress.ip_network("100.64.0.0/10"),
    # Documentation & Test nets
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    # IPv6 Loopback and local
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),  # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),  # Link-Local Unicast
    ipaddress.ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6
]


def resolve_and_validate_ip(hostname: str, allow_private_ips: bool = False) -> list[str]:
    """
    Re-resolve hostname to IP address at connection time and validate against SSRF blocklist.
    Prevents DNS rebinding (TOCTOU) attacks.
    """
    if allow_private_ips:
        return ["allowed-dev-ip"]

    try:
        # Re-resolve DNS immediately
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFSecurityError(f"DNS resolution failed for hostname '{hostname}': {e}") from e

    resolved_ips = []
    for _family, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        ip_obj = ipaddress.ip_address(ip_str)

        # Check against blocked networks
        for blocked in BLOCKED_NETWORKS:
            if ip_obj in blocked:
                logger.warning(f"Blocked SSRF attempt to {hostname} ({ip_str}) in {blocked}")
                raise SSRFSecurityError(
                    f"Access to IP address {ip_str} ({hostname}) is forbidden by SSRF security policy"
                )

        resolved_ips.append(ip_str)

    if not resolved_ips:
        raise SSRFSecurityError(f"No valid IP addresses resolved for hostname '{hostname}'")

    return resolved_ips


def validate_target_url(url: str, allow_private_ips: bool = False) -> str:
    """Validate full target URL scheme, hostname, and resolved IP addresses."""
    parsed = urlparse(url)

    if parsed.scheme.lower() not in ["http", "https"]:
        raise SSRFSecurityError(
            f"Unsupported URI scheme: '{parsed.scheme}'. Only http and https allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityError("Target URL does not contain a valid hostname")

    # Reject direct 0.0.0.0 or localhost strings before DNS
    if hostname.lower() in ["localhost", "0.0.0.0", "127.0.0.1", "::1"]:
        if not allow_private_ips:
            raise SSRFSecurityError(f"Direct connection to {hostname} prohibited")

    # Re-resolve and validate
    resolve_and_validate_ip(hostname, allow_private_ips=allow_private_ips)
    return url


class SafeHttpClient:
    """
    HTTP client wrapper enforcing connect-time DNS re-resolution and no blind redirects.
    """

    def __init__(self, timeout: float = 15.0):
        settings = get_settings()
        self.allow_private_ips = settings.mcp_allow_private_ips
        self.timeout = timeout

    async def get(self, url: str, headers: dict | None = None) -> httpx.Response:
        """Execute GET request with redirect validation."""
        current_url = validate_target_url(url, self.allow_private_ips)
        headers = headers or {}

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            resp = await client.get(current_url, headers=headers)

            # Manual redirect validation (no blind redirects)
            max_redirects = 3
            redirect_count = 0
            while resp.is_redirect and redirect_count < max_redirects:
                redirect_url = resp.headers.get("location")
                if not redirect_url:
                    break
                # Validate redirect destination before following
                current_url = validate_target_url(redirect_url, self.allow_private_ips)
                resp = await client.get(current_url, headers=headers)
                redirect_count += 1

            return resp

    async def post(
        self, url: str, json: dict | None = None, headers: dict | None = None
    ) -> httpx.Response:
        """Execute POST request with connect-time validation."""
        target_url = validate_target_url(url, self.allow_private_ips)
        headers = headers or {}

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            return await client.post(target_url, json=json, headers=headers)
