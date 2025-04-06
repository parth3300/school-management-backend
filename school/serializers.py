from rest_framework import serializers
from .models import School, AcademicYear, Class, Subject, Teacher, Student, Attendance, Exam, ExamResult
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password']

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
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        subjects = validated_data.pop('subjects', [])
        user = User.objects.create_user(**user_data)
        teacher = Teacher.objects.create(user=user, **validated_data)
        teacher.subjects.set(subjects)
        return teacher

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        subjects = validated_data.pop('subjects', None)

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
    class_teacher = TeacherSerializer(read_only=True)
    class_teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        source='class_teacher',
        write_only=True,
        allow_null=True
    )

    class Meta:
        model = Class
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")
    updated_at = serializers.DateTimeField(read_only=True, format="%B %d, %Y, %I:%M %p")

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

    def create(self, validated_data):
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

    def validate_admission_number(self, value):
        if not value.isalnum():
            raise serializers.ValidationError("Admission number must be alphanumeric")
        return value

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
