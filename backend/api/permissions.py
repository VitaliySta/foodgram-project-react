from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnlyPermission(BasePermission):
    """
    Разрешает анонимному пользователю только безопасные запросы.
    Полный доступ предоставляется только автору объекта и
    суперпользователю Джанго.
    """

    def has_object_permission(self, request, view, obj):
        return (
            request.method in SAFE_METHODS
            or obj.author == request.user
            or request.user.is_superuser
        )
