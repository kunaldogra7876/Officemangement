


from django.contrib import admin
from django.urls import path, include
from accounts.views import LoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # App URLs
    path('', include('accounts.urls')),

    # Chat
    path('chat/', include('chat.urls')),

    # Allauth (IMPORTANT)
    path('accounts/', include('allauth.urls')),

    path("", LoginView.as_view(), name= "login-root")

]