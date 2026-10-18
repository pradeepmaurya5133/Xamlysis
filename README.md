# Xamlysis

An online examination portal built with Django. Teachers schedule exams, author
multiple-choice question papers and review results; students register for exams,
attempt them in the browser and get scored instantly.

> Originally written against **Django 3.2 / Python 3.9** with MySQL. It also runs
> on SQLite with no configuration, which is the default and the quickest way to
> get started.

---

## Features

**For teachers (`role_id = 1`)**
- Schedule an exam: code, title, date, start time, duration, question count, max marks, course and class
- Author the question paper (4 options per question, correct answer, per-question marks)
- Browse upcoming and past exams
- Read student queries and notes attached to an exam

**For students (`role_id = 2`)**
- Sign up, pick a class (1–12) and enrol in courses
- See upcoming exams and register for them
- Attempt an exam and get auto-graded on submit (score + percentage)
- Review previous exams, answers and results
- Raise queries and keep private notes per exam

**Shared**
- Custom user model keyed on email address
- Django admin at `/admin/` ("Xamlysis Admin Portal")
- Chat-bot and WebSocket echo scaffolding (Django Channels — currently disabled)

---

## Tech stack

| Layer     | Choice                                              |
|-----------|-----------------------------------------------------|
| Framework | Django (3.2 originally; verified on 5.2)            |
| Database  | SQLite by default, MySQL optional                   |
| Templates | Django templates, flat under `template/`            |
| Frontend  | Hand-written CSS in `static/`                       |
| Extras    | Django REST Framework, Pillow, Channels (scaffold)  |

---

## Quick start

From the project root (the directory containing `manage.py`):

### Fastest route

A launcher script is included that creates the virtualenv on first use, installs
dependencies and starts the server:

```powershell
.\run.ps1              # PowerShell, port 8000
.\run.ps1 8080         # custom port
```

```bat
run.bat                :: cmd.exe
```

Then open <http://127.0.0.1:8000/>.

> **Note:** `manage.py runserver` on its own will not work in PowerShell. PowerShell
> does not execute programs from the current directory, and `.py` files are not
> associated with the virtualenv's interpreter. Always invoke Python explicitly —
> `python manage.py runserver` with the venv active, or use `run.ps1` above.

### Manual setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# .venv\Scripts\activate.bat    # Windows cmd.exe
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install Django djangorestframework Pillow

# 3. Apply migrations
python manage.py migrate

# 4. Seed the two roles the app assumes exist (see "Required seed data")
python manage.py shell -c "from database.models import role_id; role_id.objects.get_or_create(role_id=1, defaults={'role_name':'TEACHER'}); role_id.objects.get_or_create(role_id=2, defaults={'role_name':'STUDENT'})"

# 5. Run it
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

### Python version note

The project originally pinned Python 3.9 and Django 3.2.6 via a `Pipfile`,
which was removed because it broke Vercel builds. Django 3.2 does **not**
build on Python 3.12+. If you are on a newer interpreter, install a current
Django instead of the pinned versions:

| Your Python | Install                                  |
|-------------|------------------------------------------|
| 3.9 – 3.11  | `Django==3.2.6` (the original pin) |
| 3.12 – 3.14 | `Django>=5.2`                            |

The codebase runs unmodified on Django 5.2 — this README was verified against
**Django 5.2.18 on Python 3.14**.

### Required seed data

The `User` model has a non-nullable `role_id` foreign key defaulting to `2`.
If the `role_id` table is empty, sign-up and most authenticated pages fail.
Seed it before creating any user (step 4 above):

| `role_id` | `role_name` |
|-----------|-------------|
| 1         | TEACHER     |
| 2         | STUDENT     |

### Demo dataset

A management command loads a complete, realistic dataset — the roles above plus
users, courses, exams, question papers, registrations and results:

```bash
python manage.py seed_demo           # add what is missing, keep existing rows
python manage.py seed_demo --reset   # wipe the demo rows first, then reseed
```

It creates **6 courses, 7 exam papers, 35 questions, 12 registrations and 7 results**:

| Exam         | Course           | When          | Marks | Questions |
|--------------|------------------|---------------|-------|-----------|
| `PHY-MID-01` | Physics          | 21 days ago   | 100   | 5         |
| `MAT-MID-01` | Mathematics      | 14 days ago   | 100   | 5         |
| `ENG-UT-01`  | English          | 7 days ago    | 50    | 5         |
| `PHY-UT-02`  | Physics          | today         | 50    | 5         |
| `CHE-UT-01`  | Chemistry        | in 5 days     | 50    | 5         |
| `BIO-FIN-01` | Biology          | in 12 days    | 100   | 5         |
| `CSC-QZ-01`  | Computer Science | in 20 days    | 50    | 5         |

Dates are relative to the day you run it, so there are always past, present and
future exams to look at. Accounts (all with password `Xamlysis@123`):

| Email               | Role    |
|---------------------|---------|
| `teacher@demo.test` | Teacher |
| `student@demo.test` | Student |
| `priya@demo.test`   | Student |
| `arjun@demo.test`   | Student |

The command is idempotent — running it twice changes nothing. Edit the `COURSES`,
`EXAMS`, `PAPERS` and `RESULTS` tables at the top of
`database/management/commands/seed_demo.py` to change what it loads.

### Creating an admin user

Because `USERNAME_FIELD` is `email_id`, `createsuperuser` prompts for an email:

```bash
python manage.py createsuperuser
```

---

## Using MySQL instead of SQLite

`settings.py` switches backends on an environment variable. Set `XAMLYSIS_DB=mysql`
and the project uses the MySQL block (database `xamlysis_datab` on
`localhost:3306`); leave it unset for SQLite.

```bash
pip install mysqlclient
set XAMLYSIS_DB=mysql           # Windows
# export XAMLYSIS_DB=mysql      # macOS / Linux
python manage.py migrate
```

Update the credentials in `Online_Exam_Portal_Xamlysis/settings.py` to match your
MySQL instance before running.

---

## Project layout

```
Xamlysis/
├── manage.py
├── run.ps1  run.bat                # dev-server launchers (create venv on first use)
├── db.sqlite3                      # SQLite database (schema migrated)
├── requirements.txt                 # pinned dependencies, used by Vercel
├── Online_Exam_Portal_Xamlysis/    # project package
│   ├── settings.py                 # SQLite/MySQL switch, custom user model
│   ├── urls.py                     # admin + database.urls
│   ├── routing.py                  # Channels WebSocket routing (unused)
│   ├── asgi.py  wsgi.py
├── database/                       # the single application
│   ├── models.py                   # User, exams, questions, answers, scores
│   ├── views.py                    # all view functions
│   ├── urls.py                     # URL table
│   ├── forms.py                    # ModelForms for sign-up, exams, questions
│   ├── admin.py                    # admin registration
│   ├── consumers.py                # Channels echo consumer
│   ├── management/commands/
│   │   └── seed_demo.py            # demo dataset loader
│   └── migrations/                 # 0001 … 0007
├── template/                       # all HTML templates (flat, not per-app)
├── static/                         # CSS and images
└── img/                            # SVG assets
```

### Data model

| Model                | Purpose                                                         |
|----------------------|-----------------------------------------------------------------|
| `User`               | `AbstractUser` keyed on `email_id`, plus `mobile_no`, `role_id` |
| `role_id`            | TEACHER (1) / STUDENT (2)                                       |
| `course_id`          | Course catalogue, scoped to a class                             |
| `class_stu_tech`     | Which class (1–12) a user belongs to                            |
| `courses_availed`    | User ↔ course enrolment                                         |
| `exam_details`       | Exam code, title, schedule, duration, marks, course, class      |
| `ques_table`         | MCQ: question, 4 options, correct option, marks                 |
| `answer_table`       | A student's marked option per question + correctness flag       |
| `score_table`        | Final marks and percentage per student per exam                 |
| `registration_table` | Student registrations for an exam                               |
| `notes_table`        | Private per-exam notes                                          |
| `query_table`        | Student queries raised against an exam                          |

`AUTH_USER_MODEL` is `database.User`.

---

## Key URLs

| Path                  | View           | Notes                                |
|-----------------------|----------------|--------------------------------------|
| `/`                   | `home`         | Landing page                         |
| `/about/`             | `about`        |                                      |
| `/features/`          | `features`     | Feature overview                     |
| `/how_it_works/`      | `how_it_works` | Step-by-step guide for both roles    |
| `/courses/`           | `courses`      | Live course catalogue                |
| `/faq/`               | `faq`          | Frequently asked questions           |
| `/contact/`           | `contact`      | Contact form and details             |
| `/login`              | `login`        | Working login (email + password)     |
| `/logout`             | `logout`       |                                      |
| `/sign_up/`           | `sign_up`      | Role chooser — student or teacher    |
| `/student_sign_up/`   | `stu_sign_up`  | Student registration                 |
| `/student_login/`     | `stu_login`    | Student login                        |
| `/teachers_login/`    | `teach_login`  | Teacher login                        |
| `/stu_home/`          | `stu_home`     | Student dashboard (login required)   |
| `/student_exams_scheduled/` | `stu_future` | Upcoming exams + register      |
| `/student_previous_exams/`  | `stu_prev`   | Past results and percentages   |
| `/teachers_home/`     | `teach_home`   | Teacher dashboard (login required)   |
| `/teachers_schedule/` | `teach_schedule` | Full timetable, past and upcoming  |
| `/teachers_future_exam_scheduled/` | `teach_future` | Scheduled exams + paper status |
| `/teachers_previous_exams_scheduled/` | `teach_prev` | Completed exams + class stats |
| `/chat_bot/`          | `chat_bot`     | Help and FAQ                         |
| `/class_select/`      | `class_select` | Pick your class                      |
| `/course_select`      | `course_select`| Enrol in courses                     |
| `/exam_detail`        | `exam_detail`  | Teacher: schedule an exam            |
| `/ques_setup`         | `ques_setup`   | Teacher: author questions            |
| `/test/`              | `test`         | Attempt an exam                      |
| `/correct_ans/`       | `correct_ans`  | Grading / results                    |
| `/query_page/`        | `query_page`   | Raise a query                        |
| `/add_notes/`         | `add_notes`    | Save notes                           |
| `/admin/`             | Django admin   |                                      |

Full table in `database/urls.py`.

---

## UI structure

### Content pages

Five public pages carry the explanatory content, so the app pages stay focused
on doing the work:

| Page             | URL              | What it holds                                                      |
|------------------|------------------|--------------------------------------------------------------------|
| Features         | `/features/`     | Split teacher/student sections, then six "under the hood" cards    |
| How It Works     | `/how_it_works/` | Numbered walkthroughs — 5 steps for students, 4 for teachers       |
| Courses          | `/courses/`      | Live catalogue grouped by class, with exam and question counts     |
| FAQ              | `/faq/`          | 14 questions in four groups, as collapsible `<details>` items      |
| Contact          | `/contact/`      | Message form plus direct contact details and shortcuts             |

The Courses page is data-driven — its counts come from `course_id`,
`exam_details` and `ques_table`, so it reflects whatever is actually loaded.

### Landing page

`/` runs eight sections: hero, three-stat strip, a role-aware panel, feature
cards, a three-step explainer, a teacher-focused split block, a four-question
FAQ preview, and a closing call to action.

The role-aware panel changes with the viewer:

| Viewer     | Panel               | Links to                                                            |
|------------|---------------------|---------------------------------------------------------------------|
| Anonymous  | Get Started         | Student login, teacher login, create account, FAQ                   |
| Student    | Your Exams          | Scheduled exams, previous results, classes & courses, raise a query |
| Teacher    | Your Teaching Tools | Exam timetable, upcoming exams, previous exams, create exam         |

The hero and closing CTA switch the same way — students get *Open Dashboard* and
*Scheduled Exams*, teachers get *Open Dashboard* and *Create Exam*. Role is read
from `user.role_id.role_id` (1 = teacher, 2 = student).

### Layouts

All templates live flat in `template/`. There are two layouts:

| Layout       | Use                                                                   |
|--------------|-----------------------------------------------------------------------|
| `base1.html` | Standard page — navbar, flash messages, footer. Almost everything.     |
| `base.html`  | Chrome-free — no navbar or footer. Splash and live exam pages only, where navigation away should not be offered. |

The `base1.html` navbar carries a Help dropdown (Help Centre, FAQ, How It Works,
About, Contact) for everyone. Logged-in users additionally get Dashboard, Classes
and Courses; anonymous visitors get Features, How It Works, Courses and a Sign Up
dropdown instead. The footer is organised into Explore, Support and Account
columns.

Styling is plain CSS in `static/`, driven by custom properties declared at the top
of `style.css` (`--ink`, `--accent`, `--panel`, `--line`, `--radius`, …). Change a
token there and it propagates across every page. Bootstrap 4 and Font Awesome are
pulled from a CDN for the grid and icons.

Reusable classes worth knowing: `.page-shell` (page width), `.page-heading`
(title + lead), `.table-panel` / `.table-panel-header` / `.table-panel-scroll`
(scrollable data tables), `.exam-card` and `.exam-list` (exam rows),
`.kpi-strip` / `.kpi-card` (summary numbers), `.form-card` / `.form-page`
(centred forms), `.action-card` (call-to-action tiles),
`.status-pill` with `.status-pass` / `.status-fail` / `.status-warn`,
`.empty-state` and `.empty-cell` (no-data messages).

Every list page renders an empty state rather than a blank panel when there is
no data, so pages stay readable on a fresh database.

---

## Known issues

These are pre-existing defects in the application code.

1. **`teach_sign_up` still writes to the removed `sign_up` model.** The page at
   `/teachers_sign_up/` renders, but submitting it raises `NameError` because
   `models.sign_up` is commented out. `/temp_sign_up` is the working sign-up flow.
   The same applies to `stu_sign_up` (`/student_sign_up/`).

2. **`add_notes` renders the sign-up template.** `/add_notes/` returns 200 but shows
   `stu_sign_up.html` instead of a notes form; no `add_notes.html` exists yet.

3. **Channels is disabled.** `'channels'` is commented out of `INSTALLED_APPS`, so
   `routing.py` and `consumers.py` are inert. `/chat_bot/` is a static help page
   rather than a live assistant.

4. **Secrets are committed.** `SECRET_KEY` is hard-coded and `DEBUG = True` in
   `settings.py`, and the MySQL password is in plain text. Move these to environment
   variables before deploying anywhere.

---

## Verified working

Checked against Django 5.2.18 on Python 3.14 with roles seeded.

**Public** — `/`, `/about/`, `/features/`, `/how_it_works/`, `/courses/`, `/faq/`,
`/contact/`, `/login`, `/sign_up/`, `/chat_bot/`, `/student_login/`,
`/teachers_login/`, `/teachers_sign_up/`, `/student_sign_up/`, `/quiz/`, `/show`,
`/index/`, `/check/`, `/add_notes/`, and `/admin/` (redirects to admin login).

**Authenticated (student)** — `/stu_home/`, `/student_exams_scheduled/`,
`/student_previous_exams/`, `/query_page/`, `/class_select/`, `/course_select`,
`/change_setting/`.

**Authenticated (teacher)** — `/teachers_schedule/`,
`/teachers_future_exam_scheduled/`, `/teachers_previous_exams_scheduled/`.

Pages decorated with `@login_required` redirect anonymous visitors to
`/login?next=…` (via `LOGIN_URL` in `settings.py`) instead of raising a 500.
That covers `stu_home`, `teach_home`, `class_select`, `course_select`,
`stu_future`, `stu_prev`, `teach_future`, `teach_prev` and `teach_schedule`.

Checked by crawling every `href` rendered across 28 pages as anonymous, student
and teacher — 84 page loads and 79 unique links, all returning 200 or a clean
302, no exceptions.

The `exam_delete/` links in `change_mobile_no.html` and `change_setting.html`
point at a URL that does not exist, but both sit inside HTML comments and are
inert in a browser.

Static assets under `/static/` serve correctly.
