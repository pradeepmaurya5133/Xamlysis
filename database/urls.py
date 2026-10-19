from django.urls import path
from database import views
from database import exam_views
from database import question_bank
from database import csv_import
from database import analytics
from django.contrib import admin

urlpatterns = [
    path('', views.home , name="home"),
    path('about/' , views.about , name='about'),
    path('features/' , views.features , name='features'),
    path('how_it_works/' , views.how_it_works , name='how_it_works'),
    path('faq/' , views.faq , name='faq'),
    path('contact/' , views.contact , name='contact'),
    path('courses/' , views.courses , name='courses'),
    path('change_setting/' , views.change_setting , name='change_setting'),
    path('chat_bot/' ,views.chat_bot , name='chat_bot'),
    path('login' , views.login , name='login' ),
    path('logout' , views.logout , name='logout' ),
    path('query_page/' , views.query_page ,name='query_page'),
    path('add_notes/' , views.add_notes ,name='add_notes'),
    path('sign_up/' , views.sign_up , name='sign_up'),
    path('student_exams_scheduled/' , views.stu_future , name='stu_future'),
    
    path('stu_home/' , views.stu_home , name='stu_home'),
    path('login/stu_home/' , views.stu_home , name='stu_home'),

    path('student_home_page/' , views.stu_home , name='stu_home'),
    path('student_login/' , views.stu_login , name='stu_login'),
    path('student_previous_exams/' , views.stu_prev , name='stu_prev'),
    path('student_sign_up/' , views.stu_sign_up , name='stu_sign_up'),
    path('teachers_future_exam_scheduled/' , views.teach_future, name='teach_future'),
    path('teachers_home/' , views.teach_home , name='teach_home'),
    path('teachers_login/' , views.teach_login , name='teach_login'),
    path('teachers_previous_exams_scheduled/' , views.teach_prev , name='teach_prev'),
    path('teachers_schedule/' , views.teach_schedule , name='teach_schedule'),
    path('teachers_sign_up/' , views.teach_sign_up , name='teach_sign_up'),
    #added for checking
    path('check/',views.base1,name="base1"),

    path('add_course/',views.add_course,name="add_course"),
    path('remove_course/',views.remove_course,name="remove_course"),
    path('add_class/',views.add_class,name="add_class"),
    path('remove_class/',views.remove_class,name="remove_class"),

    path('temp_sign_up' ,views.temp_sign_up , name="temp_sign_up"),
    path('course_select', views.course_select,name='course_select'),
    path('class_select/', views.class_select,name='class_select'),
    #path('delete/<int:primry_key>/' ,views.delete_data , name="deletedata"),
    #path('update/<int:primry_key>/' ,views.update_data , name="updatedata"),
    path('quiz/', views.quiz,name='quiz'),
    path('exam_detail' , views.exam_detail , name="exam_detail"),
    path('ques_setup' , views.ques_setup , name="ques_setup"),
    
    path('course_select/', views.course_select,name='course_select'),
    path('show',views.show),
    path('test/',views.test),
    path('returner/',views.returner),
    path('correct_ans/',views.correct_ans),

    path('index/' , views.index , name="index" ),

    # Exam engine. The legacy /test/ route above now redirects into this flow,
    # so there is one way to sit an exam rather than two.
    path('dashboard/', exam_views.student_dashboard, name='student_dashboard'),

    # Staff question bank.
    path('staff/analytics/', analytics.analytics_overview, name='analytics_overview'),
    path('staff/analytics/exam/<str:exam_code>/', analytics.analytics_exam, name='analytics_exam'),
    path('staff/analytics/student/<str:email>/', analytics.analytics_student, name='analytics_student'),
    path('staff/questions/', question_bank.question_bank, name='question_bank'),
    path('staff/questions/new/', question_bank.question_create, name='question_create'),
    path('staff/questions/import/', csv_import.question_import, name='question_import'),
    path('staff/questions/import/confirm/', csv_import.question_import_confirm, name='question_import_confirm'),
    path('staff/questions/<str:ques_id>/', question_bank.question_preview, name='question_preview'),
    path('staff/questions/<str:ques_id>/edit/', question_bank.question_edit, name='question_edit'),
    path('exams/', exam_views.exam_catalogue, name='exam_catalogue'),
    path('exams/history/', exam_views.exam_history, name='exam_history'),
    path('exams/<str:exam_code>/start/', exam_views.start_attempt, name='exam_start'),
    path('exams/attempt/<int:attempt_id>/', exam_views.take_exam, name='exam_take'),
    path('exams/attempt/<int:attempt_id>/save/', exam_views.save_answer, name='exam_save_answer'),
    path('exams/attempt/<int:attempt_id>/submit/', exam_views.submit_attempt, name='exam_submit'),
    path('exams/attempt/<int:attempt_id>/result/', exam_views.exam_result, name='exam_result'),
]
