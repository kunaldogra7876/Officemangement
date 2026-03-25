from django.shortcuts import get_object_or_404, redirect, render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework import status
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import timezone
from datetime import date
from .models import CustomUser, UserRole, Skills, Department, Profile, Role, LeaveRequest
from .serializers import RegisterSerializer, ProfileSerializer, DepartmentSerializer, SkillsSerializer, ForgotPasswordSerializer, ResetPasswordSerializer, HRUpdateSerializer, VerifyOTPSerializer, LeaveSerializer
from django.contrib import messages
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from django.http import HttpResponse
from django.db.models import Count
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q, Count
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
# import pandas as pd
from django.urls import reverse
from django.contrib.auth.hashers import make_password


class RegisterView(APIView):
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    template_name = 'register.html'

    def get(self, request):
        if request.user.is_authenticated and not (request.user.is_superuser or request.user.is_hr):
            return redirect('profile-list')
        
        if not (request.user.is_authenticated and (request.user.is_superuser or request.user.is_hr)):
            return render(request, 'restricted_access.html', status=403)
        return Response({'serializer': RegisterSerializer()}, template_name=self.template_name)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            raw_password = request.data.get('password')
            
            user = serializer.save()
            user.is_active = True 
            
            if request.user.is_superuser:
                hr_role, _ = Role.objects.get_or_create(name="HR")
                UserRole.objects.get_or_create(user=user, role=hr_role)
                user.save()

                self.send_welcome_email(user, raw_password, "HR Admin")

                return Response({"message": f"HR Admin account created! Credentials sent to {user.email}. Redirecting..."}, status=201)
            
            elif request.user.is_hr:
                emp_role, _ = Role.objects.get_or_create(name="EMP")
                UserRole.objects.get_or_create(user=user, role=emp_role)
                user.created_by = request.user 
                user.is_hr_approved = True
                user.save()

                self.send_welcome_email(user, raw_password, "Employee")
                
                return Response({"message": f"Employee {user.username} registered! Email sent. Redirecting..."}, status=201)

        return Response(serializer.errors, status=400)

    def send_welcome_email(self, user, password, role_name):
        subject = f"Welcome to OfficeHub - Your {role_name} Credentials"
        login_url = f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/login/"

        html_content = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
            <h2 style="color: #1e293b; text-align: center;">OfficeHub Management</h2>
            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 20px 0;">
            <p>Hello <strong>{user.username}</strong>,</p>
            <p>Your account as an <strong>{role_name}</strong> has been created. You can now log in using   the credentials below:</p>
            
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; margin: 20px 0; border: 1px solid #cbd5e1;">
                <p style="margin: 5px 0;"><strong>Login Email:</strong> {user.email}</p>
                <p style="margin: 5px 0;"><strong>Password:</strong> <code style="background: #e2e8f0; padding: 2px 4px;">{password}</code></p>
            </div>
            <div style="text-align: center;">
                <a href="{login_url}" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Login to OfficeHub</a>
            </div>
            <p style="font-size: 11px; color: #64748b; margin-top: 30px; text-align: center;">
                Security Note: Please change your password immediately after logging in for the first time.
            </p>
        </div>
        """
        send_mail(
            subject,
            f"Your {role_name} login: {user.email} / Password: {password}",
            settings.EMAIL_HOST_USER,
            [user.email],
            html_message=html_content,
            fail_silently=False,
        )
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def approve_user(request, user_id):
    if not request.user.is_hr:
        return HttpResponse("Unauthorized: Only HR can approve users.", status=403)

    user_to_approve = get_object_or_404(CustomUser, id=user_id)
    
    if user_to_approve.is_active and user_to_approve.created_by:
        return HttpResponse("This user has already been claimed by another HR.")

    user_to_approve.is_active = True
    user_to_approve.is_hr_approved = True
    user_to_approve.created_by = request.user 
    user_to_approve.save()
    
    return HttpResponse(f"User {user_to_approve.username} is now under your management.")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reject_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    
    user.is_active = False
    user.is_deleted = True 
    user.created_by = request.user 
    user.save()
    
    return HttpResponse(f"<h1>User Rejected</h1><p>{user.username} has been deactivated.</p>")


class LoginView(APIView):
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    template_name = 'login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('profile-list')
        return Response({})

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if getattr(user, 'is_deleted', False):
                return Response({"message": "Your account has been deactivated by HR."}, status=status.HTTP_403_FORBIDDEN)
            
            login(request, user)
            
            if request.accepted_renderer.format == 'html':
                return redirect('profile-list') 
            
            return Response({"message": "Login successful"}, status=status.HTTP_200_OK)
        
        return Response({"message": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)


class ProfileAPIView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'profile_list.html'

    def get(self, request):
        if getattr(request.user, 'is_deleted', False):
            logout(request) 
            return redirect('login')

        profiles = Profile.objects.filter(user=request.user, user__is_deleted=False).order_by('-date')

        serializer = ProfileSerializer(profiles, many=True)
        
        if request.accepted_renderer.format == 'html':
            return Response({'profiles': profiles, }, template_name=self.template_name)
        
        return Response(serializer.data)
    

class LoginAttendence(APIView):
    def post(self, request):
        today = timezone.localtime(timezone.now()).date()
        profile = Profile.objects.filter(user=request.user, date=today).first()

        if profile and profile.login_time:
            return Response({"status": "error", "message": "You are already punched in for today."}, status=400)

        if not profile:
            profile = Profile.objects.create(user=request.user, date=today)

        profile.login_time = timezone.localtime(timezone.now()).time()
        profile.save()
        
        return Response({"status": "success", "message": f"Punched in at {profile.login_time.strftime('%H:%M')} IST"}, status=200)
    

class LogoutAttendence(APIView):
    def post(self, request):
        today = timezone.localtime(timezone.now()).date()
        profile = Profile.objects.filter(user=request.user, date=today).first()

        if not profile or not profile.login_time:
            return Response({"status": "error", "message": "Error: You must Punch In first before you can Punch Out!"}, status=400)

        if profile.logout_time:
            return Response({"status": "error", "message": "You have already punched out for today."}, status=400)

        profile.logout_time = timezone.localtime(timezone.now()).time()
        profile.save()
        
        work_time = profile.working_hours()
        return Response({"status": "success", "message": f"Punched out! Total work duration: {work_time}"}, status=200)


class HRApproval(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        
        user.is_active = True
        user.save()
        
        return HttpResponse(f"""
            <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                <h1 style="color: #16a34a;">User Approved!</h1>
                <p>Employee <strong>{user.username}</strong> is now active and can log in.</p>
                <a href="/login/" style="color: #2563eb;">Go to Login Page</a>
            </div>
        """)
    

class DepartmentAPIView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'management.html'

    def get(self, request):
        depts = Department.objects.all()
        serializer = DepartmentSerializer(depts, many=True)
        return Response({'departments': serializer.data, 'type': 'department'})

    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class SkillsAPIView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'management.html'

    def get(self, request):
        skills = Skills.objects.all()
        serializer = SkillsSerializer(skills, many=True)
        return Response({'skills': serializer.data, 'type': 'skill'})

    def post(self, request):
        serializer = SkillsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    

class LogoutView(APIView):

    def get(self, request):
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        return redirect('login')
    

class ForgotPasswordView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'forgot_password.html'

    def get(self, request):
        return Response()

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = get_object_or_404(CustomUser, email=email)
            user.generate_otp()
            
            send_mail(
                subject="Forgot Password OTP",
                message=f"Your OTP is: {user.otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            return Response({"message": "OTP sent to your email.", "next_url": f"/reset-password/?email={email}"}, status=200)
            
        return Response(serializer.errors, status=400)
    

class ResetPasswordView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'enter_otp.html'

    def get(self, request):
        email = request.GET.get('email', '')
        return Response({'email': email})

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():

            return Response(serializer.errors, status=400)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        user = get_object_or_404(CustomUser, email=email)

        if str(user.otp).strip() == str(otp).strip():
            return Response({
                "next_url": f"/set-new-password/?email={email}&otp={otp}"
            }, status=200)
        
        return Response({"otp": ["Invalid OTP"]}, status=400)


class FinalResetPasswordView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'new_password.html'

    def get(self, request):
        return Response({
            'email': request.GET.get('email', ''),
            'otp': request.GET.get('otp', '')})

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        user = get_object_or_404(CustomUser, email=email)
        
        if not any(char.isdigit() for char in new_password):
            return Response({"message": "Password must have Digits!"}, status=400)

        if str(user.otp).strip() == str(otp).strip():
            user.set_password(new_password)
            user.otp = None  
            user.save()
            return Response({"message": "Password updated successfully!"}, status=200)
            
        return Response({"otp": ["Session expired or invalid OTP."]}, status=400)


class CheckUsernameView(APIView):

    def get(self, request):
        username = request.GET.get('username')

        if not username:
            return Response({"error": "Username required"}, status=400)

        exists = CustomUser.objects.filter(username=username).exists()

        return Response({"available": not exists})
    

class HRUserManagementView(UserPassesTestMixin, APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'hr_manage_employees.html' 
    permission_classes = [IsAuthenticated]

    def test_func(self):
        return self.request.user.is_hr

    def get(self, request):
        show_deleted = request.GET.get('show_deleted') == 'true'
        base_query = CustomUser.objects.filter(created_by=request.user)
        
        if show_deleted:
            employees = base_query.filter(is_deleted=True)
        else:
            employees = base_query.filter(is_deleted=False, is_active=True)
            
        employees = employees.select_related('department').prefetch_related('skills')
        
        departments = Department.objects.all()
        all_skills = Skills.objects.all()
        
        chart_data = Department.objects.annotate(emp_count=Count('customuser', filter=Q(customuser__created_by=request.user, customuser__is_deleted=False))
        ).values('name', 'emp_count')
        
        return Response({'employees': employees, 
                         'departments': departments,
                         'all_skills': all_skills,
                         'chart_data': list(chart_data),
                         'showing_deleted': show_deleted
                        })

    def post(self, request):
        user_id = request.data.get('user_id')
        action = request.data.get('action') 
        
        user_instance = get_object_or_404(CustomUser, id=user_id, created_by=request.user)

        if action == 'soft_delete':
            user_instance.soft_delete()
            messages.warning(request, f"Employee {user_instance.username} moved to archive.")
        
        elif action == 'restore':
            user_instance.restore()
            messages.success(request, f"Employee {user_instance.username} restored to active list.")
        
        elif action == 'update':
            serializer = HRUpdateSerializer(user_instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                messages.success(request, f"Details updated for {user_instance.username}.")
            else:
                return Response(serializer.errors, status=400)
                
        return redirect('hr_management')
    

class ChangePasswordView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'change_password.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return render(request, 'restricted_access.html', status=403)
        return Response({})

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        errors = {}
        if not old_password: errors['old_password'] = "Current password is required."
        if not new_password: errors['new_password'] = "New password is required."
        if not confirm_password: errors['confirm_password'] = "Please confirm your password."
        
        if errors:
            return Response(errors, status=400)

        if not user.check_password(old_password):
            return Response({'old_password': ['Current password is incorrect.']}, status=400)

        if new_password != confirm_password:
            return Response({'confirm_password': ['Passwords do not match.']}, status=400)

        if len(new_password) < 8:
            return Response({'new_password': ['Must be at least 8 characters long.']}, status=400)
        
        valid_complexity = (
            any(char.isdigit() for char in new_password) and
            any(char.isupper() for char in new_password) and
            any(char.islower() for char in new_password)
        )

        if not valid_complexity:
            return Response({
                'new_password': ['Password must contain Uppercase, Lowercase, and Digits.']
            }, status=400)

        user.set_password(new_password)
        user.save()
        
        update_session_auth_hash(request, user)

        return Response({'message': 'Your password has been updated successfully!'}, status=200)
    

class BulkUploadEmployees(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_hr:
            messages.error(request, "Only HR can upload employees.")
            return redirect('hr_management')  

        file = request.FILES.get('file')

        if not file:    
            messages.error(request, "Please select a file.")
            return redirect('hr_management')  

        try:
            import pandas as pd
            df = pd.read_excel(file)

            created = 0
            skipped = []

            for _, row in df.iterrows():
                email = str(row.get('email')).strip()
                username = str(row.get('username')).strip()

                if CustomUser.objects.filter(email=email).exists():
                    skipped.append(email)
                    continue

                CustomUser.objects.create(
                    username=username,
                    email=email,
                    created_by=request.user, 
                    is_active=True,   
                    is_deleted=False, 
                    is_hr_approved=False,      
                    password=make_password("Office@123"), 
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', '')
                )

                created += 1

            if skipped:
                messages.warning(request, f"{created} uploaded, {len(skipped)} skipped (duplicates).")
            else:
                messages.success(request, f"{created} employees uploaded successfully!")

            return redirect('hr_management') 

        except Exception as e:
            messages.error(request, f"Upload failed: {str(e)}")
            return redirect('hr_management')  
        

class LeaveManagementView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'leave_management.html'

    def get(self, request):
        if request.user.is_hr:
            leaves = LeaveRequest.objects.all().order_by('-applied_on')
        else:
            leaves = LeaveRequest.objects.filter(user=request.user).order_by('-applied_on')
        return Response({'leaves': leaves})

    def post(self, request):
        serializer = LeaveSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            messages.success(request, "Leave application submitted successfully!")
            return Response({"message": "Success"}, status=201)
        
        messages.error(request, "Failed to submit leave. Please check the dates.")
        return Response(serializer.errors, status=400)
    

class LeaveActionView(APIView):
    def post(self, request, pk):
        if not request.user.is_hr:
            return Response({"error": "Unauthorized"}, status=403)
            
        leave = get_object_or_404(LeaveRequest, pk=pk)
        action = request.data.get('action') 
        
        leave.status = action
        leave.save()
        
        messages.success(request, f"Leave for {leave.user.username} has been {action}.")
        
        try:
            send_mail(
                "Leave Update",
                f"Your leave from {leave.start_date} has been {action}.",
                settings.EMAIL_HOST_USER,
                [leave.user.email]
            )
        except Exception:
            messages.warning(request, "Leave updated, but email notification failed.")

        return Response({"message": f"Leave {action} successfully!"})
    

class ForgotPassword(APIView):
    
    def post(self, request):
        email = request.POST.get("email")
        password = request.POST.get("password")
        username = request.POST.get("username")

        try:
            user = CustomUser.objects.get(email=email)

        except CustomUser.DoesNotExist:
            return Response({"message": "email is not exists."})
        
        user.generate_otp()
        send_mail(
            "Forgot Password OTP",
            f"{user.otp}",
            "kunaldogra7876@gmail.com",
            False,
            [user.email]
        )
        return Response({"message": "OTP send to the email."})
    
class VerifyOTP(APIView):
    def get(self, request):
        return Response({"message": "OTP matched."})
    
    def post(self, request, id):
        user = get_object_or_404(CustomUser, id=id)
        otp = request.POST.get("otp")

        if otp != str(user.otp):
            return Response({"message": "OTP is not matched."})
        
        else:
            messages.success(request, "OTP matched.")
            return redirect("new_password")
        
class NewPassword(APIView):

    def get(self, request):
        return Response({"message": "password changed successfully."})
    
    def post(self, request, id):
        user = get_object_or_404(CustomUser, id=id)

        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "both password are not same.")
            return redirect("new_password", id=id)
        if len(new_password) > 100:
            messages.warning(request, "password is too long.")
            return redirect('new_password', id=id)
        if len(new_password) < 6:
            messages.warning(request, "password is too short")
            return redirect("new_password", id=id)
        