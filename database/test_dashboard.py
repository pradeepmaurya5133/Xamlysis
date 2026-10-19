"""Tests for the student dashboard and historical result integrity.

Kept in its own module rather than appended to tests.py, which already holds
the exam-engine suite. The shared fixture is reused by importing it.
"""

import datetime

from django.urls import reverse
from django.utils import timezone

from database.models import (
    ExamAttempt, AttemptAnswer, exam_details, ques_table,
)
from database.exam_views import score_attempt
from database.tests import ExamEngineTestCase

# session, user, classes, availed courses, attempts (joined), exams (joined).
# The number itself matters less than it staying the same as data grows, which
# is what the N+1 test below asserts.
EXPECTED_DASHBOARD_QUERIES = 6


class StudentDashboardTests(ExamEngineTestCase):
    """The dashboard aggregates attempts and exams for one student only."""

    URL = '/dashboard/'

    def test_requires_login(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

    def test_renders_with_no_attempts(self):
        self.login_student()
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['attempted'], 0)
        self.assertEqual(list(response.context['recent_results']), [])
        self.assertContains(response, 'You have not completed an exam yet')

    def test_available_exam_is_listed_with_its_type_label(self):
        self.login_student()
        response = self.client.get(self.URL)
        codes = [r['exam'].exam_code for r in response.context['available']]
        self.assertIn(self.exam.exam_code, codes)
        row = [r for r in response.context['available']
               if r['exam'].exam_code == self.exam.exam_code][0]
        self.assertFalse(row['is_practice'])
        self.assertContains(response, 'Full-length')

    def test_practice_exams_are_labelled_separately(self):
        self.exam.exam_type = exam_details.PRACTICE
        self.exam.save(update_fields=['exam_type'])
        self.login_student()
        response = self.client.get(self.URL)
        row = [r for r in response.context['available']
               if r['exam'].exam_code == self.exam.exam_code][0]
        self.assertTrue(row['is_practice'])
        self.assertContains(response, 'Practice')

    def test_future_dated_exams_appear_under_upcoming(self):
        self.exam.date = timezone.localdate() + datetime.timedelta(days=7)
        self.exam.save(update_fields=['date'])
        self.login_student()
        response = self.client.get(self.URL)
        self.assertIn(self.exam.exam_code,
                      [r['exam'].exam_code for r in response.context['upcoming']])
        self.assertNotIn(self.exam.exam_code,
                         [r['exam'].exam_code for r in response.context['available']])

    def test_attempts_remaining_is_reported(self):
        self.login_student()
        row = [r for r in self.client.get(self.URL).context['available']
               if r['exam'].exam_code == self.exam.exam_code][0]
        self.assertEqual(row['attempts_left'], 2)
        self.assertFalse(row['unlimited'])

        score_attempt(self.start_attempt())
        row = [r for r in self.client.get(self.URL).context['available']
               if r['exam'].exam_code == self.exam.exam_code][0]
        self.assertEqual(row['attempts_used'], 1)
        self.assertEqual(row['attempts_left'], 1)
        self.assertTrue(row['can_start'])

    def test_unlimited_attempts_are_reported_as_unlimited(self):
        self.exam.max_attempts = 0
        self.exam.save(update_fields=['max_attempts'])
        self.login_student()
        row = [r for r in self.client.get(self.URL).context['available']
               if r['exam'].exam_code == self.exam.exam_code][0]
        self.assertTrue(row['unlimited'])
        self.assertIsNone(row['attempts_left'])
        self.assertTrue(row['can_start'])

    def test_exhausted_attempts_cannot_be_started(self):
        for _ in range(self.exam.max_attempts):
            score_attempt(self.start_attempt())
        response = self.client.get(self.URL)
        row = [r for r in response.context['available']
               if r['exam'].exam_code == self.exam.exam_code][0]
        self.assertEqual(row['attempts_left'], 0)
        self.assertFalse(row['can_start'])
        self.assertContains(response, 'No attempts left')

    def test_in_progress_attempt_is_resumable(self):
        self.start_attempt()
        response = self.client.get(self.URL)
        listed = list(response.context['in_progress'])
        self.assertEqual(len(listed), 1)
        self.assertTrue(listed[0].resumable)
        self.assertEqual(listed[0].display_status, 'In progress')
        self.assertContains(response, 'Resume')

    def test_expired_attempt_is_not_resumable(self):
        attempt = self.start_attempt()
        ExamAttempt.objects.filter(pk=attempt.pk).update(
            expires_at=timezone.now() - datetime.timedelta(seconds=1))
        response = self.client.get(self.URL)
        listed = list(response.context['in_progress'])
        self.assertEqual(len(listed), 1)
        self.assertFalse(
            listed[0].resumable, 'an expired attempt must not be resumable')
        self.assertEqual(listed[0].display_status, 'Expired')

    def test_results_and_stats_are_computed(self):
        attempt = self.start_attempt()
        for q in self.questions:
            AttemptAnswer.objects.create(
                attempt=attempt, question=q, selected_option=q.correct)
        score_attempt(attempt)

        response = self.client.get(self.URL)
        stats = response.context['stats']
        self.assertEqual(stats['attempted'], 1)
        self.assertEqual(stats['passed'], 1)
        self.assertEqual(stats['average'], 100.0)
        self.assertEqual(stats['best'], 100.0)
        self.assertEqual(len(response.context['recent_results']), 1)

    def test_only_this_students_attempts_are_shown(self):
        mine = self.start_attempt()
        score_attempt(mine)
        theirs = ExamAttempt.objects.create(
            exam=self.exam, student=self.other, attempt_no=1,
            expires_at=timezone.now() + datetime.timedelta(hours=1))
        score_attempt(theirs)

        response = self.client.get(self.URL)
        shown = [a.pk for a in response.context['recent_results']]
        self.assertEqual(shown, [mine.pk])
        self.assertNotIn(theirs.pk, shown)

    def test_query_count_does_not_grow_with_data(self):
        """Guards against an N+1: more exams and attempts, same query count."""
        self.login_student()
        self.client.get(self.URL)          # warm the session/auth queries
        with self.assertNumQueries(EXPECTED_DASHBOARD_QUERIES):
            self.client.get(self.URL)

        for n in range(6):
            extra = exam_details.objects.create(
                exam_code='EXTRA-%d' % n, exam_title='Extra %d' % n,
                date=timezone.now().date(), start_time=datetime.time(9, 0),
                duration=datetime.timedelta(hours=1), no_of_ques=1, max_marks=5,
                course_id=self.course, email_id=self.teacher, class_stu=11)
            ques_table.objects.create(
                ques_id='EXTRA-%d-Q1' % n, ques='q', option1='a', option2='b',
                option3='c', option4='d', correct=1, marks=5, exam_code=extra)
            score_attempt(ExamAttempt.objects.create(
                exam=extra, student=self.student, attempt_no=1,
                expires_at=timezone.now() + datetime.timedelta(hours=1)))

        with self.assertNumQueries(EXPECTED_DASHBOARD_QUERIES):
            self.client.get(self.URL)


class HistoricalResultIntegrityTests(ExamEngineTestCase):
    """Editing a question must not rewrite a result that was already scored."""

    def test_editing_the_key_does_not_change_a_past_review(self):
        attempt = self.start_attempt()
        for q in self.questions:
            AttemptAnswer.objects.create(
                attempt=attempt, question=q, selected_option=q.correct)
        score_attempt(attempt)
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 20)

        # A member of staff later changes the key on question 1.
        first = self.questions[0]
        first.correct = (first.correct % 4) + 1
        first.save(update_fields=['correct'])

        response = self.client.get(reverse('exam_result', args=[attempt.pk]))
        row = response.context['review'][0]
        self.assertTrue(
            row['is_correct'],
            'the stored verdict must stand, not be recomputed from the edit')
        self.assertTrue(row['key_changed'], 'the divergence should be detectable')

        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 20, 'the recorded score must not move')

    def test_legacy_score_rows_are_not_rewritten_by_viewing_a_result(self):
        from database.models import score_table
        attempt = self.start_attempt()
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[0],
            selected_option=self.questions[0].correct)
        score_attempt(attempt)

        row = score_table.objects.get(
            exam_code=self.exam, email_id_id=self.student.email_id)
        before = (row.scored_marks, row.percentage)

        self.client.get(reverse('exam_result', args=[attempt.pk]))
        self.client.get('/dashboard/')

        row.refresh_from_db()
        self.assertEqual((row.scored_marks, row.percentage), before)
