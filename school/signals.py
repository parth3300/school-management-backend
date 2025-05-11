# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Teacher, User

@receiver(post_save, sender=Teacher)
def set_teacher_permissions(sender, instance, created, **kwargs):
    if created:
        # Assign default permissions to teacher
        from django.contrib.auth.models import Permission, Group
        
        teacher_group, _ = Group.objects.get_or_create(name='Teachers')
        
        # Add permissions
        permissions = [
            'view_attendance', 'add_attendance', 'change_attendance',
            'view_examresult', 'add_examresult', 'change_examresult',
            'view_student', 
            'view_class'
        ]
        
        for perm in permissions:
            try:
                permission = Permission.objects.get(codename=perm)
                teacher_group.permissions.add(permission)
            except Permission.DoesNotExist:
                pass
        
        # Add user to group
        instance.user.groups.add(teacher_group)