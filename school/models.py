import random
import string
from django.db import models
from django.conf import settings
from django.utils import timezone
from cloudinary.models import CloudinaryField
from django.db.models.signals import post_delete
from django.dispatch import receiver

# Custom ID generator
def generate_custom_uuid(length=12):
    characters = string.ascii_uppercase + string.digits  # A-Z and 0-9
    return ''.join(random.choices(characters, k=length))


class BaseModel(models.Model):
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="%(class)s_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="%(class)s_updated")

    class Meta:
        abstract = True

class School(BaseModel):
    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    established_date = models.DateField()
    logo = CloudinaryField('image', null=True, blank=True)

    def __str__(self):
        return self.name

class AcademicYear(BaseModel):
    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Subject(BaseModel):
    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Class(BaseModel):
    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    name = models.CharField(max_length=50)
    teachers = models.ManyToManyField('Teacher', blank=True, related_name='classes')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    capacity = models.PositiveIntegerField(default=30)

    def __str__(self):
        return f"{self.name} ({self.academic_year})"

class Teacher(BaseModel):
    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    date_of_birth = models.DateField()
    joining_date = models.DateField()
    qualification = models.CharField(max_length=100)
    subjects = models.ManyToManyField(Subject, blank=True, related_name='teachers')
    photo = CloudinaryField('image', null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Student(BaseModel):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    admission_number = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    address = models.TextField()
    phone = models.CharField(max_length=15, blank=True, null=True)
    parent_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=15)
    admission_date = models.DateField()
    current_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    photo = CloudinaryField('image', null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.admission_number})"

class Attendance(BaseModel):
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Late'),
    ]

    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    remarks = models.CharField(max_length=100, blank=True, null=True)
    recorded_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student} - {self.date} - {self.get_status_display()}"

class Exam(BaseModel):
    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    name = models.CharField(max_length=100)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.academic_year})"

class ExamResult(BaseModel):
    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2)
    remarks = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = ('student', 'exam', 'subject')

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.subject}: {self.marks}"

class Announcement(BaseModel):
    PRIORITY_CHOICES = [
        ('L', 'Low'),
        ('M', 'Medium'),
        ('H', 'High'),
        ('C', 'Critical'),
    ]
    
    AUDIENCE_CHOICES = [
        ('ALL', 'Everyone'),
        ('STU', 'Students Only'),
        ('TEA', 'Teachers Only'),
        ('CLS', 'Specific Class'),
        ('SUB', 'Subject Students'),
    ]
    
    id = models.CharField(primary_key=True, default=generate_custom_uuid, editable=False, max_length=12, unique=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default='M')
    audience = models.CharField(max_length=3, choices=AUDIENCE_CHOICES, default='ALL')
    
    # Relationships
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, null=True, blank=True)
    classes = models.ManyToManyField(Class, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    created_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    
    # Additional fields
    is_pinned = models.BooleanField(default=False)
    attachment = CloudinaryField('raw', null=True, blank=True)
    
    class Meta:
        ordering = ['-is_pinned', '-start_date']
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
    
    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"
    
    @property
    def is_active(self):
        now = timezone.now()
        if self.end_date:
            return self.start_date <= now <= self.end_date
        return self.start_date <= now
    
    def save(self, *args, **kwargs):
        # Set default academic year if not set
        if not self.academic_year:
            self.academic_year = AcademicYear.objects.filter(is_current=True).first()
        super().save(*args, **kwargs)

@receiver(post_delete, sender=Teacher)
def delete_user_when_teacher_deleted(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()

@receiver(post_delete, sender=Student)
def delete_user_when_student_deleted(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()