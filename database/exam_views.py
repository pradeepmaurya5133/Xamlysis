"""The exam engine: catalogue, sitting an exam, scoring and history.

Kept in its own module rather than appended to views.py, which is already more
than 1300 lines of the original application. Nothing here replaces those views;
the legacy /test/ route now redirects into this flow so there is one code path
for sitting an exam rather than two.

Security rules enforced here, not in the template:

- every view requires a login, and an attempt can only ever be read or written
  by the student it belongs to
- the deadline lives on the attempt row, so reloading, opening a second tab or
  changing the client clock cannot extend an exam
- the correct answer never reaches the browser until the attempt is submitted
- submission is idempotent and guarded by a row lock, so a double click or a
  resubmitted form cannot score an attempt twice or overwrite a result
"""

import json
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, Http404, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from database.models import (
    ExamAttempt, AttemptAnswer, exam_details, ques_table, course_id,
    answer_table, score_table, class_stu_tech, courses_availed,
)

STUDENT_ROLE = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _student_classes(user):
    """The classes this user belongs to.

    Uses filter() rather than get(): a student may legitimately join more than
    one class through /class_select/, and assuming a single row is what makes
    the original stu_home view raise MultipleObjectsReturned.
    """
    return set(
        class_stu_tech.objects.filter(email_id_id=user.email_id)
        .values_list('class_stu_tech', flat=True)
    )


def _availed_courses(user):
    return set(
        courses_availed.objects.filter(email_id_id=user.email_id)
        .values_list('course_id_id', flat=True)
    )


def _get_own_attempt(request, attempt_id):
    """Fetch an attempt, 404ing for anyone who does not own it.

    404 rather than 403 so the response does not confirm that an attempt with
    that id exists for some other student.
    """
    try:
        return ExamAttempt.objects.select_related('exam').get(
            pk=attempt_id, student_id=request.user.email_id
        )
    except ExamAttempt.DoesNotExist:
        raise Http404('No such attempt')


def _expire_if_due(attempt):
    """Auto-submit an attempt whose time ran out while the student was away."""
    if attempt.status == ExamAttempt.IN_PROGRESS and timezone.now() >= attempt.expires_at:
        score_attempt(attempt, auto_submitted=True)
        return True
    return False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

@transaction.atomic
def score_attempt(attempt, auto_submitted=False):
    """Mark an attempt and write the result. Safe to call more than once.

    The row is locked and the status re-read inside the transaction, so two
    concurrent submissions cannot both score it.
    """
    locked = ExamAttempt.objects.select_for_update().get(pk=attempt.pk)
    if locked.status != ExamAttempt.IN_PROGRESS:
        return locked

    questions = {q.ques_id: q for q in ques_table.objects.filter(exam_code_id=locked.exam_id)}
    answers = {a.question_id: a for a in AttemptAnswer.objects.filter(attempt=locked)}

    score = 0
    total = 0
    correct = wrong = unanswered = 0

    for ques_id, question in questions.items():
        total += question.marks
        answer = answers.get(ques_id)
        if answer is None or answer.selected_option is None:
            unanswered += 1
            continue
        if answer.selected_option == question.correct:
            score += question.marks
            correct += 1
            answer.is_correct = True
        else:
            wrong += 1
            answer.is_correct = False
        answer.save(update_fields=['is_correct'])

    percentage = Decimal(0)
    if total:
        percentage = (Decimal(score) * 100 / Decimal(total)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    locked.score = score
    locked.max_marks = total
    locked.percentage = percentage
    locked.passed = percentage >= locked.exam.pass_percentage
    locked.correct_count = correct
    locked.wrong_count = wrong
    locked.unanswered_count = unanswered
    locked.status = ExamAttempt.SUBMITTED
    locked.auto_submitted = auto_submitted
    locked.submitted_at = timezone.now()
    locked.save()

    _write_legacy_rows(locked, questions, answers)
    return locked


def _write_legacy_rows(attempt, questions, answers):
    """Mirror the result into answer_table and score_table.

    The original "previous exams" and "correct answers" pages read those two
    tables, so writing them keeps the old screens working against results
    produced by the new engine instead of stranding them on legacy data.
    """
    role = attempt.student.role_id_id or STUDENT_ROLE

    answer_table.objects.filter(
        exam_code_id=attempt.exam_id, email_id_id=attempt.student_id
    ).delete()
    rows = []
    for ques_id, answer in answers.items():
        if answer.selected_option is None:
            continue
        rows.append(answer_table(
            exam_code_id=attempt.exam_id,
            ques_id_id=ques_id,
            email_id_id=attempt.student_id,
            role_id_id=role,
            option_marked=answer.selected_option,
            check_correct=bool(answer.is_correct),
        ))
    if rows:
        answer_table.objects.bulk_create(rows)

    score_table.objects.update_or_create(
        exam_code_id=attempt.exam_id,
        email_id_id=attempt.student_id,
        role_id_id=role,
        defaults={'scored_marks': attempt.score, 'percentage': attempt.percentage},
    )


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

@login_required
def exam_catalogue(request):
    """Class -> course -> practice tests and full-length exams."""
    my_classes = _student_classes(request.user)
    my_courses = _availed_courses(request.user)

    attempts = ExamAttempt.objects.filter(student_id=request.user.email_id)
    attempts_by_exam = {}
    for a in attempts:
        attempts_by_exam.setdefault(a.exam_id, []).append(a)

    exams = (
        exam_details.objects.filter(is_published=True)
        .select_related('course_id')
        .order_by('class_stu', 'course_id__course_name', 'exam_title')
    )

    classes = {}
    for exam in exams:
        course = exam.course_id
        entry = {
            'exam': exam,
            'attempts': attempts_by_exam.get(exam.exam_code, []),
            'attempts_used': len(attempts_by_exam.get(exam.exam_code, [])),
            'enrolled': course.course_id in my_courses,
        }
        bucket = classes.setdefault(exam.class_stu, {})
        course_bucket = bucket.setdefault(course.course_id, {
            'course': course, 'practice': [], 'full': [],
        })
        key = 'practice' if exam.exam_type == exam_details.PRACTICE else 'full'
        course_bucket[key].append(entry)

    ordered = []
    for class_no in sorted(classes):
        ordered.append({
            'class_no': class_no,
            'is_my_class': class_no in my_classes,
            'courses': [classes[class_no][c] for c in sorted(classes[class_no])],
        })

    return render(request, 'exam_catalogue.html', {
        'classes': ordered,
        'my_classes': sorted(my_classes),
        'total_exams': exams.count(),
    })


# ---------------------------------------------------------------------------
# Sitting an exam
# ---------------------------------------------------------------------------

@login_required
def start_attempt(request, exam_code):
    """Resume an open attempt, or begin a new one if the limit allows."""
    exam = get_object_or_404(exam_details, pk=exam_code, is_published=True)

    if not ques_table.objects.filter(exam_code_id=exam.exam_code).exists():
        return render(request, 'exam_blocked.html', {
            'exam': exam,
            'reason': 'This exam has no questions yet, so it cannot be started.',
        }, status=409)

    open_attempt = ExamAttempt.objects.filter(
        exam=exam, student_id=request.user.email_id, status=ExamAttempt.IN_PROGRESS
    ).first()
    if open_attempt:
        if not _expire_if_due(open_attempt):
            return redirect('exam_take', attempt_id=open_attempt.pk)
        return redirect('exam_result', attempt_id=open_attempt.pk)

    used = ExamAttempt.objects.filter(exam=exam, student_id=request.user.email_id).count()
    if exam.max_attempts and used >= exam.max_attempts:
        return render(request, 'exam_blocked.html', {
            'exam': exam,
            'reason': 'You have used all %d attempts for this exam.' % exam.max_attempts,
        }, status=403)

    attempt = ExamAttempt.objects.create(
        exam=exam,
        student=request.user,
        attempt_no=used + 1,
        expires_at=timezone.now() + exam.duration,
        max_marks=exam.max_marks,
    )
    return redirect('exam_take', attempt_id=attempt.pk)


@login_required
def take_exam(request, attempt_id):
    """The exam interface. Never receives the correct answers."""
    attempt = _get_own_attempt(request, attempt_id)

    if _expire_if_due(attempt) or attempt.status != ExamAttempt.IN_PROGRESS:
        return redirect('exam_result', attempt_id=attempt.pk)

    questions = list(
        ques_table.objects.filter(exam_code_id=attempt.exam_id).order_by('ques_id')
    )
    saved = {
        a.question_id: a
        for a in AttemptAnswer.objects.filter(attempt=attempt)
    }

    payload = []
    for index, q in enumerate(questions, start=1):
        answer = saved.get(q.ques_id)
        payload.append({
            'number': index,
            'id': q.ques_id,
            'text': q.ques,
            'marks': q.marks,
            'options': q.options(),
            'selected': answer.selected_option if answer else None,
            'marked': answer.marked_for_review if answer else False,
        })

    return render(request, 'exam_take.html', {
        'attempt': attempt,
        'exam': attempt.exam,
        # json_script in the template escapes this safely; it carries no answer key
        'questions_json': payload,
        'seconds_remaining': attempt.seconds_remaining(),
        'total_questions': len(questions),
    })


@login_required
@require_POST
def save_answer(request, attempt_id):
    """Autosave one answer. Returns JSON; never reveals whether it is right."""
    attempt = _get_own_attempt(request, attempt_id)

    if attempt.status != ExamAttempt.IN_PROGRESS:
        return JsonResponse({'ok': False, 'reason': 'submitted'}, status=409)
    if timezone.now() >= attempt.expires_at:
        score_attempt(attempt, auto_submitted=True)
        return JsonResponse({'ok': False, 'reason': 'expired'}, status=409)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest('Malformed JSON')

    question_id = body.get('question_id')
    selected = body.get('selected_option')
    marked = bool(body.get('marked_for_review', False))

    if selected is not None:
        try:
            selected = int(selected)
        except (TypeError, ValueError):
            return HttpResponseBadRequest('selected_option must be an integer')
        if selected not in (1, 2, 3, 4):
            return HttpResponseBadRequest('selected_option out of range')

    # The question must belong to this attempt's exam, so a crafted request
    # cannot write an answer against someone else's paper.
    if not ques_table.objects.filter(
        ques_id=question_id, exam_code_id=attempt.exam_id
    ).exists():
        return HttpResponseBadRequest('Unknown question for this exam')

    AttemptAnswer.objects.update_or_create(
        attempt=attempt,
        question_id=question_id,
        defaults={'selected_option': selected, 'marked_for_review': marked},
    )
    return JsonResponse({
        'ok': True,
        'question_id': question_id,
        'selected_option': selected,
        'marked_for_review': marked,
        'seconds_remaining': attempt.seconds_remaining(),
    })


@login_required
@require_POST
def submit_attempt(request, attempt_id):
    """Submit and score. A second submission just returns the same result."""
    attempt = _get_own_attempt(request, attempt_id)
    if attempt.status == ExamAttempt.IN_PROGRESS:
        auto = request.POST.get('auto') == '1'
        score_attempt(attempt, auto_submitted=auto)
    return redirect('exam_result', attempt_id=attempt.pk)


@login_required
@require_GET
def exam_result(request, attempt_id):
    """The result, with explanations. Only readable once submitted."""
    attempt = _get_own_attempt(request, attempt_id)
    _expire_if_due(attempt)
    attempt.refresh_from_db()

    if attempt.status == ExamAttempt.IN_PROGRESS:
        return redirect('exam_take', attempt_id=attempt.pk)

    questions = list(
        ques_table.objects.filter(exam_code_id=attempt.exam_id).order_by('ques_id')
    )
    saved = {a.question_id: a for a in AttemptAnswer.objects.filter(attempt=attempt)}

    review = []
    for index, q in enumerate(questions, start=1):
        answer = saved.get(q.ques_id)
        selected = answer.selected_option if answer else None
        review.append({
            'number': index,
            'text': q.ques,
            'marks': q.marks,
            'options': q.options(),
            'selected': selected,
            'correct': q.correct,
            'is_correct': selected == q.correct,
            'answered': selected is not None,
            'explanation': q.explanation,
        })

    return render(request, 'exam_result.html', {
        'attempt': attempt,
        'exam': attempt.exam,
        'review': review,
    })


@login_required
def exam_history(request):
    """Every attempt this student has made, newest first."""
    attempts = (
        ExamAttempt.objects.filter(student_id=request.user.email_id)
        .select_related('exam', 'exam__course_id')
    )
    submitted = [a for a in attempts if a.status != ExamAttempt.IN_PROGRESS]
    best = {}
    for a in submitted:
        current = best.get(a.exam_id)
        if current is None or a.percentage > current.percentage:
            best[a.exam_id] = a

    return render(request, 'exam_history.html', {
        'attempts': attempts,
        'total': len(submitted),
        'passed': len([a for a in submitted if a.passed]),
        'best_by_exam': best,
    })
