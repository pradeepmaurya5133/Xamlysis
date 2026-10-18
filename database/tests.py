"""Tests for the exam engine.

Covers the behaviour the engine is responsible for: authentication, creating
and resuming attempts, autosaving, server-side expiry, scoring, permissions and
submission. Each test asserts against the database rather than the rendered
page, so a template change cannot make a security test pass by accident.
"""

import datetime
import json

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from database.models import (
    User, role_id, course_id, exam_details, ques_table,
    ExamAttempt, AttemptAnswer, score_table, answer_table, class_stu_tech,
)
from database.exam_views import score_attempt

PASSWORD = 'TestPass@12345'


class ExamEngineTestCase(TestCase):
    """Shared fixture: one exam of four questions worth five marks each."""

    def setUp(self):
        role_id.objects.get_or_create(role_id=1, defaults={'role_name': 'TEACHER'})
        role_id.objects.get_or_create(role_id=2, defaults={'role_name': 'STUDENT'})

        self.teacher = User.objects.create(
            email_id='teacher@test.local', username='teacher', role_id_id=1)
        self.teacher.set_password(PASSWORD)
        self.teacher.save()

        self.student = User.objects.create(
            email_id='student@test.local', username='student', role_id_id=2)
        self.student.set_password(PASSWORD)
        self.student.save()

        self.other = User.objects.create(
            email_id='other@test.local', username='other', role_id_id=2)
        self.other.set_password(PASSWORD)
        self.other.save()

        class_stu_tech.objects.create(
            role_id_id=2, email_id_id=self.student.email_id, class_stu_tech=11)

        self.course = course_id.objects.create(
            course_id='TST11', course_name='Testing', class_stu_tech=11)

        self.exam = exam_details.objects.create(
            exam_code='TST11-EXAM',
            exam_title='Testing Examination',
            date=timezone.now().date(),
            start_time=datetime.time(10, 0),
            duration=datetime.timedelta(hours=1),
            no_of_ques=4,
            max_marks=20,
            course_id=self.course,
            email_id=self.teacher,
            class_stu=11,
            pass_percentage=50,
            max_attempts=2,
        )

        self.questions = []
        for n in range(1, 5):
            self.questions.append(ques_table.objects.create(
                ques_id='TST11-EXAM-Q%d' % n,
                ques='Question %d?' % n,
                option1='A%d' % n, option2='B%d' % n,
                option3='C%d' % n, option4='D%d' % n,
                correct=((n - 1) % 4) + 1,
                marks=5,
                exam_code=self.exam,
                explanation='Because of reason %d.' % n,
            ))

        self.client = Client()

    def login_student(self):
        self.assertTrue(
            self.client.login(email_id=self.student.email_id, password=PASSWORD))

    def start_attempt(self):
        """Start (or resume) an attempt and return the newest one.

        Uses latest() rather than get(): the attempt-limit test deliberately
        creates several, and get() would raise MultipleObjectsReturned.
        """
        self.login_student()
        self.client.get(reverse('exam_start', args=[self.exam.exam_code]))
        return ExamAttempt.objects.filter(
            student_id=self.student.email_id, exam=self.exam).latest('started_at')


class AuthenticationTests(ExamEngineTestCase):

    def test_catalogue_requires_login(self):
        response = self.client.get(reverse('exam_catalogue'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

    def test_taking_an_exam_requires_login(self):
        response = self.client.get(reverse('exam_start', args=[self.exam.exam_code]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

    def test_student_can_log_in_and_reach_the_catalogue(self):
        self.login_student()
        response = self.client.get(reverse('exam_catalogue'))
        self.assertEqual(response.status_code, 200)

    def test_logout_ends_the_session(self):
        self.login_student()
        self.client.get('/logout')
        response = self.client.get(reverse('exam_catalogue'))
        self.assertEqual(response.status_code, 302)


class AttemptLifecycleTests(ExamEngineTestCase):

    def test_starting_creates_one_attempt_with_a_server_deadline(self):
        attempt = self.start_attempt()
        self.assertEqual(attempt.status, ExamAttempt.IN_PROGRESS)
        self.assertEqual(attempt.attempt_no, 1)
        remaining = (attempt.expires_at - timezone.now()).total_seconds()
        self.assertTrue(3500 < remaining <= 3600, 'deadline should be ~1 hour away')

    def test_starting_again_resumes_rather_than_duplicating(self):
        first = self.start_attempt()
        self.client.get(reverse('exam_start', args=[self.exam.exam_code]))
        self.assertEqual(ExamAttempt.objects.filter(student=self.student).count(), 1)
        self.assertEqual(
            ExamAttempt.objects.get(student=self.student).pk, first.pk)

    def test_attempt_limit_is_enforced(self):
        for _ in range(self.exam.max_attempts):
            attempt = self.start_attempt()
            score_attempt(attempt)
        response = self.client.get(reverse('exam_start', args=[self.exam.exam_code]))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            ExamAttempt.objects.filter(student=self.student).count(),
            self.exam.max_attempts)

    def test_exam_with_no_questions_cannot_be_started(self):
        empty = exam_details.objects.create(
            exam_code='EMPTY-01', exam_title='Empty', date=timezone.now().date(),
            start_time=datetime.time(9, 0), duration=datetime.timedelta(hours=1),
            no_of_ques=0, max_marks=0, course_id=self.course,
            email_id=self.teacher, class_stu=11)
        self.login_student()
        response = self.client.get(reverse('exam_start', args=[empty.exam_code]))
        self.assertEqual(response.status_code, 409)
        self.assertFalse(ExamAttempt.objects.filter(exam=empty).exists())


class AutosaveTests(ExamEngineTestCase):

    def post_answer(self, attempt, question, option, marked=False):
        return self.client.post(
            reverse('exam_save_answer', args=[attempt.pk]),
            data=json.dumps({
                'question_id': question.ques_id,
                'selected_option': option,
                'marked_for_review': marked,
            }),
            content_type='application/json',
        )

    def test_answer_is_saved_and_can_be_changed(self):
        attempt = self.start_attempt()
        response = self.post_answer(attempt, self.questions[0], 2)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

        saved = AttemptAnswer.objects.get(attempt=attempt, question=self.questions[0])
        self.assertEqual(saved.selected_option, 2)

        self.post_answer(attempt, self.questions[0], 4)
        saved.refresh_from_db()
        self.assertEqual(saved.selected_option, 4)
        self.assertEqual(
            AttemptAnswer.objects.filter(attempt=attempt, question=self.questions[0]).count(),
            1, 'changing an answer must update the row, not add another')

    def test_saved_answers_are_restored_after_a_refresh(self):
        attempt = self.start_attempt()
        self.post_answer(attempt, self.questions[1], 3, marked=True)

        response = self.client.get(reverse('exam_take', args=[attempt.pk]))
        self.assertEqual(response.status_code, 200)
        payload = response.context['questions_json']
        second = [q for q in payload if q['id'] == self.questions[1].ques_id][0]
        self.assertEqual(second['selected'], 3)
        self.assertTrue(second['marked'])

    def test_mark_for_review_is_persisted(self):
        attempt = self.start_attempt()
        self.post_answer(attempt, self.questions[2], None, marked=True)
        saved = AttemptAnswer.objects.get(attempt=attempt, question=self.questions[2])
        self.assertIsNone(saved.selected_option)
        self.assertTrue(saved.marked_for_review)

    def test_option_outside_one_to_four_is_rejected(self):
        attempt = self.start_attempt()
        self.assertEqual(self.post_answer(attempt, self.questions[0], 9).status_code, 400)
        self.assertFalse(AttemptAnswer.objects.filter(attempt=attempt).exists())

    def test_question_from_another_exam_is_rejected(self):
        attempt = self.start_attempt()
        other_exam = exam_details.objects.create(
            exam_code='OTHER-01', exam_title='Other', date=timezone.now().date(),
            start_time=datetime.time(9, 0), duration=datetime.timedelta(hours=1),
            no_of_ques=1, max_marks=5, course_id=self.course,
            email_id=self.teacher, class_stu=11)
        foreign = ques_table.objects.create(
            ques_id='OTHER-01-Q1', ques='Foreign?', option1='a', option2='b',
            option3='c', option4='d', correct=1, marks=5, exam_code=other_exam)
        response = self.post_answer(attempt, foreign, 1)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttemptAnswer.objects.filter(attempt=attempt).exists())

    def test_malformed_json_is_rejected(self):
        attempt = self.start_attempt()
        response = self.client.post(
            reverse('exam_save_answer', args=[attempt.pk]),
            data='not json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_saving_requires_post(self):
        attempt = self.start_attempt()
        response = self.client.get(reverse('exam_save_answer', args=[attempt.pk]))
        self.assertEqual(response.status_code, 405)


class TimerExpiryTests(ExamEngineTestCase):

    def expire(self, attempt):
        """Move the deadline into the past, as if the clock had run out."""
        ExamAttempt.objects.filter(pk=attempt.pk).update(
            expires_at=timezone.now() - datetime.timedelta(seconds=1))

    def test_saving_after_expiry_is_refused_and_auto_submits(self):
        attempt = self.start_attempt()
        self.client.post(
            reverse('exam_save_answer', args=[attempt.pk]),
            data=json.dumps({'question_id': self.questions[0].ques_id,
                             'selected_option': self.questions[0].correct}),
            content_type='application/json')
        self.expire(attempt)

        response = self.client.post(
            reverse('exam_save_answer', args=[attempt.pk]),
            data=json.dumps({'question_id': self.questions[1].ques_id,
                             'selected_option': 1}),
            content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['reason'], 'expired')

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, ExamAttempt.SUBMITTED)
        self.assertTrue(attempt.auto_submitted)
        # the answer saved before expiry still counts
        self.assertEqual(attempt.score, 5)

    def test_opening_an_expired_attempt_shows_the_result(self):
        attempt = self.start_attempt()
        self.expire(attempt)
        response = self.client.get(reverse('exam_take', args=[attempt.pk]))
        self.assertRedirects(response, reverse('exam_result', args=[attempt.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, ExamAttempt.SUBMITTED)
        self.assertTrue(attempt.auto_submitted)

    def test_seconds_remaining_never_goes_negative(self):
        attempt = self.start_attempt()
        self.expire(attempt)
        attempt.refresh_from_db()      # expire() updates the row, not the instance
        self.assertEqual(attempt.seconds_remaining(), 0)


class ScoringTests(ExamEngineTestCase):

    def answer_all(self, attempt, correctly=True):
        for q in self.questions:
            option = q.correct if correctly else (q.correct % 4) + 1
            AttemptAnswer.objects.update_or_create(
                attempt=attempt, question=q,
                defaults={'selected_option': option})

    def test_all_correct_scores_full_marks_and_passes(self):
        attempt = self.start_attempt()
        self.answer_all(attempt, correctly=True)
        scored = score_attempt(attempt)
        self.assertEqual(scored.score, 20)
        self.assertEqual(scored.max_marks, 20)
        self.assertEqual(float(scored.percentage), 100.0)
        self.assertTrue(scored.passed)
        self.assertEqual(scored.correct_count, 4)
        self.assertEqual(scored.wrong_count, 0)
        self.assertEqual(scored.unanswered_count, 0)

    def test_all_wrong_scores_zero_and_fails(self):
        attempt = self.start_attempt()
        self.answer_all(attempt, correctly=False)
        scored = score_attempt(attempt)
        self.assertEqual(scored.score, 0)
        self.assertEqual(float(scored.percentage), 0.0)
        self.assertFalse(scored.passed)
        self.assertEqual(scored.wrong_count, 4)

    def test_unanswered_questions_are_counted_not_marked_wrong(self):
        attempt = self.start_attempt()
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[0],
            selected_option=self.questions[0].correct)
        scored = score_attempt(attempt)
        self.assertEqual(scored.correct_count, 1)
        self.assertEqual(scored.wrong_count, 0)
        self.assertEqual(scored.unanswered_count, 3)
        self.assertEqual(scored.score, 5)

    def test_pass_mark_boundary(self):
        attempt = self.start_attempt()
        for q in self.questions[:2]:        # 10 of 20 = 50%, pass mark is 50
            AttemptAnswer.objects.create(
                attempt=attempt, question=q, selected_option=q.correct)
        scored = score_attempt(attempt)
        self.assertEqual(float(scored.percentage), 50.0)
        self.assertTrue(scored.passed, '50% must pass when the pass mark is 50')

    def test_scoring_writes_the_legacy_tables(self):
        attempt = self.start_attempt()
        self.answer_all(attempt, correctly=True)
        score_attempt(attempt)
        row = score_table.objects.get(
            exam_code=self.exam, email_id_id=self.student.email_id)
        self.assertEqual(row.scored_marks, 20)
        self.assertEqual(
            answer_table.objects.filter(
                exam_code=self.exam, email_id_id=self.student.email_id).count(), 4)

    def test_result_page_reveals_the_key_only_after_submission(self):
        attempt = self.start_attempt()

        # While open, the payload sent to the browser carries no correct answers.
        response = self.client.get(reverse('exam_take', args=[attempt.pk]))
        for q in response.context['questions_json']:
            self.assertNotIn('correct', q)

        self.answer_all(attempt, correctly=True)
        score_attempt(attempt)
        result = self.client.get(reverse('exam_result', args=[attempt.pk]))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.context['review'][0]['correct'], self.questions[0].correct)
        self.assertIn('Because of reason 1.', result.content.decode())


class SubmissionTests(ExamEngineTestCase):

    def test_submitting_scores_and_redirects_to_the_result(self):
        attempt = self.start_attempt()
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[0],
            selected_option=self.questions[0].correct)
        response = self.client.post(reverse('exam_submit', args=[attempt.pk]))
        self.assertRedirects(response, reverse('exam_result', args=[attempt.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, ExamAttempt.SUBMITTED)
        self.assertEqual(attempt.score, 5)

    def test_submitting_twice_does_not_change_the_result(self):
        attempt = self.start_attempt()
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[0],
            selected_option=self.questions[0].correct)
        self.client.post(reverse('exam_submit', args=[attempt.pk]))
        attempt.refresh_from_db()
        first_score, first_time = attempt.score, attempt.submitted_at

        # A second answer sneaked in after submission must not be counted.
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[1],
            selected_option=self.questions[1].correct)
        self.client.post(reverse('exam_submit', args=[attempt.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, first_score)
        self.assertEqual(attempt.submitted_at, first_time)
        self.assertEqual(
            score_table.objects.filter(
                exam_code=self.exam, email_id_id=self.student.email_id).count(), 1)

    def test_submitting_requires_post(self):
        attempt = self.start_attempt()
        response = self.client.get(reverse('exam_submit', args=[attempt.pk]))
        self.assertEqual(response.status_code, 405)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, ExamAttempt.IN_PROGRESS)

    def test_answers_cannot_be_saved_after_submission(self):
        attempt = self.start_attempt()
        self.client.post(reverse('exam_submit', args=[attempt.pk]))
        response = self.client.post(
            reverse('exam_save_answer', args=[attempt.pk]),
            data=json.dumps({'question_id': self.questions[0].ques_id,
                             'selected_option': 1}),
            content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['reason'], 'submitted')


class PermissionTests(ExamEngineTestCase):

    def test_another_student_cannot_open_the_attempt(self):
        attempt = self.start_attempt()
        self.client.logout()
        self.client.login(email_id=self.other.email_id, password=PASSWORD)
        for name in ('exam_take', 'exam_result'):
            self.assertEqual(
                self.client.get(reverse(name, args=[attempt.pk])).status_code, 404)

    def test_another_student_cannot_write_to_the_attempt(self):
        attempt = self.start_attempt()
        self.client.logout()
        self.client.login(email_id=self.other.email_id, password=PASSWORD)

        save = self.client.post(
            reverse('exam_save_answer', args=[attempt.pk]),
            data=json.dumps({'question_id': self.questions[0].ques_id,
                             'selected_option': 1}),
            content_type='application/json')
        self.assertEqual(save.status_code, 404)
        self.assertEqual(
            self.client.post(reverse('exam_submit', args=[attempt.pk])).status_code, 404)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, ExamAttempt.IN_PROGRESS)
        self.assertFalse(AttemptAnswer.objects.filter(attempt=attempt).exists())

    def test_anonymous_requests_are_redirected_to_login(self):
        attempt = self.start_attempt()
        self.client.logout()
        for name in ('exam_take', 'exam_result'):
            response = self.client.get(reverse(name, args=[attempt.pk]))
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.url)

    def test_csrf_is_enforced_on_save_and_submit(self):
        attempt = self.start_attempt()
        csrf_client = Client(enforce_csrf_checks=True)
        self.assertTrue(
            csrf_client.login(email_id=self.student.email_id, password=PASSWORD))

        save = csrf_client.post(
            reverse('exam_save_answer', args=[attempt.pk]),
            data=json.dumps({'question_id': self.questions[0].ques_id,
                             'selected_option': 1}),
            content_type='application/json')
        self.assertEqual(save.status_code, 403)
        self.assertEqual(
            csrf_client.post(reverse('exam_submit', args=[attempt.pk])).status_code, 403)

    def test_unpublished_exams_cannot_be_started(self):
        self.exam.is_published = False
        self.exam.save(update_fields=['is_published'])
        self.login_student()
        response = self.client.get(reverse('exam_start', args=[self.exam.exam_code]))
        self.assertEqual(response.status_code, 404)


class LegacyRouteTests(ExamEngineTestCase):

    def test_legacy_test_url_redirects_into_the_engine(self):
        self.login_student()
        response = self.client.get('/test/?exid=%s' % self.exam.exam_code)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse('exam_start', args=[self.exam.exam_code]))

    def test_legacy_test_url_without_an_exam_goes_to_the_catalogue(self):
        self.login_student()
        response = self.client.get('/test/')
        self.assertRedirects(response, reverse('exam_catalogue'))


class HistoryTests(ExamEngineTestCase):

    def test_history_lists_only_this_student_and_counts_passes(self):
        attempt = self.start_attempt()
        for q in self.questions:
            AttemptAnswer.objects.create(
                attempt=attempt, question=q, selected_option=q.correct)
        score_attempt(attempt)

        other_attempt = ExamAttempt.objects.create(
            exam=self.exam, student=self.other, attempt_no=1,
            expires_at=timezone.now() + datetime.timedelta(hours=1))
        score_attempt(other_attempt)

        response = self.client.get(reverse('exam_history'))
        self.assertEqual(response.status_code, 200)
        listed = list(response.context['attempts'])
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].pk, attempt.pk)
        self.assertEqual(response.context['passed'], 1)
