
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.db.models.deletion import CASCADE
from django.db.models.fields import AutoField, IntegerField
from django.db.models.fields import related
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone

# Create your models here.

class User(AbstractUser):
    email_id = models.EmailField(max_length=200  , primary_key=True ,unique=True)
    mobile_no = models.CharField(max_length=200 , default="0")
    role_id = models.ForeignKey("role_id" , on_delete=models.CASCADE , default=2)
    USERNAME_FIELD = 'email_id'
    
    REQUIRED_FIELDS = [] 
    # A list of the field names that will be prompted for when creating a user via the createsuperuser management command. 
    # The user will be prompted to supply a value for each of these fields. 
    # REQUIRED_FIELDS has no effect in other parts of Django, like creating a user in the admin.

class UserManager(BaseUserManager):

    def create_user(self , email_id,password=None):
        if not email_id:
            raise ValueError('User must have an email address')

        user = self.model( email_id=self.normalize_email(email_id) ,)
        # Normalizes email addresses by lowercasing the domain portion of the email address.

        user.set_password(password)
        user.save(using = self.db)
        return user

    def create_superuser(self, username, password, **kwargs):
        user = self.model(email=username, is_staff=True, is_superuser=True,**kwargs)
        user.set_password(password)
        user.save()
        return user


class role_id(models.Model):
    role_id = models.IntegerField(primary_key=True)
    role_name= models.CharField(max_length=100)
    def __str__(self):
        return str (self.role_name)

class course_id(models.Model):
    course_id = models.CharField(primary_key=True , max_length=100)
    course_name= models.TextField(max_length=100)
    class_stu_tech=models.IntegerField(default=11)
"""
class sign_up(models.Model):
    role_id=models.ForeignKey("role_id" , on_delete=models.CASCADE)
    id=models.CharField( max_length=50)
    name=models.TextField()
    username=models.CharField(max_length=100)
    password=models.CharField(max_length=200)
    email_id=models.EmailField(primary_key=True)
    mobile_no=models.CharField(max_length=200)
    institute_name=models.TextField()
"""


class class_stu_tech(models.Model):
    role_id=models.ForeignKey("role_id" , on_delete=models.CASCADE)
    #email_id=models.ForeignKey("sign_up" , on_delete=models.CASCADE)
    email_id = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE )
    class_stu_tech=models.IntegerField()
    serial_no=models.AutoField(primary_key=True)


class courses_availed(models.Model):
    course_id=models.ForeignKey("course_id" , on_delete=models.CASCADE )
    role_id=models.ForeignKey("role_id" , on_delete=models.CASCADE)
    #email_id=models.ForeignKey("sign_up" , on_delete=models.CASCADE)
    email_id = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE )
    serial_no=models.AutoField(primary_key=True)

class exam_details(models.Model):
    exam_code=models.CharField(max_length=50 , primary_key=True)
    exam_title=models.TextField()
    date=models.DateField(help_text = "(YYYY-MM-DD)")
    start_time=models.TimeField()
    duration=models.DurationField( help_text="(HH:MM:SS)")
    no_of_ques=models.IntegerField()
    max_marks=models.IntegerField()
    course_id=models.ForeignKey("course_id" , on_delete=models.CASCADE )
    #email_id=models.ForeignKey("sign_up" , on_delete=models.CASCADE)
    email_id = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE )
    class_stu = models.IntegerField(default=11)

    # Added by the exam engine. Every field has a default so existing rows
    # migrate without a data migration.
    PRACTICE = 'practice'
    FULL_LENGTH = 'full'
    EXAM_TYPE_CHOICES = [
        (PRACTICE, 'Practice Test'),
        (FULL_LENGTH, 'Full-Length Exam'),
    ]
    exam_type = models.CharField(
        max_length=20, choices=EXAM_TYPE_CHOICES, default=FULL_LENGTH,
        help_text='Practice tests are open-ended; full-length exams are the scheduled papers.',
    )
    pass_percentage = models.PositiveSmallIntegerField(
        default=35, help_text='Percentage needed to pass.',
    )
    max_attempts = models.PositiveSmallIntegerField(
        default=3, help_text='How many times a student may sit this exam. 0 means unlimited.',
    )
    is_published = models.BooleanField(
        default=True, help_text='Unpublished exams are hidden from students.',
    )

    def __str__(self):
        return '%s - %s' % (self.exam_code, self.exam_title)

class ques_table(models.Model):
    ques_id=models.CharField(max_length=50 , primary_key=True)
    ques=models.TextField(max_length=500)
    option1=models.CharField(max_length=200)
    option2=models.CharField(max_length=200)
    option3=models.CharField(max_length=200)
    option4=models.CharField(max_length=200)
    correct=models.IntegerField()
    marks=models.IntegerField()
    exam_code=models.ForeignKey("exam_details" , on_delete=models.CASCADE )

    # Shown on the result page only, never while the exam is open.
    explanation = models.TextField(
        max_length=1000, blank=True, default='',
        help_text='Shown to the student with their result. Optional.',
    )

    # Question-bank classification. Both are optional with defaults, so the
    # existing rows take the default without a backfill, and neither takes any
    # part in scoring: changing them cannot alter a past attempt.
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'
    DIFFICULTY_CHOICES = [
        (EASY, 'Easy'),
        (MEDIUM, 'Medium'),
        (HARD, 'Hard'),
    ]
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, default=MEDIUM, db_index=True,
        help_text='Used for filtering the question bank only.',
    )
    topic = models.CharField(
        max_length=120, blank=True, default='', db_index=True,
        help_text='Chapter or topic within the course. Optional, free text.',
    )

    def options(self):
        """The four options in order, so templates do not repeat themselves."""
        return [self.option1, self.option2, self.option3, self.option4]

class answer_table(models.Model):
    exam_code=models.ForeignKey("exam_details" , on_delete=models.CASCADE )
    ques_id=models.ForeignKey("ques_table",on_delete=models.CASCADE , related_name="ques_idd")
    #email_id=models.ForeignKey("sign_up",on_delete=models.CASCADE)
    email_id = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE )
    role_id=models.ForeignKey("role_id",on_delete=models.CASCADE )
    option_marked=models.IntegerField()
    check_correct=models.BooleanField()

class score_table(models.Model):
    exam_code=models.ForeignKey("exam_details" , on_delete=models.CASCADE )
    #email_id=models.ForeignKey("sign_up" , on_delete=models.CASCADE)
    email_id = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE )
    role_id=models.ForeignKey("role_id" , on_delete=models.CASCADE )
    scored_marks=models.IntegerField()
    percentage=models.DecimalField(max_digits=5,decimal_places=2)

class registration_table(models.Model):
    exam_code=models.ForeignKey("exam_details" , on_delete=models.CASCADE )
    #email_id=models.ForeignKey("sign_up" , on_delete=models.CASCADE)
    email_id = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE )
    role_id=models.ForeignKey("role_id" , on_delete=models.CASCADE )   

class notes_table(models.Model):
    #email_id=models.ForeignKey("sign_up" , on_delete=models.CASCADE)
    email_id = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE )
    exam_code=models.ForeignKey("exam_details" , on_delete=models.CASCADE )
    notes=models.TextField(max_length=500)

class query_table(models.Model):
    #email_id=models.ForeignKey("sign_up" , on_delete=models.CASCADE)
    email_id = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE )
    exam_code=models.ForeignKey("exam_details" , on_delete=models.CASCADE )
    role_id=models.ForeignKey("role_id" , on_delete=models.CASCADE)
    query=models.TextField(max_length=500)


"""
class sample(models.Model):
    email=models.CharField(max_length=200)
    phone=models.CharField(max_length=200)
    def __str__(self): #this is used so that the fields that are stored are displayed with thier respective emails instead of being numbered as table_name1,table_name2
        return self.email
"""

# You should also define a custom manager for your user model.
# If your user model defines username, email, is_staff, is_active, is_superuser, last_login, and date_joined fields the same as Django’s default user, you can install Django’s UserManager;
#  however, if your user model defines different fields, you’ll need to define a custom manager that extends BaseUserManager


# ---------------------------------------------------------------------------
# Exam engine
#
# The models above are the project's original schema and are left untouched so
# that existing rows keep working. The engine below adds what a real sitting
# needs and the originals do not model: a single attempt, when it started, when
# it must end, and one saved answer per question that survives a refresh.
#
# answer_table and score_table are still written on submission so the existing
# "previous exams" pages keep working against the same data they always used.
# ---------------------------------------------------------------------------


class ExamAttempt(models.Model):
    """One student's sitting of one exam.

    The deadline is stored rather than counted in the browser, so a reload, a
    second tab or a edited clock cannot buy extra time: every request checks
    expires_at on the server.
    """

    IN_PROGRESS = 'in_progress'
    SUBMITTED = 'submitted'
    EXPIRED = 'expired'
    STATUS_CHOICES = [
        (IN_PROGRESS, 'In progress'),
        (SUBMITTED, 'Submitted'),
        (EXPIRED, 'Expired'),
    ]

    exam = models.ForeignKey('exam_details', on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    attempt_no = models.PositiveIntegerField(default=1)

    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=IN_PROGRESS)
    auto_submitted = models.BooleanField(default=False)

    # Filled in by the server when the attempt is scored.
    score = models.IntegerField(default=0)
    max_marks = models.IntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)
    correct_count = models.IntegerField(default=0)
    wrong_count = models.IntegerField(default=0)
    unanswered_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['student', 'exam']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return '%s - %s (attempt %d)' % (self.student_id, self.exam_id, self.attempt_no)

    @property
    def is_open(self):
        """True while the attempt may still accept answers."""
        return self.status == self.IN_PROGRESS and timezone.now() < self.expires_at

    def seconds_remaining(self):
        if self.status != self.IN_PROGRESS:
            return 0
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))


class AttemptAnswer(models.Model):
    """A single saved answer, rewritten in place every time it changes.

    selected_option is null while a question is untouched, which is what makes
    the unanswered count meaningful. is_correct stays null until the attempt is
    scored, so nothing in this table reveals the key before submission.
    """

    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('ques_table', on_delete=models.CASCADE)
    selected_option = models.PositiveSmallIntegerField(null=True, blank=True)
    marked_for_review = models.BooleanField(default=False)
    is_correct = models.BooleanField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('attempt', 'question')]
        ordering = ['question_id']

    def __str__(self):
        return '%s / %s = %s' % (self.attempt_id, self.question_id, self.selected_option)
