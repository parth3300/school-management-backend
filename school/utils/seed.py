from __future__ import annotations

import random
import string
import requests
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

from django.contrib.auth import get_user_model
from faker import Faker
from django.db import transaction

from school.models import (
    School, AcademicYear, Subject, Class, Teacher, Student,
    Exam, ExamResult, Announcement, ClassSchedule,
)
import os
from dotenv import load_dotenv
load_dotenv()
GENERAL_PASS = os.environ.get('GENERAL_PASS')
# --------------------------------------------------------------------------- #
fake = Faker("en_IN")
User = get_user_model()
ALPHANUM = string.ascii_uppercase + string.digits
rand_id = lambda n=12: "".join(random.choices(ALPHANUM, k=n))
trim = lambda s, l=20: s[:l]

REAL_SCHOOL_NAMES = ["Springfield High", "Lincoln Academy"]
REAL_SUBJECTS = ["Mathematics", "Physics", "Chemistry"]
EXAM_TYPES = ["Midterm", "Final"]
GRADE_LEVELS = [f"Grade {i}" for i in range(1, 4)]
QUALIFICATIONS = ["B.Ed", "M.Ed", "B.Sc", "M.Sc"]

ANNOUNCEMENT_TPL = [
    "School will be closed on {date} for {reason}.",
    "{teacher} will be absent on {date}. Substitute: {sub}.",
    "Reminder: {event} happening this {day} at {time}.",
]

# --------------------------------------------------------------------------- #
def load_real_names() -> Tuple[List[str], List[str]]:
    try:
        res = requests.get("https://randomuser.me/api/?results=100&nat=us,gb", timeout=4)
        res.raise_for_status()
        users = res.json()["results"]
        first = {u["name"]["first"] for u in users}
        last = {u["name"]["last"] for u in users}
        return list(first), list(last)
    except Exception:
        return (["James", "Mary"], ["Smith", "Johnson"])

FIRST_NAMES, LAST_NAMES = load_real_names()

def realistic_grade(mark: float) -> str:
    if mark >= 90: return "A+"
    if mark >= 80: return "A"
    if mark >= 70: return "B"
    if mark >= 60: return "C"
    if mark >= 50: return "D"
    return "F"

def time_slot() -> datetime.time:
    hour = random.choice([8, 9, 10, 11, 13, 14, 15])
    minute = random.choice([0, 15, 30, 45])
    return datetime.strptime(f"{hour}:{minute:02}", "%H:%M").time()

# --------------------------------------------------------------------------- #
@transaction.atomic
def populate() -> Dict[str, int]:
    wipe()

    schools, years = create_schools_years()
    subjects = create_subjects(schools)
    teachers = create_teachers(schools, subjects)
    classes = create_classes(schools, years, teachers)
    students = create_students(classes)
    exams = create_exams(years)
    create_exam_results(exams, subjects, students)
    create_announcements(schools, teachers)
    create_schedules(classes, subjects, teachers)

    summary = {
        "schools": len(schools),
        "teachers": len(teachers),
        "students": len(students),
        "subjects": len(subjects),
        "classes": len(classes),
        "exams": len(exams),
        "exam_results": ExamResult.objects.count(),
        "announcements": Announcement.objects.count(),
        "class_schedules": ClassSchedule.objects.count()
    }
    print("\n✔ Database seeded:", summary)
    return summary

from django.db import connection

def wipe():
    print("\n🧹 Wiping DB... (using raw bulk deletes)")
    
    models_to_wipe = [
        ClassSchedule, ExamResult, Exam, Announcement, Student,
        Class, Teacher, Subject, AcademicYear, School, User
    ]

    with connection.cursor() as cursor:
        for model in models_to_wipe:
            table = model._meta.db_table
            cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
    
    print("✔ Database wiped using TRUNCATE")


def create_schools_years():
    schools, years = [], []
    for name in REAL_SCHOOL_NAMES:
        school = School.objects.create(
            id=rand_id(), name=name,
            address=fake.address(), phone=trim(fake.phone_number()),
            email=fake.company_email(), website=fake.url(),
            established_date=fake.date_between("-30y", "today"),
            general_password=GENERAL_PASS,
            is_active = True,
            is_deleted = False
        )
        schools.append(school)

        start = datetime.now().date().replace(month=4, day=1)
        end = start.replace(year=start.year + 1) - timedelta(days=1)
        ay = AcademicYear.objects.create(
            id=rand_id(), name=f"{start.year}-{end.year}",
            start_date=start, end_date=end,
            is_current=True, school=school
        )
        years.append(ay)
    return schools, years


def create_subjects(schools):
    subs = [
        Subject(
            id=rand_id(), name=name,
            code=f"{name[:3].upper()}{random.randint(100,999)}",
            description=f"Intro to {name}",
            school=school,
            is_active = True,
            is_deleted = False
        )
        for school in schools for name in REAL_SUBJECTS
    ]
    Subject.objects.bulk_create(subs)
    return subs


def create_teachers(schools, subjects):
    users, teachers = [], []
    for school in schools:
        local_subjects = [s for s in subjects if s.school_id == school.id]
        for _ in range(3):
            first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}@{school.name.replace(' ','').lower()}.edu"
            user = User(
                email=email,
                name=full_name,
                first_name=first,
                last_name=last,
                phone=fake.msisdn()[:10],
                address=fake.address(),
                date_of_birth=fake.date_of_birth(minimum_age=25, maximum_age=55),
                gender=random.choice(['M', 'F', 'O']),
                role="teacher",
                school=school,
                is_active=True,
                is_admin=False,  # Only make True if this user is admin
            )
            user.set_password(GENERAL_PASS)
            users.append(user)
    User.objects.bulk_create(users)
    for user in User.objects.filter(role="teacher"):
        teacher = Teacher(
            id=rand_id(), user=user,
            joining_date=fake.date_between("-3y", "today"),
            qualification=random.choice(QUALIFICATIONS),
            school=user.school,
            is_active = True,
            is_deleted = False
        )
        teachers.append(teacher)
    Teacher.objects.bulk_create(teachers)
    return Teacher.objects.all()


def create_classes(schools, years, teachers):
    class_objs = []
    for school, year in zip(schools, years):
        local_teachers = [t for t in teachers if t.school_id == school.id]
        for level in GRADE_LEVELS:
            cls = Class(
                id=rand_id(),
                name=f"{level} {random.choice(['A','B'])}",
                academic_year=year, school=school,
                capacity=random.choice([25, 30, 35]),
                is_active = True,
                is_deleted = False
            )
            class_objs.append(cls)
    Class.objects.bulk_create(class_objs)
    return Class.objects.all()


def create_students(classes):
    users, students = [], []
    for cls in classes:
        for _ in range(5):
            first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
            email = f"{first.lower()}.{last.lower()}@{cls.school.name.replace(' ','').lower()}.edu"
            user = User(
                email=email,
                name=full_name,
                first_name=first,
                last_name=last,
                phone=fake.msisdn()[:10],
                address=fake.address(),
                date_of_birth=fake.date_of_birth(minimum_age=25, maximum_age=55),
                gender=random.choice(['M', 'F', 'O']),
                role="student",
                school=cls.school,
                is_active=True,
                is_admin=False,  # Only make True if this user is admin
            )
            user.set_password(GENERAL_PASS)
            users.append(user)
    User.objects.bulk_create(users)
    for user in User.objects.filter(role="student"):
        students.append(
            Student(
                id=rand_id(), user=user,
                admission_number=f"ST{rand_id(4)}",
                parent_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                parent_phone=trim(fake.msisdn())[:10],
                admission_date=fake.date_between("-2y", "today"),
                school=user.school, current_class=random.choice(classes),
                is_active = True,
                is_deleted = False
            )
        )
    Student.objects.bulk_create(students)
    return Student.objects.all()


def create_exams(years):
    exams = []
    for year in years:
        for typ in EXAM_TYPES:
            exams.append(
                Exam(
                    id=rand_id(),
                    name=f"{typ} {datetime.now().year}",
                    academic_year=year,
                    start_date=fake.date_between("-8w", "-2w"),
                    end_date=fake.date_between("-1w", "today"),
                    description=f"{typ} assessment",
                    school=year.school,
                    is_active = True,
                    is_deleted = False
                )
            )
    Exam.objects.bulk_create(exams)
    return Exam.objects.all()


def create_exam_results(exams, subjects, students):
    results = []
    for exam in exams:
        subs_local = [s for s in subjects if s.school_id == exam.school_id]
        sample_students = random.sample(list(students.filter(school=exam.school)), k=10)
        for stu in sample_students:
            for subj in random.sample(subs_local, k=min(2, len(subs_local))):
                mark = max(0, min(100, random.gauss(75, 12)))
                results.append(
                    ExamResult(
                        id=rand_id(), student=stu, exam=exam,
                        subject=subj, marks=round(mark, 2),
                        grade=realistic_grade(mark),
                        remarks="Excellent!" if mark >= 85 else "Needs practice",
                        school=exam.school,
                        is_active = True,
                        is_deleted = False
                    )
                )
    ExamResult.objects.bulk_create(results, batch_size=500)


def create_announcements(schools, teachers):
    for school in schools:
        local_teachers = [t for t in teachers if t.school_id == school.id]
        for _ in range(2):
            tpl = random.choice(ANNOUNCEMENT_TPL)
            msg = tpl.format(
                date=fake.date_between("today","+20d").strftime("%b %d"),
                reason=random.choice(["maintenance", "festival"]),
                teacher=random.choice(local_teachers).user.name,
                sub=random.choice(LAST_NAMES),
                event=random.choice(["Sports Day", "Science Fair"]),
                day=fake.day_of_week(),
                time=random.choice(["10:00 AM", "02:00 PM"])
            )
            Announcement.objects.create(
                id=rand_id(), title=msg[:100], message=msg,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=10),
                priority=random.choice(["L","M","H"]),
                audience="ALL", school=school,
                is_pinned=random.choice([True, False]),
                is_deleted = False
            )


def create_schedules(classes, subjects, teachers):
    schedules = []
    for cls in classes:
        local_subs = [s for s in subjects if s.school_id == cls.school_id]
        local_tchs = [t for t in teachers if t.school_id == cls.school_id]
        for _ in range(3):
            start = time_slot()
            end = (datetime.combine(datetime.today(), start) + timedelta(minutes=45)).time()
            schedules.append(
                ClassSchedule(
                    id=rand_id(), class_instance=cls,
                    subject=random.choice(local_subs),
                    teacher=random.choice(local_tchs),
                    date=fake.date_between("today", "+30d"),
                    start_time=start, end_time=end,
                    room=f"Room {random.randint(101, 305)}",
                    school=cls.school,
                    is_active = True,
                    is_deleted = False
                )
            )
    ClassSchedule.objects.bulk_create(schedules)