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


def dependencies_importable():
    """True when this interpreter can import everything settings.py needs.

    An interpreter may carry some of them and not others, which fails part way
    through startup, so check the whole set rather than just Django.
    """
    import importlib.util

    for module in ('django', 'rest_framework', 'whitenoise'):
        if importlib.util.find_spec(module) is None:
            return False
    return True


def reexec_in_venv():
    """Re-run this command under .venv when the current interpreter cannot.

    Only switches when something settings.py imports is missing here, so a
    build or hosting platform running manage.py with its own prepared
    interpreter is never hijacked, even if a .venv directory happens to be
    present in the project root.
    """
    if os.environ.get('XAMLYSIS_NO_REEXEC'):
        return
    # Hosting platforms prepare their own environment; never second guess it.
    if any(os.environ.get(v) for v in ('RENDER', 'VERCEL', 'DYNO', 'CI')):
        return
    if dependencies_importable():
        return
    target = venv_python()
    if not target:
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
