from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

# ModelViewSets
router.register(r'schools', SchoolViewSet)
router.register(r'academic-years', AcademicYearViewSet)
router.register(r'classes', ClassViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'teachers', TeacherViewSet)
router.register(r'students', StudentViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'exams', ExamViewSet)
router.register(r'exam-results', ExamResultViewSet)
router.register(r'announcements', AnnouncementViewSet)
router.register(r'class-schedules', ClassScheduleViewSet)

# Djoser auth URLs (extended with custom UserViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Additional custom URLs
    path('exam-results-summary/', ExamResultsSummaryView.as_view(), name='exam-results-summary'),
    path('teacher-dashboard/', TeacherDashboardView.as_view(), name='teacher-dashboard'),
    path('teacher-school-info/', TeacherSchoolInfoView.as_view(), name='teacher-school-info'),
    
    # Include Djoser's auth URLs
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('auth/', include('djoser.urls.jwt')),
]

# School-related URLs
school_urls = [
    path('school/login/', SchoolLoginView.as_view(), name='school-login'),
    path('schools/stats/', SchoolViewSet.as_view({'get': 'stats'}), name='school-stats'),
    path('schools/staff/', SchoolViewSet.as_view({'get': 'staff'}), name='school-staff'),
    path('schools/<str:pk>/upload-logo/', SchoolViewSet.as_view({'post': 'upload-logo'}), name='school-upload-logo'),
]

# Academic Year URLs
academic_year_urls = [
    path('academic-years/<str:pk>/set-current/', AcademicYearViewSet.as_view({'post': 'set_current'}), name='academic-year-set-current'),
    path('academic-years/current/', AcademicYearViewSet.as_view({'get': 'current'}), name='academic-year-current'),
]

# Subject URLs
subject_urls = [
    path('subjects/<str:pk>/curriculum/', SubjectViewSet.as_view({'get': 'curriculum'}), name='subject-curriculum'),
    path('subjects/teachers/', SubjectViewSet.as_view({'get': 'teachers'}), name='subject-teachers'),
    path('subjects/classes/', SubjectViewSet.as_view({'get': 'classes'}), name='subject-classes'),
]

# Class URLs
class_urls = [
    path('classes/students/', ClassViewSet.as_view({'get': 'students'}), name='class-students'),
    path('classes/teachers/', ClassViewSet.as_view({'get': 'teachers'}), name='class-teachers'),
    path('classes/subjects/', ClassViewSet.as_view({'get': 'subjects'}), name='class-subjects'),
    path('classes/schedule/', ClassViewSet.as_view({'get': 'schedule'}), name='class-schedule'),
]

# Teacher URLs
teacher_urls = [
#     path('teachers/<str:pk>/profile/', TeacherViewSet.as_view({'get': 'profile'}), name='teacher-profile'),
#     path('teachers/<str:pk>/classes/', TeacherViewSet.as_view({'get': 'classes'}), name='teacher-classes'),
#     path('teachers/<str:pk>/students/', TeacherViewSet.as_view({'get': 'students'}), name='teacher-students'),
#     path('teachers/<str:pk>/full-history/<str:student_id>/', TeacherViewSet.as_view({'get': 'full_history'}), name='teacher-student-full-history'),
#     path('teachers/<str:pk>/subjects/', TeacherViewSet.as_view({'get': 'subjects'}), name='teacher-subjects'),
#     path('teachers/attendance-stats/', TeacherViewSet.as_view({'get': 'attendance_stats'}), name='teacher-attendance-stats'),
]

# Student URLs
student_urls = [
    path('students/<str:pk>/profile/', StudentViewSet.as_view({'get': 'profile'}), name='student-profile'),
    path('students/<str:pk>/upload-photo/', StudentViewSet.as_view({'post': 'upload_photo'}), name='student-upload-photo'),
    path('students/<str:pk>/courses/', StudentViewSet.as_view({'get': 'courses'}), name='student-courses'),
    path('students/<str:pk>/attendance/', StudentViewSet.as_view({'get': 'attendance'}), name='student-attendance'),
    path('students/<str:pk>/results/', StudentViewSet.as_view({'get': 'results'}), name='student-results'),
]

# Attendance URLs
attendance_urls = [
    path('attendance/by-date/', AttendanceViewSet.as_view({'get': 'by_date'}), name='attendance-by-date'),
    path('attendance/by-class/<str:class_id>/', AttendanceViewSet.as_view({'get': 'by_class'}), name='attendance-by-class'),
    path('attendance/by-student/<str:student_id>/', AttendanceViewSet.as_view({'get': 'by_student'}), name='attendance-by-student'),
    path('attendance/bulk-update/', AttendanceViewSet.as_view({'post': 'bulk_update'}), name='attendance-bulk-update'),
    path('attendance/monthly-stats/', AttendanceViewSet.as_view({'get': 'monthly_stats'}), name='attendance-monthly-stats'),
    path('attendance/class-stats/<str:class_id>/', AttendanceViewSet.as_view({'get': 'class_stats'}), name='attendance-class-stats'),
]

# Exam URLs
exam_urls = [
    path('exams/by-academic-year/', ExamViewSet.as_view({'get': 'by_academic_year'}), name='exam-by-academic-year'),
    path('exams/<str:pk>/schedule/', ExamViewSet.as_view({'get': 'schedule'}), name='exam-schedule'),
]

# Exam Result URLs
exam_result_urls = [
    path('exam-results/class-summary/<str:class_id>/', ExamResultViewSet.as_view({'get': 'class_summary'}), name='exam-result-class-summary'),
    path('exam-results/student-summary/<str:student_id>/', ExamResultViewSet.as_view({'get': 'student_summary'}), name='exam-result-student-summary'),
]

# Announcement URLs
announcement_urls = [
    path('announcements/active/', AnnouncementViewSet.as_view({'get': 'active'}), name='announcement-active'),
    path('announcements/pinned/', AnnouncementViewSet.as_view({'get': 'pinned'}), name='announcement-pinned'),
    path('announcements/by-audience/', AnnouncementViewSet.as_view({'get': 'by_audience'}), name='announcement-by-audience'),
    path('announcements/<str:pk>/upload-attachment/', AnnouncementViewSet.as_view({'post': 'upload_attachment'}), name='announcement-upload-attachment'),
    path('announcements/<str:pk>/pin/', AnnouncementViewSet.as_view({'post': 'pin'}), name='announcement-pin'),
    path('announcements/upcoming/', AnnouncementViewSet.as_view({'get': 'upcoming'}), name='announcement-upcoming'),
    path('announcements/expired/', AnnouncementViewSet.as_view({'get': 'expired'}), name='announcement-expired'),
    path('announcements/for-user/', AnnouncementViewSet.as_view({'get': 'for_user'}), name='announcement-for-user'),
]

# Class Schedule URLs
class_schedule_urls = [
    path('class-schedules/weekly/', ClassScheduleViewSet.as_view({'get': 'weekly'}), name='class-schedule-weekly'),
]

# User URLs (extending Djoser)
user_urls = [
    path('users/profile/', UserViewSet.as_view({'get': 'profile'}), name='user-profile'),
    path('users/change-password/', UserViewSet.as_view({'post': 'change_password'}), name='user-change-password'),
    path('users/reset-password/', UserViewSet.as_view({'post': 'reset_password'}), name='user-reset-password'),
    path('users/verify-email/', UserViewSet.as_view({'post': 'verify_email'}), name='user-verify-email'),
    path('users/activate/<uidb64>/<token>/', activate_user, name='activate_user'),

]

# Combine all URL patterns
urlpatterns += (
    school_urls +
    academic_year_urls +
    subject_urls +
    class_urls +
    teacher_urls +
    student_urls +
    attendance_urls +
    exam_urls +
    exam_result_urls +
    announcement_urls +
    class_schedule_urls +
    user_urls
)