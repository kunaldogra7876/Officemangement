from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import CustomUser, Profile
from django.core.mail import send_mail
from django.conf import settings

@receiver(post_save, sender= CustomUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user = instance)

@receiver(post_save, sender= CustomUser)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()

@receiver(post_save, sender=CustomUser)
def send_mail_create(sender, instance, created, **kwargs):
    if created:
        send_mail(
            "Welcome",
            "Your account sucessfully created.",
            settings.EMAIL_HOST_USER,
            [instance.email]
            
        )
        # print("----------------------------")
        # print('|     ',instance.email,'   |')
        # print('|                          |')
        # print('|                          |')
        # print('|                          |')
        # print("----------------------------")
