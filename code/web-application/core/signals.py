from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Candidate, HiringManager
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.is_hiring_manager:
            HiringManager.objects.create(user=instance, company_name="Doodle Gmbh")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.is_candidate and not hasattr(instance, 'candidate_profile'):
        Candidate.objects.create(user=instance)
    if instance.is_hiring_manager and not hasattr(instance, 'hiring_manager_profile'):
        HiringManager.objects.create(user=instance, company_name="Doodle Gmbh")

    if hasattr(instance, 'candidate_profile'):
        instance.candidate_profile.save()
    if hasattr(instance, 'hiring_manager_profile'):
        instance.hiring_manager_profile.save()