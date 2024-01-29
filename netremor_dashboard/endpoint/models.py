from django.db import models
from django.contrib import admin
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from utils import get_random_string
from django.db.models.signals import post_delete
from django.dispatch import receiver

import os
import datetime

class Subject(models.Model):
    def __str__(self):
        return self.name if self.name != None else str(self.id)
    
    GENDER_CHOICES = [
        ("male", "Hombre"),
        ("female", "Mujer"),
    ]
        
    DOMINANT_HAND_CHOICES = [
        ("left", "Izquierda"),
        ("right", "Derecha"),
    ]
    
    id                 = models.CharField(max_length=64, primary_key=True)
    name               = models.CharField(max_length=255, null=True)
    gender             = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True)
    birth_year         = models.PositiveIntegerField(null=True)
    illness_start_year = models.PositiveIntegerField(null=True)
    dominant_hand      = models.CharField(max_length=10, choices=DOMINANT_HAND_CHOICES, null=True)
    diagnosis          = models.TextField(null=True)
    
    def age(self):
        return datetime.datetime.today().year - self.birth_year
    # @admin.display(
    #     boolean=True,
    #     ordering="birth_year",
    #     description="Is the subject retired?"
    # )
    # def is_retired(self):
    #     return self.birth_year - datetime.datetime.now().year > 65
    
    
class Record(models.Model):
    def __str__(self):
        return "%s (%s)" % (self.subject.name, self.get_type_display())
    
    RECORD_TYPES = [
        ("ambulatory", "Ambulatory"),
        ("continuous", "Continuous"),
        ("finger_tap", "Finger Tap")
    ]
    
    subject  = models.ForeignKey("Subject", on_delete=models.CASCADE)
    type     = models.CharField(max_length=20, choices=RECORD_TYPES)
    added_on = models.DateTimeField(default=timezone.now)
    
class DataFile(models.Model):
    def __str__(self):
        return self.name
    
    record           = models.ForeignKey("Record", models.CASCADE)
    name             = models.CharField(max_length=255)
    sensor           = models.CharField(max_length=20, choices=settings.SENSOR_CHOICES, null=True)
    task_id          = models.CharField(max_length=255, null=True)
    task_name        = models.CharField(max_length=255, null=True)
    task_description = models.TextField(null=True)
    trial            = models.IntegerField(null=True)
    

@receiver(post_delete, sender=DataFile)
def signal_data_file_deleted(sender, instance, using, **kwargs):
    """When a DataFile object is deleted, delete its corresponding file in the system.

    Args:
        instance: the DataFile instance that has been deleted.
    """
    data_file_path = os.path.join(settings.DATA_FILES_DIR, instance.name)
    if os.path.isfile(data_file_path):
        os.remove(data_file_path)
    
class Verification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=256, default=get_random_string(settings.VERIFICATION_CODE_LENGTH))
    is_verified = models.BooleanField(default=False)
