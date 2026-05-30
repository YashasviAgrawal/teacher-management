from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Allows access only to users with role = 'admin'.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsTeacher(BasePermission):
    """
    Allows access only to users with role = 'teacher'.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "teacher"
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission:
    - Admins can access any object.
    - Teachers can access only their own objects.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        # Check if the object has a 'teacher' or 'user' field that matches
        if hasattr(obj, "teacher"):
            return obj.teacher == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        # If the object IS the user
        return obj == request.user
