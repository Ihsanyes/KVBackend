from rest_framework.permissions import BasePermission
from .models import ModulePermission

class HasModulePermission(BasePermission):

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True  # Superusers have access to all modules
        
        required_module = getattr(view, 'required_module', None)
        if not required_module:
            return True  # If no specific module is required, allow access
                
        return ModulePermission.objects.filter(user=request.user, module_name=required_module).exists()