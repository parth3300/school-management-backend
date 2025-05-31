from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from cloudinary.models import CloudinaryField
from django.core.exceptions import ObjectDoesNotExist

from school.models import School  # Ensure this import is correct


# Custom user manager
class UserManager(BaseUserManager):
    def create_user(self, email, school, role, name=None, password=None, is_admin=False, **extra_fields):
        """
        Creates and saves a user with the given email, name, password, and optional school.
        """
        print("Creating user with:", email, name, password, extra_fields)

        if not email:
            raise ValueError('User must have an email address')
        if not password:
            raise ValueError('User must have a password')

        # Normalize and clean data
        email = self.normalize_email(email)
        extra_fields.pop("re_password", None)  # Remove redundant field

        # Create user instance
        user = self.model(
            email=email,
            name=name,
            is_admin=is_admin,
            school=school,
            role=role,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name=None, password=None, is_admin=True, **extra_fields):
        """
        Creates and saves a superuser.
        """
        user = self.create_user(
            email=email,
            password=password,
            name=name,
            is_admin=is_admin,
            **extra_fields
        )
        user.save(using=self._db)
        return user


# Custom user model
class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('visitor', 'Visitor'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    email = models.EmailField(verbose_name='Email', max_length=255, unique=True)
    name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    photo = CloudinaryField('image', blank=True, null=True)

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='visitor')
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Required by Django
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'is_admin']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.name

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    @property
    def is_staff(self):
        return self.is_admin
