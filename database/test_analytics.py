"""Tests for the staff analytics pages.

Most of these are about denominators. An attempt still in progress has no
score, so including it in an average or a pass rate silently understates both;
several tests below exist only to pin that down.
"""

import datetime

from django.urls import reverse
from django.utils import timezone

from database.models import (
    ExamAttempt, AttemptAnswer, exam_details, ques_table, score_table, User,
)
from database.exam_views import score_attempt
from database.tests import ExamEngineTestCase, PASSWORD


class AnalyticsPermissionTests(ExamEngineTestCase):

    def urls(self):
        return [
            reverse('analytics_overview'),
            reverse('analytics_exam', args=[self.exam.exam_code]),
            reverse('analytics_student', args=[self.student.email_id]),
        ]

    def test_anonymous_is_redirected_to_login(self):
        for url in self.urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login', response.url)

    def test_student_is_forbidden(self):
        self.login_student()
        for url in self.urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_a_student_cannot_read_another_students_analytics(self):
        """Per-student analytics is private data, so it is staff only."""
        self.login_student()
        response = self.client.get(
            reverse('analytics_student', args=[self.other.email_id]))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_reach_every_page(self):
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)
        for url in self.urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_unknown_student_is_404(self):
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)
        self.assertEqual(
            self.client.get(
                reverse('analytics_student', args=['nobody@nowhere.test'])
            ).status_code, 404)


class AnalyticsBase(ExamEngineTestCase):

    def setUp(self):
        super().setUp()
        self.staff_client = self.client

    def as_staff(self):
        self.client.logout()
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)

    def sit(self, student, correct_count):
        """Create a submitted attempt answering `correct_count` questions right."""
        attempt = ExamAttempt.objects.create(
            exam=self.exam, student=student, attempt_no=1,
            expires_at=timezone.now() + datetime.timedelta(hours=1))
        for i, q in enumerate(self.questions):
            if i < correct_count:
                option = q.correct
            else:
                option = (q.correct % 4) + 1
            AttemptAnswer.objects.create(
                attempt=attempt, question=q, selected_option=option)
        return score_attempt(attempt)


class AnalyticsOverviewTests(AnalyticsBase):

    def test_empty_state_when_nothing_has_been_attempted(self):
        self.as_staff()
        response = self.client.get(reverse('analytics_overview'))
        self.assertEqual(response.status_code, 200)
        head = response.context['headline']
        self.assertEqual(head['started'], 0)
        self.assertEqual(head['submitted'], 0)
        self.assertEqual(head['average'], 0.0)
        self.assertEqual(head['pass_rate'], 0.0)
        self.assertContains(response, 'No attempts recorded yet')

    def test_headline_counts_and_rates(self):
        self.sit(self.student, correct_count=4)      # 100%, passes
        self.sit(self.other, correct_count=1)        # 25%, fails (pass mark 50)
        self.as_staff()
        head = self.client.get(reverse('analytics_overview')).context['headline']

        self.assertEqual(head['started'], 2)
        self.assertEqual(head['submitted'], 2)
        self.assertEqual(head['passed'], 1)
        self.assertEqual(head['pass_rate'], 50.0)
        self.assertEqual(head['average'], 62.5)      # (100 + 25) / 2
        self.assertEqual(head['students'], 2)

    def test_in_progress_attempts_are_excluded_from_averages(self):
        """An unscored attempt must not drag the average toward zero."""
        self.sit(self.student, correct_count=4)      # 100%
        ExamAttempt.objects.create(                  # still open, no score
            exam=self.exam, student=self.other, attempt_no=1,
            expires_at=timezone.now() + datetime.timedelta(hours=1))

        self.as_staff()
        head = self.client.get(reverse('analytics_overview')).context['headline']
        self.assertEqual(head['started'], 2)
        self.assertEqual(head['submitted'], 1)
        self.assertEqual(head['in_progress'], 1)
        self.assertEqual(head['average'], 100.0,
                         'the open attempt must not be averaged in')
        self.assertEqual(head['pass_rate'], 100.0,
                         'pass rate is over submitted attempts only')
        self.assertEqual(head['completion_rate'], 50.0)

    def test_accuracy_counts_only_marked_answers(self):
        attempt = ExamAttempt.objects.create(
            exam=self.exam, student=self.student, attempt_no=1,
            expires_at=timezone.now() + datetime.timedelta(hours=1))
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[0],
            selected_option=self.questions[0].correct)
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[1],
            selected_option=(self.questions[1].correct % 4) + 1)
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[2], selected_option=None)
        score_attempt(attempt)

        self.as_staff()
        head = self.client.get(reverse('analytics_overview')).context['headline']
        self.assertEqual(head['answered'], 2, 'the skipped answer is not marked')
        self.assertEqual(head['accuracy'], 50.0)
        self.assertEqual(head['skipped'], 1)

    def test_legacy_scores_are_reported_but_excluded_from_accuracy(self):
        score_table.objects.create(
            exam_code=self.exam, email_id=self.student, role_id_id=2,
            scored_marks=15, percentage=75)
        self.as_staff()
        head = self.client.get(reverse('analytics_overview')).context['headline']
        self.assertEqual(head['legacy_results'], 1)
        self.assertEqual(head['submitted'], 0, 'a legacy row is not an attempt')
        self.assertEqual(head['accuracy'], 0.0, 'legacy rows have no answer detail')

    def test_course_rows_aggregate_per_course(self):
        self.sit(self.student, correct_count=4)
        self.as_staff()
        rows = self.client.get(reverse('analytics_overview')).context['rows']
        mine = [r for r in rows if r['course'].course_id == self.course.course_id][0]
        self.assertEqual(mine['attempts'], 1)
        self.assertEqual(mine['passed'], 1)
        self.assertEqual(mine['average'], 100.0)
        self.assertEqual(mine['pass_rate'], 100.0)

    def test_topic_accuracy_only_counts_questions_with_a_topic(self):
        first = self.questions[0]
        first.topic = 'Kinematics'
        first.save(update_fields=['topic'])
        self.sit(self.student, correct_count=4)

        self.as_staff()
        topics = self.client.get(reverse('analytics_overview')).context['topic_rows']
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]['topic'], 'Kinematics')
        self.assertEqual(topics[0]['answered'], 1)
        self.assertEqual(topics[0]['accuracy'], 100.0)

    def test_query_count_does_not_grow_with_attempts(self):
        self.as_staff()
        self.client.get(reverse('analytics_overview'))
        with self.assertNumQueries(EXPECTED_OVERVIEW_QUERIES):
            self.client.get(reverse('analytics_overview'))

        for student in (self.student, self.other):
            self.sit(student, correct_count=2)

        with self.assertNumQueries(EXPECTED_OVERVIEW_QUERIES):
            self.client.get(reverse('analytics_overview'))


class AnalyticsExamTests(AnalyticsBase):

    def test_exam_stats(self):
        self.sit(self.student, correct_count=4)      # 100%
        self.sit(self.other, correct_count=2)        # 50%, passes at pass mark 50
        self.as_staff()
        stats = self.client.get(
            reverse('analytics_exam', args=[self.exam.exam_code])).context['stats']
        self.assertEqual(stats['submitted'], 2)
        self.assertEqual(stats['students'], 2)
        self.assertEqual(stats['average'], 75.0)
        self.assertEqual(stats['best'], 100.0)
        self.assertEqual(stats['pass_rate'], 100.0)

    def test_questions_are_ordered_hardest_first(self):
        # Student answers only question 1 correctly; the rest are wrong.
        self.sit(self.student, correct_count=1)
        self.as_staff()
        rows = list(self.client.get(
            reverse('analytics_exam', args=[self.exam.exam_code])).context['question_rows'])
        self.assertEqual(rows[0]['accuracy'], 0.0, 'a missed question comes first')
        self.assertEqual(rows[-1]['accuracy'], 100.0,
                         'the one everyone got right comes last')

    def test_unanswered_questions_report_no_accuracy_and_sort_last(self):
        attempt = ExamAttempt.objects.create(
            exam=self.exam, student=self.student, attempt_no=1,
            expires_at=timezone.now() + datetime.timedelta(hours=1))
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[0],
            selected_option=(self.questions[0].correct % 4) + 1)
        score_attempt(attempt)

        self.as_staff()
        rows = list(self.client.get(
            reverse('analytics_exam', args=[self.exam.exam_code])).context['question_rows'])
        self.assertEqual(rows[0]['question'].ques_id, self.questions[0].ques_id)
        self.assertEqual(rows[0]['accuracy'], 0.0)
        self.assertEqual(rows[-1]['answered'], 0)

    def test_exam_with_no_attempts_renders(self):
        self.as_staff()
        response = self.client.get(
            reverse('analytics_exam', args=[self.exam.exam_code]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['submitted'], 0)
        self.assertEqual(response.context['stats']['average'], 0.0)

    def test_unknown_exam_is_404(self):
        self.as_staff()
        self.assertEqual(
            self.client.get(reverse('analytics_exam', args=['NOPE'])).status_code,
            404)


class AnalyticsStudentTests(AnalyticsBase):

    def test_summary_for_one_student_only(self):
        self.sit(self.student, correct_count=4)
        self.sit(self.other, correct_count=0)

        self.as_staff()
        response = self.client.get(
            reverse('analytics_student', args=[self.student.email_id]))
        summary = response.context['summary']
        self.assertEqual(summary['submitted'], 1)
        self.assertEqual(summary['passed'], 1)
        self.assertEqual(summary['average'], 100.0)
        self.assertEqual(summary['accuracy'], 100.0)
        self.assertEqual(len(response.context['attempts']), 1,
                         'the other student must not appear')

    def test_progress_is_ordered_oldest_first(self):
        first = self.sit(self.student, correct_count=1)
        ExamAttempt.objects.filter(pk=first.pk).update(
            started_at=timezone.now() - datetime.timedelta(days=2))
        second = ExamAttempt.objects.create(
            exam=self.exam, student=self.student, attempt_no=2,
            expires_at=timezone.now() + datetime.timedelta(hours=1))
        for q in self.questions:
            AttemptAnswer.objects.create(
                attempt=second, question=q, selected_option=q.correct)
        score_attempt(second)

        self.as_staff()
        progress = self.client.get(
            reverse('analytics_student', args=[self.student.email_id])
        ).context['progress']
        self.assertEqual([p['percentage'] for p in progress], [25.0, 100.0])

    def test_legacy_rows_are_listed_separately(self):
        score_table.objects.create(
            exam_code=self.exam, email_id=self.student, role_id_id=2,
            scored_marks=12, percentage=60)
        self.as_staff()
        response = self.client.get(
            reverse('analytics_student', args=[self.student.email_id]))
        self.assertEqual(len(response.context['legacy']), 1)
        self.assertContains(response, 'Historical results')
        self.assertEqual(response.context['summary']['submitted'], 0,
                         'a legacy row is not counted as a completed attempt')

    def test_student_with_no_attempts_renders(self):
        self.as_staff()
        response = self.client.get(
            reverse('analytics_student', args=[self.other.email_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'has not attempted an exam yet')


# Overview issues a fixed set of aggregates: session, user, two headline
# aggregates, the course page count and page, the topic rollup and the exam
# list. The exact number matters less than it not growing with attempts.
EXPECTED_OVERVIEW_QUERIES = 9
