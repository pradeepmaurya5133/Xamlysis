"""Tests for the staff question bank.

The bank exposes answer keys, so the permission tests matter as much as the
filtering ones: a student must not reach any of it.
"""

from django.urls import reverse

from database.models import ques_table, AttemptAnswer, ExamAttempt, User
from database.exam_views import score_attempt
from database.tests import ExamEngineTestCase, PASSWORD


class QuestionBankPermissionTests(ExamEngineTestCase):

    def urls(self):
        return [
            reverse('question_bank'),
            reverse('question_create'),
            reverse('question_preview', args=[self.questions[0].ques_id]),
            reverse('question_edit', args=[self.questions[0].ques_id]),
        ]

    def test_anonymous_is_redirected_to_login(self):
        for url in self.urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login', response.url)

    def test_student_is_forbidden_everywhere(self):
        self.login_student()
        for url in self.urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_student_cannot_create_or_edit_by_post(self):
        self.login_student()
        before = ques_table.objects.count()
        payload = {
            'ques_id': 'HACK-1', 'exam_code': self.exam.exam_code, 'ques': 'x',
            'option1': 'a', 'option2': 'b', 'option3': 'c', 'option4': 'd',
            'correct': '1', 'marks': '5', 'difficulty': 'easy', 'topic': '',
            'explanation': '',
        }
        self.assertEqual(
            self.client.post(reverse('question_create'), payload).status_code, 403)
        self.assertEqual(ques_table.objects.count(), before)

        target = self.questions[0]
        original = target.correct
        self.assertEqual(
            self.client.post(
                reverse('question_edit', args=[target.ques_id]), payload).status_code,
            403)
        target.refresh_from_db()
        self.assertEqual(target.correct, original, 'the key must not change')

    def test_answer_key_is_not_exposed_to_students(self):
        """Even the preview page, which shows the key, must refuse a student."""
        self.login_student()
        response = self.client.get(
            reverse('question_preview', args=[self.questions[0].ques_id]))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_reach_every_page(self):
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)
        for url in self.urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class QuestionBankFilterTests(ExamEngineTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)
        first = self.questions[0]
        first.difficulty = ques_table.HARD
        first.topic = 'Kinematics'
        first.save(update_fields=['difficulty', 'topic'])

    def listed(self, **params):
        response = self.client.get(reverse('question_bank'), params)
        self.assertEqual(response.status_code, 200)
        return [q.ques_id for q in response.context['page'].object_list]

    def test_lists_every_question_by_default(self):
        ids = self.listed()
        for q in self.questions:
            self.assertIn(q.ques_id, ids)

    def test_filter_by_difficulty(self):
        ids = self.listed(difficulty=ques_table.HARD)
        self.assertEqual(ids, [self.questions[0].ques_id])

    def test_filter_by_topic(self):
        self.assertEqual(self.listed(topic='Kinematics'),
                         [self.questions[0].ques_id])

    def test_filter_by_course_and_class(self):
        self.assertEqual(len(self.listed(course=self.course.course_id)), 4)
        self.assertEqual(len(self.listed(**{'class': '11'})), 4)
        self.assertEqual(self.listed(**{'class': '12'}), [])

    def test_filter_by_exam(self):
        self.assertEqual(len(self.listed(exam=self.exam.exam_code)), 4)
        self.assertEqual(self.listed(exam='NOPE'), [])

    def test_search_matches_text_id_and_topic(self):
        self.assertIn(self.questions[1].ques_id, self.listed(q='Question 2'))
        self.assertIn(self.questions[0].ques_id, self.listed(q='Kinematics'))
        self.assertEqual(self.listed(q='zzzz-no-match'), [])

    def test_filters_combine(self):
        self.assertEqual(
            self.listed(course=self.course.course_id, difficulty=ques_table.HARD),
            [self.questions[0].ques_id])
        self.assertEqual(
            self.listed(course=self.course.course_id, difficulty=ques_table.EASY),
            [])

    def test_pagination_keeps_filters(self):
        response = self.client.get(reverse('question_bank'), {'difficulty': 'hard'})
        self.assertIn('difficulty=hard', response.context['filter_qs'])

    def test_empty_state_is_shown(self):
        response = self.client.get(reverse('question_bank'), {'q': 'zzzz-no-match'})
        self.assertContains(response, 'No questions match these filters')


class QuestionEditingTests(ExamEngineTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)

    def payload(self, question, **overrides):
        data = {
            'ques_id': question.ques_id,
            'exam_code': question.exam_code_id,
            'ques': question.ques,
            'option1': question.option1, 'option2': question.option2,
            'option3': question.option3, 'option4': question.option4,
            'correct': question.correct, 'marks': question.marks,
            'difficulty': question.difficulty, 'topic': question.topic,
            'explanation': question.explanation,
        }
        data.update(overrides)
        return data

    def test_staff_can_create_a_question(self):
        before = ques_table.objects.count()
        response = self.client.post(reverse('question_create'), {
            'ques_id': 'TST11-EXAM-Q9', 'exam_code': self.exam.exam_code,
            'ques': 'A brand new question?', 'option1': 'w', 'option2': 'x',
            'option3': 'y', 'option4': 'z', 'correct': '3', 'marks': '5',
            'difficulty': 'easy', 'topic': 'Newtopic', 'explanation': 'Because.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ques_table.objects.count(), before + 1)
        created = ques_table.objects.get(ques_id='TST11-EXAM-Q9')
        self.assertEqual(created.correct, 3)
        self.assertEqual(created.topic, 'Newtopic')

    def test_duplicate_options_are_rejected(self):
        before = ques_table.objects.count()
        response = self.client.post(reverse('question_create'), {
            'ques_id': 'DUP-1', 'exam_code': self.exam.exam_code,
            'ques': 'Same options?', 'option1': 'same', 'option2': 'same',
            'option3': 'c', 'option4': 'd', 'correct': '1', 'marks': '5',
            'difficulty': 'easy', 'topic': '', 'explanation': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'must all be different')
        self.assertEqual(ques_table.objects.count(), before)

    def test_zero_marks_is_rejected(self):
        response = self.client.post(reverse('question_create'), self.payload(
            self.questions[0], ques_id='ZERO-1', marks='0'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'greater than zero')

    def test_editing_does_not_change_a_recorded_score(self):
        """The core history-preservation requirement."""
        attempt = self.start_attempt()
        for q in self.questions:
            AttemptAnswer.objects.create(
                attempt=attempt, question=q, selected_option=q.correct)
        score_attempt(attempt)
        attempt.refresh_from_db()
        recorded = (attempt.score, attempt.percentage, attempt.correct_count)
        self.assertEqual(attempt.score, 20)

        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)
        target = self.questions[0]
        new_key = (target.correct % 4) + 1
        response = self.client.post(
            reverse('question_edit', args=[target.ques_id]),
            self.payload(target, correct=new_key, ques='Reworded question?'))
        self.assertEqual(response.status_code, 302)

        target.refresh_from_db()
        self.assertEqual(target.correct, new_key)
        self.assertEqual(target.ques, 'Reworded question?')

        attempt.refresh_from_db()
        self.assertEqual(
            (attempt.score, attempt.percentage, attempt.correct_count), recorded,
            'editing a question must not move an already recorded score')

        stored = AttemptAnswer.objects.get(attempt=attempt, question=target)
        self.assertTrue(stored.is_correct, 'the stored verdict must survive the edit')

    def test_edit_page_warns_when_the_question_is_already_used(self):
        attempt = self.start_attempt()
        AttemptAnswer.objects.create(
            attempt=attempt, question=self.questions[0],
            selected_option=self.questions[0].correct)
        score_attempt(attempt)

        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)
        response = self.client.get(
            reverse('question_edit', args=[self.questions[0].ques_id]))
        self.assertEqual(response.context['used_in'], 1)
        self.assertContains(response, 'scored attempt')

    def test_question_id_cannot_be_changed_by_editing(self):
        target = self.questions[1]
        self.client.post(
            reverse('question_edit', args=[target.ques_id]),
            self.payload(target, ques_id='RENAMED-1'))
        self.assertTrue(ques_table.objects.filter(ques_id=target.ques_id).exists())
        self.assertFalse(ques_table.objects.filter(ques_id='RENAMED-1').exists())


class QuestionPreviewTests(ExamEngineTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)

    def test_preview_shows_the_key_and_explanation_to_staff(self):
        question = self.questions[0]
        response = self.client.get(
            reverse('question_preview', args=[question.ques_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Correct answer')
        self.assertContains(response, question.explanation)

    def test_preview_reports_answer_statistics(self):
        attempt = self.start_attempt()
        question = self.questions[0]
        AttemptAnswer.objects.create(
            attempt=attempt, question=question, selected_option=question.correct)
        score_attempt(attempt)

        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)
        response = self.client.get(
            reverse('question_preview', args=[question.ques_id]))
        self.assertEqual(response.context['stats']['total'], 1)
        self.assertEqual(response.context['stats']['correct'], 1)
        self.assertEqual(response.context['stats']['wrong'], 0)

    def test_unknown_question_is_404(self):
        self.assertEqual(
            self.client.get(reverse('question_preview', args=['NOPE'])).status_code,
            404)
