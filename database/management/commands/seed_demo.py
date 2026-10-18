"""Populate the database with a realistic demo dataset.

    python manage.py seed_demo          # add anything missing, keep existing rows
    python manage.py seed_demo --reset  # wipe demo rows first, then reseed

Creates the two roles the app requires, a teacher and three students, six
courses, seven exams with complete question papers, registrations and scores.
Everything is idempotent, so running it twice is safe.
"""

import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from database.models import (
    User, role_id, course_id, class_stu_tech, courses_availed,
    exam_details, ques_table, answer_table, score_table,
    registration_table, notes_table, query_table,
)

PASSWORD = "Xamlysis@123"

COURSES = [
    ("PHY11", "Physics", 11),
    ("MAT11", "Mathematics", 11),
    ("CHE11", "Chemistry", 11),
    ("BIO11", "Biology", 11),
    ("CSC11", "Computer Science", 11),
    ("ENG11", "English", 11),
]

TEACHERS = [
    ("teacher@demo.test", "demoteacher", "Tara", "Rao", "9000000001"),
]

STUDENTS = [
    ("student@demo.test", "demostudent", "Sam", "Iyer", "9000000002"),
    ("priya@demo.test", "priyan", "Priya", "Nair", "9000000003"),
    ("arjun@demo.test", "arjunk", "Arjun", "Kapoor", "9000000004"),
]

# exam_code, title, course, offset in days from today, start, duration h, max marks
EXAMS = [
    ("PHY-MID-01", "Physics Midterm", "PHY11", -21, (9, 0), 2, 100),
    ("MAT-MID-01", "Mathematics Midterm", "MAT11", -14, (9, 30), 2, 100),
    ("ENG-UT-01", "English Unit Test", "ENG11", -7, (11, 0), 1, 50),
    ("PHY-UT-02", "Physics Unit Test II", "PHY11", 0, (10, 0), 1, 50),
    ("CHE-UT-01", "Chemistry Unit Test", "CHE11", 5, (10, 30), 1, 50),
    ("BIO-FIN-01", "Biology Final", "BIO11", 12, (9, 0), 3, 100),
    ("CSC-QZ-01", "Computer Science Quiz", "CSC11", 20, (14, 0), 1, 50),
]

# exam_code -> list of (question, opt1, opt2, opt3, opt4, correct index, marks)
PAPERS = {
    "PHY-MID-01": [
        ("The SI unit of force is the", "Newton", "Joule", "Watt", "Pascal", 1, 20),
        ("Acceleration due to gravity on Earth is approximately", "9.8 m/s2", "3.7 m/s2", "1.6 m/s2", "11.2 m/s2", 1, 20),
        ("Which quantity is a vector?", "Speed", "Mass", "Velocity", "Temperature", 3, 20),
        ("Newton's third law describes", "Inertia", "Action and reaction", "Gravitation", "Momentum decay", 2, 20),
        ("Work is measured in", "Pascal", "Joule", "Ampere", "Kelvin", 2, 20),
    ],
    "MAT-MID-01": [
        ("The derivative of x squared is", "x", "2x", "x cubed", "2", 2, 20),
        ("The value of pi to two decimal places is", "3.14", "3.41", "2.17", "3.11", 1, 20),
        ("A triangle's interior angles sum to", "90 degrees", "180 degrees", "270 degrees", "360 degrees", 2, 20),
        ("The square root of 144 is", "11", "12", "13", "14", 2, 20),
        ("log base 10 of 1000 equals", "2", "3", "10", "100", 2, 20),
    ],
    "ENG-UT-01": [
        ("Choose the correct spelling", "Recieve", "Receive", "Receeve", "Receve", 2, 10),
        ("The plural of 'child' is", "Childs", "Childes", "Children", "Childrens", 3, 10),
        ("'Quickly' is which part of speech?", "Noun", "Adjective", "Adverb", "Verb", 3, 10),
        ("A synonym for 'begin' is", "Cease", "Commence", "Conclude", "Cancel", 2, 10),
        ("Identify the past tense of 'go'", "Goed", "Gone", "Went", "Going", 3, 10),
    ],
    "PHY-UT-02": [
        ("Ohm's law relates voltage, current and", "Power", "Resistance", "Charge", "Energy", 2, 10),
        ("The unit of electric current is the", "Volt", "Ohm", "Ampere", "Coulomb", 3, 10),
        ("Light travels fastest through", "Water", "Glass", "Vacuum", "Diamond", 3, 10),
        ("Sound cannot travel through", "Air", "Water", "Steel", "Vacuum", 4, 10),
        ("The device that measures current is a", "Voltmeter", "Ammeter", "Barometer", "Thermometer", 2, 10),
    ],
    "CHE-UT-01": [
        ("The chemical symbol for sodium is", "So", "Sd", "Na", "Nm", 3, 10),
        ("Water's chemical formula is", "H2O", "HO2", "H2O2", "OH", 1, 10),
        ("The pH of a neutral solution is", "0", "7", "10", "14", 2, 10),
        ("Which gas do plants absorb?", "Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen", 3, 10),
        ("The atomic number of carbon is", "4", "6", "8", "12", 2, 10),
    ],
    "BIO-FIN-01": [
        ("The powerhouse of the cell is the", "Nucleus", "Ribosome", "Mitochondrion", "Vacuole", 3, 20),
        ("Photosynthesis takes place in the", "Mitochondria", "Chloroplast", "Nucleus", "Golgi body", 2, 20),
        ("Human blood is pumped by the", "Liver", "Lungs", "Heart", "Kidney", 3, 20),
        ("DNA stands for", "Deoxyribonucleic acid", "Dinucleic acid", "Deoxyribose nucleotide", "Dual nucleic acid", 1, 20),
        ("The basic unit of life is the", "Tissue", "Organ", "Cell", "Molecule", 3, 20),
    ],
    "CSC-QZ-01": [
        ("HTML stands for", "Hyper Text Markup Language", "High Text Machine Language", "Hyper Tabular Markup Language", "Home Tool Markup Language", 1, 10),
        ("Which is not a programming language?", "Python", "Java", "HTTP", "Ruby", 3, 10),
        ("A variable stores", "Only numbers", "Only text", "A value", "Nothing", 3, 10),
        ("The binary value of decimal 5 is", "100", "101", "110", "111", 2, 10),
        ("Django is written in", "Java", "Python", "PHP", "Ruby", 2, 10),
    ],
}

# exam_code -> {student email: scored marks}
RESULTS = {
    "PHY-MID-01": {"student@demo.test": 80, "priya@demo.test": 60, "arjun@demo.test": 40},
    "MAT-MID-01": {"student@demo.test": 60, "priya@demo.test": 100},
    "ENG-UT-01": {"student@demo.test": 40, "arjun@demo.test": 30},
}


class Command(BaseCommand):
    help = "Seed the database with demo roles, users, courses, exams and results."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo rows before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self._roles()
        self._courses()
        teacher, students = self._users()
        self._exams(teacher)
        self._papers()
        self._registrations(students)
        self._results(students)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("  Teacher  teacher@demo.test / %s" % PASSWORD)
        self.stdout.write("  Student  student@demo.test / %s" % PASSWORD)
        self.stdout.write("  Also     priya@demo.test, arjun@demo.test (same password)")
        self.stdout.write(
            "  %d courses, %d exams, %d questions, %d results"
            % (
                course_id.objects.count(),
                exam_details.objects.count(),
                ques_table.objects.count(),
                score_table.objects.count(),
            )
        )

    # ------------------------------------------------------------------

    def _reset(self):
        demo_emails = [e for e, *_ in TEACHERS + STUDENTS]
        exam_codes = [c for c, *_ in EXAMS]

        answer_table.objects.filter(exam_code_id__in=exam_codes).delete()
        score_table.objects.filter(exam_code_id__in=exam_codes).delete()
        registration_table.objects.filter(exam_code_id__in=exam_codes).delete()
        notes_table.objects.filter(exam_code_id__in=exam_codes).delete()
        query_table.objects.filter(exam_code_id__in=exam_codes).delete()
        ques_table.objects.filter(exam_code_id__in=exam_codes).delete()
        exam_details.objects.filter(exam_code__in=exam_codes).delete()
        courses_availed.objects.filter(email_id_id__in=demo_emails).delete()
        class_stu_tech.objects.filter(email_id_id__in=demo_emails).delete()
        User.objects.filter(email_id__in=demo_emails).delete()
        course_id.objects.filter(course_id__in=[c for c, *_ in COURSES]).delete()
        self.stdout.write(self.style.WARNING("Removed existing demo rows."))

    def _roles(self):
        role_id.objects.get_or_create(role_id=1, defaults={"role_name": "TEACHER"})
        role_id.objects.get_or_create(role_id=2, defaults={"role_name": "STUDENT"})
        self.stdout.write("Roles      ok")

    def _courses(self):
        for code, name, klass in COURSES:
            course_id.objects.get_or_create(
                course_id=code,
                defaults={"course_name": name, "class_stu_tech": klass},
            )
        self.stdout.write("Courses    %d" % course_id.objects.count())

    def _users(self):
        teacher = None
        for email, username, first, last, mobile in TEACHERS:
            u, _ = User.objects.get_or_create(
                email_id=email,
                defaults={
                    "username": username, "first_name": first,
                    "last_name": last, "mobile_no": mobile, "role_id_id": 1,
                },
            )
            u.set_password(PASSWORD)
            u.save()
            class_stu_tech.objects.get_or_create(
                role_id_id=1, email_id_id=u.email_id, class_stu_tech=11
            )
            teacher = u

        students = []
        for email, username, first, last, mobile in STUDENTS:
            u, _ = User.objects.get_or_create(
                email_id=email,
                defaults={
                    "username": username, "first_name": first,
                    "last_name": last, "mobile_no": mobile, "role_id_id": 2,
                },
            )
            u.set_password(PASSWORD)
            u.save()
            class_stu_tech.objects.get_or_create(
                role_id_id=2, email_id_id=u.email_id, class_stu_tech=11
            )
            for code, *_ in COURSES:
                courses_availed.objects.get_or_create(
                    course_id_id=code, role_id_id=2, email_id_id=u.email_id
                )
            students.append(u)

        self.stdout.write("Users      1 teacher, %d students" % len(students))
        return teacher, students

    def _exams(self, teacher):
        today = datetime.date.today()
        for code, title, course, offset, (hh, mm), hours, marks in EXAMS:
            exam_details.objects.get_or_create(
                exam_code=code,
                defaults={
                    "exam_title": title,
                    "date": today + datetime.timedelta(days=offset),
                    "start_time": datetime.time(hh, mm),
                    "duration": datetime.timedelta(hours=hours),
                    "no_of_ques": len(PAPERS.get(code, [])),
                    "max_marks": marks,
                    "course_id_id": course,
                    "email_id_id": teacher.email_id,
                    "class_stu": 11,
                },
            )
        self.stdout.write("Exams      %d" % exam_details.objects.count())

    def _papers(self):
        for code, questions in PAPERS.items():
            for n, (q, o1, o2, o3, o4, correct, marks) in enumerate(questions, start=1):
                ques_table.objects.get_or_create(
                    ques_id="%s-Q%d" % (code, n),
                    defaults={
                        "ques": q, "option1": o1, "option2": o2,
                        "option3": o3, "option4": o4,
                        "correct": correct, "marks": marks,
                        "exam_code_id": code,
                    },
                )
        self.stdout.write("Questions  %d" % ques_table.objects.count())

    def _registrations(self, students):
        today = datetime.date.today()
        upcoming = exam_details.objects.filter(date__gte=today)
        for e in upcoming:
            for s in students:
                registration_table.objects.get_or_create(
                    exam_code_id=e.exam_code, email_id_id=s.email_id, role_id_id=2
                )
        self.stdout.write("Registered %d" % registration_table.objects.count())

    def _results(self, students):
        by_email = {s.email_id: s for s in students}
        for code, scores in RESULTS.items():
            exam = exam_details.objects.get(exam_code=code)
            for email, marks in scores.items():
                if email not in by_email:
                    continue
                percent = Decimal(marks * 100) / Decimal(exam.max_marks)
                score_table.objects.get_or_create(
                    exam_code_id=code,
                    email_id_id=email,
                    role_id_id=2,
                    defaults={
                        "scored_marks": marks,
                        "percentage": percent.quantize(Decimal("0.01")),
                    },
                )
        self.stdout.write("Results    %d" % score_table.objects.count())
