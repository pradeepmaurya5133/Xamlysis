"""Staff analytics: participation, scores, pass rates and weak questions.

Denominators are the thing worth being careful about here, so they are stated
rather than implied:

- averages and pass rates count SUBMITTED attempts only. An attempt still in
  progress has no score yet, and including it would drag every average toward
  zero.
- accuracy is computed from AttemptAnswer rows whose is_correct was set when
  the attempt was scored. An unanswered question has is_correct null and is
  counted as neither right nor wrong, but is reported separately so a question
  everybody skipped is visible.
- the legacy score_table rows predate the attempt engine and have no per-answer
  detail. They are reported as a separate count and deliberately excluded from
  accuracy figures, which would otherwise be computed over a different and
  smaller population than the headline numbers.

Every figure is aggregated in the database rather than by looping in Python, so
the query count does not grow with the number of attempts or questions.
"""

from django.core.paginator import Paginator
from django.db.models import (
    Avg, Count, Q, F, FloatField, ExpressionWrapper, Max,
)
from django.shortcuts import render, get_object_or_404

from database.models import (
    ExamAttempt, AttemptAnswer, exam_details, course_id, ques_table,
    score_table, User,
)
from database.permissions import staff_required

PAGE_SIZE = 20


def _percent(part, whole):
    """Integer-safe percentage, 0 when there is nothing to divide by."""
    if not whole:
        return 0.0
    return round(100.0 * part / whole, 1)


def _headline():
    """Overall counters, taken in two aggregate queries rather than per row."""
    attempts = ExamAttempt.objects.aggregate(
        started=Count('id'),
        submitted=Count('id', filter=Q(status=ExamAttempt.SUBMITTED)),
        in_progress=Count('id', filter=Q(status=ExamAttempt.IN_PROGRESS)),
        auto=Count('id', filter=Q(auto_submitted=True)),
        passed=Count('id', filter=Q(status=ExamAttempt.SUBMITTED, passed=True)),
        average=Avg('percentage', filter=Q(status=ExamAttempt.SUBMITTED)),
        students=Count('student', distinct=True),
    )
    answers = AttemptAnswer.objects.aggregate(
        answered=Count('id', filter=Q(is_correct__isnull=False)),
        correct=Count('id', filter=Q(is_correct=True)),
        skipped=Count('id', filter=Q(selected_option__isnull=True)),
    )
    submitted = attempts['submitted'] or 0
    return {
        'started': attempts['started'] or 0,
        'submitted': submitted,
        'in_progress': attempts['in_progress'] or 0,
        'auto_submitted': attempts['auto'] or 0,
        'passed': attempts['passed'] or 0,
        'pass_rate': _percent(attempts['passed'] or 0, submitted),
        'completion_rate': _percent(submitted, attempts['started'] or 0),
        'average': round(float(attempts['average']), 1) if attempts['average'] else 0.0,
        'students': attempts['students'] or 0,
        'answered': answers['answered'] or 0,
        'accuracy': _percent(answers['correct'] or 0, answers['answered'] or 0),
        'skipped': answers['skipped'] or 0,
        'legacy_results': score_table.objects.count(),
    }


@staff_required
def analytics_overview(request):
    """Headline numbers, then course-wise performance, paginated."""
    headline = _headline()

    # One grouped query over courses: no per-course follow-up queries.
    courses = (
        course_id.objects
        .annotate(
            exam_count=Count('exam_details', distinct=True),
            attempts=Count(
                'exam_details__attempts',
                filter=Q(exam_details__attempts__status=ExamAttempt.SUBMITTED),
                distinct=True),
            passed=Count(
                'exam_details__attempts',
                filter=Q(exam_details__attempts__status=ExamAttempt.SUBMITTED,
                         exam_details__attempts__passed=True),
                distinct=True),
            average=Avg(
                'exam_details__attempts__percentage',
                filter=Q(exam_details__attempts__status=ExamAttempt.SUBMITTED)),
        )
        .order_by('-attempts', 'class_stu_tech', 'course_name')
    )

    page = Paginator(courses, PAGE_SIZE).get_page(request.GET.get('page'))
    rows = [{
        'course': c,
        'exam_count': c.exam_count,
        'attempts': c.attempts,
        'passed': c.passed,
        'pass_rate': _percent(c.passed, c.attempts),
        'average': round(float(c.average), 1) if c.average else 0.0,
    } for c in page.object_list]

    # Topic accuracy, only over answers that were actually marked.
    topics = (
        AttemptAnswer.objects
        .filter(is_correct__isnull=False)
        .exclude(question__topic='')
        .values('question__topic')
        .annotate(
            answered=Count('id'),
            correct=Count('id', filter=Q(is_correct=True)),
        )
        .order_by('-answered')[:10]
    )
    topic_rows = [{
        'topic': t['question__topic'],
        'answered': t['answered'],
        'correct': t['correct'],
        'accuracy': _percent(t['correct'], t['answered']),
    } for t in topics]

    return render(request, 'analytics_overview.html', {
        'headline': headline,
        'page': page,
        'rows': rows,
        'topic_rows': topic_rows,
        'exams': (
            exam_details.objects
            .annotate(attempt_count=Count(
                'attempts', filter=Q(attempts__status=ExamAttempt.SUBMITTED)))
            .filter(attempt_count__gt=0)
            .order_by('-attempt_count')[:10]
        ),
    })


@staff_required
def analytics_exam(request, exam_code):
    """One exam: participation, score spread and the questions most often missed."""
    exam = get_object_or_404(
        exam_details.objects.select_related('course_id'), pk=exam_code)

    stats = ExamAttempt.objects.filter(exam=exam).aggregate(
        started=Count('id'),
        submitted=Count('id', filter=Q(status=ExamAttempt.SUBMITTED)),
        passed=Count('id', filter=Q(status=ExamAttempt.SUBMITTED, passed=True)),
        average=Avg('percentage', filter=Q(status=ExamAttempt.SUBMITTED)),
        best=Max('percentage', filter=Q(status=ExamAttempt.SUBMITTED)),
        students=Count('student', distinct=True),
    )
    submitted = stats['submitted'] or 0

    # Hardest questions first: one grouped query, not one per question.
    questions = (
        ques_table.objects.filter(exam_code=exam)
        .annotate(
            # Prefixed because ques_table already has a field called `correct`,
            # which is the answer key: annotating that name is a hard error.
            n_answered=Count('attemptanswer',
                             filter=Q(attemptanswer__is_correct__isnull=False)),
            n_correct=Count('attemptanswer',
                            filter=Q(attemptanswer__is_correct=True)),
            n_skipped=Count('attemptanswer',
                            filter=Q(attemptanswer__selected_option__isnull=True)),
        )
        .order_by('ques_id')
    )
    question_rows = sorted(
        [{
            'question': q,
            'answered': q.n_answered,
            'correct': q.n_correct,
            'wrong': q.n_answered - q.n_correct,
            'skipped': q.n_skipped,
            'accuracy': _percent(q.n_correct, q.n_answered),
        } for q in questions],
        key=lambda r: (r['answered'] == 0, r['accuracy']),
    )

    page = Paginator(question_rows, PAGE_SIZE).get_page(request.GET.get('page'))

    return render(request, 'analytics_exam.html', {
        'exam': exam,
        'stats': {
            'started': stats['started'] or 0,
            'submitted': submitted,
            'students': stats['students'] or 0,
            'passed': stats['passed'] or 0,
            'pass_rate': _percent(stats['passed'] or 0, submitted),
            'completion_rate': _percent(submitted, stats['started'] or 0),
            'average': round(float(stats['average']), 1) if stats['average'] else 0.0,
            'best': round(float(stats['best']), 1) if stats['best'] else 0.0,
        },
        'page': page,
        'question_rows': page.object_list,
        'total_questions': len(question_rows),
    })


@staff_required
def analytics_student(request, email):
    """One student's progress over time. Staff only: this is private data."""
    student = get_object_or_404(User, pk=email)

    attempts = list(
        ExamAttempt.objects.filter(student=student)
        .select_related('exam', 'exam__course_id')
        .order_by('started_at')
    )
    submitted = [a for a in attempts if a.status == ExamAttempt.SUBMITTED]

    totals = AttemptAnswer.objects.filter(attempt__student=student).aggregate(
        answered=Count('id', filter=Q(is_correct__isnull=False)),
        correct=Count('id', filter=Q(is_correct=True)),
        skipped=Count('id', filter=Q(selected_option__isnull=True)),
    )

    return render(request, 'analytics_student.html', {
        'student': student,
        'attempts': list(reversed(attempts)),
        'progress': [{
            'n': i,
            'label': a.exam.exam_title,
            'percentage': float(a.percentage),
            'passed': a.passed,
            'on': a.submitted_at,
        } for i, a in enumerate(submitted, start=1)],
        'summary': {
            'started': len(attempts),
            'submitted': len(submitted),
            'passed': len([a for a in submitted if a.passed]),
            'pass_rate': _percent(len([a for a in submitted if a.passed]), len(submitted)),
            'average': round(
                sum(float(a.percentage) for a in submitted) / len(submitted), 1
            ) if submitted else 0.0,
            'best': round(max((float(a.percentage) for a in submitted), default=0.0), 1),
            'answered': totals['answered'] or 0,
            'accuracy': _percent(totals['correct'] or 0, totals['answered'] or 0),
            'skipped': totals['skipped'] or 0,
        },
        'legacy': score_table.objects.filter(email_id=student).select_related('exam_code'),
    })
