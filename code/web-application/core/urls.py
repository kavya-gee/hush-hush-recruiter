from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('candidate-login/', views.candidate_login, name='candidate_login'),
    path('manager-login/', views.manager_login, name='manager_login'),
    path('candidate-dashboard/', views.candidate_dashboard, name='candidate_dashboard'),
    path('manager-dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('add-candidate/', views.add_candidate, name='add_candidate'),
    path('invite-assessment/<int:candidate_id>/', views.invite_assessment, name='invite_assessment'),
    path('candidate/assessment/accept/<int:assessment_id>/', views.accept_assessment_invite, name='accept_assessment_invite'),
    path('candidate/assessment/start/<str:token>/', views.start_assessment, name='start_assessment'),
    path('candidate/assessment/choose-question/<str:token>/', views.choose_assessment_question,
         name='choose_assessment_question'),
    path('candidate/assessment/view/<str:token>/', views.view_assessment, name='view_assessment'),
    path('candidate/assessment/submit/<str:token>/', views.submit_assessment, name='submit_assessment'),
    path('candidate/assessment/save-code/<str:token>/', views.save_code, name='save_code'),
    path('assessment/<int:assessment_id>/evaluate/', views.trigger_evaluation, name='trigger_evaluation'),
    path('api/assessment/<int:assessment_id>/status/', views.check_evaluation_status, name='check_evaluation_status'),
    path('candidates/<int:candidate_id>/', views.view_candidate, name='view_candidate'),
    path('candidates/<int:candidate_id>/edit/', views.edit_candidate, name='edit_candidate'),
    path('assessments/<int:assessment_id>/resend/', views.resend_assessment, name='resend_assessment'),
    path('assessments/<int:assessment_id>/', views.manager_assessment_detail, name='manager_assessment_detail'),
    path('assessments/<int:assessment_id>/feedback/', views.save_feedback, name='save_feedback'),
    # Add these URL patterns
    path('candidates/<int:candidate_id>/decision/<str:decision>/', views.finalize_interview_decision, name='finalize_interview_decision'),
    path('api/candidates/<int:candidate_id>/decision/', views.interview_decision_ajax, name='interview_decision_ajax'),
]