from __future__ import annotations

"""Policy for URLs that FridaDev may hand to web-reading transports."""

import ipaddress
import socket
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse


REASON_URL_BLOCKED_INTERNAL = "web_url_blocked_internal"

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "host.docker.internal",
    "gateway.docker.internal",
}
_BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".docker",
)


def blocked_url_reason(
    url: str,
    *,
    resolver: Callable[..., Any] | None = None,
) -> str:
    """Return a content-free reason when an HTTP(S) URL is not proven public."""
    try:
        normalized_url = str(url or "").strip()
        has_ambiguous_character = "\\" in normalized_url or any(
            ord(char) < 0x20 or ord(char) == 0x7F
            for char in normalized_url
        )
        if has_ambiguous_character:
            return REASON_URL_BLOCKED_INTERNAL
        parsed = urlparse(normalized_url)
        scheme = str(parsed.scheme or "").lower()
        host = str(parsed.hostname or "").strip().lower().rstrip(".")
    except (TypeError, ValueError):
        return REASON_URL_BLOCKED_INTERNAL

    if scheme not in _ALLOWED_SCHEMES or not host:
        return REASON_URL_BLOCKED_INTERNAL
    if host in _BLOCKED_HOSTS or any(
        host.endswith(suffix)
        for suffix in _BLOCKED_HOST_SUFFIXES
    ):
        return REASON_URL_BLOCKED_INTERNAL

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            return REASON_URL_BLOCKED_INTERNAL
        return _blocked_hostname_reason(host, resolver=resolver)
    return REASON_URL_BLOCKED_INTERNAL if _is_blocked_ip(address) else ""


def _blocked_hostname_reason(
    host: str,
    *,
    resolver: Callable[..., Any] | None = None,
) -> str:
    resolve = resolver or socket.getaddrinfo
    try:
        infos = resolve(host, None, type=socket.SOCK_STREAM)
    except Exception:
        return REASON_URL_BLOCKED_INTERNAL

    resolved: list[str] = []
    for info in infos or []:
        try:
            resolved.append(str(info[4][0]))
        except (IndexError, TypeError):
            continue
    if not resolved:
        return REASON_URL_BLOCKED_INTERNAL

    for value in resolved:
        try:
            if _is_blocked_ip(ipaddress.ip_address(value)):
                return REASON_URL_BLOCKED_INTERNAL
        except ValueError:
            return REASON_URL_BLOCKED_INTERNAL
    return ""


def _is_blocked_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
        or not address.is_global
    )
