from django.utils import timezone
from django.db.models import Q, Count
from .models import StudentAttendance, ExamResult, ClassSchedule

def get_teacher_upcoming_classes(teacher):
    """Get teacher's scheduled classes for today and tomorrow."""
    today = timezone.now().date()
    tomorrow = today + timezone.timedelta(days=1)

    return ClassSchedule.objects.filter(
        teacher=teacher,
        date__range=[today, tomorrow],
        class_instance__is_active=True
    ).order_by('date', 'start_time')

def get_teacher_attendance_stats(teacher, days=30):
    """Get attendance statistics for teacher's classes"""
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=days)

    stats = StudentAttendance.objects.filter(
        recorded_by=teacher,
        date__range=[start_date, end_date]
    ).values('status').annotate(
        count=Count('status')
    )

    return {item['status']: item['count'] for item in stats}

def validate_teacher_exam_access(teacher, exam, subject):
    """Validate if teacher can enter grades for this exam/subject"""
    return all([
        teacher.subjects.filter(id=subject.id).exists(),
        exam.subject_set.filter(id=subject.id).exists(),  # Make sure this is correct
        ExamResult.objects.filter(
            id=exam.id,
            subjects__classes__teachers=teacher
        ).exists()
    ])
