from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

class Verification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=settings.VERIFICATION_CODE_LENGTH)
    is_verified = models.BooleanField(default=False)
