from django.contrib import admin
from database.models import *
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from django.contrib.auth.forms import UserCreationForm

from .forms import MyUserCreationForm, MyUserChangeForm


class AdminUserCreationForm(UserCreationForm):
    """Create a user from the admin, including the fields the model needs.

    Django's stock UserAdmin add form only collects username and a password.
    This model's primary key is email_id, which that form never asks for, so
    saving produced a row with an empty primary key and the redirect afterwards
    failed with NoReverseMatch. Asking for email_id here is what makes creating
    a teacher account possible at all.

    Unlike the public sign-up form, this one does expose role_id: the admin is
    already trusted, and choosing the role is the entire point of creating a
    teacher here.
    """

    class Meta:
        model = User
        fields = ('email_id', 'username', 'first_name', 'last_name',
                  'mobile_no', 'role_id')


class MyUserAdmin(UserAdmin):
    add_form = AdminUserCreationForm
    model = User
    ordering = ['email_id']
    list_display = ['email_id', 'username', 'first_name', 'last_name',
                    'role_id', 'is_staff', 'is_superuser', 'is_active']
    list_filter = ['role_id', 'is_staff', 'is_superuser', 'is_active']
    search_fields = ['email_id', 'username', 'first_name', 'last_name']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email_id', 'username', 'first_name', 'last_name',
                       'mobile_no', 'role_id', 'password1', 'password2'),
        }),
    )
    fieldsets = (
        (None, {'fields': ('email_id', 'password')}),
        ('Personal', {'fields': ('username', 'first_name', 'last_name', 'mobile_no')}),
        ('Role and permissions', {
            'fields': ('role_id', 'is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions'),
            'description': 'role_id 1 is TEACHER and grants the exam staff '
                           'pages; role_id 2 is STUDENT.',
        }),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )


admin.site.register(User, MyUserAdmin)


# ---------------------------------------------------------------------------
# Exam administration
#
# Only User was registered before, so courses, exams, questions and results
# could not be managed from the admin at all.
# ---------------------------------------------------------------------------

@admin.register(role_id)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['role_id', 'role_name']


@admin.register(course_id)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_id', 'course_name', 'class_stu_tech', 'exam_count']
    list_filter = ['class_stu_tech']
    search_fields = ['course_id', 'course_name']
    ordering = ['class_stu_tech', 'course_id']

    @admin.display(description='Exams')
    def exam_count(self, obj):
        return exam_details.objects.filter(course_id_id=obj.course_id).count()


class QuestionInline(admin.StackedInline):
    """Author a paper from inside the exam it belongs to."""

    model = ques_table
    extra = 0
    fields = [
        'ques_id', 'ques',
        ('option1', 'option2'),
        ('option3', 'option4'),
        ('correct', 'marks'),
        'explanation',
    ]
    ordering = ['ques_id']


@admin.register(exam_details)
class ExamAdmin(admin.ModelAdmin):
    list_display = [
        'exam_code', 'exam_title', 'course_id', 'class_stu', 'exam_type',
        'date', 'duration', 'question_count', 'max_marks', 'pass_percentage',
        'max_attempts', 'is_published',
    ]
    list_filter = ['exam_type', 'is_published', 'class_stu', 'date']
    list_editable = ['is_published', 'exam_type', 'pass_percentage', 'max_attempts']
    search_fields = ['exam_code', 'exam_title']
    date_hierarchy = 'date'
    inlines = [QuestionInline]
    fieldsets = (
        ('Identity', {'fields': ('exam_code', 'exam_title', 'course_id', 'class_stu')}),
        ('Schedule', {'fields': ('date', 'start_time', 'duration')}),
        ('Marking', {'fields': ('no_of_ques', 'max_marks', 'pass_percentage')}),
        ('Availability', {'fields': ('exam_type', 'max_attempts', 'is_published', 'email_id')}),
    )

    @admin.display(description='Questions')
    def question_count(self, obj):
        actual = ques_table.objects.filter(exam_code_id=obj.exam_code).count()
        if actual == obj.no_of_ques:
            return actual
        # Flag papers whose declared length does not match the questions saved.
        return format_html('<span style="color:#b00">{} of {}</span>', actual, obj.no_of_ques)


@admin.register(ques_table)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['ques_id', 'short_question', 'exam_code', 'correct', 'marks']
    list_filter = ['exam_code__exam_type', 'exam_code__class_stu', 'marks']
    search_fields = ['ques_id', 'ques']
    ordering = ['exam_code', 'ques_id']

    @admin.display(description='Question')
    def short_question(self, obj):
        return obj.ques[:70] + ('...' if len(obj.ques) > 70 else '')


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    can_delete = False
    readonly_fields = ['question', 'selected_option', 'marked_for_review', 'is_correct', 'updated_at']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'student', 'exam', 'attempt_no', 'status', 'score', 'max_marks',
        'percentage', 'passed', 'correct_count', 'wrong_count',
        'unanswered_count', 'auto_submitted', 'started_at', 'submitted_at',
    ]
    list_filter = ['status', 'passed', 'auto_submitted', 'exam__class_stu']
    search_fields = ['student__email_id', 'exam__exam_code', 'exam__exam_title']
    date_hierarchy = 'started_at'
    inlines = [AttemptAnswerInline]
    # Results are produced by the scoring code; editing them by hand here would
    # silently disagree with the saved answers below.
    readonly_fields = [
        'exam', 'student', 'attempt_no', 'started_at', 'expires_at',
        'submitted_at', 'status', 'auto_submitted', 'score', 'max_marks',
        'percentage', 'passed', 'correct_count', 'wrong_count', 'unanswered_count',
    ]

    def has_add_permission(self, request):
        return False


@admin.register(score_table)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ['exam_code', 'email_id', 'scored_marks', 'percentage']
    list_filter = ['exam_code__class_stu']
    search_fields = ['email_id__email_id', 'exam_code__exam_code']


@admin.register(registration_table)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['exam_code', 'email_id', 'role_id']
    search_fields = ['email_id__email_id', 'exam_code__exam_code']


@admin.register(courses_availed)
class CoursesAvailedAdmin(admin.ModelAdmin):
    list_display = ['serial_no', 'email_id', 'course_id', 'role_id']
    search_fields = ['email_id__email_id', 'course_id__course_id']


@admin.register(class_stu_tech)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['serial_no', 'email_id', 'class_stu_tech', 'role_id']
    list_filter = ['class_stu_tech']
    search_fields = ['email_id__email_id']


@admin.register(query_table)
class QueryAdmin(admin.ModelAdmin):
    list_display = ['email_id', 'exam_code', 'query']
    search_fields = ['email_id__email_id', 'query']


@admin.register(notes_table)
class NotesAdmin(admin.ModelAdmin):
    list_display = ['email_id', 'exam_code', 'notes']
    search_fields = ['email_id__email_id', 'notes']


admin.site.site_header = 'Xamlysis Admin Portal'
admin.site.site_title = 'Xamlysis Admin'
admin.site.index_title = 'Courses, exams and results'
