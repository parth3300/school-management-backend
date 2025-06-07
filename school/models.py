import random
import string
from django.db import models
from django.conf import settings
from django.utils import timezone
from cloudinary.models import CloudinaryField
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password, check_password


def generate_custom_uuid(length=12):
    """Generate a custom alphanumeric ID of specified length."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))


class BaseModel(models.Model):
    """Abstract base model with common fields for all models."""
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_updated"
    )

    class Meta:
        abstract = True


class School(BaseModel):
    """Model representing a school."""
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    established_date = models.DateField()
    logo = CloudinaryField('image', null=True, blank=True)

    general_password = models.CharField(max_length=255)  # New field for school password

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.general_password and not self.general_password.startswith("pbkdf2_"):
            self.general_password = make_password(self.general_password)
        super().save(*args, **kwargs)

    def check_general_password(self, raw_password):
        return check_password(raw_password, self.general_password)

class AcademicYear(BaseModel):
    """Model representing an academic year."""
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.school})"


class Subject(BaseModel):
    """Model representing a subject."""
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'school')

        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                condition=models.Q(is_active= True, is_deleted = False),
                name='code'
            )
        ]
        
    def __str__(self):
        return f"{self.name} ({self.school})"


class Class(BaseModel):
    """Model representing a class/grade level."""
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    name = models.CharField(max_length=50)
    teachers = models.ManyToManyField('Teacher', blank=True, related_name='classes')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    capacity = models.PositiveIntegerField(default=30)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Classes"
        unique_together = ('name', 'academic_year', 'school')

    def __str__(self):
        return f"{self.name} ({self.academic_year}) - {self.school}"


class Teacher(BaseModel):
    """Model representing a teacher."""
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joining_date = models.DateField()
    qualification = models.CharField(max_length=100)
    subjects = models.ManyToManyField(Subject, blank=True, related_name='teachers')
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.school})"


class Student(BaseModel):
    """Model representing a student."""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    admission_number = models.CharField(max_length=20, unique=True)
    parent_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=20)
    admission_date = models.DateField()
    current_class = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('admission_number', 'school')

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.admission_number}) - {self.school}"


class StudentAttendance(BaseModel):
    """Model representing student attendance records."""
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Late'),
    ]

    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    remarks = models.CharField(max_length=100, blank=True, null=True)
    recorded_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('student', 'date')
        verbose_name = 'Student Attendance'
        verbose_name_plural = 'Student Attendances'

    def __str__(self):
        return f"{self.student} - {self.date} - {self.get_status_display()} - {self.school}"
    

class TeacherAttendance(BaseModel):
    """Model representing teacher attendance records."""
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Late'),
        ('CL', 'On Leave'),
        ('V', 'On Vacation'),
    ]

    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    remarks = models.CharField(max_length=100, blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_teacher_attendances'
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('teacher', 'date')
        verbose_name = 'Teacher Attendance'
        verbose_name_plural = 'Teacher Attendances'

    def __str__(self):
        return f"{self.teacher} - {self.date} - {self.get_status_display()} - {self.school}"


class Exam(BaseModel):
    """Model representing an exam."""
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    name = models.CharField(max_length=100)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'academic_year', 'school')

    def __str__(self):
        return f"{self.name} ({self.academic_year}) - {self.school}"


class ExamResult(BaseModel):
    """Model representing exam results for students."""
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2)
    remarks = models.CharField(max_length=100, blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('student', 'exam', 'subject')

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.subject}: {self.marks} - {self.school}"


class Announcement(BaseModel):
    """Model representing announcements."""
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
    
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default='M')
    audience = models.CharField(max_length=3, choices=AUDIENCE_CHOICES, default='ALL')
    
    # Relationships
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
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
        return f"{self.title} ({self.get_priority_display()}) - {self.school}"
    
    @property
    def is_active(self):
        """Check if the announcement is currently active."""
        now = timezone.now()
        if self.end_date:
            return self.start_date <= now <= self.end_date
        return self.start_date <= now
    
    def save(self, *args, **kwargs):
        """Set default academic year if not provided."""
        if not self.academic_year:
            self.academic_year = AcademicYear.objects.filter(
                is_current=True, 
                school=self.school
            ).first()
        super().save(*args, **kwargs)


class ClassSchedule(BaseModel):
    """Model representing class schedules/timetables."""
    id = models.CharField(
        primary_key=True,
        default=generate_custom_uuid,
        editable=False,
        max_length=12,
        unique=True
    )
    class_instance = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50, blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('class_instance', 'subject', 'date', 'start_time')

    def __str__(self):
        return (
            f"{self.class_instance.name} - {self.subject.name} "
            f"on {self.date} ({self.start_time}-{self.end_time}) - {self.school}"
        )


@receiver(post_delete, sender=Teacher)
def delete_user_when_teacher_deleted(sender, instance, **kwargs):
    """Delete associated user when a teacher is deleted."""
    if instance.user:
        instance.user.delete()


@receiver(post_delete, sender=Student)
def delete_user_when_student_deleted(sender, instance, **kwargs):
    """Delete associated user when a student is deleted."""
    if instance.user:
        instance.user.delete()