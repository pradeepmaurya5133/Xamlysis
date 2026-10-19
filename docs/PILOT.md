# Pilot operations: backup, recovery, rollback and test checklist

Written for a controlled pilot of 1–2 teachers and 5–10 students on the live
deployment. Every command here is read-only or additive unless explicitly
marked. Nothing in this document resets, truncates or recreates a database.

---

## 1. Back up PostgreSQL

The database is Neon Postgres, reached through `DATABASE_URL` in the Vercel
project. Read the value from **Project → Settings → Environment Variables**, or
`vercel env pull` into a local `.env.local` that is already gitignored.

```bash
# Full logical backup, custom format so it can be restored selectively.
pg_dump --no-owner --no-acl --format=custom \
        --file="xamlysis-$(date +%Y%m%d-%H%M).dump" "$DATABASE_URL"

# A plain-SQL copy as well is useful for grepping and for eyeballing a diff.
pg_dump --no-owner --no-acl --format=plain \
        --file="xamlysis-$(date +%Y%m%d-%H%M).sql" "$DATABASE_URL"
```

Take one **before each deployment** during the pilot, and one at the end of each
exam day. Keep them off the laptop that runs the pilot.

Neon also keeps its own point-in-time history; the dumps above are what you
control and can restore anywhere.

## 2. Verify a backup is actually restorable

A dump that has never been restored is a guess, not a backup.

```bash
# List its contents. Fails loudly if the file is truncated or corrupt.
pg_restore --list xamlysis-20261019-1200.dump | head -30

# Row counts in the dump, to compare against production.
grep -c "INSERT INTO" xamlysis-20261019-1200.sql
```

Then restore it somewhere isolated (next section) and compare counts:

```sql
SELECT 'courses', count(*) FROM database_course_id
UNION ALL SELECT 'exams',     count(*) FROM database_exam_details
UNION ALL SELECT 'questions', count(*) FROM database_ques_table
UNION ALL SELECT 'users',     count(*) FROM database_user
UNION ALL SELECT 'attempts',  count(*) FROM database_examattempt
UNION ALL SELECT 'legacy',    count(*) FROM database_score_table;
```

## 3. Restore into an isolated test environment

**Never restore over production.** Create a separate database first.

```bash
# A throwaway local database. Nothing here touches the live one.
createdb xamlysis_restore_test
pg_restore --no-owner --no-acl --dbname=xamlysis_restore_test \
           xamlysis-20261019-1200.dump

# Point the app at the copy and check it boots against real data.
DATABASE_URL="postgres://localhost/xamlysis_restore_test" \
  python manage.py check
DATABASE_URL="postgres://localhost/xamlysis_restore_test" \
  python manage.py showmigrations database
```

Run the row-count query above against the copy and confirm the numbers match
the production figures you recorded at backup time.

## 4. Review pending migrations before deploying

```bash
python manage.py showmigrations database        # [X] applied, [ ] pending
python manage.py makemigrations --check --dry-run   # "No changes detected" is what you want
python manage.py sqlmigrate database 00NN       # the exact SQL a migration will run
```

On SQLite `sqlmigrate` shows a table rebuild (CREATE/INSERT/DROP/RENAME). That
is a SQLite implementation detail: PostgreSQL runs `ALTER TABLE ... ADD COLUMN`
for the same migration. Check the SQL against a Postgres connection if the
distinction matters for a particular change.

`build.sh` runs `migrate` on every deployment, so a pending migration applies
during the build. Review it **before** pushing, not after.

## 5. Roll back a release

Code first; only touch the schema if you must.

```bash
# Roll back the application to the previous commit set.
git revert <sha> [<sha> ...]
git push origin main          # triggers a rebuild and redeploy

# Or promote a known-good deployment directly, with no rebuild.
vercel ls                     # find the last good deployment URL
vercel promote <deployment-url>
```

Schema rollback, only when the new code is gone and the columns are genuinely
in the way:

```bash
python manage.py migrate database 0008    # step back one migration
```

Migrations 0008 and 0009 are additive. Reversing 0009 drops `difficulty` and
`topic` from `ques_table`; nothing in scoring reads them. Reversing 0008 would
drop the attempt tables and **destroy every recorded attempt**, so do not
reverse it once students have sat exams — revert the code instead.

---

## 6. Pilot test checklist

Use dedicated pilot accounts and one dedicated test exam. Do not use real
student personal data: initials and a pilot email alias are enough.

### Setup, by an administrator

- [ ] Take a backup (section 1) and record the row counts
- [ ] Create teacher accounts in Django admin at `/admin/` — set **role_id = 1**
      and tick **staff** if they should reach the admin as well. Teachers can no
      longer self-register as teachers; this is deliberate.
- [ ] Create or pick a test exam: short duration (10 minutes), 5 questions,
      `max_attempts = 2`, `pass_percentage = 50`, `is_published = true`
- [ ] Confirm the exam's **class** matches the class the pilot students will join

### Teacher checks

- [ ] Log in at `/login` with the email address (the field is labelled
      "Username" but expects the email)
- [ ] `/staff/questions/` lists questions; filter by course, class and difficulty
- [ ] Open a question preview: the correct answer and explanation are visible
- [ ] Create one question and edit another; confirm the warning appears when the
      question has already been answered in a scored attempt
- [ ] `/staff/questions/import/`: upload a small CSV, confirm the preview shows
      row-level errors, then import and confirm only the valid rows landed
- [ ] `/staff/analytics/` renders; after students have finished, check the exam
      breakdown and a per-student page

### Student checks, one student doing each

- [ ] Register at `/temp_sign_up`, then log in
- [ ] Join a class at `/class_select/` and a course at `/course_select/`
- [ ] `/dashboard/` shows the exam with its type label and attempts remaining
- [ ] Start the exam; answer three questions, mark one for review
- [ ] **Reload the page.** Answers and the review flag must come back, and the
      timer must continue from where it was, not restart
- [ ] **Open the exam in a second tab.** Both show the same remaining time
- [ ] **Disconnect the network briefly**, change an answer, reconnect. The page
      reports that it could not save, and saves again on the next change
- [ ] Submit. Confirm marks, percentage and pass/fail match the answers given
- [ ] Try to resume the submitted attempt: it must show the result, not reopen
- [ ] Press submit twice quickly on a second attempt: the score must not change
- [ ] Let one attempt run out of time without submitting: it must auto-submit
      and show a result marked as auto-submitted

### Security checks, done deliberately

- [ ] Copy another student's result URL (`/exams/attempt/<id>/result/`) and open
      it as a different student: expect **404**
- [ ] As a student, open `/staff/questions/`, `/staff/analytics/`, `/exam_detail`
      and `/teachers_schedule/`: expect **403** on each
- [ ] As a student, open a question preview URL directly: expect **403**
- [ ] Log out and open `/dashboard/`: expect a redirect to `/login`
- [ ] Open `/exams/attempt/999999/`: expect **404**, not a 500
- [ ] View the exam page source during an attempt and search for the word
      "correct": the answer key must not be present

### Layout

- [ ] Dashboard, exam page and result page on a phone: the question palette
      moves below the question, stat tiles stack, nothing scrolls sideways
- [ ] The same three pages at desktop width

### After the pilot

- [ ] Take another backup
- [ ] Check `vercel logs --deployment xamlysis.vercel.app` for errors raised
      during the session
- [ ] Review `/staff/analytics/` for participation, averages and the questions
      most often missed

---

## 7. Investigating a failure during the pilot

Application errors reach Vercel's runtime logs, because Django writes
tracebacks to stderr and the platform captures it. This has been used in
practice on this project to find a real import error.

```bash
vercel logs --deployment xamlysis.vercel.app
```

`DEBUG` is off in production, so students see a plain error page and the detail
stays in the logs rather than on screen.

What to look for:

| Symptom | Where to look |
|---|---|
| A page 500s | `vercel logs`, find the traceback and the request path |
| An answer did not save | The exam page shows a save error; the request is a POST to `/exams/attempt/<id>/save/` |
| A submission did not score | `/admin/database/examattempt/` — check status, and whether answers exist |
| A result looks wrong | The attempt row holds the recorded score; `AttemptAnswer` holds the per-question verdicts |

Vercel's log retention is short. For anything that needs keeping, copy the
relevant lines out at the time.
