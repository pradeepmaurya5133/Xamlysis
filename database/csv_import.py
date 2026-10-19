"""Bulk question import from CSV, with a preview before anything is written.

Flow: upload -> validate every row -> show a preview with per-row errors ->
confirm -> write inside one transaction.

Deliberate choices:

- Duplicates are rejected, never overwritten. A ques_id that already exists, or
  that appears twice in the same file, is an error on that row. Re-importing
  the same file therefore rejects every row instead of silently doubling the
  bank or rewriting questions students have already answered.
- Nothing is written during validation. The parsed rows are held in the session
  until the import is confirmed, because the deployment target has no durable
  local filesystem between requests.
- The write is atomic: if any row fails on the way in, the whole import is
  rolled back rather than leaving a half-loaded exam.
"""

import csv
import io

from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect

from database.models import ques_table, exam_details
from database.permissions import staff_required

MAX_UPLOAD_BYTES = 2 * 1024 * 1024          # 2 MB
MAX_ROWS = 2000                              # keeps the session payload sane
SESSION_KEY = 'question_import_rows'

REQUIRED_COLUMNS = [
    'ques_id', 'exam_code', 'ques',
    'option1', 'option2', 'option3', 'option4',
    'correct', 'marks',
]
OPTIONAL_COLUMNS = ['difficulty', 'topic', 'explanation']


class UploadForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV file',
        help_text='Up to 2 MB and %d rows. Columns: %s (optional: %s).' % (
            MAX_ROWS, ', '.join(REQUIRED_COLUMNS), ', '.join(OPTIONAL_COLUMNS)),
    )

    def clean_csv_file(self):
        upload = self.cleaned_data['csv_file']
        if upload.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                'That file is %.1f MB. The limit is 2 MB.'
                % (upload.size / 1024 / 1024))
        if not upload.name.lower().endswith('.csv'):
            raise forms.ValidationError('Please upload a .csv file.')
        return upload


def _decode(upload):
    """Read the upload as text, tolerating a UTF-8 BOM from Excel."""
    raw = upload.read()
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('The file is not readable as text.')


def validate_rows(text):
    """Parse and check a CSV. Returns (valid_rows, errors, header_error).

    Nothing is written here. Each error is tied to the spreadsheet row number
    the person uploading will recognise, counting the header as row 1.
    """
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]

    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        return [], [], 'Missing required column(s): %s.' % ', '.join(missing)

    known_exams = set(exam_details.objects.values_list('exam_code', flat=True))
    existing_ids = set(ques_table.objects.values_list('ques_id', flat=True))
    valid_difficulties = {value for value, _ in ques_table.DIFFICULTY_CHOICES}

    seen_in_file = set()
    valid, errors = [], []

    for index, raw in enumerate(reader, start=2):      # header is row 1
        if index - 1 > MAX_ROWS:
            errors.append({
                'row': index,
                'ques_id': '',
                'problems': ['File has more than %d rows; nothing beyond that '
                             'was read.' % MAX_ROWS],
            })
            break

        row = {k: (v or '').strip() for k, v in raw.items() if k is not None}
        problems = []

        ques_id = row.get('ques_id', '')
        if not ques_id:
            problems.append('ques_id is required.')
        elif len(ques_id) > 50:
            problems.append('ques_id is longer than 50 characters.')
        elif ques_id in existing_ids:
            problems.append(
                'A question with id "%s" already exists. Duplicates are '
                'rejected, not overwritten.' % ques_id)
        elif ques_id in seen_in_file:
            problems.append('ques_id "%s" appears more than once in this file.'
                            % ques_id)

        exam_code = row.get('exam_code', '')
        if not exam_code:
            problems.append('exam_code is required.')
        elif exam_code not in known_exams:
            problems.append('No exam with code "%s".' % exam_code)

        if not row.get('ques'):
            problems.append('ques (the question text) is required.')

        options = [row.get('option%d' % n, '') for n in (1, 2, 3, 4)]
        if not all(options):
            problems.append('All four options are required.')
        elif len(set(options)) != 4:
            problems.append('The four options must all be different.')

        correct = row.get('correct', '')
        if correct not in ('1', '2', '3', '4'):
            problems.append('correct must be 1, 2, 3 or 4 (got "%s").' % correct)

        marks = row.get('marks', '')
        try:
            marks_value = int(marks)
            if marks_value <= 0:
                problems.append('marks must be greater than zero.')
        except (TypeError, ValueError):
            problems.append('marks must be a whole number (got "%s").' % marks)
            marks_value = 0

        difficulty = row.get('difficulty', '') or ques_table.MEDIUM
        if difficulty not in valid_difficulties:
            problems.append('difficulty must be one of: %s.'
                            % ', '.join(sorted(valid_difficulties)))

        topic = row.get('topic', '')
        if len(topic) > 120:
            problems.append('topic is longer than 120 characters.')

        if problems:
            errors.append({'row': index, 'ques_id': ques_id, 'problems': problems})
            continue

        seen_in_file.add(ques_id)
        valid.append({
            'row': index,
            'ques_id': ques_id,
            'exam_code': exam_code,
            'ques': row['ques'],
            'option1': options[0], 'option2': options[1],
            'option3': options[2], 'option4': options[3],
            'correct': int(correct),
            'marks': marks_value,
            'difficulty': difficulty,
            'topic': topic,
            'explanation': row.get('explanation', ''),
        })

    return valid, errors, None


@staff_required
def question_import(request):
    """Upload and preview. Nothing is written by this view."""
    form = UploadForm(request.POST or None, request.FILES or None)
    context = {'form': form, 'max_rows': MAX_ROWS,
               'required': REQUIRED_COLUMNS, 'optional': OPTIONAL_COLUMNS}

    if request.method == 'POST' and form.is_valid():
        try:
            text = _decode(form.cleaned_data['csv_file'])
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, 'question_import.html', context)

        valid, errors, header_error = validate_rows(text)
        if header_error:
            messages.error(request, header_error)
            return render(request, 'question_import.html', context)

        request.session[SESSION_KEY] = valid
        context.update({
            'previewed': True,
            'valid': valid,
            'valid_preview': valid[:20],
            'errors': errors,
            'error_preview': errors[:20],
        })

    return render(request, 'question_import.html', context)


@staff_required
def question_import_confirm(request):
    """Write the previewed rows. Atomic: all of them, or none."""
    if request.method != 'POST':
        return redirect('question_import')

    rows = request.session.get(SESSION_KEY)
    if not rows:
        messages.error(
            request, 'Nothing to import. Upload a file and review the preview first.')
        return redirect('question_import')

    # Re-check ids at commit time: another import or an edit may have created
    # one of them since the preview was generated.
    ids = [r['ques_id'] for r in rows]
    clashes = set(ques_table.objects.filter(ques_id__in=ids)
                  .values_list('ques_id', flat=True))
    if clashes:
        request.session.pop(SESSION_KEY, None)
        messages.error(
            request,
            'Import cancelled: %d question id(s) were created since the preview '
            '(%s). Nothing was written. Upload the file again to re-check it.'
            % (len(clashes), ', '.join(sorted(clashes)[:5])))
        return redirect('question_import')

    try:
        with transaction.atomic():
            ques_table.objects.bulk_create([
                ques_table(
                    ques_id=r['ques_id'],
                    exam_code_id=r['exam_code'],
                    ques=r['ques'],
                    option1=r['option1'], option2=r['option2'],
                    option3=r['option3'], option4=r['option4'],
                    correct=r['correct'], marks=r['marks'],
                    difficulty=r['difficulty'], topic=r['topic'],
                    explanation=r['explanation'],
                )
                for r in rows
            ])
    except Exception as exc:                      # pragma: no cover - safety net
        messages.error(
            request, 'Import failed and was rolled back. Nothing was written. (%s)' % exc)
        return redirect('question_import')

    count = len(rows)
    request.session.pop(SESSION_KEY, None)
    messages.success(request, 'Imported %d question%s.' % (count, '' if count == 1 else 's'))
    return redirect('question_bank')
