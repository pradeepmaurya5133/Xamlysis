"""Tests for the CSV question import.

The import writes to the question bank, so the tests check both that good data
lands correctly and that bad data lands nowhere: a rejected row must leave the
database exactly as it was.
"""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from database.models import ques_table
from database.csv_import import validate_rows, MAX_UPLOAD_BYTES, SESSION_KEY
from database.tests import ExamEngineTestCase, PASSWORD

HEADER = ('ques_id,exam_code,ques,option1,option2,option3,option4,'
          'correct,marks,difficulty,topic,explanation\n')


def row(ques_id='IMP-1', exam='TST11-EXAM', ques='Imported question?',
        o1='alpha', o2='beta', o3='gamma', o4='delta',
        correct='2', marks='5', difficulty='easy', topic='Topic',
        explanation='Because.'):
    return '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (
        ques_id, exam, ques, o1, o2, o3, o4, correct, marks,
        difficulty, topic, explanation)


def upload(text, name='questions.csv'):
    return SimpleUploadedFile(name, text.encode('utf-8'), content_type='text/csv')


class CsvImportPermissionTests(ExamEngineTestCase):

    def test_anonymous_is_redirected(self):
        for url in (reverse('question_import'), reverse('question_import_confirm')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login', response.url)

    def test_student_is_forbidden(self):
        self.login_student()
        self.assertEqual(self.client.get(reverse('question_import')).status_code, 403)
        self.assertEqual(
            self.client.post(reverse('question_import_confirm')).status_code, 403)

    def test_student_cannot_import_by_post(self):
        self.login_student()
        before = ques_table.objects.count()
        response = self.client.post(
            reverse('question_import'),
            {'csv_file': upload(HEADER + row())})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ques_table.objects.count(), before)

    def test_import_url_is_not_swallowed_by_the_question_detail_route(self):
        """/staff/questions/import/ must not resolve as a question id."""
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)
        response = self.client.get(reverse('question_import'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Import questions from CSV')


class CsvValidationTests(ExamEngineTestCase):
    """validate_rows must never write; it only reports."""

    def test_missing_required_column_is_reported(self):
        text = 'ques_id,exam_code,ques\nIMP-1,TST11-EXAM,hi\n'
        valid, errors, header_error = validate_rows(text)
        self.assertIsNotNone(header_error)
        self.assertIn('option1', header_error)
        self.assertEqual(valid, [])

    def test_a_good_row_validates(self):
        valid, errors, header_error = validate_rows(HEADER + row())
        self.assertIsNone(header_error)
        self.assertEqual(errors, [])
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]['ques_id'], 'IMP-1')
        self.assertEqual(valid[0]['correct'], 2)
        self.assertEqual(valid[0]['marks'], 5)

    def test_existing_ques_id_is_rejected_not_overwritten(self):
        existing = self.questions[0]
        valid, errors, _ = validate_rows(HEADER + row(ques_id=existing.ques_id))
        self.assertEqual(valid, [])
        self.assertEqual(len(errors), 1)
        self.assertIn('already exists', errors[0]['problems'][0])

        existing.refresh_from_db()
        self.assertEqual(existing.ques, 'Question 1?', 'the original must be untouched')

    def test_duplicate_id_within_the_file_is_rejected(self):
        text = HEADER + row(ques_id='DUP') + row(ques_id='DUP', ques='Second')
        valid, errors, _ = validate_rows(text)
        self.assertEqual(len(valid), 1, 'the first occurrence is kept')
        self.assertEqual(len(errors), 1)
        self.assertIn('more than once', errors[0]['problems'][0])

    def test_unknown_exam_code_is_rejected(self):
        valid, errors, _ = validate_rows(HEADER + row(exam='NO-SUCH-EXAM'))
        self.assertEqual(valid, [])
        self.assertIn('No exam with code', errors[0]['problems'][0])

    def test_correct_outside_one_to_four_is_rejected(self):
        for bad in ('0', '5', 'two', ''):
            with self.subTest(correct=bad):
                valid, errors, _ = validate_rows(HEADER + row(correct=bad))
                self.assertEqual(valid, [])
                self.assertTrue(
                    any('correct must be' in p for p in errors[0]['problems']))

    def test_bad_marks_are_rejected(self):
        for bad in ('0', '-3', 'five'):
            with self.subTest(marks=bad):
                valid, errors, _ = validate_rows(HEADER + row(marks=bad))
                self.assertEqual(valid, [])

    def test_duplicate_options_are_rejected(self):
        valid, errors, _ = validate_rows(HEADER + row(o1='same', o2='same'))
        self.assertEqual(valid, [])
        self.assertTrue(
            any('all be different' in p for p in errors[0]['problems']))

    def test_blank_question_text_is_rejected(self):
        valid, errors, _ = validate_rows(HEADER + row(ques=''))
        self.assertEqual(valid, [])

    def test_invalid_difficulty_is_rejected(self):
        valid, errors, _ = validate_rows(HEADER + row(difficulty='impossible'))
        self.assertEqual(valid, [])
        self.assertTrue(
            any('difficulty must be' in p for p in errors[0]['problems']))

    def test_blank_difficulty_defaults_to_medium(self):
        valid, errors, _ = validate_rows(HEADER + row(difficulty=''))
        self.assertEqual(errors, [])
        self.assertEqual(valid[0]['difficulty'], ques_table.MEDIUM)

    def test_errors_carry_the_spreadsheet_row_number(self):
        text = HEADER + row(ques_id='OK-1') + row(ques_id='', ques='bad')
        valid, errors, _ = validate_rows(text)
        self.assertEqual(len(valid), 1)
        self.assertEqual(errors[0]['row'], 3, 'header is row 1, so the second data row is 3')

    def test_good_and_bad_rows_are_separated(self):
        text = HEADER + row(ques_id='G-1') + row(ques_id='B-1', correct='9') + row(ques_id='G-2')
        valid, errors, _ = validate_rows(text)
        self.assertEqual([v['ques_id'] for v in valid], ['G-1', 'G-2'])
        self.assertEqual([e['ques_id'] for e in errors], ['B-1'])

    def test_validation_writes_nothing(self):
        before = ques_table.objects.count()
        validate_rows(HEADER + row() + row(ques_id='IMP-2'))
        self.assertEqual(ques_table.objects.count(), before)


class CsvImportFlowTests(ExamEngineTestCase):

    def setUp(self):
        super().setUp()
        self.client.login(email_id=self.teacher.email_id, password=PASSWORD)

    def preview(self, text):
        return self.client.post(
            reverse('question_import'), {'csv_file': upload(text)})

    def test_preview_does_not_write(self):
        before = ques_table.objects.count()
        response = self.preview(HEADER + row() + row(ques_id='IMP-2'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['valid']), 2)
        self.assertEqual(ques_table.objects.count(), before,
                         'preview must not create anything')

    def test_confirm_writes_the_previewed_rows(self):
        before = ques_table.objects.count()
        self.preview(HEADER + row() + row(ques_id='IMP-2', correct='3'))
        response = self.client.post(reverse('question_import_confirm'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ques_table.objects.count(), before + 2)

        created = ques_table.objects.get(ques_id='IMP-1')
        self.assertEqual(created.correct, 2)
        self.assertEqual(created.marks, 5)
        self.assertEqual(created.difficulty, 'easy')
        self.assertEqual(created.topic, 'Topic')
        self.assertEqual(created.exam_code_id, self.exam.exam_code)

    def test_confirming_twice_does_not_import_twice(self):
        self.preview(HEADER + row())
        self.client.post(reverse('question_import_confirm'))
        count_after_first = ques_table.objects.count()

        second = self.client.post(reverse('question_import_confirm'))
        self.assertEqual(second.status_code, 302)
        self.assertEqual(ques_table.objects.count(), count_after_first,
                         'the session payload is cleared after a successful import')

    def test_re_importing_the_same_file_rejects_every_row(self):
        text = HEADER + row() + row(ques_id='IMP-2')
        self.preview(text)
        self.client.post(reverse('question_import_confirm'))
        after_first = ques_table.objects.count()

        response = self.preview(text)
        self.assertEqual(len(response.context['valid']), 0)
        self.assertEqual(len(response.context['errors']), 2)
        self.assertEqual(ques_table.objects.count(), after_first)

    def test_confirm_without_a_preview_is_refused(self):
        before = ques_table.objects.count()
        response = self.client.post(reverse('question_import_confirm'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ques_table.objects.count(), before)

    def test_confirm_rechecks_ids_created_since_the_preview(self):
        """A clash created between preview and confirm must abort the whole import."""
        self.preview(HEADER + row(ques_id='RACE-1') + row(ques_id='RACE-2'))
        # Someone else creates one of those ids in the meantime.
        ques_table.objects.create(
            ques_id='RACE-1', ques='Created elsewhere', option1='a', option2='b',
            option3='c', option4='d', correct=1, marks=5, exam_code=self.exam)
        before = ques_table.objects.count()

        response = self.client.post(reverse('question_import_confirm'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ques_table.objects.count(), before,
                         'nothing may be written when a clash is detected')
        self.assertFalse(ques_table.objects.filter(ques_id='RACE-2').exists(),
                         'the clean row must not be written either: all or nothing')

    def test_only_valid_rows_are_imported_from_a_mixed_file(self):
        before = ques_table.objects.count()
        self.preview(HEADER + row(ques_id='G-1') + row(ques_id='B-1', marks='0')
                     + row(ques_id='G-2'))
        self.client.post(reverse('question_import_confirm'))
        self.assertEqual(ques_table.objects.count(), before + 2)
        self.assertTrue(ques_table.objects.filter(ques_id='G-1').exists())
        self.assertTrue(ques_table.objects.filter(ques_id='G-2').exists())
        self.assertFalse(ques_table.objects.filter(ques_id='B-1').exists())

    def test_oversized_file_is_rejected(self):
        before = ques_table.objects.count()
        big = SimpleUploadedFile(
            'big.csv', b'x' * (MAX_UPLOAD_BYTES + 1), content_type='text/csv')
        response = self.client.post(reverse('question_import'), {'csv_file': big})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The limit is 2 MB')
        self.assertEqual(ques_table.objects.count(), before)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_non_csv_extension_is_rejected(self):
        bad = SimpleUploadedFile('questions.txt', HEADER.encode(), content_type='text/plain')
        response = self.client.post(reverse('question_import'), {'csv_file': bad})
        self.assertContains(response, 'Please upload a .csv file')

    def test_utf8_bom_from_a_spreadsheet_is_handled(self):
        text = '﻿' + HEADER + row(ques_id='BOM-1')
        response = self.preview(text)
        self.assertEqual(len(response.context['valid']), 1)
        self.assertEqual(response.context['valid'][0]['ques_id'], 'BOM-1')

    def test_missing_header_shows_a_message_and_writes_nothing(self):
        before = ques_table.objects.count()
        response = self.preview('ques_id,exam_code\nIMP-9,TST11-EXAM\n')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ques_table.objects.count(), before)
        self.assertNotIn('previewed', response.context)

    def test_imported_questions_appear_in_the_bank(self):
        self.preview(HEADER + row(ques_id='SHOWN-1', topic='Imported'))
        self.client.post(reverse('question_import_confirm'))
        listing = self.client.get(reverse('question_bank'), {'topic': 'Imported'})
        self.assertEqual(
            [q.ques_id for q in listing.context['page'].object_list], ['SHOWN-1'])
