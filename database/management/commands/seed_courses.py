"""Add the professional / career-stream course catalogue.

    python manage.py seed_courses           # add anything missing, keep existing rows
    python manage.py seed_courses --list    # just print what is in the catalogue

Courses are offered to a class (the app models classes 1-12), so the
professional stream sits in classes 11 and 12 where students actually pick
electives. Running this twice is safe - existing rows are left alone.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from database.models import course_id

# course_id, course_name, class
COURSES = [
    # Computing and IT
    ("PYT11", "Python Programming", 11),
    ("WEB11", "Web Development", 11),
    ("DBS11", "Database Management Systems", 11),
    ("NET11", "Computer Networks", 11),
    ("DSA12", "Data Structures and Algorithms", 12),
    ("AIM12", "Artificial Intelligence and Machine Learning", 12),
    ("DSC12", "Data Science and Analytics", 12),
    ("CYB12", "Cyber Security", 12),
    ("CLD12", "Cloud Computing", 12),
    ("MOB12", "Mobile Application Development", 12),
    # Design and media
    ("UIX11", "UI/UX Design", 11),
    ("GRD11", "Graphic Design", 11),
    ("DGM11", "Digital Marketing", 11),
    ("ANM12", "Animation and Multimedia", 12),
    # Commerce and management
    ("ACC11", "Accountancy", 11),
    ("BST11", "Business Studies", 11),
    ("ECO11", "Economics", 11),
    ("STA11", "Statistics", 11),
    ("FIN12", "Financial Management", 12),
    ("ENT12", "Entrepreneurship Development", 12),
    ("BNK12", "Banking and Insurance", 12),
    ("HRM12", "Human Resource Management", 12),
    # Engineering and applied
    ("ELE11", "Electronics and Circuits", 11),
    ("ROB12", "Robotics and Automation", 12),
    ("MEC12", "Mechanical Engineering Basics", 12),
    ("CIV12", "Civil Engineering Basics", 12),
]


class Command(BaseCommand):
    help = "Seed the professional course catalogue (%d courses)." % len(COURSES)

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="Print the catalogue without writing anything.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["list"]:
            for code, name, klass in COURSES:
                self.stdout.write("  %-6s %-46s class %d" % (code, name, klass))
            self.stdout.write("")
            self.stdout.write("%d courses in the catalogue." % len(COURSES))
            return

        added = 0
        for code, name, klass in COURSES:
            _, created = course_id.objects.get_or_create(
                course_id=code,
                defaults={"course_name": name, "class_stu_tech": klass},
            )
            if created:
                added += 1
                self.stdout.write("  + %-6s %s" % (code, name))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Added %d course(s); %d already present. %d courses total."
                % (added, len(COURSES) - added, course_id.objects.count())
            )
        )
