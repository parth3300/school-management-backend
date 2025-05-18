from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Avg, Count, Q, Min, Max
from .models import (
    School, AcademicYear, Class, Subject, Teacher,
    Student, StudentAttendance, Exam, ExamResult, Announcement, ClassSchedule
)
from .serializers import *
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from .permissions import IsTeacher
from django.contrib.auth import get_user_model
from djoser.views import UserViewSet as DjoserUserViewSet
from django.contrib.auth.hashers import check_password

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
        

    @action(detail=False, methods=['get'])
    def stats(self, request):
        stats = {
            'total_students': Student.objects.filter(is_deleted=False).count(),
            'total_teachers': Teacher.objects.filter(is_deleted=False).count(),
            'total_classes': Class.objects.filter(is_deleted=False).count(),
            'total_subjects': Subject.objects.filter(is_deleted=False).count(),
        }
        serializer = SchoolStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def staff(self, request):
        role = request.query_params.get('role', None)
        teachers = Teacher.objects.filter(is_deleted=False)
        
        if role:
            # You might need to add role field to Teacher model or use user groups
            pass
            
        serializer = SchoolStaffSerializer(teachers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def upload_logo(self, request, pk=None):

        school = self.get_object()
        print("request.data",request.data)
        serializer = SchoolLogoUploadSerializer(school, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SchoolLoginView(APIView):
    """API for verifying school login using the general password."""

    def post(self, request):
        school_id = request.data.get('school_id')
        password = request.data.get('password')

        # Validate inputs
        if not school_id or not password:
            return Response({'detail': 'School ID and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return Response({'detail': 'School not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Use the model method to check password
        if school.check_general_password(password):
            return Response({'detail': 'School login successful.'}, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Invalid school password.'}, status=status.HTTP_400_BAD_REQUEST)

class AcademicYearViewSet(SoftDeleteModelViewSet):
    queryset = AcademicYear.objects.filter(is_active=True, is_deleted=False)
    serializer_class = AcademicYearSerializer
    
    @action(detail=True, methods=['post'])
    def set_current(self, request, pk=None):
        academic_year = self.get_object()
        # Set all other years to not current
        AcademicYear.objects.filter(is_current=True).update(is_current=False)
        academic_year.is_current = True
        academic_year.save()
        return Response({'status': 'current year set'})

    @action(detail=False, methods=['get'])
    def current(self, request):
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if current_year:
            serializer = AcademicYearCurrentSerializer(current_year)
            return Response(serializer.data)
        return Response({'detail': 'No current academic year set'}, status=status.HTTP_404_NOT_FOUND)



class SubjectViewSet(SoftDeleteModelViewSet):
    queryset = Subject.objects.filter(is_active=True, is_deleted=False)
    serializer_class = SubjectSerializer
    
    @action(detail=True, methods=['get'])
    def curriculum(self, request, pk=None):
        subject = self.get_object()
        serializer = SubjectCurriculumSerializer(subject)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def teachers(self, request):
        subject_id = request.query_params.get('subject_id', None)
        if subject_id:
            subject = self.get_queryset().filter(id=subject_id).first()
            if subject:
                teachers = subject.teachers.all()
                serializer = SubjectTeacherSerializer(teachers, many=True)
                return Response(serializer.data)
        return Response({'detail': 'Subject ID required'}, status=status.HTTP_400_BAD_REQUEST)
    @action(detail=False, methods=['get'])
    def classes(self, request):
        subject_id = request.query_params.get('subject_id', None)
        if not subject_id:
            return Response({'detail': 'Subject ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get all classes where at least one teacher teaches this subject
            classes = Class.objects.filter(
                teachers__subjects__id=subject_id
            ).distinct()
            
            serializer = SubjectClassSerializer(classes, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'detail': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class ClassViewSet(SoftDeleteModelViewSet):
    queryset = Class.objects.filter(is_active=True, is_deleted=False)
    serializer_class = ClassSerializer
    
    @action(detail=False, methods=['get'])
    def students(self, request):
        class_id = request.query_params.get('classId', None)
        if class_id:
            class_obj = self.get_queryset().filter(id=class_id).first()
            if class_obj:
                students = Student.objects.filter(current_class=class_obj)
                serializer = ClassStudentSerializer(students, many=True)
                return Response(serializer.data)
        return Response({'detail': 'Class ID required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def teachers(self, request):
        class_id = request.query_params.get('classId', None)
        if class_id:
            class_obj = self.get_queryset().filter(id=class_id).first()
            if class_obj:
                teachers = class_obj.teachers.all()
                serializer = ClassTeacherSerializer(teachers, many=True)
                return Response(serializer.data)
        return Response({'detail': 'Class ID required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def subjects(self, request):
        class_id = request.query_params.get('classId', None)
        if class_id:
            class_obj = self.get_queryset().filter(id=class_id).first()
            if class_obj:
                # Assuming subjects are linked through teachers or directly
                subjects = Subject.objects.filter(teachers__classes=class_obj).distinct()
                serializer = ClassSubjectSerializer(subjects, many=True)
                return Response(serializer.data)
        return Response({'detail': 'Class ID required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def schedule(self, request):
        class_id = request.query_params.get('classId', None)
        date = request.query_params.get('date', None)
        
        schedules = ClassSchedule.objects.all()
        
        if class_id:
            schedules = schedules.filter(class_instance_id=class_id)
        
        if date:
            schedules = schedules.filter(date=date)
            
        serializer = ClassScheduleSerializer(schedules, many=True)
        return Response(serializer.data)



class TeacherViewSet(SoftDeleteModelViewSet):
    queryset = Teacher.objects.filter(is_active=True, is_deleted=False)
    serializer_class = TeacherSerializer
    
    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        teacher = self.get_object()
        serializer = TeacherProfileSerializer(teacher)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def classes(self, request, pk=None):
        teacher = self.get_object()
        classes = teacher.classes.all()
        serializer = TeacherClassSerializer(classes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        teacher = self.get_object()
        # Get students from teacher's classes
        classes = teacher.classes.all()
        students = Student.objects.filter(current_class__in=classes)
        serializer = TeacherStudentSerializer(students, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def full_history(self, request, pk=None, student_id=None):
        teacher = self.get_object()
        try:
            student = Student.objects.get(id=student_id)
            # Verify student is in teacher's classes
            if not teacher.classes.filter(id=student.current_class_id).exists():
                return Response({'detail': 'Student not in your classes'}, status=status.HTTP_403_FORBIDDEN)
            
            # Get all data for student
            data = {
                'student': TeacherStudentSerializer(student).data,
                'attendance': StudentAttendanceSerializer(
                    StudentAttendance.objects.filter(student=student), 
                    many=True
                ).data,
                'results': ExamResultSerializer(
                    ExamResult.objects.filter(student=student), 
                    many=True
                ).data,
            }
            return Response(data)
        except Student.DoesNotExist:
            return Response({'detail': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def subjects(self, request, pk=None):
        teacher = self.get_object()
        subjects = teacher.subjects.all()
        serializer = TeacherSubjectSerializer(subjects, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def attendance_stats(self, request):
        # Get attendance stats for teacher's classes
        teacher = request.user.teacher
        classes = teacher.classes.all()
        attendance_data = []
        
        # Example: Last 30 days stats
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        
        for date in dates:
            attendance = StudentAttendance.objects.filter(
                student__current_class__in=classes,
                date=date
            )
            stats = {
                'date': date,
                'present': attendance.filter(status='P').count(),
                'absent': attendance.filter(status='A').count(),
                'late': attendance.filter(status='L').count(),
            }
            attendance_data.append(stats)
        
        serializer = TeacherAttendanceStatsSerializer(attendance_data, many=True)
        return Response(serializer.data)


# ========== TEACHER PROFILE VIEWS ==========
class TeacherProfileViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def retrieve(self, request):
        teacher = get_object_or_404(Teacher, user=request.user)
        serializer = TeacherProfileSerializer(teacher)
        return Response(serializer.data)
    
    def update(self, request):
        teacher = get_object_or_404(Teacher, user=request.user)
        serializer = TeacherProfileUpdateSerializer(
            teacher,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

# ========== TEACHER CLASS MANAGEMENT ==========
class TeacherClassViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TeacherClassDetailSerializer
    
    def get_queryset(self):
        teacher = self.request.user.teacher
        return teacher.classes.filter(
            is_active=True,
            is_deleted=False
        ).select_related('academic_year').prefetch_related('subjects')
    
    @action(detail=True, methods=['get'])
    def timetable(self, request, pk=None):
        # Implement class timetable logic
        return Response({"detail": "Timetable endpoint"}, status=200)

# ========== TEACHER STUDENT MANAGEMENT ==========
class TeacherStudentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TeacherStudentDetailSerializer
    
    def get_queryset(self):
        teacher = self.request.user.teacher
        return Student.objects.filter(
            current_class__in=teacher.classes.all(),
            is_active=True,
            is_deleted=False
        ).select_related('user', 'current_class')
    
    @action(detail=True, methods=['get'])
    def full_history(self, request, pk=None):
        student = self.get_object()
        # Implement full student history logic
        return Response({"detail": "Full history endpoint"}, status=200)

# ========== TEACHER ATTENDANCE MANAGEMENT ==========
class TeacherAttendanceViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TeacherAttendanceSerializer
    
    def get_queryset(self):
        teacher = self.request.user.teacher
        return StudentAttendance.objects.filter(
            recorded_by=teacher
        ).select_related('student', 'student__user')
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = TeacherBulkAttendanceSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        teacher = request.user.teacher
        # Implement attendance statistics logic
        return Response({"detail": "Stats endpoint"}, status=200)

# ========== TEACHER EXAM MANAGEMENT ==========
class TeacherExamResultViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TeacherExamResultCreateSerializer
        return TeacherExamResultSerializer
    
    def get_queryset(self):
        teacher = self.request.user.teacher
        return ExamResult.objects.filter(
            subject__in=teacher.subjects.all()
        ).select_related('student', 'exam', 'subject')
    
    @action(detail=False, methods=['get'])
    def by_class(self, request):
        class_id = request.query_params.get('class_id')
        exam_id = request.query_params.get('exam_id')
        
        if not class_id or not exam_id:
            return Response(
                {"error": "Both class_id and exam_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = ExamResult.objects.filter(
            exam_id=exam_id,
            student__current_class_id=class_id
        ).select_related('student', 'subject')
        
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)

# ========== TEACHER ANNOUNCEMENTS ==========
class TeacherAnnouncementViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TeacherAnnouncementSerializer
    
    def get_queryset(self):
        teacher = self.request.user.teacher
        return Announcement.objects.filter(
            Q(audience='TEA') | Q(classes__in=teacher.classes.all()),
            is_deleted=False,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).distinct().select_related('created_by')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.teacher)
    
    @action(detail=True, methods=['post'])
    def toggle_pin(self, request, pk=None):
        announcement = self.get_object()
        announcement.is_pinned = not announcement.is_pinned
        announcement.save()
        return Response({'is_pinned': announcement.is_pinned})

# ========== TEACHER DASHBOARD ==========
class TeacherDashboardView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher = request.user.teacher
        serializer = TeacherDashboardSerializer(teacher)
        return Response(serializer.data)
# ========== TEACHER SCHOOL INFO ==========
class TeacherSchoolInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        teacher = request.user.teacher
        school = teacher.school  # Assuming teacher has school relation
        return Response({
            'name': school.name,
            'address': school.address,
            'phone': school.phone,
            'email': school.email,
            'logo': request.build_absolute_uri(school.logo.url) if school.logo else None,
            'current_academic_year': {
                'name': school.current_academic_year.name,
                'start_date': school.current_academic_year.start_date,
                'end_date': school.current_academic_year.end_date
            } if hasattr(school, 'current_academic_year') else None
        })
        
class StudentViewSet(SoftDeleteModelViewSet):
    queryset = Student.objects.select_related('user', 'current_class').filter(is_active=True, is_deleted=False)
    serializer_class = StudentSerializer

class AttendanceViewSet(SoftDeleteModelViewSet):
    queryset = StudentAttendance.objects.select_related('student', 'recorded_by').filter(is_active=True, is_deleted=False)
    serializer_class = StudentAttendanceSerializer
    
    @action(detail=False, methods=['get'])
    def by_date(self, request):
        date = request.query_params.get('date', None)
        if date:
            attendance = StudentAttendance.objects.filter(date=date)
            serializer = AttendanceByDateSerializer(attendance, many=True)
            return Response(serializer.data)
        return Response({'detail': 'Date parameter required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_class(self, request, class_id=None):
        attendance = StudentAttendance.objects.filter(student__current_class_id=class_id)
        serializer = self.get_serializer(attendance, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_student(self, request, student_id=None):
        attendance = StudentAttendance.objects.filter(student_id=student_id)
        serializer = self.get_serializer(attendance, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        # Similar to bulk_create but for updates
        data = request.data
        if isinstance(data, list):
            updated = []
            for item in data:
                try:
                    attendance = StudentAttendance.objects.get(id=item.get('id'))
                    serializer = self.get_serializer(attendance, data=item, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        updated.append(serializer.data)
                except StudentAttendance.DoesNotExist:
                    continue
            return Response(updated, status=status.HTTP_200_OK)
        return Response({'detail': 'List of attendance records required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def monthly_stats(self, request):
        from django.db.models import Count
        from datetime import datetime, timedelta

        # Get stats for last 6 months
        months = []
        today = datetime.now().date()
        for i in range(6):
            month = today - timedelta(days=30*i)
            months.append(month.strftime('%Y-%m'))

        stats = []
        for month in months:
            attendance = StudentAttendance.objects.filter(date__startswith=month)
            stats.append({
                'month': month,
                'present': attendance.filter(status='P').count(),
                'absent': attendance.filter(status='A').count(),
                'late': attendance.filter(status='L').count(),
            })

        serializer = AttendanceStatsSerializer(stats, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def class_stats(self, request, class_id=None):
        students = Student.objects.filter(current_class_id=class_id)
        stats = []
        
        for student in students:
            attendance = StudentAttendance.objects.filter(student=student)
            total = attendance.count()
            if total > 0:
                present = attendance.filter(status='P').count()
                absent = attendance.filter(status='A').count()
                late = attendance.filter(status='L').count()
                rate = (present + late * 0.5) / total * 100  # Late counts as half present
                
                stats.append({
                    'student_id': student.id,
                    'student_name': f"{student.user.first_name} {student.user.last_name}",
                    'present': present,
                    'absent': absent,
                    'late': late,
                    'attendance_rate': round(rate, 2)
                })
        
        serializer = ClassAttendanceStatsSerializer(stats, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        student = self.get_object()
        serializer = StudentProfileSerializer(student)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def upload_photo(self, request, pk=None):
        student = self.get_object()
        serializer = StudentPhotoUploadSerializer(student, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def courses(self, request, pk=None):
        student = self.get_object()
        if student.current_class:
            # Get subjects from class through teachers
            subjects = Subject.objects.filter(teachers__classes=student.current_class).distinct()
            serializer = StudentCourseSerializer(subjects, many=True)
            return Response(serializer.data)
        return Response([], status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def attendance(self, request, pk=None):
        student = self.get_object()
        start_date = request.query_params.get('start', None)
        end_date = request.query_params.get('end', None)
        
        attendance = StudentAttendance.objects.filter(student=student)
        
        if start_date and end_date:
            attendance = attendance.filter(date__gte=start_date, date__lte=end_date)
        
        serializer = StudentAttendanceSerializer(attendance, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        student = self.get_object()
        exam_id = request.query_params.get('exam', None)
        
        results = ExamResult.objects.filter(student=student)
        
        if exam_id:
            results = results.filter(exam_id=exam_id)
        
        serializer = StudentResultSerializer(results, many=True)
        return Response(serializer.data)


class ExamViewSet(SoftDeleteModelViewSet):
    queryset = Exam.objects.filter(is_active=True, is_deleted=False)
    serializer_class = ExamSerializer
    @action(detail=False, methods=['get'])
    def by_academic_year(self, request):
        year_id = request.query_params.get('yearId', None)
        if year_id:
            exams = self.get_queryset().filter(academic_year_id=year_id)
            serializer = ExamByYearSerializer(exams, many=True)
            return Response(serializer.data)
        return Response({'detail': 'Academic year ID required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        exam = self.get_object()
        # Assuming exam schedule is based on class schedules during exam period
        schedules = ClassSchedule.objects.filter(
            date__gte=exam.start_date,
            date__lte=exam.end_date
        )
        serializer = ExamScheduleSerializer(schedules, many=True)
        return Response(serializer.data)


class ExamResultViewSet(SoftDeleteModelViewSet):
    queryset = ExamResult.objects.select_related('student', 'exam', 'subject').filter(is_active=True, is_deleted=False)
    serializer_class = ExamResultSerializer
    @action(detail=False, methods=['get'])
    def class_summary(self, request, class_id=None):
        from django.db.models import Avg, Max, Min
        
        # Get all results for this class
        results = ExamResult.objects.filter(
            student__current_class_id=class_id
        ).values('subject__name').annotate(
            average_marks=Avg('marks'),
            highest_marks=Max('marks'),
            lowest_marks=Min('marks'),
            pass_count=Count('id'),
            total_count=Count('id')
        )
        
        summary = []
        for item in results:
            pass_rate = (item['pass_count'] / item['total_count'] * 100) if item['total_count'] > 0 else 0
            summary.append({
                'subject_name': item['subject__name'],
                'average_marks': round(item['average_marks'], 2),
                'highest_marks': item['highest_marks'],
                'lowest_marks': item['lowest_marks'],
                'pass_rate': round(pass_rate, 2)
            })
        
        serializer = ExamResultClassSummarySerializer(summary, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def student_summary(self, request, student_id=None):
        from django.db.models import Avg, Window, F
        from django.db.models.functions import Rank
        
        # Get all results for this student
        student_results = ExamResult.objects.filter(student_id=student_id)
        
        # Get class averages and ranks for each exam/subject
        summary = []
        for result in student_results:
            # Get class average for this exam/subject
            class_avg = ExamResult.objects.filter(
                exam=result.exam,
                subject=result.subject,
                student__current_class=result.student.current_class
            ).aggregate(avg=Avg('marks'))['avg'] or 0
            
            # Get student's rank in class for this exam/subject
            ranked_results = ExamResult.objects.filter(
                exam=result.exam,
                subject=result.subject,
                student__current_class=result.student.current_class
            ).annotate(
                rank=Window(
                    expression=Rank(),
                    order_by=F('marks').desc()
                )
            ).values('student_id', 'rank')
            
            student_rank = next(
                (item['rank'] for item in ranked_results if item['student_id'] == student_id),
                None
            )
            
            summary.append({
                'exam_name': result.exam.name,
                'subject_name': result.subject.name,
                'marks': result.marks,
                'grade': result.grade,
                'class_average': round(class_avg, 2),
                'class_rank': student_rank
            })
        
        serializer = ExamResultStudentSummarySerializer(summary, many=True)
        return Response(serializer.data)


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def active(self, request):
        now = timezone.now()
        announcements = Announcement.objects.filter(
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-priority', '-start_date')
        serializer = AnnouncementActiveSerializer(announcements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pinned(self, request):
        announcements = Announcement.objects.filter(
            is_pinned=True
        ).order_by('-start_date')
        serializer = AnnouncementActiveSerializer(announcements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_audience(self, request):
        audience = request.query_params.get('audience', None)
        if audience:
            announcements = Announcement.objects.filter(audience=audience)
            if audience == 'CLS':
                # Filter by classes if needed
                pass
            elif audience == 'SUB':
                # Filter by subjects if needed
                pass
            serializer = self.get_serializer(announcements, many=True)
            return Response(serializer.data)
        return Response({'detail': 'Audience parameter required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def upload_attachment(self, request, pk=None):
        announcement = self.get_object()
        serializer = AnnouncementAttachmentUploadSerializer(announcement, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    


class ExamResultsSummaryView(APIView):
    """
    View to get exam results summary statistics
    """
    def get(self, request, *args, **kwargs):
        exam_id = request.query_params.get('exam_id')
        class_id = request.query_params.get('class_id')
        
        if not exam_id and not class_id:
            return Response(
                {"error": "Either exam_id or class_id must be provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters = Q()
        if exam_id:
            filters &= Q(exam__id=exam_id)
        if class_id:
            filters &= Q(student__class_id=class_id)
        
        # Calculate summary statistics
        results = ExamResult.objects.filter(filters)
        
        if not results.exists():
            return Response(
                {"error": "No results found for the given criteria"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        summary = {
            'total_students': results.values('student').distinct().count(),
            'average_score': results.aggregate(avg_score=Avg('score'))['avg_score'],
            'highest_score': results.aggregate(max_score=Max('score'))['max_score'],
            'lowest_score': results.aggregate(min_score=Min('score'))['min_score'],
            'pass_count': results.filter(score__gte=50).count(),
            'fail_count': results.filter(score__lt=50).count(),
            'grade_distribution': results.values('grade').annotate(count=Count('grade')).order_by('grade')
        }
        
        serializer = ExamResultSummarySerializer(summary)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
# views.py
class ClassScheduleViewSet(viewsets.ModelViewSet):
    queryset = ClassSchedule.objects.all()
    serializer_class = ClassScheduleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        class_id = self.request.query_params.get('class', None)
        teacher_id = self.request.query_params.get('teacher', None)
        date = self.request.query_params.get('date', None)
        
        if class_id:
            queryset = queryset.filter(class_instance_id=class_id)
        
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        if date:
            queryset = queryset.filter(date=date)
            
        return queryset

    @action(detail=False, methods=['get'])
    def weekly(self, request):
        class_id = request.query_params.get('class', None)
        week_start = request.query_params.get('week_start', None)
        
        if not class_id or not week_start:
            return Response(
                {'detail': 'Class ID and week_start parameters required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from datetime import datetime, timedelta
            start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
            end_date = start_date + timedelta(days=6)
            
            schedules = ClassSchedule.objects.filter(
                class_instance_id=class_id,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date', 'start_time')
            
            # Group by day
            weekly_schedule = {}
            for day in range(7):
                current_date = start_date + timedelta(days=day)
                day_schedules = schedules.filter(date=current_date)
                weekly_schedule[current_date.strftime('%A')] = ClassScheduleWeeklySerializer(
                    day_schedules, many=True
                ).data
                
            return Response(weekly_schedule)
        except ValueError:
            return Response(
                {'detail': 'Invalid date format. Use YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )   
            
            
# views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
class UserViewSet(DjoserUserViewSet):
    """
    Custom user viewset that extends Djoser and includes:
    - Profile retrieval
    - Password change
    - Password reset
    - Email verification
    """

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """
        Get the authenticated user's profile.
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change password for the authenticated user.
        """
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not check_password(serializer.validated_data['old_password'], user.password):
                return Response({'old_password': 'Wrong password'}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'status': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def reset_password(self, request):
        """
        Simulated password reset (email logic not implemented).
        """
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            # Send reset email logic goes here
            return Response({'status': 'Password reset email sent'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verify_email(self, request):
        """
        Simulated email verification.
        """
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            # Email verification logic goes here
            return Response({'status': 'Email verified'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)