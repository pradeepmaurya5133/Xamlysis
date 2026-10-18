# Xamlysis

An online examination portal built with Django. Teachers schedule exams, author
multiple-choice question papers and review results; students register for exams,
attempt them in the browser and get scored instantly.

> Originally written against **Django 3.2 / Python 3.9** with MySQL. It runs on
> SQLite with no configuration, which is the default and the quickest way to get
> started, and on Postgres via `DATABASE_URL` when deployed.

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
- A seeded catalogue of up to **32 courses, 39 exams and 780 questions** across
  computing, design, commerce, management and engineering
- Chat-bot and WebSocket echo scaffolding (Django Channels — currently disabled)

---

## Tech stack

| Layer      | Choice                                                     |
|------------|------------------------------------------------------------|
| Framework  | Django (3.2 originally; verified on 5.2)                   |
| Database   | SQLite locally, Postgres in deployment, MySQL optional     |
| Templates  | Django templates, flat under `template/`                   |
| Frontend   | Hand-written CSS in `static/`                              |
| Static     | WhiteNoise, served by the app itself                       |
| Server     | `runserver` locally, gunicorn in deployment                |
| Deployment | Render (`render.yaml` blueprint + `build.sh`)              |
| Extras     | Django REST Framework, Channels (scaffold, disabled)       |

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

> **Note:** `manage.py` re-executes itself under `.venv` when the interpreter
> running it has no Django installed, so `python manage.py runserver` works
> without activating the virtualenv first. It prints which interpreter it
> switched to. Set `XAMLYSIS_NO_REEXEC=1` to disable that and get the plain
> Django import error instead.

### Manual setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# .venv\Scripts\activate.bat    # Windows cmd.exe
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Migrate, seed the roles and the course catalogue, create the admin
python manage.py bootstrap_deploy --admin-password "ChooseSomethingStrong"

# 4. Create an exam with a 20 question paper for every course
python manage.py seed_exams

# 5. Run it
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

### Python version note

The project originally pinned Python 3.9 and Django 3.2.6 via a `Pipfile`. That
file has been removed: it declared an obsolete dependency set that cannot build
on a current interpreter, and its presence misled the deployment build into
using it instead of `requirements.txt`. Django 3.2 does **not** build on Python
3.12+. If you are on a newer interpreter, install a current Django instead of
the original pins:

| Your Python | Install                                  |
|-------------|------------------------------------------|
| 3.9 – 3.11  | `Django==3.2.6` (the original pin) |
| 3.12 – 3.14 | `Django>=5.2`                            |

The codebase runs unmodified on Django 5.2 — this README was verified against
**Django 5.2.18 on Python 3.14**.

### Required seed data

The `User` model has a non-nullable `role_id` foreign key defaulting to `2`.
If the `role_id` table is empty, sign-up and most authenticated pages fail.

| `role_id` | `role_name` |
|-----------|-------------|
| 1         | TEACHER     |
| 2         | STUDENT     |

`bootstrap_deploy` seeds both rows, loads the course catalogue and creates or
resets the admin account, all idempotently:

```bash
python manage.py bootstrap_deploy --admin-password "ChooseSomethingStrong"
python manage.py bootstrap_deploy --skip-admin      # migrate and seed only
```

The password can come from `DJANGO_ADMIN_PASSWORD` instead of the flag. The
command refuses to run without one unless `--skip-admin` is given, so it never
invents a credential.

### Demo dataset

A management command loads a complete, realistic dataset — the roles above plus
users, courses, exams, question papers, registrations and results:

```bash
python manage.py seed_demo           # add what is missing, keep existing rows
python manage.py seed_demo --reset   # wipe the demo rows first, then reseed
```

It creates **6 courses, 7 exam papers, 12 registrations and 7 results**. Each
paper starts with 5 questions; `topup_exams` raises every one to 20:

| Exam         | Course           | When          | Marks | Questions     |
|--------------|------------------|---------------|-------|---------------|
| `PHY-MID-01` | Physics          | 21 days ago   | 100   | 5 -> 20       |
| `MAT-MID-01` | Mathematics      | 14 days ago   | 100   | 5 -> 20       |
| `ENG-UT-01`  | English          | 7 days ago    | 50    | 5 -> 20       |
| `PHY-UT-02`  | Physics          | today         | 50    | 5 -> 20       |
| `CHE-UT-01`  | Chemistry        | in 5 days     | 50    | 5 -> 20       |
| `BIO-FIN-01` | Biology          | in 12 days    | 100   | 5 -> 20       |
| `CSC-QZ-01`  | Computer Science | in 20 days    | 50    | 5 -> 20       |

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

### Course catalogue and exam papers

Three commands build the academic content. All are idempotent, so re-running
them adds only what is missing.

```bash
python manage.py seed_courses          # 26 professional courses (32 with seed_demo)
python manage.py seed_courses --list   # print the catalogue without writing
python manage.py seed_exams            # one 20 question exam per course
python manage.py seed_exams --enrol    # also avail students of their class's courses
python manage.py seed_exams --reset    # delete those exams and rebuild
python manage.py topup_exams           # raise the seed_demo papers to 20 questions
python manage.py topup_exams --dry-run # report what would change
```

What you end up with depends on which commands you run:

| Commands run                              | Courses | Exams | Questions |
|-------------------------------------------|---------|-------|-----------|
| `seed_courses` + `seed_exams`             | 26      | 26    | 520       |
| `seed_demo` as well, plus `topup_exams`   | 32      | 39    | 780       |

`seed_courses` loads the 26 professional courses; the six school subjects
(Physics, Mathematics, Chemistry, Biology, Computer Science, English) come from
`seed_demo`, along with the seven exams that `topup_exams` fills out. The full
catalogue splits 18 courses in class 11 and 14 in class 12.

Questions live in two banks, separate from the commands that load them:

| File                                          | Holds                                     |
|-----------------------------------------------|-------------------------------------------|
| `database/management/commands/_exam_bank.py`  | 20 questions for each of the 32 courses   |
| `database/management/commands/_topup_bank.py` | 15 extra for each of the 7 `seed_demo` exams |

Each bank entry is `(text, option1, option2, option3, option4, correct_option)`
with a 1-based correct option. The banks mostly list the correct option first,
which on its own would let a student pass by always picking option 1. Both
commands therefore rotate the options as they write, so within every paper the
answer falls on option 1, 2, 3 and 4 in equal measure. Rotation is derived from
the question number, so a re-run reproduces the same paper rather than
reshuffling it. Across all 780 questions the key sits at exactly 25% per
position.

`topup_exams` keeps each exam's existing `max_marks` rather than raising it, so
results already recorded against a paper stay valid: a 100 mark paper becomes
20 questions worth 5, and a 50 mark paper becomes ten worth 3 and ten worth 2.
It refuses to run if any answers have been recorded against those exams, since
re-marking a paper someone has already sat would change their score.

**Visibility.** A student sees an exam only when the exam's class matches the
class they are in *and* they have availed the course. `seed_exams --enrol` wires
that up for existing students, and deliberately does not add a second class row
— see Known issues.

### Creating an admin user

`bootstrap_deploy` is the quickest route; it sets `is_staff`, `is_superuser` and
the TEACHER role, so the account works in the admin and on the teacher pages:

```bash
python manage.py bootstrap_deploy --admin-password "ChooseSomethingStrong"
```

It defaults to `admin@xamlysis.test`; pass `--admin-email` for another address.
Or use Django's own command — because `USERNAME_FIELD` is `email_id` it prompts
for an email rather than a username:

```bash
python manage.py createsuperuser
```

> **Signing in:** the admin login form labels its first field **Username**, but
> the project keys users on their email address, so type the email there.

---

## Using MySQL instead of SQLite

`settings.py` picks a backend in this order:

1. `XAMLYSIS_DB=mysql` -> MySQL, configured from the `MYSQL_*` variables below
2. `DATABASE_URL` set -> that database, parsed by `dj-database-url` with SSL required
3. neither -> SQLite at `db.sqlite3`

```bash
pip install mysqlclient
set XAMLYSIS_DB=mysql           # Windows
# export XAMLYSIS_DB=mysql      # macOS / Linux
set MYSQL_PASSWORD=yourpassword
python manage.py migrate
```

Credentials are read from the environment, not stored in `settings.py`.

---

## Environment variables

Nothing below is required for local development; the defaults give a working
SQLite setup with `DEBUG` on.

| Variable                      | Effect                                                              |
|-------------------------------|---------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`           | Signing key. **Always set this in deployment** — the fallback is a development key committed to this repo. |
| `DJANGO_DEBUG`                | `1` forces debug on, `0` forces it off. Unset means on locally and off on any recognised platform. |
| `DJANGO_ALLOWED_HOSTS`        | Extra hosts, comma separated, added to the built-in list            |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Extra trusted origins, comma separated                              |
| `DATABASE_URL`                | Postgres (or any `dj-database-url`) connection string               |
| `DJANGO_ADMIN_PASSWORD`       | Password `bootstrap_deploy` gives the admin account                 |
| `XAMLYSIS_DB`                 | `mysql` selects the MySQL backend                                   |
| `MYSQL_NAME` `MYSQL_USER` `MYSQL_PASSWORD` `MYSQL_HOST` `MYSQL_PORT` | MySQL connection details        |
| `XAMLYSIS_NO_REEXEC`          | `1` stops `manage.py` switching to `.venv`                          |
| `RENDER` / `VERCEL` / `DYNO`  | Set by the host. Any of them turns `DEBUG` off and enables secure cookies, HSTS and the HTTPS redirect. |
| `RENDER_EXTERNAL_HOSTNAME`    | Set by Render; added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`  |

---

## Deployment (Render)

`render.yaml` is a Blueprint: it declares the web service and a free Postgres
database together, so Render wires `DATABASE_URL` between them and generates
`DJANGO_SECRET_KEY` and `DJANGO_ADMIN_PASSWORD` itself. No manual environment
variables.

1. Render dashboard -> **New** -> **Blueprint**
2. Point it at this repository and **Apply**
3. Read `DJANGO_ADMIN_PASSWORD` from the service's **Environment** tab to sign
   in at `/admin/` as `admin@xamlysis.test`

| File               | Role                                                      |
|--------------------|-----------------------------------------------------------|
| `render.yaml`      | Web service + Postgres, region, plan, env vars            |
| `build.sh`         | Install, `collectstatic`, migrate, seed. Exits non-zero on failure so a bad migration stops the deploy |
| `.python-version`  | Pins the interpreter to 3.12                              |
| `requirements.txt` | Pinned dependencies                                       |

The start command is `gunicorn Online_Exam_Portal_Xamlysis.wsgi:application`.
Static files are served by WhiteNoise from inside the app, so no separate static
host is needed; `WHITENOISE_USE_FINDERS` keeps that working whether or not
`collectstatic` has run.

On Render's free plan the service sleeps after about 15 minutes idle, so the
first request after a quiet spell takes 30–60 seconds to wake.

> **Serverless hosts.** An earlier attempt to deploy to Vercel was abandoned.
> Django needs a persistent process and a writable filesystem; on serverless
> every cold start pays Django's startup inside a short function timeout, and
> SQLite cannot persist at all. `wsgi.py` still exposes `app` alongside
> `application` for such platforms, which is harmless under gunicorn.

---

## Project layout

```
Xamlysis/
├── manage.py                       # re-execs under .venv if Django is missing
├── run.ps1  run.bat                # dev-server launchers (create venv on first use)
├── requirements.txt                # pinned dependencies
├── render.yaml                     # Render blueprint: web service + Postgres
├── build.sh                        # Render build: install, collectstatic, migrate, seed
├── .python-version                 # interpreter pin for the host
├── db.sqlite3                      # local SQLite database (untracked)
├── Online_Exam_Portal_Xamlysis/    # project package
│   ├── settings.py                 # env-driven config, custom user model
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
│   │   ├── seed_demo.py            # demo users, courses, exams and results
│   │   ├── seed_courses.py         # 26 professional courses
│   │   ├── seed_exams.py           # one 20 question exam per course
│   │   ├── _exam_bank.py           # 640 questions, 20 per course
│   │   ├── topup_exams.py          # raises the seed_demo papers to 20 questions
│   │   ├── _topup_bank.py          # 105 questions, 15 per demo exam
│   │   └── bootstrap_deploy.py     # migrate + seed + admin, for a fresh database
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

4. **A student in two classes breaks their dashboard.** `stu_home` calls
   `class_stu_tech.objects.get(email_id=...)` (`database/views.py:261`), which
   assumes exactly one class per student. `/class_select/` lets a student join
   several, and the second one turns `/stu_home/` into a 500 with
   `get() returned more than one class_stu_tech`. Reachable through normal UI
   use; `seed_exams --enrol` avoids it by never adding a second class row.

5. **A stray exam exists in the shipped SQLite file.** Exam code `test`
   ("test 1") has `no_of_ques = 20` but no questions, and sits in class 1 where
   no student is enrolled, so nothing renders it. Harmless, but it fails the
   "every exam has 20 questions" check.

### Fixed since first release

- **Secrets are no longer hard-coded.** `SECRET_KEY`, `DEBUG` and the MySQL
  credentials come from the environment. The committed fallback key is for
  development only — set `DJANGO_SECRET_KEY` in deployment. Note that the old
  MySQL password remains in this repository's git history, so treat it as
  compromised and rotate it anywhere it was used.
- **`DEBUG` can no longer be left on by accident.** It is off whenever a
  platform variable (`RENDER`, `VERCEL`, `DYNO`) is present, not only on one
  named host.

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

**Exam content** — every one of the 39 real exams carries 20 questions whose
marks sum to that exam's `max_marks`, and the answer key is 25% on each of the
four options across all 780 questions. Grading was checked by submitting papers
through the `/test/` view: an all-correct submission scores full marks and an
all-wrong submission scores zero, on 100 mark papers and on 50 mark papers with
the uneven 3/2 mark split. All seven `seed_demo` results still agree with their
stored marks after the top-up.

**Fresh install** — the Quick start steps were run against an empty database:
`bootstrap_deploy` seeded 2 roles, 26 courses and the admin account,
`seed_exams` added 26 exams and 520 questions, and `topup_exams` correctly
skipped the `seed_demo` exams that were not present. Every exam ended up with
exactly 20 questions.

**Deployment path** — the gunicorn target
`Online_Exam_Portal_Xamlysis.wsgi:application` was loaded with `RENDER` set and
asked for `/`, `/courses/`, `/contact/`, `/static/style.css` and
`/admin/login/`: all 200, `DEBUG` off, HTTPS redirect on, static files served by
WhiteNoise. `manage.py check --deploy` reports no issues once
`DJANGO_SECRET_KEY` is set.
