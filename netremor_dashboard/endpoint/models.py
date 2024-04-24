from django.db import models
from django.contrib import admin
from django.utils import timezone
from django.conf import settings
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
        if self.birth_year is None:
            return 0
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
    
class Datafile(models.Model):
    def __str__(self):
        return self.name
    
    record              = models.ForeignKey("Record", models.CASCADE)
    name                = models.CharField(max_length=255)
    sensor              = models.CharField(max_length=20, choices=settings.SENSOR_CHOICES, null=True) 
    delta_t             = models.PositiveIntegerField(null=True)
    timestamp_threshold = models.PositiveIntegerField(null=True)
    timestamp_colname   = models.CharField(max_length=255, null=True)
    initial_timestamp   = models.PositiveBigIntegerField(null=True)
    final_timestamp     = models.PositiveBigIntegerField(null=True)
    separator           = models.CharField(max_length=10, null=True)
    is_processed        = models.BooleanField(default=False)
    
class Imufile(models.Model):
    record            = models.ForeignKey("Record", models.CASCADE, null=True)
    datafile          = models.ForeignKey("Datafile", models.CASCADE, null=True)
    name              = models.CharField(max_length=255)
    sensor            = models.CharField(max_length=20, choices=settings.SENSOR_CHOICES, null=True) 
    initial_timestamp = models.PositiveBigIntegerField()
    final_timestamp   = models.PositiveBigIntegerField()
    
class Spectrogram(models.Model):
    datafile = models.ForeignKey("Datafile", models.CASCADE)
    name = models.CharField(max_length=255)
    
class Task(models.Model):
    def __str__(self):
        return self.name

    id          = models.CharField(max_length=255, primary_key=True)
    name        = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True)


class Datafile_task_rel(models.Model):
    """
    Relate information from Task, Datafile and Record.
    - How many tasks are carried out in a record.
    - Which task belongs to which datafile.
    - Which trial of an ambulatory record a task is.
    - When the task starts and ends in a continuous record.
    """
    record    = models.ForeignKey("Record", models.CASCADE)
    datafile  = models.ForeignKey("Datafile", models.CASCADE)
    task      = models.ForeignKey("Task", models.CASCADE)
    trial     = models.IntegerField(null=True)
    starts_at = models.PositiveBigIntegerField(null=True)
    ends_at   = models.PositiveBigIntegerField(null=True)

@receiver(post_delete)
def signal_data_file_deleted(sender, instance, using, **kwargs):
    """When a Datafile or Imufile object is deleted, delete its corresponding file in the system.

    Args:
        instance: Datafile or Imufile instance that has been deleted.
    """

    if isinstance(instance, Datafile):
        dirname = settings.DATAFILES_DIR
        
    elif isinstance(instance, Imufile):
        dirname = settings.IMUFILES_DIR
        
    else:
        return
    
    filepath = os.path.join(dirname, instance.name)
    if os.path.isfile(filepath):
        os.remove(filepath)
