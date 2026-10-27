"""
The address of the client that sent a request.

X-Forwarded-For is written by whoever sends the request, so its leftmost
entries can be anything. nginx appends the address it saw
($proxy_add_x_forwarded_for), so with N trusted proxies in front of Django
the real client is the Nth entry from the right. This mirrors Django REST
framework's NUM_PROXIES handling; both read TRUSTED_PROXY_COUNT.
"""

from django.conf import settings


def client_ip(request):
    meta = getattr(request, "META", {}) or {}
    remote = meta.get("REMOTE_ADDR") or None
    trusted = int(getattr(settings, "TRUSTED_PROXY_COUNT", 0) or 0)
    forwarded = meta.get("HTTP_X_FORWARDED_FOR")
    if trusted <= 0 or not forwarded:
        return remote
    entries = [part.strip() for part in forwarded.split(",") if part.strip()]
    if not entries:
        return remote
    return entries[-min(trusted, len(entries))]
