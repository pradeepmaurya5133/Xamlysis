"""Pilot-readiness regressions.

These pin behaviour that a real cohort will hit on day one: students who have
just registered and have not joined a class yet, and students who join more
than one class because the interface lets them.
"""

import datetime

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from database.models import (
    User, class_stu_tech, courses_availed, exam_details, ExamAttempt,
)
from database.tests import ExamEngineTestCase, PASSWORD

STUDENT_PAGES = [
    '/dashboard/',
    '/stu_home/',
    '/exams/',
    '/exams/history/',
    '/class_select/',
    '/course_select/',
    '/student_exams_scheduled/',
    '/student_previous_exams/',
]


class NewStudentTests(ExamEngineTestCase):
    """A freshly registered student has no class and no courses yet."""

    def setUp(self):
        super().setUp()
        self.fresh = User.objects.create(
            email_id='fresh@test.local', username='freshuser', role_id_id=2)
        self.fresh.set_password(PASSWORD)
        self.fresh.save()
        self.client.login(email_id=self.fresh.email_id, password=PASSWORD)

    def test_no_class_yet_means_no_crash_anywhere(self):
        """stu_home used to raise DoesNotExist for every new sign-up."""
        self.assertEqual(
            class_stu_tech.objects.filter(email_id_id=self.fresh.email_id).count(), 0)
        for url in STUDENT_PAGES:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_dashboard_is_empty_rather_than_broken(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['attempted'], 0)
        self.assertEqual(list(response.context['in_progress']), [])

    def test_a_new_student_can_still_be_shown_available_exams(self):
        response = self.client.get('/dashboard/')
        codes = [r['exam'].exam_code for r in response.context['available']]
        self.assertIn(self.exam.exam_code, codes)
        row = [r for r in response.context['available']
               if r['exam'].exam_code == self.exam.exam_code][0]
        self.assertFalse(row['relevant'],
                         'not in their class yet, so it is not flagged as theirs')


class MultiClassStudentTests(ExamEngineTestCase):
    """/class_select/ lets a student join several classes; pages must cope."""

    def setUp(self):
        super().setUp()
        self.login_student()
        # The fixture already puts this student in class 11.
        class_stu_tech.objects.create(
            role_id_id=2, email_id_id=self.student.email_id, class_stu_tech=12)

    def test_two_classes_does_not_crash_any_student_page(self):
        """stu_home used to raise MultipleObjectsReturned here."""
        self.assertEqual(
            class_stu_tech.objects.filter(
                email_id_id=self.student.email_id).count(), 2)
        for url in STUDENT_PAGES:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_exams_from_both_classes_are_considered(self):
        courses_availed.objects.create(
            course_id=self.course, role_id_id=2, email_id_id=self.student.email_id)
        response = self.client.get('/stu_home/')
        self.assertEqual(response.status_code, 200)
        # stu_home publishes the class list under the context key "class".
        self.assertIn(11, response.context['class'])
        self.assertIn(12, response.context['class'])


class RegistrationTests(ExamEngineTestCase):
    """The sign-up route a pilot cohort will actually use."""

    def test_a_student_can_register_and_log_in(self):
        before = User.objects.count()
        response = Client().post('/temp_sign_up', {
            'role_id': '2',
            'email_id': 'newjoiner@test.local',
            'username': 'newjoiner',
            'first_name': 'New', 'last_name': 'Joiner',
            'mobile_no': '9000000001',
            'password1': 'Tarkashri#7741', 'password2': 'Tarkashri#7741',
        })
        self.assertIn(response.status_code, (200, 302))
        self.assertEqual(User.objects.count(), before + 1)

        created = User.objects.get(email_id='newjoiner@test.local')
        self.assertEqual(created.role_id_id, 2, 'registers as a student')
        self.assertFalse(created.is_staff, 'a sign-up must not create staff')
        self.assertFalse(created.is_superuser)
        self.assertNotEqual(created.password, 'Tarkashri#7741',
                            'the password must be hashed, not stored as given')
        self.assertTrue(
            Client().login(email_id='newjoiner@test.local', password='Tarkashri#7741'))

    def test_a_signup_cannot_grant_itself_the_teacher_role(self):
        """Posting role_id=1 used to create a teacher with full staff access.

        Anyone registering on the public form could then read the question bank
        and every answer key. Self-registration must always produce a student.
        """
        client = Client()
        client.post('/temp_sign_up', {
            'role_id': '1',                      # asks to be a teacher
            'email_id': 'wannabe@test.local', 'username': 'wannabezz',
            'first_name': 'Wanna', 'last_name': 'Be', 'mobile_no': '9000000002',
            'password1': 'Tarkashri#7741', 'password2': 'Tarkashri#7741',
        })
        created = User.objects.get(email_id='wannabe@test.local')
        self.assertEqual(created.role_id_id, 2, 'must be created as a student')
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_superuser)

        self.assertTrue(
            client.login(email_id='wannabe@test.local', password='Tarkashri#7741'))
        for url in ('/staff/questions/', '/staff/analytics/',
                    '/exam_detail', '/teachers_schedule/'):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 403, url)

    def test_the_answer_key_is_unreachable_by_a_self_registered_account(self):
        client = Client()
        client.post('/temp_sign_up', {
            'role_id': '1',
            'email_id': 'keyseeker@test.local', 'username': 'keyseekerz',
            'first_name': 'Key', 'last_name': 'Seeker', 'mobile_no': '9000000005',
            'password1': 'Tarkashri#7741', 'password2': 'Tarkashri#7741',
        })
        client.login(email_id='keyseeker@test.local', password='Tarkashri#7741')
        response = client.get(
            reverse('question_preview', args=[self.questions[0].ques_id]))
        self.assertEqual(response.status_code, 403)


class UnauthorizedUrlTests(ExamEngineTestCase):
    """Invalid and unauthorised URLs must fail cleanly, not with a 500."""

    def test_unknown_attempt_ids_are_not_found(self):
        self.login_student()
        for url in ('/exams/attempt/999999/',
                    '/exams/attempt/999999/result/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_unknown_exam_code_is_not_found(self):
        self.login_student()
        self.assertEqual(
            self.client.get('/exams/NO-SUCH-EXAM/start/').status_code, 404)

    def test_non_numeric_attempt_id_is_not_found(self):
        self.login_student()
        self.assertEqual(self.client.get('/exams/attempt/abc/').status_code, 404)

    def test_unpublished_exam_cannot_be_started(self):
        self.exam.is_published = False
        self.exam.save(update_fields=['is_published'])
        self.login_student()
        self.assertEqual(
            self.client.get(
                reverse('exam_start', args=[self.exam.exam_code])).status_code, 404)
        self.assertFalse(ExamAttempt.objects.filter(exam=self.exam).exists())
