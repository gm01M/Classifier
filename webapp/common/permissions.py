"""Reusable DRF permission classes (safety rule #5 — least privilege)."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminUserRole(BasePermission):
    """Allow only staff/admin users. Used to gate all admin endpoints."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsOwnerOrAdmin(BasePermission):
    """Object-level: owners may access their own records; admins may access all."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        owner = getattr(obj, "owner_id", None)
        if request.method in SAFE_METHODS or request.method in ("PUT", "PATCH", "DELETE"):
            return owner == request.user.id
        return owner == request.user.id
