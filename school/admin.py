from django.contrib import admin
from .models import *

admin.site.register(School)
admin.site.register(AcademicYear)
admin.site.register(Class)
admin.site.register(Subject)
admin.site.register(Teacher)
admin.site.register(Student)
admin.site.register(StudentAttendance)
admin.site.register(TeacherAttendance)
admin.site.register(Exam)
admin.site.register(ExamResult)