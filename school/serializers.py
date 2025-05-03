from rest_framework import serializers
from .models import (
    School, AcademicYear, Class, Subject, Teacher, 
    Student, Attendance, Exam, ExamResult, Announcement
)
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }
        
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        
        # Hide password field for non-POST requests
        if request and request.method != 'POST':
            fields.pop('password', None)
        
        return fields
    
class SchoolSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    class Meta:
        model = School
        fields = '__all__'

class AcademicYearSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    school = SchoolSerializer(read_only=True)
    school_id = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(),
        source='school',
        write_only=True
    )

    class Meta:
        model = AcademicYear
        fields = '__all__'

class SubjectSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    class Meta:
        model = Subject
        fields = '__all__'

class TeacherSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    user = UserSerializer()
    subjects = SubjectSerializer(many=True, read_only=True)
    subject_ids = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subjects',
        many=True,
        write_only=True
    )

    class Meta:
        model = Teacher
        fields = '__all__'

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        subjects = validated_data.pop('subjects', [])
        user = User.objects.create_user(**user_data)
        teacher = Teacher.objects.create(user=user, **validated_data)
        teacher.subjects.set(subjects)
        return teacher

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        subjects = validated_data.pop('subjects', [])

        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if subjects is not None:
            instance.subjects.set(subjects)

        return instance

class ClassSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

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

class StudentSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    admission_number = serializers.CharField(read_only=True)
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
        extra_kwargs = {
            'admission_number': {'required': False, 'allow_null': True}
        }

    def create(self, validated_data):
        # Generate admission number if not provided
        if 'admission_number' not in validated_data or not validated_data['admission_number']:
            validated_data['admission_number'] = self.generate_admission_number(validated_data)
        user_data = validated_data.pop('user')
        
        user = User.objects.create_user(**user_data)
        student = Student.objects.create(user=user, **validated_data)
        return student

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
        """
        Generates admission number in format: HS-2025-JS-8A
        Where:
        - HS: School initials (first letters of each word in school name)
        - 2025: Academic year
        - JS: Student initials (first letters of first and last name)
        - 8A: Class name
        """
        try:
            # Get the current_class instance from validated_data
            current_class = validated_data.get('current_class')
            if not current_class:
                raise serializers.ValidationError("Class is required for admission number generation")

            # Get school through the class's academic year
            school = current_class.academic_year.school
            if not school:
                raise serializers.ValidationError("School not found for the given class")

            # Get user data from validated_data
            user_data = validated_data.get('user', {})
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')

            # --- School initials ---
            school_initials = ''.join([word[0].upper() for word in school.name.split()])

            # --- Current Year ---
            current_year = str(datetime.now().year)

            # --- Student initials ---
            student_initials = f"{first_name[0].upper() if first_name else 'X'}{last_name[0].upper() if last_name else 'X'}"

            # --- Class name ---
            class_name = current_class.name

            # --- Construct Admission Number ---
            admission_number = f"{school_initials}-{current_year}-{student_initials}-{class_name}"

            # --- Uniqueness Handling ---
            counter = 1
            original_admission_number = admission_number
            while Student.objects.filter(admission_number=admission_number).exists():
                admission_number = f"{original_admission_number}-{counter}"
                counter += 1

            return admission_number

        except Exception as e:
            raise serializers.ValidationError(f"Error generating admission number: {str(e)}")

class StudentListSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    class Meta:
        model = Student
        fields = ['id', 'admission_number', 'user']

class AttendanceSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    student = StudentSerializer(read_only=True)
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
        model = Attendance
        fields = '__all__'

class ExamSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    academic_year = AcademicYearSerializer(read_only=True)
    academic_year_id = serializers.PrimaryKeyRelatedField(
        queryset=AcademicYear.objects.all(),
        source='academic_year',
        write_only=True
    )

    class Meta:
        model = Exam
        fields = '__all__'

class ExamResultSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

    student = StudentSerializer(read_only=True)
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
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        source='subject',
        write_only=True
    )

    class Meta:
        model = ExamResult
        fields = '__all__'

class AnnouncementSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    start_date = serializers.DateTimeField(format="%B %d, %Y, %I:%M %p")
    end_date = serializers.DateTimeField(format="%B %d, %Y, %I:%M %p", allow_null=True)

    # Read-only nested representations
    school = SchoolSerializer(read_only=True)
    academic_year = AcademicYearSerializer(read_only=True)
    classes = ClassSerializer(many=True, read_only=True)
    subjects = SubjectSerializer(many=True, read_only=True)
    created_by = TeacherSerializer(read_only=True)

    # Write-only ID fields
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
            'is_pinned', 'attachment', 'is_active', 'is_deleted',
            'created_at', 'updated_at', 'created_by', 'created_by_id',
            'school', 'school_id', 'academic_year', 'academic_year_id',
            'classes', 'class_ids', 'subjects', 'subject_ids'
        ]
        read_only_fields = ['is_active']

    def validate(self, data):
        """
        Validate that end_date is after start_date if provided
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if end_date and end_date < start_date:
            raise serializers.ValidationError("End date must be after start date")
        
        return data

    def to_representation(self, instance):
        """
        Custom representation to include computed fields
        """
        representation = super().to_representation(instance)
        
        # Add human-readable priority and audience
        representation['priority_display'] = instance.get_priority_display()
        representation['audience_display'] = instance.get_audience_display()
        
        return representation

class AnnouncementListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing announcements
    """
    created_by = serializers.StringRelatedField()
    priority_display = serializers.CharField(source='get_priority_display')
    audience_display = serializers.CharField(source='get_audience_display')
    start_date = serializers.DateTimeField(format="%B %d, %Y, %I:%M %p")
    end_date = serializers.DateTimeField(format="%B %d, %Y, %I:%M %p", allow_null=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'start_date', 'end_date', 'priority', 'priority_display',
            'audience', 'audience_display', 'is_pinned', 'created_by', 'created_at'
        ]
        read_only_fields = fields