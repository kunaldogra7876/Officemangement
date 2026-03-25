from .models import CustomUser, Role, UserRole, Skills, Department, Profile
from rest_framework import serializers
from .models import CustomUser, LeaveRequest
from rest_framework.validators import UniqueValidator
import re
from datetime import date


class RegisterSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=CustomUser.objects.all())])
    username = serializers.CharField(required=True, validators=[UniqueValidator(queryset=CustomUser.objects.all())])
    password = serializers.CharField(write_only=True, required=True,style={'input_type': 'password'})
    department = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'department']

    def validate_username(self, value):

        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        if " " in value:
            raise serializers.ValidationError("Username can't contain spaces.")
        
        if len(value) > 30:
            raise serializers.ValidationError("Username is too long.")
        
        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError("Username must contain at least one number.")
        
        return value

    def validate_email(self, value):

        if len(value) < 5:
            raise serializers.ValidationError("invalid email")

        if len(value) > 250:
            raise serializers.ValidationError("invalid email") 
        
        if value.startswith("_"):
            raise serializers.ValidationError("email not starts with _")
        
        if value.startswith("-"):
            raise serializers.ValidationError("email not starts with -")
        
        if "@" not in value and "." not in value:
            raise serializers.ValidationError("invalid email.")
        
        if any (char.isupper() for char in value):
            raise serializers.ValidationError("invalid email")
        
        return value

    def validate_password(self, value):
        
        if len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters long.")
        
        if len(value) > 128:
            raise serializers.ValidationError("Password is too long.")

        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")

        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")

        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError("Password must contain at least one number.")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise serializers.ValidationError("Must contain at least one special character.")

        return value

    def validate(self, data):
        if data['username'] == data['password']:
            raise serializers.ValidationError("Username and password cannot be the same.")
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(min_length=6, max_length=6)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class SkillsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skills
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = ["id", "user", "role"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['user'] = {"id": instance.user.id, "username": instance.user.username, "email": instance.user.email}
        rep['role'] = {"id": instance.role.id, "name": instance.role.name}
        return rep


class CustomUserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    skill_names = serializers.StringRelatedField(source="skills", many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "is_hr_approved", "department", "department_name", "skill_names"]


class ProfileSerializer(serializers.ModelSerializer):
    hours_worked = serializers.ReadOnlyField(source='working_hours')
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Profile
        fields = ['id', 'username', 'login_time', 'logout_time', 'date', 'work_status', 'hours_worked']


class HRUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'department', 'skills']

    def update(self, instance, validated_data):
        skills = validated_data.pop('skills', None)
        instance = super().update(instance, validated_data)
        if skills is not None:
            instance.skills.set(skills)
        return instance
    

class LeaveSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    total_days = serializers.ReadOnlyField()

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'user_name', 'leave_type', 'start_date', 
            'end_date', 'reason', 'status', 'applied_on', 'total_days'
        ]
        read_only_fields = ['status', 'applied_on']

    def validate(self, data):
        """
        Check that start_date is not in the past and end_date is after start_date.
        """
        if data['start_date'] < date.today():
            raise serializers.ValidationError({"start_date": "You cannot apply for leave in the past."})
            
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError({"end_date": "End date must be after the start date."})
            
        return data