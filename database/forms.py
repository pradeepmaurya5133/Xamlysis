from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.forms.models import ModelForm
from database.models import *
from django.core import validators

class_stu=[tuple([x,x]) for x in range(1,13)]
role_id=[tuple([1,"    TEACHER    "]) , tuple([2,"    STUDENT    "])]

class MyUserCreationForm(UserCreationForm):
    """Public sign-up. Always creates a student.

    role_id is deliberately not a field here. It used to be, and because this
    form backs the public /temp_sign_up page, anyone could register choosing
    the TEACHER role and immediately reach the question bank, every answer key,
    exam creation and the analytics pages. Teacher accounts are created by an
    administrator instead, through the Django admin.
    """

    STUDENT_ROLE = 2

    class Meta(UserCreationForm):
        model = User
        fields = ('email_id', 'username', 'first_name', 'last_name', 'mobile_no',)

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set on the instance rather than trusted from the request, so a crafted
        # POST cannot grant itself the teacher role.
        user.role_id_id = self.STUDENT_ROLE
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user

class MyUserChangeForm(UserChangeForm):

    class Meta(UserChangeForm):
        model = User
        fields = ('email_id',)

class class_stu_tech_form(forms.ModelForm):
    class Meta:
        model = class_stu_tech
        fields= ('class_stu_tech' , )
        #widgets={
        #    'class_stu_tech' : forms.TextInput(attrs={'class':'form-control'}),
        #}

class Add_Question_Form(ModelForm):
    class Meta:
        model=ques_table
        fields="__all__"

class Exam_Detail_Form(ModelForm,forms.Form):
    class_= forms.ChoiceField(choices=class_stu)
    class Meta:
        model=exam_details
        fields=('exam_code', 'exam_title' , 'date' ,'start_time' ,'duration' ,'no_of_ques' , 'max_marks' , 'course_id' ,)

class Change_Date_Form(ModelForm):
    class Meta:
        model=exam_details
        fields=('date',)

class Change_Duration_Form(ModelForm):
    class Meta:
        model=exam_details
        fields=('duration',)

class  Change_Start_Time_Form(ModelForm):
    class Meta:
        model=exam_details
        fields=('start_time',)

class Ques_Setup_Form(ModelForm):
    class Meta:
        model=ques_table
        fields=('ques', 'option1', 'option2' , 'option3' , 'option4' , 'correct' , 'marks' ,)

class  Change_Mobile_No_Form(ModelForm):
    class Meta:
        model=User
        fields=('mobile_no',)

class Query_Form(ModelForm):
    class Meta:
        model=query_table
        fields=('query',)

class Notes_Form(ModelForm):
    class Meta:
        model=notes_table
        fields=('notes',)
