from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import *
from school_user.views import CustomTokenObtainPairView

router = DefaultRouter()
router.register(r'schools', SchoolViewSet)
router.register(r'academic-years', AcademicYearViewSet)
router.register(r'classes', ClassViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'teachers', TeacherViewSet)
router.register(r'students', StudentViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'exams', ExamViewSet)
router.register(r'exam-results', ExamResultViewSet)
router.register(r'announcement', AnnouncementViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('token-by-email/', CustomTokenObtainPairView.as_view(), name='token_by_email'),

]
