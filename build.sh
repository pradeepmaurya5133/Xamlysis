#!/usr/bin/env bash
# Render build step. Any non-zero exit fails the deploy, which is what we want:
# better to stop here than to start a server against an unmigrated database.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Collect static files for WhiteNoise to serve.
python manage.py collectstatic --no-input

# Migrate and seed roles and courses. bootstrap_deploy creates the admin when a
# password is available: the admin has the teacher role, and seed_exams needs a
# teacher to own the exams it creates.
if [ -n "$DJANGO_ADMIN_PASSWORD" ]; then
  python manage.py bootstrap_deploy
  python manage.py seed_exams
else
  echo "DJANGO_ADMIN_PASSWORD is not set: skipping the admin account."
  echo "Exams need a teacher to own them, so seed_exams is skipped too."
  python manage.py bootstrap_deploy --skip-admin
fi
