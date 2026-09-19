"""Procurement-specific DRF permissions.

The project does not yet expose an API credential (token/session) flow
to the React client: login is Google-OAuth only and does not issue API
credentials. Setting a project-wide ``DEFAULT_PERMISSION_CLASSES`` would
therefore affect unrelated modules, which is out of scope, so the
protection is deliberately scoped to Procurement only.

Effect:
  * Safe methods (GET/HEAD/OPTIONS) stay open. Reads are still confined
    to a single hospital by object-level scoping, so they never leak
    another hospital's records.
  * Unsafe methods (POST/PUT/PATCH/DELETE), including the stock-mutating
    GRN ``receive`` action, require an authenticated user.

Limitation (reported, not silently ignored): because no API credentials
are issued yet, writes require a Django-authenticated session (for
example the DRF browsable API or Django admin). When a project-wide
token authentication is introduced, replace this class with the shared
permission.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsProcurementWriteAuthenticated(BasePermission):
    """Allow reads; require authentication for any write."""

    message = "Authentication is required to modify procurement records."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
