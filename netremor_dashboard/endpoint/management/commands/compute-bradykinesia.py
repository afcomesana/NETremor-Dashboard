from typing import Any
from django.core.management.base import BaseCommand, CommandError
from endpoint.models import Subject, Record
from django.conf import settings

import utils
import endpoint.utils as endpoint

class Command(BaseCommand):
    def handle(self, *args, **options):
        endpoint.compute_bradykinesia("905fc1af54a90c358821ef9ca04e6b40767d90dc4ee7c0a53c466fee98bc5029")