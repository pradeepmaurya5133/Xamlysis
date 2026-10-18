#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import subprocess
import sys


def venv_python():
    """Path to the project virtualenv interpreter, if there is one."""
    name = 'python.exe' if os.name == 'nt' else 'python'
    folder = 'Scripts' if os.name == 'nt' else 'bin'
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv', folder, name)
    return path if os.path.exists(path) else None


def reexec_in_venv():
    """Re-run this command under .venv whenever we are not already in it.

    The project's dependencies live in .venv, so a global interpreter may have
    some of them (Django) and not others (rest_framework, PIL) and fail halfway
    through startup. Switching unconditionally avoids guessing which.
    """
    target = venv_python()
    if not target or os.environ.get('XAMLYSIS_NO_REEXEC'):
        return
    if os.path.normcase(target) == os.path.normcase(os.path.abspath(sys.executable)):
        return
    sys.stderr.write('Using project virtualenv: %s\n\n' % target)
    env = dict(os.environ, XAMLYSIS_NO_REEXEC='1')
    sys.exit(subprocess.call([target, os.path.abspath(__file__)] + sys.argv[1:], env=env))


def main():
    """Run administrative tasks."""
    reexec_in_venv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Online_Exam_Portal_Xamlysis.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
