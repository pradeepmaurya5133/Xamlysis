"""Create one exam per course, each with a full 20 question paper.

    python manage.py seed_exams              # add anything missing, keep existing rows
    python manage.py seed_exams --reset      # delete these exams first, then rebuild
    python manage.py seed_exams --enrol      # also enrol demo students so the exams show

Questions come from _exam_bank.py, which holds 20 subject specific questions for
every course code. Each exam is worth 100 marks at 5 marks per question.

The bank lists the correct option first most of the time, which would make every
paper guessable by always picking option 1. Options are therefore rotated as
they are written, so within each paper the correct answer falls on option 1, 2,
3 and 4 in equal measure. Rotation keeps the options in their original relative
order and is derived from the question number, so re-running produces the same
paper rather than reshuffling it.

Everything is idempotent: exams and questions are keyed on their codes, so
running this twice adds nothing.
"""

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from database.models import (
    User, course_id, exam_details, ques_table, class_stu_tech, courses_availed,
)

from ._exam_bank import QUESTIONS

MARKS_PER_QUESTION = 5
START_TIME = datetime.time(10, 0)
DURATION = datetime.timedelta(hours=1)
FIRST_EXAM_IN_DAYS = 3


def rotate_options(options, correct, target):
    """Return options re-ordered so the correct one sits at position target.

    Both correct and target are 1-based. The relative order of the options is
    preserved, which keeps sequences such as numeric ranges readable.
    """
    shift = (target - correct) % 4
    if not shift:
        return list(options)
    return list(options[-shift:]) + list(options[:-shift])


class Command(BaseCommand):
    help = "Create an exam with a 20 question paper for every course."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the exams this command creates (and their questions) first.",
        )
        parser.add_argument(
            "--enrol",
            action="store_true",
            help="Enrol every student in every course and class so the exams are visible.",
        )
        parser.add_argument(
            "--teacher",
            help="Email of the teacher to own the exams. Defaults to the first teacher.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        teacher = self._teacher(options.get("teacher"))
        courses = list(course_id.objects.all().order_by("class_stu_tech", "course_id"))
        if not courses:
            raise CommandError("No courses found. Run seed_courses first.")

        if options["reset"]:
            self._reset(courses)

        created_exams, created_ques, skipped = self._build(courses, teacher)

        if options["enrol"]:
            self._enrol(courses)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "%d exam(s) and %d question(s) created." % (created_exams, created_ques)
            )
        )
        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    "No questions in the bank for: %s" % ", ".join(skipped)
                )
            )
        self.stdout.write(
            "  %d exams and %d questions in the database in total."
            % (exam_details.objects.count(), ques_table.objects.count())
        )

    # ------------------------------------------------------------------

    def _teacher(self, preferred):
        if preferred:
            try:
                return User.objects.get(email_id=preferred)
            except User.DoesNotExist:
                raise CommandError("No user with email %s" % preferred)
        teacher = (
            User.objects.filter(email_id="teacher@demo.test").first()
            or User.objects.filter(role_id_id=1).order_by("email_id").first()
        )
        if not teacher:
            raise CommandError(
                "No teacher account found. Create one, or run seed_demo first."
            )
        self.stdout.write("Exams will be owned by %s" % teacher.email_id)
        return teacher

    def _exam_code(self, course):
        return "%s-EXAM" % course.course_id

    def _reset(self, courses):
        codes = [self._exam_code(c) for c in courses]
        ques = ques_table.objects.filter(exam_code_id__in=codes)
        n_ques = ques.count()
        ques.delete()
        exams = exam_details.objects.filter(exam_code__in=codes)
        n_exams = exams.count()
        exams.delete()
        self.stdout.write(
            self.style.WARNING("Removed %d exam(s) and %d question(s)." % (n_exams, n_ques))
        )

    def _build(self, courses, teacher):
        today = datetime.date.today()
        created_exams = created_ques = 0
        skipped = []

        for offset, course in enumerate(courses):
            bank = QUESTIONS.get(course.course_id)
            if not bank:
                skipped.append(course.course_id)
                continue

            code = self._exam_code(course)
            exam, made = exam_details.objects.get_or_create(
                exam_code=code,
                defaults={
                    "exam_title": "%s Examination" % course.course_name,
                    "date": today + datetime.timedelta(days=FIRST_EXAM_IN_DAYS + offset),
                    "start_time": START_TIME,
                    "duration": DURATION,
                    "no_of_ques": len(bank),
                    "max_marks": len(bank) * MARKS_PER_QUESTION,
                    "course_id_id": course.course_id,
                    "email_id_id": teacher.email_id,
                    "class_stu": course.class_stu_tech,
                },
            )
            if made:
                created_exams += 1

            for n, (text, o1, o2, o3, o4, correct) in enumerate(bank, start=1):
                target = ((n - 1) % 4) + 1
                opts = rotate_options([o1, o2, o3, o4], correct, target)
                _, q_made = ques_table.objects.get_or_create(
                    ques_id="%s-Q%d" % (code, n),
                    defaults={
                        "ques": text,
                        "option1": opts[0], "option2": opts[1],
                        "option3": opts[2], "option4": opts[3],
                        "correct": target,
                        "marks": MARKS_PER_QUESTION,
                        "exam_code_id": code,
                    },
                )
                if q_made:
                    created_ques += 1

            if made:
                self.stdout.write(
                    "  + %-12s %-46s %d questions, class %d"
                    % (code, course.course_name, len(bank), course.class_stu_tech)
                )

        return created_exams, created_ques, skipped

    def _enrol(self, courses):
        """Avail every student of the courses that match the class they are in.

        A student only sees an exam when their class matches the exam's class and
        they have availed the course, so without this the new exams stay hidden.

        Classes are deliberately left alone: stu_home calls
        class_stu_tech.objects.get() for a student, which raises
        MultipleObjectsReturned if the student is in more than one class, so this
        never adds a second class row.
        """
        students = User.objects.filter(role_id_id=2)
        if not students:
            self.stdout.write(self.style.WARNING("No students to enrol."))
            return

        enrolled = 0
        for student in students:
            klasses = set(
                class_stu_tech.objects.filter(
                    email_id_id=student.email_id, role_id_id=2
                ).values_list("class_stu_tech", flat=True)
            )
            if not klasses:
                self.stdout.write(
                    self.style.WARNING(
                        "  %s is in no class yet, skipping" % student.email_id
                    )
                )
                continue
            for course in courses:
                if course.class_stu_tech not in klasses:
                    continue
                _, made = courses_availed.objects.get_or_create(
                    course_id_id=course.course_id,
                    role_id_id=2,
                    email_id_id=student.email_id,
                )
                enrolled += bool(made)

        self.stdout.write(
            "Availed %d student(s) of the courses for their own class (%d new rows)"
            % (students.count(), enrolled)
        )
