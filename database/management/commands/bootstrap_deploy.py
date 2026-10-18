"""Prepare a fresh deployment database in one step.

    python manage.py bootstrap_deploy --admin-password "<password>"

Applies migrations, creates the two roles the app assumes exist, loads the
professional course catalogue and creates (or resets) the admin account. Safe to
re-run: every step is idempotent, and nothing is deleted.

Intended for a brand new managed database, e.g. straight after connecting
Postgres to the Vercel project:

    DATABASE_URL="postgres://..." python manage.py bootstrap_deploy --admin-password "..."
"""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from database.models import User, role_id, class_stu_tech


class Command(BaseCommand):
    help = "Migrate, seed roles and courses, and create the admin account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-email",
            default="admin@xamlysis.test",
            help="Admin login (default: admin@xamlysis.test).",
        )
        parser.add_argument(
            "--admin-password",
            default=os.environ.get("DJANGO_ADMIN_PASSWORD"),
            help="Admin password. Falls back to the DJANGO_ADMIN_PASSWORD env var.",
        )
        parser.add_argument(
            "--skip-admin",
            action="store_true",
            help="Only migrate and seed; leave accounts alone.",
        )

    def handle(self, *args, **options):
        if not options["skip_admin"] and not options["admin_password"]:
            raise CommandError(
                "No admin password given. Pass --admin-password or set "
                "DJANGO_ADMIN_PASSWORD, or pass --skip-admin."
            )

        self.stdout.write(self.style.MIGRATE_HEADING("Applying migrations"))
        call_command("migrate", interactive=False, verbosity=1)

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding roles"))
        with transaction.atomic():
            role_id.objects.get_or_create(role_id=1, defaults={"role_name": "TEACHER"})
            role_id.objects.get_or_create(role_id=2, defaults={"role_name": "STUDENT"})
        self.stdout.write("  TEACHER and STUDENT present")

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding courses"))
        call_command("seed_courses", verbosity=1)

        if options["skip_admin"]:
            self.stdout.write(self.style.SUCCESS("\nDatabase ready (admin untouched)."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Admin account"))
        email = options["admin_email"]
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email_id=email,
                defaults={
                    "username": "admin", "first_name": "Site", "last_name": "Admin",
                    "mobile_no": "0", "role_id_id": 1,
                },
            )
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.role_id_id = 1
            user.set_password(options["admin_password"])
            user.save()
            class_stu_tech.objects.get_or_create(
                role_id_id=1, email_id_id=user.email_id, class_stu_tech=11
            )
        self.stdout.write("  %s %s" % ("created" if created else "password reset for", email))

        self.stdout.write(self.style.SUCCESS("\nDatabase ready."))
        self.stdout.write("  Sign in at /admin/ with %s" % email)
        self.stdout.write(
            "  Note: the admin login field is labelled Username but expects this email."
        )
