"""Authorization helpers for exam management.

The original views rely on login_required at most, and several exam-authoring
views had no decorator at all, so any logged-in student could create exams and
author questions. The decorators here put that decision in one place rather
than repeating role checks through views.py.

"Staff" here means anyone entitled to author exams:

- Django staff or superusers, which is how the admin account is set up, and
- users whose role is TEACHER (role_id 1), which is how the application itself
  models teachers.
"""

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

TEACHER_ROLE = 1
STUDENT_ROLE = 2


def is_exam_staff(user):
    """True when this user may create or change exams and questions."""
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    # role_id is a FK; read the raw column so an extra query is not needed.
    return getattr(user, 'role_id_id', None) == TEACHER_ROLE


def is_student(user):
    """True for an authenticated student account."""
    return user.is_authenticated and getattr(user, 'role_id_id', None) == STUDENT_ROLE


def staff_required(view_func):
    """Allow only exam staff.

    Anonymous users are sent to the login page so the normal sign-in flow still
    works; authenticated users who are not staff get 403 rather than a redirect,
    because logging in again would not help them and a redirect would hide the
    refusal.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(), settings.LOGIN_URL, 'next')
        if not is_exam_staff(request.user):
            raise PermissionDenied(
                'An exam staff account is required for this page.')
        return view_func(request, *args, **kwargs)

    return wrapper
