from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
import random
from datetime import timedelta
from django.utils import timezone
from datetime import datetime
# Create your models here.


class CustomUserManager(BaseUserManager):

    def create_user(self, email, password, username, **extra_fields):
        if not email:
            raise ValueError("invalid email")
        
        email = self.normalize_email(email)
        user = self.model(email= email, username= username, **extra_fields)
        user.set_password(password)
        user.save()

        return user
    
    def create_superuser(self, email, password, username, **extra_fields):

        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)

        if extra_fields.get("is_active") is not True:
            raise ValueError("SuperUser must have is_active=True")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("SuperUser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("SuperUser must have is_superuser=True")
        return self.create_user(email, password, username, **extra_fields)
    

class Department(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name
    

class Skills(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Role(models.Model):
    ROLE_CHOICE= (
        ("HR", "HR"),
        ("EMP", "Employee"),
    )
    name = models.CharField(max_length=20, choices=ROLE_CHOICE, unique=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_hr_approved = models.BooleanField(default=False)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    skills = models.ManyToManyField('Skills', blank=True)
    otp = models.PositiveIntegerField(null=True, blank=True)
    otp_expire = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_employees')
    is_deleted = models.BooleanField(default=False)

    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False 
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.is_active = True  
        self.deleted_at = None
        self.save()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    @property
    def is_hr(self):
       
        return UserRole.objects.filter(user=self, role__name="HR").exists()

    def __str__(self):
        return self.email
    
    def generate_otp(self):
        self.otp = random.randint(100000, 999999)
        self.otp_expire= timezone.now() + timedelta(minutes=10)
        self.otp_verified = False
        self.save()


class UserRole(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"
    

class Profile(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    login_time = models.TimeField(blank=True, null=True)
    logout_time = models.TimeField(blank=True, null=True)
    date = models.DateField(auto_now_add=True) 
    work_status = models.TextField(null=True, blank=True)
    

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.email} Profile"
    
    def working_hours(self):
        if self.login_time and self.logout_time:

            current_date = self.date or timezone.localtime(timezone.now()).date()
            login_dt = datetime.combine(current_date, self.login_time)
            logout_dt = datetime.combine(current_date, self.logout_time)

            duration = logout_dt - login_dt
            total_seconds = int(duration.total_seconds())
            
            if total_seconds < 0:
                return "0h 0m"

            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        
        return "N/A"
    
class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('CL', 'Casual Leave'),
        ('SL', 'Sick Leave'),
        ('PL', 'Paid Leave'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=2, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    applied_on = models.DateTimeField(auto_now_add=True)

    def total_days(self):
        return (self.end_date - self.start_date).days + 1
    