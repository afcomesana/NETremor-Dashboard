from django.test import TestCase
from .models import Subject

import utils

class SubjectTestCase(TestCase):
    
    subject = Subject.objects.create(**{field.name: None for field in Subject._meta.fields})