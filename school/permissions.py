# permissions.py
from rest_framework import permissions

class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'teacher')

class IsTeacherForSubject(IsTeacher):
    def has_object_permission(self, request, view, obj):
        return obj.teachers.filter(user=request.user).exists()

class IsClassTeacher(IsTeacher):
    def has_object_permission(self, request, view, obj):
        return obj.teachers.filter(user=request.user).exists()