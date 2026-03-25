from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.cache import cache
from .models import Message
from accounts.models import CustomUser, UserRole

def get_visible_users(current_user):
    """
    Helper function to get allowed users for the sidebar.
    Keeps logic consistent between index and room views.
    """
    role_obj = UserRole.objects.filter(user=current_user).select_related('role').first()
    current_role = role_obj.role.name if role_obj else "EMP"

    if current_user.is_superuser:
        # Admins see everyone
        users_qs = CustomUser.objects.filter(is_deleted=False)
        
    elif current_role == "HR":
        # HR sees Admins + People they created + other HRs
        users_qs = CustomUser.objects.filter(
            Q(is_superuser=True) | 
            Q(created_by=current_user) | 
            Q(userrole__role__name="HR"),
            is_deleted=False
        ).distinct()
        
    else:
        # Employees see Admins + All HRs + Peers (same manager/HR)
        # Note: we use getattr to safely handle cases where created_by might be None
        manager_id = getattr(current_user.created_by, 'id', None)
        
        users_qs = CustomUser.objects.filter(
            Q(is_superuser=True) | 
            Q(userrole__role__name="HR") | 
            Q(created_by_id=manager_id), 
            is_deleted=False
        ).distinct()
    
    return users_qs.exclude(id=current_user.id)

@login_required
def index(request):
    current_user = request.user
    users_qs = get_visible_users(current_user)

    user_data = []
    for u in users_qs:
        unread = Message.objects.filter(sender=u, receiver=current_user, is_read=False).count()
        is_online = cache.get(f"user_online_{u.id}", False)
        u_role = UserRole.objects.filter(user=u).select_related('role').first()
        
        user_data.append({
            "id": u.id,
            "username": u.username,
            "role": u_role.role.name if u_role else "EMP",
            "is_online": is_online,
            "unread": unread
        })

    return render(request, 'chat/room.html', {
        'users': user_data,
        'selected_user': None, 
        'messages': []
    })

@login_required
def room(request, user_id=None):
    current_user = request.user
    users_qs = get_visible_users(current_user)

    user_data = []
    for u in users_qs:
        unread = Message.objects.filter(sender=u, receiver=current_user, is_read=False).count()
        is_online = cache.get(f"user_online_{u.id}", False)
        u_role = UserRole.objects.filter(user=u).select_related('role').first()
        
        user_data.append({
            "id": u.id,
            "username": u.username,
            "role": u_role.role.name if u_role else "EMP",
            "is_online": is_online,
            "unread": unread
        })

    selected_user = None
    messages = []
    if user_id:
        # Check if user exists AND is in the allowed visible list
        potential_user = get_object_or_404(CustomUser, id=user_id)
        
        # Security check: if user is not in visible list, don't let them chat
        # (Admins are usually included in visible list anyway)
        if users_qs.filter(id=potential_user.id).exists():
            selected_user = potential_user
            Message.objects.filter(sender=selected_user, receiver=current_user).update(is_read=True)
            messages = Message.objects.filter(
                Q(sender=current_user, receiver=selected_user) |
                Q(sender=selected_user, receiver=current_user)
            ).order_by('timestamp')

    return render(request, 'chat/room.html', {
        'users': user_data,
        'selected_user': selected_user,
        'messages': messages
    })