from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from cloudinary.models import CloudinaryField

class UserManager(BaseUserManager):
    def create_user(self, email, name=None, password=None, is_admin=False, **extra_fields):
        """
        Creates and saves a User with the given email, name and password.
        """
        if not email:
            raise ValueError('User must have an email address')
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            name=name,
            is_admin=is_admin,
            **extra_fields  # <-- Accept other fields like first_name, last_name
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name=None, password=None, is_admin=True, **extra_fields):
        """
        Creates and saves a Superuser with the given email, name and password.
        """
        user = self.create_user(
            email=email,
            password=password,
            name=name,
            is_admin=is_admin,
            **extra_fields
        )
        user.is_admin = True
        user.save(using=self._db)
        return user

# Custom User Model.
class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('visitor', 'Visitor'),
    ]
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    photo = CloudinaryField('image', null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='visitor')
    email = models.EmailField(
        verbose_name='Email',
        max_length=255,
        unique=True,
    )
    date_of_birth = models.DateField(null=True,
        blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES,        null=True,
        blank=True)
    address = models.TextField(        null=True,
        blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    is_active=models.BooleanField(default=True)
    is_admin=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS=['name', 'is_admin']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.name

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return self.is_admin

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin
    
    