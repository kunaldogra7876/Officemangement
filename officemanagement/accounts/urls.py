from django.urls import path
from .views import RegisterView, LoginView, LogoutView, ProfileAPIView, LoginAttendence, LogoutAttendence, HRApproval, DepartmentAPIView, SkillsAPIView, ForgotPasswordView, ResetPasswordView, HRUserManagementView, CheckUsernameView, BulkUploadEmployees, FinalResetPasswordView, LeaveActionView, LeaveManagementView
from . import views

urlpatterns = [

    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profiles/', ProfileAPIView.as_view(), name='profile-list'),
    path('profiles/<int:pk>/', ProfileAPIView.as_view(), name='profile-detail'),
    path('punch-in/', LoginAttendence.as_view(), name='punch-in'),
    path('punch-out/', LogoutAttendence.as_view(), name='punch-out'),
    path('approve/<int:user_id>/', HRApproval.as_view(), name='approve-user'),
    path('hr-dashboard/', HRApproval.as_view(), name='hr-dashboard'),
    path('departments/', DepartmentAPIView.as_view(), name='departments'),
    path('skills/', SkillsAPIView.as_view(), name='skills'),
    path('approve/<int:user_id>/', views.approve_user, name='approve_user'),
    path('reject/<int:user_id>/', views.reject_user, name='reject_user'),
    path("hr-update-manager", HRUserManagementView.as_view(), name="hr_management"),
    path('check-username/', CheckUsernameView.as_view(), name='check_username'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('bulk-upload/', BulkUploadEmployees.as_view(), name='bulk_upload'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('set-new-password/', FinalResetPasswordView.as_view(), name='set-new-password'),
    path('leave-management/', LeaveManagementView.as_view(), name='leave-management'),
    path('leave-action/<int:pk>/', LeaveActionView.as_view(), name='leave-action'),
]