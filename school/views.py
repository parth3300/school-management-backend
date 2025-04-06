from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from .models import (
    School, AcademicYear, Class, Subject, Teacher,
    Student, Attendance, Exam, ExamResult
)
from .serializers import (
    SchoolSerializer, AcademicYearSerializer, ClassSerializer,
    SubjectSerializer, TeacherSerializer, StudentSerializer,
    StudentListSerializer, AttendanceSerializer, ExamSerializer, ExamResultSerializer
)

# Custom paginator
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# Base viewset with soft delete
class SoftDeleteModelViewSet(viewsets.ModelViewSet):

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        serializer = serializer_class(*args, **kwargs)

        # Remove is_active and is_deleted for write operations
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            if 'is_active' in serializer.fields:
                serializer.fields.pop('is_active')
            if 'is_deleted' in serializer.fields:
                serializer.fields.pop('is_deleted')
        return serializer

# ViewSets with soft delete applied
class SchoolViewSet(SoftDeleteModelViewSet):
    queryset = School.objects.filter(is_active=True, is_deleted=False)
    serializer_class = SchoolSerializer

class AcademicYearViewSet(SoftDeleteModelViewSet):
    queryset = AcademicYear.objects.filter(is_active=True, is_deleted=False)
    serializer_class = AcademicYearSerializer

class ClassViewSet(SoftDeleteModelViewSet):
    queryset = Class.objects.filter(is_active=True, is_deleted=False)
    serializer_class = ClassSerializer

class SubjectViewSet(SoftDeleteModelViewSet):
    queryset = Subject.objects.filter(is_active=True, is_deleted=False)
    serializer_class = SubjectSerializer

class TeacherViewSet(SoftDeleteModelViewSet):
    queryset = Teacher.objects.filter(is_active=True, is_deleted=False)
    serializer_class = TeacherSerializer

class StudentViewSet(SoftDeleteModelViewSet):
    queryset = Student.objects.select_related('user', 'current_class').filter(is_active=True, is_deleted=False)
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return StudentListSerializer
        return StudentSerializer

class AttendanceViewSet(SoftDeleteModelViewSet):
    queryset = Attendance.objects.select_related('student', 'recorded_by').filter(is_active=True, is_deleted=False)
    serializer_class = AttendanceSerializer

class ExamViewSet(SoftDeleteModelViewSet):
    queryset = Exam.objects.filter(is_active=True, is_deleted=False)
    serializer_class = ExamSerializer

class ExamResultViewSet(SoftDeleteModelViewSet):
    queryset = ExamResult.objects.select_related('student', 'exam', 'subject').filter(is_active=True, is_deleted=False)
    serializer_class = ExamResultSerializer