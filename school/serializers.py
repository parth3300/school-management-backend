import random
import string
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    School, AcademicYear, Class, Subject, Teacher,
    Student, StudentAttendance, Exam, ExamResult, Announcement, ClassSchedule
)
from .teacher_utils import get_teacher_upcoming_classes, get_teacher_attendance_stats

User = get_user_model()

class BaseModelSerializer(serializers.ModelSerializer):
    """Base serializer with common fields for all models"""
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}
        
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.method != 'POST':
            fields.pop('password', None)
        return fields

class SchoolSerializer(BaseModelSerializer):
    general_password = serializers.CharField(write_only=True, required=False)
    logo = serializers.ImageField(required=False)  # Handles uploads

    class Meta:
        model = School
        fields = '__all__'

class BasicSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code']
        
class SubjectSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    class Meta:
        model = Subject
        fields = '__all__'
        
class AcademicYearSerializer(BaseModelSerializer):
    school = SchoolSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(),
        source='school',
        write_only=True
    )

    class Meta:
        model = AcademicYear
        fields = '__all__'

class TeacherSerializer(BaseModelSerializer):
    user = UserSerializer()
    subjects = serializers.SerializerMethodField()
    subject_ids = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.filter(is_active=True, is_deleted = False),
        source='subjects',
        many=True,
        write_only=True
    )

    class Meta:
        model = Teacher
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If it's an update (partial or full), remove the user field
        request = self.context.get('request', None)
        if request and request.method in ['PUT', 'PATCH']:
            self.fields.pop('user', None)


    def get_subjects(self, obj):
        filtered_subjects = obj.subjects.filter(is_active=True, is_deleted=False)
        return BasicSubjectSerializer(filtered_subjects, many=True).data
    
    def create(self, validated_data):

        user_data = validated_data.pop('user')
        subjects = validated_data.pop('subjects', [])
        user = User.objects.create_user(**user_data)
        teacher = Teacher.objects.create(user=user, **validated_data)
        teacher.subjects.set(subjects)
        return teacher
    def update(self, instance, validated_data):
        print("in updation")
        user_data = validated_data.pop('user', None)
        subjects = validated_data.pop('subjects', [])

        # Update user data manually if provided
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        # Update other teacher fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if subjects is not None:
            instance.subjects.set(subjects)

        return instance

class BasicClassSerializer(serializers.ModelSerializer):
    academic_year = serializers.StringRelatedField()
    
    class Meta:
        model = Class
        fields = ['id', 'name', 'academic_year', 'capacity']

class ClassSerializer(BaseModelSerializer):
    academic_year = AcademicYearSerializer(read_only=True)
    academic_year_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all(),
        source='academic_year',
        write_only=True
    )
    teachers = TeacherSerializer(read_only=True, many=True)
    teacher_ids = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teachers',
        many=True,
        write_only=True
    )

    class Meta:
        model = Class
        fields = '__all__'

class BasicStudentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Student
        fields = ['id', 'user', 'admission_number', 'current_class']

class StudentSerializer(BaseModelSerializer):
    user = UserSerializer()
    current_class = ClassSerializer(read_only=True)
    current_class_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source='current_class',
        write_only=True,
        allow_null=True
    )

    class Meta:
        model = Student
        fields = '__all__'
        extra_kwargs = {'admission_number': {'required': False, 'allow_null': True}}

    def create(self, validated_data):
        if 'admission_number' not in validated_data or not validated_data['admission_number']:
            validated_data['admission_number'] = self.generate_admission_number(validated_data)
        user_data = validated_data.pop('user')
        user = User.objects.create_user(**user_data)
        return Student.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def generate_admission_number(self, validated_data):
        try:
            current_class = validated_data.get('current_class')
            if not current_class:
                raise serializers.ValidationError("Class is required for admission number generation")

            school = current_class.academic_year.school
            if not school:
                raise serializers.ValidationError("School not found for the given class")

            user_data = validated_data.get('user', {})
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')

            school_initials = ''.join([word[0].upper() for word in school.name.split()])
            current_year = str(datetime.now().year)
            student_initials = f"{first_name[0].upper() if first_name else 'X'}{last_name[0].upper() if last_name else 'X'}"
            class_name = current_class.name
            admission_number = f"{school_initials}-{current_year}-{student_initials}-{class_name}"

            counter = 1
            original_admission_number = admission_number
            while Student.objects.filter(admission_number=admission_number).exists():
                admission_number = f"{original_admission_number}-{counter}"
                counter += 1

            return admission_number
        except Exception as e:
            raise serializers.ValidationError(f"Error generating admission number: {str(e)}")


class StudentAttendanceSerializer(BaseModelSerializer):
    student = BasicStudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(),
        source='student',
        write_only=True
    )
    recorded_by = TeacherSerializer(read_only=True)
    recorded_by_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='recorded_by',
        write_only=True,
        allow_null=True
    )

    class Meta:
        model = StudentAttendance
        fields = '__all__'

class AttendanceStatsSerializer(serializers.Serializer):
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    on_leave = serializers.IntegerField(required=False)
    vacation = serializers.IntegerField(required=False)
    total = serializers.IntegerField()

class AttendanceByDateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    class_name = serializers.CharField(source='student.current_class.name', read_only=True, allow_null=True)
    recorded_by_name = serializers.CharField(source='recorded_by.user.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = StudentAttendance
        fields = [
            'id',
            'student',
            'student_name',
            'class_name',
            'date',
            'status',
            'remarks',
            'recorded_by',
            'recorded_by_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
     

class ClassAttendanceStatsSerializer(serializers.Serializer):
    class_id = serializers.CharField()
    class_name = serializers.CharField()
    date = serializers.DateField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    total_students = serializers.IntegerField()
       
class ExamSerializer(BaseModelSerializer):
    academic_year = AcademicYearSerializer(read_only=True)
    academic_year_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all(),
        source='academic_year',
        write_only=True
    )

    class Meta:
        model = Exam
        fields = '__all__'

class ExamResultSerializer(BaseModelSerializer):
    student = BasicStudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(),
        source='student',
        write_only=True
    )
    exam = ExamSerializer(read_only=True)
    exam_id = serializers.PrimaryKeyRelatedField(
        queryset=Exam.objects.all(),
        source='exam',
        write_only=True
    )
    subject = BasicSubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subject',
        write_only=True
    )

    class Meta:
        model = ExamResult
        fields = '__all__'

class ExamResultStudentSummarySerializer(serializers.Serializer):
    exam_name = serializers.CharField()
    subject_name = serializers.CharField()
    marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    grade = serializers.CharField()
    class_average = serializers.DecimalField(max_digits=6, decimal_places=2)
    class_rank = serializers.IntegerField(allow_null=True)

class ExamResultClassSummarySerializer(serializers.Serializer):
    subject_name = serializers.CharField()
    average_marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    highest_marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    lowest_marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    pass_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

class AnnouncementSerializer(BaseModelSerializer):
    start_date = serializers.DateTimeField(format="%B %d, %Y, %I:%M %p")
    end_date = serializers.DateTimeField(format="%B %d, %Y, %I:%M %p", allow_null=True)
    school = SchoolSerializer(read_only=True)
    academic_year = AcademicYearSerializer(read_only=True)
    classes = ClassSerializer(many=True, read_only=True)
    subjects = BasicSubjectSerializer(many=True, read_only=True)
    created_by = TeacherSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(),
        source='school',
        write_only=True
    )
    academic_year_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all(),
        source='academic_year',
        write_only=True,
        allow_null=True
    )
    class_ids = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source='classes',
        many=True,
        write_only=True,
        required=False
    )
    subject_ids = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subjects',
        many=True,
        write_only=True,
        required=False
    )
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='created_by',
        write_only=True
    )

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'message', 'start_date', 'end_date', 'priority', 'audience',
            'is_pinned', 'attachment', 'is_active', 'is_deleted', 'created_at', 'updated_at',
            'created_by', 'created_by_id', 'school', 'school_id', 'academic_year', 
            'academic_year_id', 'classes', 'class_ids', 'subjects', 'subject_ids'
        ]
        read_only_fields = ['is_active']

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if end_date and end_date < start_date:
            raise serializers.ValidationError("End date must be after start date")
        return data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['priority_display'] = instance.get_priority_display()
        representation['audience_display'] = instance.get_audience_display()
        return representation

class AnnouncementActiveSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'message', 'start_date', 'end_date',
            'priority', 'audience', 'is_pinned', 'attachment', 'is_active'
        ]

    def get_is_active(self, obj):
        now = timezone.now()
        return obj.start_date <= now and (obj.end_date is None or obj.end_date >= now)


class ClassScheduleSerializer(BaseModelSerializer):
    class_instance = ClassSerializer(read_only=True)
    class_instance_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source='class_instance',
        write_only=True
    )
    subject = BasicSubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subject',
        write_only=True
    )
    teacher = TeacherSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='teacher',
        write_only=True
    )

    class Meta:
        model = ClassSchedule
        fields = '__all__'

# ========== SPECIALIZED SERIALIZERS ==========

class SchoolStatsSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_teachers = serializers.IntegerField()
    total_classes = serializers.IntegerField()
    total_subjects = serializers.IntegerField()

class SchoolStaffSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ['id', 'name', 'email', 'qualification', 'joining_date']

    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    def get_email(self, obj):
        return obj.user.email

class SchoolLogoUploadSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(required=False)  # Handles uploads

    class Meta:
        model = School
        fields = ['logo','id']

    def update(self, instance, validated_data):
        logo_file = validated_data.pop('logo')
        print("loggggggg",logo_file, instance   )
        instance.logo = logo_file  # This will trigger Cloudinary upload
        instance.save()
        return instance
    
class AcademicYearCurrentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current']

class SubjectCurriculumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'description']

class SubjectTeacherSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ['id', 'teacher_name', 'qualification']

    def get_teacher_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

class SubjectClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ['id', 'name']

class ClassStudentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['id', 'admission_number', 'student_name', 'current_class']

    def get_student_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

class ClassTeacherSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ['id', 'teacher_name', 'qualification']

    def get_teacher_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

class ClassScheduleDetailSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name')
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = ClassSchedule
        fields = ['id', 'date', 'start_time', 'end_time', 'room', 'subject_name', 'teacher_name']

    def get_teacher_name(self, obj):
        return f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}"


class BasicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']

class BasicSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code']

class BasicClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ['id', 'name', 'academic_year']

class BasicStudentSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer()
    
    class Meta:
        model = Student
        fields = ['id', 'user', 'admission_number', 'current_class']

class StudentAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAttendance
        fields = ['id', 'date', 'status', 'remarks']

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'start_date', 'priority']

# Main Teacher serializers
class TeacherProfileSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer()
    subjects = BasicSubjectSerializer(many=True)
    classes = BasicClassSerializer(many=True)
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Teacher
        fields = [
            'id', 'user', 'phone', 'address', 'date_of_birth',
            'joining_date', 'qualification', 'subjects', 'classes',
            'photo', 'photo_url'
        ]
        extra_kwargs = {'photo': {'write_only': True}}
    
    def get_photo_url(self, obj):
        return obj.photo.url if obj.photo else None

class TeacherClassDetailSerializer(serializers.ModelSerializer):
    academic_year = serializers.StringRelatedField()
    subjects = BasicSubjectSerializer(many=True)
    students = serializers.SerializerMethodField()
    attendance_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Class
        fields = [
            'id', 'name', 'academic_year', 'capacity',
            'subjects', 'students', 'attendance_stats'
        ]
    
    def get_students(self, obj):
        students = obj.student_set.filter(is_active=True, is_deleted=False)
        return BasicStudentSerializer(students, many=True).data
    
    def get_attendance_stats(self, obj):
        today = timezone.now().date()
        attendance = StudentAttendance.objects.filter(
            student__current_class=obj,
            date=today
        ).values('status').annotate(count=Count('status'))
        
        stats = {item['status']: item['count'] for item in attendance}
        total = sum(stats.values())
        
        return {
            'present': stats.get('P', 0),
            'absent': stats.get('A', 0),
            'late': stats.get('L', 0),
            'total': total,
            'attendance_rate': round((stats.get('P', 0) / total * 100, 2) if total > 0 else 0)
        }

class TeacherStudentDetailSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer()
    current_class = BasicClassSerializer()
    parent_info = serializers.SerializerMethodField()
    attendance_history = serializers.SerializerMethodField()
    exam_results = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'user', 'admission_number', 'current_class',
            'date_of_birth', 'gender', 'address', 'phone',
            'parent_info', 'attendance_history', 'exam_results',
            'photo'
        ]
    
    def get_parent_info(self, obj):
        return {'name': obj.parent_name, 'phone': obj.parent_phone}
    
    def get_attendance_history(self, obj):
        last_month = timezone.now() - timedelta(days=30)
        attendance = StudentAttendance.objects.filter(
            student=obj,
            date__gte=last_month
        ).order_by('-date')[:10]
        return StudentAttendanceSerializer(attendance, many=True).data
    
    def get_exam_results(self, obj):
        results = ExamResult.objects.filter(student=obj).select_related('exam', 'subject').order_by('-exam__start_date')
        return ExamResultSerializer(results, many=True).data

class TeacherAttendanceSerializer(serializers.ModelSerializer):
    student = BasicStudentSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.filter(is_active=True, is_deleted=False),
        source='student',
        write_only=True
    )
    
    class Meta:
        model = StudentAttendance
        fields = ['id', 'student', 'student_id', 'date', 'status', 'remarks', 'recorded_by']
        read_only_fields = ['recorded_by']
    
    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user.teacher
        return super().create(validated_data)

class TeacherBulkAttendanceSerializer(serializers.Serializer):
    date = serializers.DateField()
    attendance_data = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField(), allow_empty=False)
    )
    
    def validate(self, data):
        for record in data['attendance_data']:
            if 'student_id' not in record or 'status' not in record:
                raise serializers.ValidationError("Each record must contain student_id and status")
            if record['status'] not in ['P', 'A', 'L']:
                raise serializers.ValidationError("Status must be P (Present), A (Absent), or L (Late)")
        return data
    
    def create(self, validated_data):
        teacher = self.context['request'].user.teacher
        date = validated_data['date']
        attendance_data = validated_data['attendance_data']
        
        created = []
        for record in attendance_data:
            attendance, _ = StudentAttendance.objects.update_or_create(
                student_id=record['student_id'],
                date=date,
                defaults={
                    'status': record['status'],
                    'remarks': record.get('remarks', ''),
                    'recorded_by': teacher
                }
            )
            created.append(attendance)
        
        return {'date': date, 'count': len(created)}

class TeacherDashboardSerializer(serializers.Serializer):
    upcoming_classes = serializers.SerializerMethodField()
    recent_attendance = serializers.SerializerMethodField()
    pending_grades = serializers.SerializerMethodField()
    important_announcements = serializers.SerializerMethodField()
    performance_analytics = serializers.SerializerMethodField()
    
    def get_upcoming_classes(self, obj):
        now = timezone.now()
        return ClassSchedule.objects.filter(
            teacher=obj,
            date__gte=now.date(),
            start_time__gte=now.time()
        ).order_by('date', 'start_time')[:5]
    
    def get_recent_attendance(self, obj):
        today = timezone.now().date()
        classes = obj.classes.all()
        
        stats = []
        for class_obj in classes:
            attendance = StudentAttendance.objects.filter(
                student__current_class=class_obj,
                date=today
            ).values('status').annotate(count=Count('status'))
            
            status_counts = {item['status']: item['count'] for item in attendance}
            total = sum(status_counts.values())
            
            stats.append({
                'class_id': class_obj.id,
                'class_name': class_obj.name,
                'present': status_counts.get('P', 0),
                'absent': status_counts.get('A', 0),
                'late': status_counts.get('L', 0),
                'total': total,
                'attendance_rate': round((status_counts.get('P', 0) / total * 100, 2) if total > 0 else 0)
            })
        
        return stats
    
    def get_pending_grades(self, obj):
        exams = Exam.objects.filter(
            end_date__lte=timezone.now(),
            examresult__isnull=True,
            subjects__in=obj.subjects.all()
        ).distinct()
        return [{'id': exam.id, 'name': exam.name} for exam in exams]
    
    def get_important_announcements(self, obj):
        announcements = Announcement.objects.filter(
            Q(audience='TEA') | Q(classes__in=obj.classes.all()),
            is_pinned=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).distinct()[:3]
        return AnnouncementSerializer(announcements, many=True).data
    
    def get_performance_analytics(self, obj):
        subjects = obj.subjects.annotate(
            avg_marks=Avg('examresult__marks'),
            pass_rate=Count(
                'examresult',
                filter=Q(examresult__grade__in=['A', 'B', 'C']),
                distinct=True
            ) / Count('examresult') * 100 if Count('examresult') > 0 else 0
        )
        return [{
            'subject': subject.name,
            'avg_marks': subject.avg_marks,
            'pass_rate': subject.pass_rate
        } for subject in subjects]

class TeacherExamResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = ExamResult
        fields = [
            'id',
            'student',
            'student_name',
            'exam',
            'exam_name',
            'subject',
            'subject_name',
            'marks',
            'grade',
            'remarks',
            'created_at',
            'updated_at',
            'created_by',
            'updated_by',
            'is_active',
            'is_deleted'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active', 'is_deleted']

class TeacherExamResultCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamResult
        fields = [
            'student',
            'exam',
            'subject',
            'marks',
            'grade',
            'remarks'
        ]

    def validate(self, data):
        """
        Validate that the combination of student, exam, and subject is unique.
        Also ensure marks and grade are within acceptable ranges.
        """
        student = data.get('student')
        exam = data.get('exam')
        subject = data.get('subject')

        # Check for unique_together constraint
        if self.instance:
            # For updates, exclude the current instance
            if ExamResult.objects.filter(
                student=student,
                exam=exam,
                subject=subject
            ).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    "An exam result for this student, exam, and subject already exists."
                )
        else:
            # For creation
            if ExamResult.objects.filter(
                student=student,
                exam=exam,
                subject=subject
            ).exists():
                raise serializers.ValidationError(
                    "An exam result for this student, exam, and subject already exists."
                )

        # Validate marks
        marks = data.get('marks')
        if marks < 0 or marks > 100:
            raise serializers.ValidationError("Marks must be between 0 and 100.")

        # Validate grade (example: assuming grades like A+, A, B, etc.)
        grade = data.get('grade')
        valid_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F']
        if grade not in valid_grades:
            raise serializers.ValidationError(f"Grade must be one of: {', '.join(valid_grades)}.")

        return data

class TeacherAttendanceStatsSerializer(serializers.Serializer):
    teacher_id = serializers.CharField()
    total_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    late_days = serializers.IntegerField()
    leave_days = serializers.IntegerField()
    vacation_days = serializers.IntegerField()

    def to_representation(self, instance):
        """Custom representation using aggregated attendance data."""
        teacher = instance['teacher']
        stats = instance['stats']

        return {
            'teacher_id': teacher.id,
            'total_days': stats.get('total', 0),
            'present_days': stats.get('P', 0),
            'absent_days': stats.get('A', 0),
            'late_days': stats.get('L', 0),
            'leave_days': stats.get('CL', 0),
            'vacation_days': stats.get('V', 0),
        }

class ClassSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ['id', 'name']


class SubjectSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']

class TeacherAnnouncementSerializer(serializers.ModelSerializer):
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    audience_display = serializers.CharField(source='get_audience_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    classes = ClassSimpleSerializer(many=True, read_only=True)
    subjects = SubjectSimpleSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Announcement
        fields = [
            'id',
            'title',
            'message',
            'start_date',
            'end_date',
            'priority',
            'priority_display',
            'audience',
            'audience_display',
            'classes',
            'subjects',
            'is_active',
            'is_pinned',
            'created_by',
            'attachment'
        ]

class NewBaseSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code']

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

class TeacherProfileUpdateSerializer(serializers.ModelSerializer):
    user = UserUpdateSerializer(required=False)
    subjects = NewBaseSubjectSerializer(many=True, read_only=True)
    subject_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Subject.objects.all(),
        source='subjects',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Teacher
        fields = [
            'id',
            'user',
            'phone',
            'address',
            'date_of_birth',
            'qualification',
            'photo',
            'subjects',
            'subject_ids',
            'joining_date'
        ]
        extra_kwargs = {
            'date_of_birth': {'required': False},
            'joining_date': {'required': False, 'read_only': True},
        }

    def update(self, instance, validated_data):
        # Update user data if provided
        user_data = validated_data.pop('user', None)
        if user_data and instance.user:
            user_serializer = UserUpdateSerializer(instance.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
        
        # Handle subjects update
        if 'subjects' in validated_data:
            instance.subjects.set(validated_data['subjects'])
            del validated_data['subjects']
        
        # Update remaining teacher fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Remove the write-only field from the response
        representation.pop('subject_ids', None)
        return representation
    
class ExamResultSummarySerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    average_score = serializers.FloatField()
    highest_score = serializers.FloatField()
    lowest_score = serializers.FloatField()
    pass_count = serializers.IntegerField()
    fail_count = serializers.IntegerField()
    grade_distribution = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField(), allow_empty=True)
    )

class ClassScheduleWeeklySerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name')
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = ClassSchedule
        fields = ['id', 'date', 'start_time', 'end_time', 'room', 'subject_name', 'teacher_name']

    def get_teacher_name(self, obj):
        return f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}"

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)