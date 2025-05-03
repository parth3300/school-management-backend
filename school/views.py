from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Q
from .models import (
    School, AcademicYear, Class, Subject, Teacher,
    Student, Attendance, Exam, ExamResult, Announcement
)
from .serializers import (
    SchoolSerializer, AcademicYearSerializer, ClassSerializer,
    SubjectSerializer, TeacherSerializer, StudentSerializer,
    StudentListSerializer, AttendanceSerializer, ExamSerializer, 
    ExamResultSerializer, AnnouncementSerializer, AnnouncementListSerializer
)

from django.contrib.auth import get_user_model

User = get_user_model()


# Custom paginator
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# Base viewset with soft delete
class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if hasattr(instance, 'is_active'):
            instance.is_active = False
        if hasattr(instance, 'is_deleted'):
            instance.is_deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        serializer = serializer_class(*args, **kwargs)

        # Remove is_active and is_deleted for write operations if they exist
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            for field in ['is_active', 'is_deleted']:
                if field in serializer.fields:
                    serializer.fields.pop(field)
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


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Announcement.objects.select_related(
            'school', 'academic_year', 'created_by__user'
        ).prefetch_related(
            'classes', 'subjects'
        ).filter(is_deleted=False)
        
        now = timezone.now()
        
        # For students and teachers, only show active announcements
        if not user.is_superuser:
            queryset = queryset.filter(
                Q(start_date__lte=now) & 
                (Q(end_date__gte=now) | Q(end_date__isnull=True))
            )
        
        # Role-based filtering
        if hasattr(user, 'student'):
            student = user.student
            if student.current_class:
                queryset = queryset.filter(
                    Q(school=student.current_class.academic_year.school) &
                    (Q(audience='ALL') | Q(audience='STU') |
                     Q(classes=student.current_class) |
                     Q(subjects__in=student.current_class.subjects.all()))
                )
            else:
                queryset = queryset.none()
        elif hasattr(user, 'teacher'):
            teacher = user.teacher
            queryset = queryset.filter(
                Q(school=teacher.school) &
                (Q(audience='ALL') | Q(audience='TEA') |
                 Q(classes__in=teacher.classes.all()) |
                 Q(subjects__in=teacher.subjects.all())))
        
        # Apply additional filters from query parameters
        filters = {
            'school_id': 'school_id',
            'academic_year_id': 'academic_year_id',
            'priority': 'priority',
            'audience': 'audience',
            'pinned_only': 'is_pinned'
        }
        
        for param, field in filters.items():
            value = self.request.query_params.get(param)
            if value:
                if param == 'pinned_only':
                    if value.lower() == 'true':
                        queryset = queryset.filter(**{field: True})
                else:
                    queryset = queryset.filter(**{field: value})
        
        return queryset.distinct().order_by('-is_pinned', '-start_date')
    
    def perform_create(self, serializer):
        # Automatically set created_by to the current teacher
        if hasattr(self.request.user, 'teacher'):
            serializer.save(created_by=self.request.user.teacher)
        else:
            serializer.save()
    
    def get_permissions(self):
        # Only allow superusers and teachers to modify announcements
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAdminUser] if not hasattr(self.request.user, 'teacher') else [permissions.IsAuthenticated]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Toggle pin status of an announcement (teachers and admins only)"""
        if not (request.user.is_superuser or hasattr(request.user, 'teacher')):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        announcement = self.get_object()
        announcement.is_pinned = not announcement.is_pinned
        announcement.save()
        return Response({'is_pinned': announcement.is_pinned})
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming announcements (start_date > now)"""
        queryset = self.filter_queryset(self.get_queryset())
        upcoming = queryset.filter(start_date__gt=timezone.now())
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get expired announcements (end_date < now)"""
        if not request.user.is_superuser:
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        queryset = self.filter_queryset(self.get_queryset())
        expired = queryset.filter(end_date__lt=timezone.now())
        serializer = self.get_serializer(expired, many=True)
        return Response(serializer.data)
    queryset = Announcement.objects.select_related(
        'school', 'academic_year', 'created_by'
    ).prefetch_related(
        'classes', 'subjects'
    ).filter(is_deleted=False)
    
    pagination_class = PageNumberPagination
    page_size = 10

    def get_serializer_class(self):
        if self.action == 'list':
            return AnnouncementListSerializer
        return AnnouncementSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        now = timezone.now()

        # Filter by active announcements (start_date <= now <= end_date OR start_date <= now if no end_date)
        queryset = queryset.filter(
            Q(start_date__lte=now) & 
            (Q(end_date__gte=now) | Q(end_date__isnull=True))
        )

        # Apply additional filters from query parameters
        filters = {
            'school_id': 'school_id',
            'academic_year_id': 'academic_year_id',
            'class_id': 'classes__id',
            'subject_id': 'subjects__id',
            'priority': 'priority',
            'audience': 'audience',
            'pinned_only': 'is_pinned'
        }

        for param, field in filters.items():
            value = self.request.query_params.get(param)
            if value:
                if param == 'pinned_only':
                    if value.lower() == 'true':
                        queryset = queryset.filter(**{field: True})
                else:
                    queryset = queryset.filter(**{field: value})

        return queryset.order_by('-is_pinned', '-start_date')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Toggle pin status of an announcement"""
        announcement = self.get_object()
        announcement.is_pinned = not announcement.is_pinned
        announcement.save()
        return Response({'is_pinned': announcement.is_pinned})

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming announcements (start_date > now)"""
        queryset = self.filter_queryset(self.get_queryset())
        upcoming = queryset.filter(start_date__gt=timezone.now())
        page = self.paginate_queryset(upcoming)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get expired announcements (end_date < now)"""
        queryset = self.filter_queryset(self.get_queryset())
        expired = queryset.filter(end_date__lt=timezone.now())
        page = self.paginate_queryset(expired)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(expired, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def for_user(self, request):
        """Get announcements relevant to the current user"""
        user = request.user
        queryset = self.filter_queryset(self.get_queryset())
        
        if hasattr(user, 'teacher'):
            # For teachers: show all announcements for their school + teacher-specific
            teacher = user.teacher
            queryset = queryset.filter(
                Q(school=teacher.school) &
                (Q(audience='ALL') | Q(audience='TEA') |
                Q(classes__in=teacher.classes.all()) |
                Q(subjects__in=teacher.subjects.all())))
        elif hasattr(user, 'student'):
            # For students: show announcements for their class + student-specific
            student = user.student
            if student.current_class:
                queryset = queryset.filter(
                    Q(school=student.current_class.academic_year.school) &
                    (Q(audience='ALL') | Q(audience='STU') |
                    Q(classes=student.current_class) |
                    Q(subjects__in=student.current_class.subjects.all())))
            else:
                queryset = queryset.none()
                
        queryset = queryset.distinct().order_by('-is_pinned', '-start_date')
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)