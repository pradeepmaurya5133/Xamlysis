"""Bring the original demo exams up to 20 questions each.

    python manage.py topup_exams            # add the missing questions
    python manage.py topup_exams --dry-run  # report what would change

seed_demo created seven exams with five questions apiece. This adds fifteen
more to each from _topup_bank.py and then re-marks the whole paper so the marks
still add up to the exam's existing max_marks, leaving recorded results valid:

    100 mark exam -> 20 questions worth 5 each
     50 mark exam -> 10 questions worth 3 and 10 worth 2

Options are rotated across the finished paper so the correct answer falls on
option 1, 2, 3 and 4 in equal measure, the same way seed_exams does it.

Refuses to run if any answers have been recorded against these exams, since
re-marking a paper someone has already sat would change their score.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from database.models import exam_details, ques_table, answer_table

from ._topup_bank import TOPUP
from .seed_exams import rotate_options

TARGET_QUESTIONS = 20


def mark_plan(max_marks, count):
    """Per question marks for `count` questions summing exactly to max_marks.

    An even split is used when it divides cleanly; otherwise the remainder is
    spread one mark at a time over the first questions, so 50 marks across 20
    questions becomes ten 3s and ten 2s.
    """
    base, extra = divmod(max_marks, count)
    return [base + 1] * extra + [base] * (count - extra)


class Command(BaseCommand):
    help = "Top the original demo exams up to 20 questions each."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the changes without writing them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]

        codes = list(TOPUP)
        sat = answer_table.objects.filter(exam_code_id__in=codes).count()
        if sat:
            raise CommandError(
                "%d recorded answer(s) exist for these exams. Re-marking would "
                "change scores that students have already been given." % sat
            )

        added = remarked = 0
        for code, extra in TOPUP.items():
            exam = exam_details.objects.filter(exam_code=code).first()
            if not exam:
                self.stdout.write(self.style.WARNING("  %s not found, skipping" % code))
                continue

            existing = list(ques_table.objects.filter(exam_code_id=code).order_by("ques_id"))
            need = TARGET_QUESTIONS - len(existing)
            if need <= 0:
                self.stdout.write(
                    "  %-12s already has %d questions" % (code, len(existing))
                )
                continue
            if need > len(extra):
                raise CommandError(
                    "%s needs %d more questions but the bank holds %d"
                    % (code, need, len(extra))
                )

            if not dry:
                for n, (text, o1, o2, o3, o4, correct) in enumerate(extra[:need], start=1):
                    ques_table.objects.create(
                        ques_id="%s-T%d" % (code, n),
                        ques=text,
                        option1=o1, option2=o2, option3=o3, option4=o4,
                        correct=correct,
                        marks=0,  # set by the re-marking pass below
                        exam_code_id=code,
                    )

            added += need

            # Re-mark and rebalance the finished paper. On a dry run nothing has
            # been written, so size the plan from what the paper will hold rather
            # than from the rows that exist right now.
            paper = list(ques_table.objects.filter(exam_code_id=code).order_by("ques_id"))
            final_count = len(paper) if not dry else len(paper) + need
            plan = mark_plan(exam.max_marks, final_count)
            if not dry:
                for i, (q, marks) in enumerate(zip(paper, plan)):
                    target = (i % 4) + 1
                    opts = rotate_options(
                        [q.option1, q.option2, q.option3, q.option4], q.correct, target
                    )
                    q.option1, q.option2, q.option3, q.option4 = opts
                    q.correct = target
                    q.marks = marks
                    q.save(update_fields=[
                        "option1", "option2", "option3", "option4", "correct", "marks",
                    ])
                exam.no_of_ques = len(paper)
                exam.save(update_fields=["no_of_ques"])
            remarked += final_count

            if len(set(plan)) == 1:
                marks_desc = "%d questions x %d marks" % (final_count, plan[0])
            else:
                hi, lo = plan[0], plan[-1]
                marks_desc = "%d x %d marks and %d x %d marks" % (
                    plan.count(hi), hi, plan.count(lo), lo,
                )
            self.stdout.write(
                "  %-12s +%d -> %d questions, %s = %d"
                % (code, need, final_count, marks_desc, sum(plan))
            )

        self.stdout.write("")
        if dry:
            self.stdout.write(self.style.WARNING(
                "Dry run: %d question(s) would be added, %d re-marked." % (added, remarked)
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Added %d question(s) and re-marked %d." % (added, remarked)
            ))
