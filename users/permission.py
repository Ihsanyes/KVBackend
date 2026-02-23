from rest_framework.permissions import BasePermission
from .models import ModulePermission

class HasModulePermission(BasePermission):

    def has_permission(self, request, view):
        if request.user.is_superuser or request.user.role == 'admin':
            return True

        required_module = getattr(view, 'required_module', None)
        if not required_module:
            return True

        has_perm = request.user.module_permissions.filter(
            module_name__in=required_module
        ).exists()

        if not has_perm:
            self.message = "You don't have permission for this module"

        return has_perm
    

class IsAdminOrSuperUser(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_superuser or request.user.role == 'admin'