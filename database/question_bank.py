"""Staff question bank: browse, filter, preview, create and edit questions.

Every view here is staff-only. Questions carry the answer key, so none of this
is reachable by a student even read-only.

Editing and history
-------------------
A question can be edited after students have sat the exam it belongs to. The
engine stores each attempt's verdict on AttemptAnswer at scoring time and the
totals on ExamAttempt, so an edit cannot move a recorded score. The edit form
still warns when a question has already been answered in a scored attempt,
because the paper a student saw and the paper stored now will differ.
"""

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404

from database.models import (
    ques_table, exam_details, course_id, AttemptAnswer, ExamAttempt,
)
from database.permissions import staff_required

PAGE_SIZE = 25


class QuestionForm(forms.ModelForm):
    """Create and edit a question, with the checks the admin does not make."""

    class Meta:
        model = ques_table
        fields = [
            'ques_id', 'exam_code', 'ques',
            'option1', 'option2', 'option3', 'option4',
            'correct', 'marks', 'difficulty', 'topic', 'explanation',
        ]
        widgets = {
            'ques': forms.Textarea(attrs={'rows': 3}),
            'explanation': forms.Textarea(attrs={'rows': 3}),
            'correct': forms.Select(choices=[(i, 'Option %d' % i) for i in (1, 2, 3, 4)]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # The id is the primary key and is referenced by saved answers.
            self.fields['ques_id'].disabled = True
        for name, field in self.fields.items():
            css = 'form-control'
            if isinstance(field.widget, forms.Select):
                css = 'form-control'
            field.widget.attrs.setdefault('class', css)

    def clean_correct(self):
        correct = self.cleaned_data['correct']
        if correct not in (1, 2, 3, 4):
            raise forms.ValidationError('The correct option must be 1, 2, 3 or 4.')
        return correct

    def clean_marks(self):
        marks = self.cleaned_data['marks']
        if marks <= 0:
            raise forms.ValidationError('Marks must be greater than zero.')
        return marks

    def clean(self):
        cleaned = super().clean()
        options = [cleaned.get('option%d' % i) for i in (1, 2, 3, 4)]
        filled = [o.strip() for o in options if o and o.strip()]
        if len(filled) == 4 and len(set(filled)) != 4:
            raise forms.ValidationError('The four options must all be different.')
        return cleaned


def _filtered_questions(request):
    """Apply the request's filters and return (queryset, active filter values)."""
    qs = ques_table.objects.select_related('exam_code', 'exam_code__course_id')

    search = (request.GET.get('q') or '').strip()
    course = (request.GET.get('course') or '').strip()
    klass = (request.GET.get('class') or '').strip()
    exam = (request.GET.get('exam') or '').strip()
    difficulty = (request.GET.get('difficulty') or '').strip()
    topic = (request.GET.get('topic') or '').strip()

    if search:
        qs = qs.filter(
            Q(ques__icontains=search) |
            Q(ques_id__icontains=search) |
            Q(topic__icontains=search)
        )
    if course:
        qs = qs.filter(exam_code__course_id_id=course)
    if klass.isdigit():
        qs = qs.filter(exam_code__class_stu=int(klass))
    if exam:
        qs = qs.filter(exam_code_id=exam)
    if difficulty:
        qs = qs.filter(difficulty=difficulty)
    if topic:
        qs = qs.filter(topic__iexact=topic)

    active = {
        'q': search, 'course': course, 'class': klass,
        'exam': exam, 'difficulty': difficulty, 'topic': topic,
    }
    return qs.order_by('exam_code_id', 'ques_id'), active


@staff_required
def question_bank(request):
    """Paginated, filterable list of every question."""
    qs, active = _filtered_questions(request)
    total = qs.count()

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))

    # Querystring without `page`, so the pager keeps the active filters.
    params = request.GET.copy()
    params.pop('page', None)
    filter_qs = params.urlencode()

    return render(request, 'question_bank.html', {
        'page': page,
        'total': total,
        'grand_total': ques_table.objects.count(),
        'active': active,
        'filter_qs': filter_qs,
        'courses': course_id.objects.order_by('class_stu_tech', 'course_name'),
        'exams': exam_details.objects.order_by('exam_code').values('exam_code', 'exam_title'),
        'difficulties': ques_table.DIFFICULTY_CHOICES,
        'topics': (
            ques_table.objects.exclude(topic='')
            .values_list('topic', flat=True).distinct().order_by('topic')
        ),
        'classes': sorted(
            exam_details.objects.values_list('class_stu', flat=True).distinct()),
    })


@staff_required
def question_preview(request, ques_id):
    """Show a question exactly as a student sees it, plus the key for staff."""
    question = get_object_or_404(
        ques_table.objects.select_related('exam_code', 'exam_code__course_id'),
        pk=ques_id)
    answered = AttemptAnswer.objects.filter(question=question)
    stats = answered.aggregate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True)),
        wrong=Count('id', filter=Q(is_correct=False)),
    )
    return render(request, 'question_preview.html', {
        'question': question,
        'options': list(enumerate(question.options(), start=1)),
        'stats': stats,
    })


def _usage_warning(question):
    """How many scored attempts already include this question."""
    return AttemptAnswer.objects.filter(
        question=question,
        attempt__status=ExamAttempt.SUBMITTED,
    ).count()


@staff_required
def question_create(request):
    form = QuestionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        question = form.save()
        messages.success(request, 'Question %s created.' % question.ques_id)
        return redirect('question_preview', ques_id=question.ques_id)
    return render(request, 'question_form.html', {
        'form': form, 'mode': 'create', 'used_in': 0,
    })


@staff_required
def question_edit(request, ques_id):
    question = get_object_or_404(ques_table, pk=ques_id)
    used_in = _usage_warning(question)
    form = QuestionForm(request.POST or None, instance=question)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            'Question %s updated. Scores already recorded are unchanged.'
            % question.ques_id)
        return redirect('question_preview', ques_id=question.ques_id)
    return render(request, 'question_form.html', {
        'form': form, 'mode': 'edit', 'question': question, 'used_in': used_in,
    })
