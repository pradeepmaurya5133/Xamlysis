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


class AdminUserCreationTests(ExamEngineTestCase):
    """Creating a teacher from the admin is how pilot teachers are onboarded.

    Django's stock UserAdmin add form collects only username and a password.
    This model's primary key is email_id, which that form never asks for, so
    the row saved with an empty primary key and the admin then raised
    NoReverseMatch, returning 500.
    """

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create(
            email_id='siteadmin@test.local', username='siteadminx',
            role_id_id=1, is_staff=True, is_superuser=True)
        self.admin.set_password(PASSWORD)
        self.admin.save()
        self.client.login(email_id=self.admin.email_id, password=PASSWORD)

    def test_the_add_form_asks_for_the_primary_key(self):
        response = self.client.get('/admin/database/user/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email_id')
        self.assertContains(response, 'role_id')

    def test_a_teacher_can_be_created_and_reaches_the_staff_pages(self):
        before = User.objects.count()
        response = self.client.post('/admin/database/user/add/', {
            'email_id': 'pilotteacher@test.local', 'username': 'pilotteachx',
            'first_name': 'Pilot', 'last_name': 'Teacher',
            'mobile_no': '9000000014', 'role_id': '1',
            'password1': 'Kanchipuram#9920', 'password2': 'Kanchipuram#9920',
            'usable_password': 'true', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302, 'a 500 here means the add form is broken')
        self.assertEqual(User.objects.count(), before + 1)

        created = User.objects.get(email_id='pilotteacher@test.local')
        self.assertEqual(created.role_id_id, 1)

        teacher = Client()
        self.assertTrue(
            teacher.login(email_id=created.email_id, password='Kanchipuram#9920'))
        for url in ('/staff/questions/', '/staff/analytics/', '/exam_detail'):
            with self.subTest(url=url):
                self.assertEqual(teacher.get(url).status_code, 200, url)

    def test_creating_a_user_never_leaves_a_blank_primary_key(self):
        self.client.post('/admin/database/user/add/', {
            'username': 'nopk', 'password1': 'Kanchipuram#9920',
            'password2': 'Kanchipuram#9920', 'usable_password': 'true',
            '_save': 'Save',
        })
        self.assertEqual(
            User.objects.filter(email_id='').count(), 0,
            'a submission without an email must be rejected, not saved blank')


class ExamScheduleEnforcementTests(ExamEngineTestCase):
    """The exam date gates starting, not just what the dashboard lists.

    Found on production during the pilot: both pilot students completed fully
    scored attempts on an exam dated sixteen days out, by opening its start URL
    directly. The dashboard had filed it under "Upcoming" and never offered it.
    """

    def start(self):
        return self.client.get(reverse('exam_start', args=[self.exam.exam_code]))

    def test_future_dated_exam_cannot_be_started(self):
        self.exam.date = timezone.localdate() + datetime.timedelta(days=16)
        self.exam.save(update_fields=['date'])
        self.login_student()

        response = self.start()

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'cannot be started before then', status_code=403)
        self.assertEqual(
            ExamAttempt.objects.filter(exam=self.exam).count(), 0,
            'refusing to start must not leave an attempt behind')

    def test_refusal_does_not_consume_an_attempt(self):
        self.exam.date = timezone.localdate() + datetime.timedelta(days=1)
        self.exam.save(update_fields=['date'])
        self.login_student()

        for _ in range(3):
            self.assertEqual(self.start().status_code, 403)

        # max_attempts is 2 in the fixture: a student locked out early must
        # still have both attempts once the exam opens.
        self.exam.date = timezone.localdate()
        self.exam.save(update_fields=['date'])
        self.assertEqual(self.start().status_code, 302)
        self.assertEqual(ExamAttempt.objects.filter(exam=self.exam).count(), 1)

    def test_exam_dated_today_can_be_started(self):
        self.exam.date = timezone.localdate()
        self.exam.save(update_fields=['date'])
        self.login_student()

        self.assertEqual(self.start().status_code, 302)
        self.assertEqual(ExamAttempt.objects.filter(exam=self.exam).count(), 1)

    def test_past_dated_exam_can_still_be_started(self):
        """Only the future is refused; a past paper stays open as before."""
        self.exam.date = timezone.localdate() - datetime.timedelta(days=30)
        self.exam.save(update_fields=['date'])
        self.login_student()

        self.assertEqual(self.start().status_code, 302)
        self.assertEqual(ExamAttempt.objects.filter(exam=self.exam).count(), 1)

    def test_start_time_later_today_does_not_block(self):
        """The gate is date-only, matching what the dashboard offers.

        The dashboard lists an exam as available from midnight on its date, so
        refusing before start_time would fail a click on a card that says the
        exam is available.
        """
        self.exam.date = timezone.localdate()
        self.exam.start_time = datetime.time(23, 59)
        self.exam.save(update_fields=['date', 'start_time'])
        self.login_student()

        self.assertEqual(self.start().status_code, 302)

    def test_open_attempt_survives_the_exam_being_moved_later(self):
        """A student mid-exam is not stranded if the date moves out."""
        attempt = self.start_attempt()
        self.exam.date = timezone.localdate() + datetime.timedelta(days=7)
        self.exam.save(update_fields=['date'])

        response = self.start()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('exam_take', args=[attempt.pk]))

    def test_dashboard_and_start_agree(self):
        """Anything listed under "Available now" must actually start."""
        self.exam.date = timezone.localdate()
        self.exam.save(update_fields=['date'])
        self.login_student()

        available = self.client.get('/dashboard/').context['available']
        codes = [row['exam'].exam_code for row in available]
        self.assertIn(self.exam.exam_code, codes)
        self.assertEqual(self.start().status_code, 302)
